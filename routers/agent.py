"""
Agent router: AI-powered data analysis, PDF export (invoices/quotes), and stock import.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel
import json
import io
import os
import csv

from database import get_db
from models import User, Sale, Purchase, Expense, InventoryItem
from auth import get_current_active_user
from activity import log_activity

router = APIRouter()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ---------------------------------------------------------------------------
# Helper: gather analytics data from DB
# ---------------------------------------------------------------------------

def _gather_analytics(db: Session, period: str = "month") -> dict:
    """Aggregate sales/purchases/expenses for AI context."""
    now = datetime.utcnow()

    if period == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now - timedelta(days=30)

    sales = db.query(Sale).filter(Sale.sale_date >= start).all()
    purchases = db.query(Purchase).filter(Purchase.purchase_date >= start).all()
    expenses = db.query(Expense).filter(Expense.expense_date >= start).all()

    total_revenue = sum(s.total_amount for s in sales)
    total_cogs = sum(p.total_cost for p in purchases)
    total_expenses = sum(e.amount for e in expenses)
    net_profit = total_revenue - total_cogs - total_expenses

    # Daily breakdown (last 30 days)
    daily = {}
    for s in db.query(Sale).filter(Sale.sale_date >= now - timedelta(days=30)).all():
        d = s.sale_date.strftime("%Y-%m-%d")
        daily[d] = daily.get(d, 0) + s.total_amount

    # Monthly breakdown (last 12 months)
    monthly = {}
    for s in db.query(Sale).filter(Sale.sale_date >= now - timedelta(days=365)).all():
        m = s.sale_date.strftime("%Y-%m")
        monthly[m] = monthly.get(m, 0) + s.total_amount

    # Yearly breakdown
    yearly = {}
    for s in db.query(Sale).all():
        y = s.sale_date.strftime("%Y")
        yearly[y] = yearly.get(y, 0) + s.total_amount

    # Top selling items
    item_sales = {}
    for s in sales:
        item_sales[s.item_id] = item_sales.get(s.item_id, 0) + s.total_amount
    top_items = sorted(item_sales.items(), key=lambda x: x[1], reverse=True)[:5]
    top_items_named = []
    for item_id, amount in top_items:
        item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
        top_items_named.append({"name": item.name if item else f"Item #{item_id}", "revenue": amount})

    low_stock = db.query(InventoryItem).filter(
        InventoryItem.quantity <= InventoryItem.reorder_point
    ).all()

    return {
        "period": period,
        "period_start": start.isoformat(),
        "now": now.isoformat(),
        "summary": {
            "total_revenue": total_revenue,
            "total_cogs": total_cogs,
            "total_expenses": total_expenses,
            "net_profit": net_profit,
            "num_sales": len(sales),
            "num_purchases": len(purchases),
            "num_expenses": len(expenses),
        },
        "top_products": top_items_named,
        "low_stock_count": len(low_stock),
        "low_stock_items": [{"name": i.name, "qty": i.quantity, "reorder_at": i.reorder_point} for i in low_stock],
        "daily_sales_last30": dict(sorted(daily.items())),
        "monthly_sales_last12": dict(sorted(monthly.items())),
        "yearly_sales": dict(sorted(yearly.items())),
    }


# ---------------------------------------------------------------------------
# AI Agent Chat Endpoint
# ---------------------------------------------------------------------------

class AgentMessage(BaseModel):
    message: str
    period: Optional[str] = "month"  # day | month | year | all


@router.post("/chat")
async def agent_chat(
    payload: AgentMessage,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """AI agent that analyses business data and answers questions."""
    import httpx

    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured on server.")

    analytics = _gather_analytics(db, payload.period)

    system_prompt = f"""You are Zimbi, an expert business intelligence AI assistant for Zimbermanne Hardware Store — a retail business in Tanzania that operates in TZS (Tanzanian Shilling).

You have access to real-time business data pulled from the store's database. Always format monetary values in TZS with comma separators (e.g. 1,250,000 TZS).

CURRENT BUSINESS DATA ({analytics['period'].upper()} PERIOD: {analytics['period_start'][:10]} to {analytics['now'][:10]}):
{json.dumps(analytics['summary'], indent=2)}

TOP PRODUCTS BY REVENUE:
{json.dumps(analytics['top_products'], indent=2)}

LOW STOCK ALERTS ({analytics['low_stock_count']} items):
{json.dumps(analytics['low_stock_items'], indent=2)}

DAILY SALES TREND (Last 30 days):
{json.dumps(analytics['daily_sales_last30'], indent=2)}

