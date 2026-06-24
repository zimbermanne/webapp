from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)   # ← nullable for Google users
    role = Column(String(20), default="employee")           # admin, employee, manager
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Google OAuth fields
    google_id = Column(String(100), unique=True, nullable=True, index=True)
    auth_provider = Column(String(20), default="local")     # "local" | "google"

    # Relationships
    sales = relationship("Sale", back_populates="created_by_user")
    purchases = relationship("Purchase", back_populates="created_by_user")
    expenses = relationship("Expense", back_populates="created_by_user")


class InventoryItem(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    quantity = Column(Integer, default=0)
    price = Column(Float, nullable=False)
    category = Column(String(100), nullable=True)
    reorder_point = Column(Integer, default=10)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sales = relationship("Sale", back_populates="item")
    purchases = relationship("Purchase", back_populates="item")


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("inventory.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    customer_name = Column(String(200), nullable=True)
    customer_address = Column(Text, nullable=True)
    customer_tin = Column(String(50), nullable=True)
    sale_date = Column(DateTime, default=datetime.utcnow, index=True)
    created_by = Column(String(50), ForeignKey("users.username"), nullable=False)

    # Relationships
    item = relationship("InventoryItem", back_populates="sales")
    created_by_user = relationship("User", back_populates="sales")


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("inventory.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    supplier_name = Column(String(100), nullable=True)
    purchase_date = Column(DateTime, default=datetime.utcnow, index=True)
    created_by = Column(String(50), ForeignKey("users.username"), nullable=False)

    # Relationships
    item = relationship("InventoryItem", back_populates="purchases")
    created_by_user = relationship("User", back_populates="purchases")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    expense_date = Column(DateTime, default=datetime.utcnow, index=True)
    created_by = Column(String(50), ForeignKey("users.username"), nullable=False)

    # Relationships
    created_by_user = relationship("User", back_populates="expenses")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String(50), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class Debtor(Base):
    __tablename__ = "debtors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    contact = Column(String(20), nullable=True)
    date_owed = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class Creditor(Base):
    __tablename__ = "creditors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    contact = Column(String(20), nullable=True)
    date_owed = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
