from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# Transaction Profit/Loss schemas
class TransactionProfitLoss(BaseModel):
    transaction_id: int
    transaction_type: str  # "sale" or "purchase"
    item_name: str
    quantity: int
    buying_price: float
    selling_price: float
    profit_loss: float
    transaction_date: datetime
    customer_name: Optional[str] = None
    supplier_name: Optional[str] = None


class TransactionProfitLossReport(BaseModel):
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    total_transactions: int
    total_profit: float
    total_loss: float
    net_profit: float
    transactions: List[TransactionProfitLoss]


# Quotation and Invoice schemas
class QuotationItem(BaseModel):
    item_name: str
    quantity: int
    unit_price: float
    total: float


class QuotationCreate(BaseModel):
    customer_name: str
    customer_address: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    valid_until: datetime
    items: List[QuotationItem]
    notes: Optional[str] = None


class Quotation(BaseModel):
    id: int
    quotation_number: str
    customer_name: str
    customer_address: Optional[str]
    customer_email: Optional[str]
    customer_phone: Optional[str]
    valid_until: datetime
    items: List[QuotationItem]
    subtotal: float
    tax_rate: float
    tax_amount: float
    total: float
    notes: Optional[str]
    created_at: datetime
    status: str  # "draft", "sent", "accepted", "rejected", "expired"


class InvoiceCreate(BaseModel):
    customer_name: str
    customer_address: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_tin: Optional[str] = None
    due_date: datetime
    items: List[QuotationItem]
    notes: Optional[str] = None


class Invoice(BaseModel):
    id: int
    invoice_number: str
    customer_name: str
    customer_address: Optional[str]
    customer_email: Optional[str]
    customer_phone: Optional[str]
    customer_tin: Optional[str]
    invoice_date: datetime
    due_date: datetime
    items: List[QuotationItem]
    subtotal: float
    tax_rate: float
    tax_amount: float
    total: float
    notes: Optional[str]
    status: str  # "draft", "sent", "paid", "overdue", "cancelled"
    created_at: datetime