MONTHLY SALES (Last 12 months):
{json.dumps(analytics['monthly_sales_last12'], indent=2)}

YEARLY SALES HISTORY:
{json.dumps(analytics['yearly_sales'], indent=2)}

Your capabilities:
- Compare performance day-by-day, month-by-month, year-by-year
- Identify trends, anomalies, seasonal patterns
- Highlight profit/loss insights
- Alert on low stock and inventory health
- Give actionable business recommendations
- Answer specific questions about the data above

Always be concise, direct, and business-focused. Use bullet points and headers for clarity. Speak in English but you can include Swahili terms where appropriate (e.g. "Deni" for credit/debt, "Faida" for profit, "Hasara" for loss).
"""

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 1024,
                "system": system_prompt,
                "messages": [{"role": "user", "content": payload.message}],
            },
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"AI service error: {resp.text}")

    data = resp.json()
    reply = data["content"][0]["text"] if data.get("content") else "No response."

    return {"reply": reply, "analytics_snapshot": analytics["summary"]}


# ---------------------------------------------------------------------------
# Analytics Comparison Endpoint (no AI, just raw data)
# ---------------------------------------------------------------------------

@router.get("/analytics")
async def get_analytics(
    period: str = Query("month", description="day | month | year"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Return structured analytics for charting."""
    return _gather_analytics(db, period)


