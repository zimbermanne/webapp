from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import func
import sys
import os
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, Base, get_db
from models import InventoryItem, Sale, Debtor, Creditor, Expense, User
from report_generator import ReportGenerator
from auth import get_current_user, get_password_hash, verify_password, create_access_token
from activity import log_activity
from routers import auth, inventory, sales, purchases, expenses, reports, users, activity, backup, agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()

app = FastAPI(
    title="Zimbermanne Retail OS Engine",
    version="2.6.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all core routers
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


# --- SCHEMAS FOR INCOMING INPUT VALIDATION ---
class UserRegisterPayload(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = "user@zimbermanne.com"
    password: str = Field(..., min_length=5)
    role: str = "employee"

class PaymentPayload(BaseModel):
    amount: float = Field(..., gt=0)

class CartItemPayload(BaseModel):
    id: int
    qty: int = Field(..., gt=0)

class CheckoutPayload(BaseModel):
    customer_name: str = "Walk-In Customer"
    company_name: str = "Individual"
    payment_mode: str = "Cash"
    items: list[CartItemPayload]


# --- OPEN AUTHENTICATION & CREATION PATHWAYS ---

@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
async def register_new_user(payload: UserRegisterPayload, db: Session = Depends(get_db)):
    """Open user creation endpoint to avoid 404 errors during registration"""
    existing_user = db.query(User).filter(User.username == payload.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username is already taken inside system schemas.")
        
    new_user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"status": "Success", "username": new_user.username, "role": new_user.role}


@app.post("/api/auth/login")
async def unified_login_route(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Handles secure high-compatibility system login validation tasks"""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid access credentials.")
        
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account has been deactivated.")
        
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# --- PROTECTED REVENUE & TRANSACTIONS API ENDPOINTS ---

@app.get("/api/reports/daily-summary")
async def get_daily_summary(db: Session = Depends(get_db)):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total_earnings = db.query(func.sum(Sale.total_amount)).filter(Sale.timestamp >= today_start).scalar() or 0.0
    low_stock_count = db.query(InventoryItem).filter(InventoryItem.quantity <= InventoryItem.reorder_point).count()
    items_sold = db.query(func.sum(Sale.quantity)).filter(Sale.timestamp >= today_start).scalar() or 0
    
    return {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "items_sold": int(items_sold),
        "total_earnings_tzs": float(total_earnings),
        "low_stock_count": low_stock_count
    }

@app.get("/api/ledgers/debtors")
async def get_debtors(db: Session = Depends(get_db)):
    debtors = db.query(Debtor).filter(Debtor.status != "paid").all()
    return [
        {
            "id": d.id,
            "customer_name": d.name,
            "company": d.contact or "Individual",
            "amount_owed": d.amount,
            "date": d.date_owed.strftime("%Y-%m-%d") if d.date_owed else None,
            "status": d.status.capitalize()
        } for d in debtors
    ]

@app.post("/api/ledgers/debtors/pay/{debt_id}")
async def pay_debtor(debt_id: int, payload: PaymentPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    debt_record = db.query(Debtor).filter(Debtor.id == debt_id).first()
    if not debt_record:
        raise HTTPException(status_code=404, detail="Debtor record not found.")
    
    if payload.amount > debt_record.amount:
        raise HTTPException(status_code=400, detail="Payment amount exceeds outstanding debt.")

    debt_record.amount -= payload.amount
    if debt_record.amount <= 0:
        debt_record.amount = 0
        debt_record.status = "paid"
    else:
        debt_record.status = "partial"
        
    db.commit()
    await log_activity(db, current_user.username, "DEBT_PAYMENT", f"Paid TZS {payload.amount} for debt ID: {debt_id}")
    return {"status": "Success", "remaining": debt_record.amount}

@app.get("/api/ledgers/creditors")
async def get_creditors(db: Session = Depends(get_db)):
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
async def process_checkout(payload: CheckoutPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_bill = 0.0
    sales_to_add = []
    
    for product_item in payload.items:
        db_item = db.query(InventoryItem).filter(InventoryItem.id == product_item.id).with_for_update().first()
        if not db_item:
            raise HTTPException(status_code=404, detail=f"Stock item ID {product_item.id} missing.")
            
        if db_item.quantity < product_item.qty:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for '{db_item.name}'.")
            
        db_item.quantity -= product_item.qty
        line_cost = db_item.price * product_item.qty
        total_bill += line_cost
        
        new_sale_log = Sale(
            item_id=db_item.id,
            quantity=product_item.qty,
            total_amount=line_cost,
            timestamp=datetime.now(timezone.utc),
            created_by=current_user.username
        )
        sales_to_add.append(new_sale_log)
        
    for sale in sales_to_add:
        db.add(sale)
        
    if payload.payment_mode == "Credit (Deni)":
        new_debt_entry = Debtor(
            name=f"{payload.customer_name} / {payload.company_name}",
            amount=total_bill,
            contact=payload.company_name,
            status="pending",
            date_owed=datetime.now(timezone.utc)
        )
        db.add(new_debt_entry)
        
    db.commit()
    await log_activity(db, current_user.username, "COMPLETED_SALE", f"Total: TZS {total_bill}")
    return {"status": "Approved", "invoice_total": total_bill, "mode": payload.payment_mode}

@app.get("/api/reports/full-audit")
async def get_full_audit_report(db: Session = Depends(get_db)):
    generator = ReportGenerator(db)
    return generator.generate_full_audit_report()


# --- STATIC RENDERING AND SPA CATCHALL RULES ---

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
        raise HTTPException(status_code=404, detail="API endpoint not found.")
    static_file_path = os.path.join("static", catchall)
    if os.path.exists(static_file_path) and os.path.isfile(static_file_path):
        return FileResponse(static_file_path)
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Resource unavailable.")