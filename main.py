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
from models import InventoryItem, Sale, Debtor, Creditor, Expense
from report_generator import ReportGenerator
from routers import auth, inventory, sales, purchases, expenses, reports, users, activity, backup, agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Safe DDL execution; tables are created if they do not exist
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

# --- Real, database-backed mounted routers ---
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


# --- REAL LIVE DATABASE API ENDPOINTS ---

@app.get("/api/reports/daily-summary")
async def get_daily_summary(db: Session = Depends(get_db)):
    """Fetch real aggregate operational business metrics for the current day"""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 1. Total earnings from transactions closed today
    total_earnings = db.query(func.sum(Sale.total_amount)).filter(Sale.timestamp >= today_start).scalar() or 0.0
    
    # 2. Count of unique stock items currently matching or below their reorder safety line
    low_stock_count = db.query(InventoryItem).filter(InventoryItem.quantity <= InventoryItem.reorder_point).count()
    
    # 3. Total distinct product unit quantities sold today
    items_sold = db.query(func.sum(Sale.quantity)).filter(Sale.timestamp >= today_start).scalar() or 0
    
    return {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "items_sold": int(items_sold),
        "total_earnings_tzs": float(total_earnings),
        "low_stock_count": low_stock_count
    }


@app.get("/api/ledgers/debtors")
async def get_debtors(db: Session = Depends(get_db)):
    """Fetch all outstanding customer and company debts (Deni) directly from the database"""
    debtors = db.query(Debtor).filter(Debtor.status != "paid").all()
    return [
        {
            "id": d.id,
            "customer_name": d.name,
            "company": d.contact or "Individual",  # Uses model text properties safely
            "amount_owed": d.amount,
            "date": d.date_owed.strftime("%Y-%m-%d") if d.date_owed else None,
            "status": d.status.capitalize()
        } for d in debtors
    ]


@app.post("/api/ledgers/debtors/pay/{debt_id}")
async def pay_debtor(debt_id: int, amount: float = Body(..., embed=True), db: Session = Depends(get_db)):
    """Process a full or partial database payment updates against an active debtor record"""
    debt_record = db.query(Debtor).filter(Debtor.id == debt_id).first()
    if not debt_record:
        raise HTTPException(status_code=404, detail="Debtor record not found in system schema.")
    
    debt_record.amount -= amount
    if debt_record.amount <= 0:
        debt_record.amount = 0
        debt_record.status = "paid"
    else:
        debt_record.status = "partial"
        
    db.commit()
    db.refresh(debt_record)
    return {"status": "Success", "remaining": debt_record.amount}


@app.get("/api/ledgers/creditors")
async def get_creditors(db: Session = Depends(get_db)):
    """Fetch all supplier tracking balances and pending supply costs (Madeni ya Wauzaji)"""
    creditors = db.query(Creditor).filter(Creditor.status != "paid").all()
    return [
        {
            "id": c.id,
            "supplier_name": c.name,
            "invoice_no": c.contact or "N/A",
            "amount_due": c.amount,
            "date": c.date_owed.strftime("%Y-%m-%d") if c.date_owed else None,
            "status": c.status.capitalize()
        } for c in creditors
    ]


@app.post("/api/sales/checkout")
async def process_checkout(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Processes sales items, decrements inventory stock quantities, and binds credit accounts safely"""
    customer_name = payload.get("customer_name", "Walk-In Customer")
    company_name = payload.get("company_name", "Individual")
    payment_mode = payload.get("payment_mode", "Cash")
    items = payload.get("items", [])
    
    if not items:
        raise HTTPException(status_code=400, detail="Cannot execute checkout processing over empty shopping carts.")
        
    total_bill = 0.0
    
    # Process stock adjustments defensively
    for product_item in items:
        db_item = db.query(InventoryItem).filter(InventoryItem.id == product_item["id"]).first()
        if not db_item:
            raise HTTPException(status_code=404, detail=f"Stock item ID {product_item['id']} missing from catalog database.")
            
        if db_item.quantity < product_item["qty"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Inoperable transaction load. Item '{db_item.name}' possesses insufficient stock balance ({db_item.quantity} available)."
            )
            
        # Decrement quantities safely from relational warehouse records
        db_item.quantity -= product_item["qty"]
        
        # Log entry item volume sum totals
        line_cost = db_item.price * product_item["qty"]
        total_bill += line_cost
        
        # Instantiate persistent transaction log row entry
        new_sale_log = Sale(
            item_id=db_item.id,
            quantity=product_item["qty"],
            total_amount=line_cost,
            timestamp=datetime.utcnow(),
            created_by="system_pos"  # Swap with dynamic oauth authentication payload strings if needed
        )
        db.add(new_sale_log)
        
    # Handle localized accounting parameters
    if payment_mode == "Credit (Deni)":
        new_debt_entry = Debtor(
            name=f"{customer_name} / {company_name}",
            amount=total_bill,
            contact=company_name,
            status="pending",
            date_owed=datetime.utcnow()
        )
        db.add(new_debt_entry)
        
    db.commit()
    return {"status": "Approved", "invoice_total": total_bill, "mode": payment_mode}


@app.get("/api/reports/full-audit")
async def get_full_audit_report(db: Session = Depends(get_db)):
    """Wraps full application schemas directly into the analytics engine service pipeline"""
    class LiveDatabaseInventoryBridge:
        def __init__(self, session: Session):
            self.session = session
            
        @property
        def inventory(self):
            # Formats relational records directly back into the expected dictionary mapping structures of report_generator.py
            all_items = self.session.query(InventoryItem).all()
            return {
                str(item.id): {
                    'name': item.name,
                    'quantity': item.quantity,
                    'reorder_point': getattr(item, 'reorder_point', 5) # Fallback to 5 if reorder column missing
                } for item in all_items
            }

    # Connect bridge context to engine instances
    live_inventory_bridge = LiveDatabaseInventoryBridge(db)
    generator = ReportGenerator(inventory_manager=live_inventory_bridge)
    
    # Build live framework metrics dict representation mapping directly off our backend rows
    audit_payload = generator.generate_full_audit_report()
    
    # Overwrite the expenditure fallback structure using database aggregation instead of file path inputs
    expenses_aggregation = db.query(Expense.category, func.sum(Expense.amount)).group_by(Expense.category).all()
    total_expenses = db.query(func.sum(Expense.amount)).scalar() or 0.0
    
    audit_payload['expenditure_report'] = {
        'total_expenses': float(total_expenses),
        'expenses_by_category': {category: float(amount) for category, amount in expenses_aggregation}
    }
    
    return audit_payload


# --- UI STATICS & DEPLOYMENT ROUTING MOUNT TIERS ---

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