@router.get("/compare")
async def compare_periods(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Return day/month/year comparisons in one call."""
    now = datetime.utcnow()

    # Today vs yesterday
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    yesterday_end = today_start

    today_sales = db.query(Sale).filter(Sale.sale_date >= today_start).all()
    yesterday_sales = db.query(Sale).filter(Sale.sale_date >= yesterday_start, Sale.sale_date < yesterday_end).all()

    # This month vs last month
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_end = this_month_start
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)

    this_month_sales = db.query(Sale).filter(Sale.sale_date >= this_month_start).all()
    last_month_sales = db.query(Sale).filter(Sale.sale_date >= last_month_start, Sale.sale_date < last_month_end).all()

    # This year vs last year
    this_year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    last_year_start = this_year_start.replace(year=this_year_start.year - 1)
    last_year_end = this_year_start

    this_year_sales = db.query(Sale).filter(Sale.sale_date >= this_year_start).all()
    last_year_sales = db.query(Sale).filter(Sale.sale_date >= last_year_start, Sale.sale_date < last_year_end).all()

    def rev(sales_list): return sum(s.total_amount for s in sales_list)
    def pct(a, b): return round(((a - b) / b * 100), 1) if b else 0

    today_rev = rev(today_sales)
    yesterday_rev = rev(yesterday_sales)
    this_month_rev = rev(this_month_sales)
    last_month_rev = rev(last_month_sales)
    this_year_rev = rev(this_year_sales)
    last_year_rev = rev(last_year_sales)

    return {
        "daily": {
            "today": {"revenue": today_rev, "transactions": len(today_sales)},
            "yesterday": {"revenue": yesterday_rev, "transactions": len(yesterday_sales)},
            "change_pct": pct(today_rev, yesterday_rev),
        },
        "monthly": {
            "this_month": {"revenue": this_month_rev, "transactions": len(this_month_sales)},
            "last_month": {"revenue": last_month_rev, "transactions": len(last_month_sales)},
            "change_pct": pct(this_month_rev, last_month_rev),
        },
        "yearly": {
            "this_year": {"revenue": this_year_rev, "transactions": len(this_year_sales)},
            "last_year": {"revenue": last_year_rev, "transactions": len(last_year_sales)},
            "change_pct": pct(this_year_rev, last_year_rev),
        },
    }


# ---------------------------------------------------------------------------
# PDF Export: Invoice
# ---------------------------------------------------------------------------

class InvoiceItem(BaseModel):
    description: str
    quantity: float
    unit_price: float


class InvoicePayload(BaseModel):
    invoice_number: str
    date: Optional[str] = None
    customer_name: str
    customer_address: Optional[str] = None
    customer_tin: Optional[str] = None
    items: List[InvoiceItem]
    notes: Optional[str] = None
    type: str = "invoice"  # "invoice" or "quote"


def _build_pdf_bytes(payload: InvoicePayload) -> bytes:
    """Generate a PDF invoice or quote using reportlab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
        from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
    except ImportError:
        raise HTTPException(status_code=503, detail="reportlab not installed. Add 'reportlab' to requirements.txt")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
    )

    NAVY = colors.HexColor("#0F1923")
    GOLD = colors.HexColor("#D4A843")
    LIGHT_GREY = colors.HexColor("#F0EDE6")
    RED = colors.HexColor("#E74C3C")
    GREEN = colors.HexColor("#2ECC71")

    styles = getSampleStyleSheet()
    normal = styles["Normal"]

    title_style = ParagraphStyle("title", fontSize=22, textColor=NAVY, fontName="Helvetica-Bold", spaceAfter=4)
    subtitle_style = ParagraphStyle("sub", fontSize=10, textColor=GOLD, fontName="Helvetica-Bold", spaceAfter=2)
    small_style = ParagraphStyle("small", fontSize=9, textColor=colors.HexColor("#6F7C85"), spaceAfter=2)
    body_style = ParagraphStyle("body", fontSize=10, textColor=NAVY)
    right_style = ParagraphStyle("right", fontSize=10, textColor=NAVY, alignment=TA_RIGHT)
    total_style = ParagraphStyle("total", fontSize=14, textColor=NAVY, fontName="Helvetica-Bold", alignment=TA_RIGHT)

    doc_type = "QUOTE" if payload.type == "quote" else "INVOICE"
    color_accent = colors.HexColor("#2980B9") if payload.type == "quote" else GREEN
    date_str = payload.date or datetime.utcnow().strftime("%d %B %Y")

    story = []

    # Header
    header_data = [
        [
            Paragraph(f"<b>Zimbermanne</b>", title_style),
            Paragraph(f"<b>{doc_type}</b>", ParagraphStyle("dt", fontSize=28, textColor=color_accent, fontName="Helvetica-Bold", alignment=TA_RIGHT)),
        ],
        [
            Paragraph("Hardware & Building Materials", subtitle_style),
            Paragraph(f"#{payload.invoice_number}", ParagraphStyle("inv_no", fontSize=12, textColor=NAVY, fontName="Helvetica-Bold", alignment=TA_RIGHT)),
        ],
        [
            Paragraph("Arusha, Tanzania | +255 000 000 000", small_style),
            Paragraph(f"Date: {date_str}", ParagraphStyle("dt2", fontSize=10, textColor=colors.HexColor("#6F7C85"), alignment=TA_RIGHT)),
        ],
    ]
    header_table = Table(header_data, colWidths=[90*mm, 80*mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=2, color=NAVY, spaceAfter=12))

    # Bill To
    story.append(Paragraph("BILL TO:", subtitle_style))
    story.append(Paragraph(f"<b>{payload.customer_name}</b>", body_style))
    if payload.customer_address:
        story.append(Paragraph(payload.customer_address, small_style))
    if payload.customer_tin:
        story.append(Paragraph(f"TIN: {payload.customer_tin}", small_style))
    story.append(Spacer(1, 8*mm))

    # Items table
    table_data = [["DESCRIPTION", "QTY", "UNIT PRICE (TZS)", "TOTAL (TZS)"]]
    subtotal = 0
    for item in payload.items:
        line_total = item.quantity * item.unit_price
        subtotal += line_total
        table_data.append([
            item.description,
            f"{item.quantity:g}",
            f"{item.unit_price:,.0f}",
            f"{line_total:,.0f}",
        ])

    items_table = Table(table_data, colWidths=[85*mm, 20*mm, 40*mm, 35*mm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2DED5")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 6*mm))

    # Totals
    vat_rate = 0.18
    vat = subtotal * vat_rate
    grand_total = subtotal + vat

    totals_data = [
        ["", "Subtotal:", f"{subtotal:,.0f} TZS"],
        ["", f"VAT (18%):", f"{vat:,.0f} TZS"],
        ["", "GRAND TOTAL:", f"{grand_total:,.0f} TZS"],
    ]
    totals_table = Table(totals_data, colWidths=[85*mm, 55*mm, 35*mm])
    totals_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (1, 2), (-1, 2), "Helvetica-Bold"),
        ("FONTSIZE", (1, 2), (-1, 2), 12),
        ("TEXTCOLOR", (1, 2), (-1, 2), GREEN),
        ("LINEABOVE", (1, 2), (-1, 2), 1, NAVY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(totals_table)

    if payload.notes:
        story.append(Spacer(1, 8*mm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2DED5"), spaceAfter=6))
        story.append(Paragraph("<b>Notes:</b>", body_style))
        story.append(Paragraph(payload.notes, small_style))

    # Footer
    story.append(Spacer(1, 12*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=6))
    story.append(Paragraph("Thank you for your business! | Asante kwa biashara yako!", ParagraphStyle("footer", fontSize=9, textColor=colors.HexColor("#6F7C85"), alignment=TA_CENTER)))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


@router.post("/export/invoice")
async def export_invoice(
    payload: InvoicePayload,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate and return an Invoice or Quote as PDF."""
    pdf_bytes = _build_pdf_bytes(payload)
    doc_type = "Quote" if payload.type == "quote" else "Invoice"
    filename = f"Zimbermanne_{doc_type}_{payload.invoice_number}.pdf"

    await log_activity(
        db=db,
        user=current_user.username,
        action=f"EXPORT_{doc_type.upper()}",
        details=f"Exported {doc_type} #{payload.invoice_number} for {payload.customer_name}",
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Stock Import: CSV / Excel
# ---------------------------------------------------------------------------

@router.post("/import/stock")
async def import_stock(
    file: UploadFile = File(...),
    update_existing: bool = Query(False, description="Update price/reorder if item name already exists"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Import stock from CSV or Excel.
    
    Expected columns (case-insensitive):
      name, quantity, price, category (optional), reorder_point (optional)
    """
    filename = file.filename or ""
    content = await file.read()

    rows = []

    if filename.lower().endswith(".csv"):
        try:
            text = content.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"CSV parse error: {e}")

    elif filename.lower().endswith((".xlsx", ".xls")):
        try:
            import pandas as pd
            df = pd.read_excel(io.BytesIO(content))
            df.columns = [c.strip().lower() for c in df.columns]
            rows = df.to_dict("records")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Excel parse error: {e}")
    else:
        raise HTTPException(status_code=400, detail="Only .csv, .xlsx, or .xls files are supported.")

    # Normalise column names
    normalised = []
    for row in rows:
        normalised.append({k.strip().lower(): v for k, v in row.items()})

    required = {"name", "quantity", "price"}
    if normalised and not required.issubset(normalised[0].keys()):
        missing = required - set(normalised[0].keys())
        raise HTTPException(status_code=400, detail=f"Missing required columns: {missing}. Found: {list(normalised[0].keys())}")

    created = []
    updated = []
    errors = []

    for i, row in enumerate(normalised, start=2):  # row 2 = first data row
        try:
            name = str(row.get("name", "")).strip()
            if not name:
                errors.append({"row": i, "error": "Empty name"})
                continue

            qty = int(float(str(row.get("quantity", 0)).replace(",", "") or 0))
            price = float(str(row.get("price", 0)).replace(",", "") or 0)
            category = str(row.get("category", "") or "").strip() or None
            reorder_point = int(float(str(row.get("reorder_point", 10)).replace(",", "") or 10))

            if price <= 0:
                errors.append({"row": i, "name": name, "error": "Price must be > 0"})
                continue
            if qty < 0:
                errors.append({"row": i, "name": name, "error": "Quantity cannot be negative"})
                continue

            existing = db.query(InventoryItem).filter(InventoryItem.name == name).first()

            if existing:
                if update_existing:
                    existing.quantity += qty
                    existing.price = price
                    existing.category = category or existing.category
                    existing.reorder_point = reorder_point
                    existing.updated_at = datetime.utcnow()
                    db.commit()
                    updated.append(name)
                else:
                    errors.append({"row": i, "name": name, "error": "Item already exists (set update_existing=true to update)"})
            else:
                new_item = InventoryItem(
                    name=name,
                    quantity=qty,
                    price=price,
                    category=category,
                    reorder_point=reorder_point,
                )
                db.add(new_item)
                db.commit()
                db.refresh(new_item)
                created.append(name)

        except Exception as e:
            errors.append({"row": i, "error": str(e)})

    await log_activity(
        db=db,
        user=current_user.username,
        action="IMPORT_STOCK",
        details=f"Imported {filename}: {len(created)} created, {len(updated)} updated, {len(errors)} errors",
    )

    return {
        "status": "complete",
        "file": filename,
        "created": len(created),
        "updated": len(updated),
        "errors": len(errors),
        "created_items": created,
        "updated_items": updated,
        "error_details": errors,
    }


@router.get("/import/template")
async def download_import_template(
    current_user: User = Depends(get_current_active_user)
):
    """Download a CSV template for stock import."""
    header = "name,quantity,price,category,reorder_point\n"
    examples = (
        "PVC Pipe 1/2 Inch,100,2500,Plumbing,20\n"
        "Cement 50kg Bag,50,35000,Building Materials,10\n"
        "Steel Rod 12mm,200,8500,Steel,15\n"
    )
    csv_bytes = (header + examples).encode("utf-8")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="stock_import_template.csv"'},
    )
