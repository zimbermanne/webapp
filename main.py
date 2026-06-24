from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, Base, get_db
from report_generator import ReportGenerator

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

# --- MOCK LEDGER DATA STORAGE (Replace with database models as needed) ---
DEBTORS_LEDGER = [
    {"id": 1, "customer_name": "Theresia B. Singitha", "company": "Singitha Holdings", "amount_owed": 600000.0, "date": "2026-06-15", "status": "Pending"},
    {"id": 2, "customer_name": "Emanuel Temba", "company": "Temba Builders Moshi", "amount_owed": 150000.0, "date": "2026-06-20", "status": "Partial"}
]

CREDITORS_LEDGER = [
    {"id": 1, "supplier_name": "Alibaba Global Sourcing", "invoice_no": "INV-9921", "amount_due": 1200000.0, "date": "2026-06-10", "status": "Unpaid"},
    {"id": 2, "supplier_name": "Dar Logistics Hub", "invoice_no": "TRK-0482", "amount_due": 350000.0, "date": "2026-06-19", "status": "Unpaid"}
]

@app.get("/api/reports/daily-summary")
async def get_daily_summary(db: Session = Depends(get_db)):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return {
        "date": today,
        "items_sold": 142,
        "total_earnings_tzs": 485000,
        "top_product": "PVC Pipe 1/2 Inch",
        "low_stock_count": 3
    }

# --- DEBTORS & CREDITORS API ENDPOINTS ---

@app.get("/api/ledgers/debtors")
async def get_debtors():
    """Fetch all outstanding customer and company debts (Deni)"""
    return DEBTORS_LEDGER

@app.post("/api/ledgers/debtors/pay/{debt_id}")
async def pay_debtor(debt_id: int, amount: float = Body(..., embed=True)):
    """Process a full or partial payment from a debtor"""
    for debt in DEBTORS_LEDGER:
        if debt["id"] == debt_id:
            debt["amount_owed"] -= amount
            if debt["amount_owed"] <= 0:
                debt["status"] = "Paid"
            return {"status": "Success", "remaining": debt["amount_owed"]}
    raise HTTPException(status_code=404, detail="Debtor record not found")

@app.get("/api/ledgers/creditors")
async def get_creditors():
    """Fetch all supplier debts and pending costs (Madeni ya Wauzaji)"""
    return CREDITORS_LEDGER

@app.post("/api/sales/checkout")
async def process_checkout(payload: dict = Body(...)):
    """Handles sales transactions processing both Cash and Credit (Deni) with full Customer/Company structures"""
    customer_name = payload.get("customer_name", "Walk-In Customer")
    company_name = payload.get("company_name", "Individual")
    payment_mode = payload.get("payment_mode", "Cash")
    items = payload.get("items", [])
    
    total_bill = sum(item["price"] * item["qty"] for item in items)
    
    if payment_mode == "Credit (Deni)":
        new_debt = {
            "id": len(DEBTORS_LEDGER) + 1,
            "customer_name": customer_name,
            "company": company_name,
            "amount_owed": total_bill,
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "status": "Pending"
        }
        DEBTORS_LEDGER.append(new_debt)
        
    return {"status": "Approved", "invoice_total": total_bill, "mode": payment_mode}

@app.get("/api/reports/full-audit")
async def get_full_audit_report(db: Session = Depends(get_db)):
    class MockInventoryManager:
        def __init__(self):
            self.inventory = {} 
    generator = ReportGenerator(inventory_manager=MockInventoryManager())
    return generator.generate_full_audit_report()

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