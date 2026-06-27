from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from sqlalchemy import func
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, Base, get_db
from models import User, Sale, InventoryItem, Expense, Debtor, Creditor
from auth import get_current_active_user
from activity import log_activity
from routers import auth, inventory, sales, purchases, expenses, reports, users, activity, backup, agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()

app = FastAPI(
    title="Zimbermanne Retail OS Engine",
    description="Advanced Accounting, Debtors, Creditors & POS API",
    version="2.5.0",
    lifespan=lifespan
)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Real, database-backed routers ---
# These existed as files but were never mounted on the app before -- nothing
# under /api/auth, /api/inventory, /api/sales, etc. was actually reachable.
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["inventory"])
app.include_router(sales.router, prefix="/api/sales", tags=["sales"])
app.include_router(purchases.router, prefix="/api/purchases", tags=["purchases"])
app.include_router(expenses.router, prefix="/api/expenses", tags=["expenses"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(activity.router, prefix="/api/activity", tags=["activity"])
app.include_router(backup.router, prefix="/api/backup", tags=["backup"])
app.include_router(agent.router, prefix="/api/agent", tags=["agent"])

# --- REPORTS: backed by the real sales/inventory/expense tables ---

@app.get("/api/reports/daily-summary")
async def get_daily_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    todays_sales = db.query(Sale).filter(
        Sale.sale_date >= today_start, Sale.sale_date < today_end
    ).all()

    items_sold = sum(sale.quantity for sale in todays_sales)
    total_earnings = sum(sale.total_amount for sale in todays_sales)

    top_product_row = (
        db.query(InventoryItem.name, func.sum(Sale.quantity).label("qty_sold"))
        .join(Sale, Sale.item_id == InventoryItem.id)
        .filter(Sale.sale_date >= today_start, Sale.sale_date < today_end)
        .group_by(InventoryItem.name)
        .order_by(func.sum(Sale.quantity).desc())
        .first()
    )
    top_product = top_product_row[0] if top_product_row else None

    low_stock_count = db.query(InventoryItem).filter(
        InventoryItem.quantity <= InventoryItem.reorder_point
    ).count()

    return {
        "date": today_start.strftime("%Y-%m-%d"),
        "items_sold": items_sold,
        "total_earnings_tzs": total_earnings,
        "top_product": top_product,
        "low_stock_count": low_stock_count
    }

# --- DEBTORS & CREDITORS API ENDPOINTS (backed by the debtors/creditors tables) ---

@app.get("/api/ledgers/debtors")
async def get_debtors(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Fetch all outstanding customer and company debts (Deni)"""
    debtors = db.query(Debtor).order_by(Debtor.date_owed.desc()).all()
    return [
        {
            "id": d.id,
            "customer_name": d.name,
            "company": d.company,
            "amount_owed": d.amount,
            "date": d.date_owed.strftime("%Y-%m-%d") if d.date_owed else None,
            "status": d.status.capitalize() if d.status else d.status
        }
        for d in debtors
    ]

@app.post("/api/ledgers/debtors/pay/{debt_id}")
async def pay_debtor(
    debt_id: int,
    amount: float = Body(..., embed=True),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Process a full or partial payment from a debtor"""
    debt = db.query(Debtor).filter(Debtor.id == debt_id).first()
    if not debt:
        raise HTTPException(status_code=404, detail="Debtor record not found")

    debt.amount -= amount
    if debt.amount <= 0:
        debt.amount = 0
        debt.status = "paid"
    else:
        debt.status = "partial"

    db.commit()
    db.refresh(debt)

    await log_activity(
        db=db,
        user=current_user.username,
        action="PAY_DEBTOR",
        details=f"Recorded payment of {amount} for debtor {debt.name} (id={debt.id})"
    )

    return {"status": "Success", "remaining": debt.amount}

@app.get("/api/ledgers/creditors")
async def get_creditors(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Fetch all supplier debts and pending costs (Madeni ya Wauzaji)"""
    creditors = db.query(Creditor).order_by(Creditor.date_owed.desc()).all()
    return [
        {
            "id": c.id,
            "supplier_name": c.name,
            "invoice_no": c.invoice_no,
            "amount_due": c.amount,
            "date": c.date_owed.strftime("%Y-%m-%d") if c.date_owed else None,
            "status": c.status.capitalize() if c.status else c.status
        }
        for c in creditors
    ]

@app.post("/api/sales/checkout")
async def process_checkout(
    payload: dict = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Handles sales transactions, processing both Cash and Credit (Deni) sales against
    the real inventory and sales tables, and creating a debtor record for credit sales."""
    customer_name = payload.get("customer_name", "Walk-In Customer")
    company_name = payload.get("company_name", "Individual")
    payment_mode = payload.get("payment_mode", "Cash")
    items = payload.get("items", [])

    total_bill = 0.0
    created_sales = []

    for item in items:
        qty = item.get("qty", 0)
        unit_price = item.get("price", 0)
        item_id = item.get("id") or item.get("item_id")

        inventory_item = None
        if item_id is not None:
            inventory_item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()

        if not inventory_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory item not found for cart entry: {item.get('name', item_id)}"
            )
        if inventory_item.quantity < qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for {inventory_item.name}. Available: {inventory_item.quantity}, Requested: {qty}"
            )

        line_total = unit_price * qty
        total_bill += line_total

        new_sale = Sale(
            item_id=inventory_item.id,
            quantity=qty,
            unit_price=unit_price,
            buying_price=inventory_item.buying_price or unit_price,  # Use inventory buying price or fallback to unit price
            total_amount=line_total,
            customer_name=customer_name,
            sale_date=datetime.utcnow(),
            created_by=current_user.username
        )
        db.add(new_sale)
        created_sales.append(new_sale)

        inventory_item.quantity -= qty
        inventory_item.updated_at = datetime.utcnow()

    if payment_mode == "Credit (Deni)":
        new_debt = Debtor(
            name=customer_name,
            company=company_name,
            amount=total_bill,
            date_owed=datetime.utcnow(),
            status="pending"
        )
        db.add(new_debt)

    db.commit()

    await log_activity(
        db=db,
        user=current_user.username,
        action="CHECKOUT",
        details=f"Checkout for {customer_name} ({payment_mode}) totaling {total_bill}"
    )

    return {"status": "Approved", "invoice_total": total_bill, "mode": payment_mode}

@app.get("/api/reports/full-audit")
async def get_full_audit_report(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Full audit report sourced directly from the inventory and expenses tables."""
    items = db.query(InventoryItem).all()
    low_stock_report = {
        item.name: {"quantity": item.quantity, "reorder_point": item.reorder_point}
        for item in items if item.quantity <= item.reorder_point
    }

    expenses = db.query(Expense).all()
    expenses_by_category = {}
    total_expenses = 0.0
    for exp in expenses:
        total_expenses += exp.amount
        expenses_by_category[exp.category] = expenses_by_category.get(exp.category, 0.0) + exp.amount

    return {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "low_stock_report": low_stock_report,
        "expenditure_report": {
            "total_expenses": total_expenses,
            "expenses_by_category": expenses_by_category
        }
    }

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_root():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "Online"}

@app.get("/{catchall:path}")
async def serve_frontend(catchall: str):
    if catchall.startswith("api/"):
        return {"detail": "Not Found"}, 404
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"detail": "Not Found"}