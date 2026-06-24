from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional, List


# User schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    role: str = "employee"


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)


class User(UserBase):
    id: int
    created_at: datetime
    is_active: bool = True

    class Config:
        from_attributes = True


# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


# Inventory schemas
class InventoryItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    quantity: int = Field(..., ge=0)
    price: float = Field(..., gt=0)
    category: Optional[str] = None
    reorder_point: int = Field(default=10, ge=0)


class InventoryItemCreate(InventoryItemBase):
    pass


class InventoryItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    quantity: Optional[int] = Field(None, ge=0)
    price: Optional[float] = Field(None, gt=0)
    category: Optional[str] = None
    reorder_point: Optional[int] = Field(None, ge=0)


class InventoryItem(InventoryItemBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Sales schemas
class SaleBase(BaseModel):
    item_id: int
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    customer_name: Optional[str] = None
    customer_address: Optional[str] = None
    customer_tin: Optional[str] = Field(None, max_length=50)


class SaleCreate(SaleBase):
    pass


class Sale(SaleBase):
    id: int
    total_amount: float
    sale_date: datetime
    created_by: str

    class Config:
        from_attributes = True


# Purchase schemas
class PurchaseBase(BaseModel):
    item_id: int
    quantity: int = Field(..., gt=0)
    unit_cost: float = Field(..., gt=0)
    supplier_name: Optional[str] = None


class PurchaseCreate(PurchaseBase):
    pass


class Purchase(PurchaseBase):
    id: int
    total_cost: float
    purchase_date: datetime
    created_by: str

    class Config:
        from_attributes = True


# Expense schemas
class ExpenseBase(BaseModel):
    category: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0)
    description: Optional[str] = None
    expense_date: Optional[datetime] = None


class ExpenseCreate(ExpenseBase):
    pass


class Expense(ExpenseBase):
    id: int
    expense_date: datetime
    created_by: str

    class Config:
        from_attributes = True


# Report schemas
class FinancialSummary(BaseModel):
    total_sales: float
    total_purchases: float
    total_expenses: float
    profit_loss: float
    period_start: datetime
    period_end: datetime


class InventoryMetrics(BaseModel):
    total_items: int
    total_value: float
    average_price: float
    low_stock_items: int


# Activity Log schemas
class ActivityLogBase(BaseModel):
    user: str
    action: str
    details: str


class ActivityLogCreate(ActivityLogBase):
    pass


class ActivityLog(ActivityLogBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


# Backup schemas
class BackupInfo(BaseModel):
    filename: str
    created_at: datetime
    size: int
    files_included: List[str]
