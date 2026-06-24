import os
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import InventoryItem, Sale, Expense

class ReportGenerator:
    def __init__(self, db: Session):
        """
        Initialize the ReportGenerator with a live SQLAlchemy session database context
        instead of a mock file-system inventory manager.
        """
        self.db = db

    def generate_low_stock_report(self) -> dict:
        """
        Queries the database to find items matching or below their reorder safety points.
        """
        low_stock_items = self.db.query(InventoryItem).filter(
            InventoryItem.quantity <= InventoryItem.reorder_point
        ).all()
        
        return {
            str(item.id): {
                "name": item.name,
                "quantity": item.quantity,
                "reorder_point": item.reorder_point,
                "category": item.category
            } for item in low_stock_items
        }

    def generate_sales_report(self, start_date: datetime = None, end_date: datetime = None) -> dict:
        """
        Aggregates transaction histories cleanly off relational database rows.
        """
        query = self.db.query(Sale)
        
        if start_date:
            query = query.filter(Sale.timestamp >= start_date)
        if end_date:
            query = query.filter(Sale.timestamp <= end_date)
            
        sales_records = query.all()
        
        total_sales_value = sum(sale.total_amount for sale in sales_records)
        total_items_sold = sum(sale.quantity for sale in sales_records)
        
        return {
            "total_sales_tzs": float(total_sales_value),
            "total_items_sold": total_items_sold,
            "transaction_count": len(sales_records),
            "transactions": [
                {
                    "sale_id": sale.id,
                    "item_id": sale.item_id,
                    "quantity": sale.quantity,
                    "total_amount": float(sale.total_amount),
                    "timestamp": sale.timestamp.strftime("%Y-%m-%d %H:%M:%S") if sale.timestamp else None
                } for sale in sales_records
            ]
        }

    def generate_expenditure_report(self, start_date: datetime = None, end_date: datetime = None) -> dict:
        """
        Aggregates operational expenses dynamically using SQL group-by mechanics.
        """
        query = self.db.query(Expense)
        
        if start_date:
            query = query.filter(Expense.expense_date >= start_date)
        if end_date:
            query = query.filter(Expense.expense_date <= end_date)
            
        expenses_records = query.all()
        
        # Calculate total operational cost
        total_expenses = sum(exp.amount for exp in expenses_records)
        
        # Aggregate categories dynamically using database dictionary operations
        category_group_query = self.db.query(
            Expense.category, func.sum(Expense.amount)
        ).group_by(Expense.category)
        
        if start_date:
            category_group_query = category_group_query.filter(Expense.expense_date >= start_date)
        if end_date:
            category_group_query = category_group_query.filter(Expense.expense_date <= end_date)
            
        category_metrics = category_group_query.all()
        
        return {
            "total_expenses_tzs": float(total_expenses),
            "expenses_by_category": {category: float(amount) for category, amount in category_metrics},
            "records": [
                {
                    "id": exp.id,
                    "category": exp.category,
                    "amount": float(exp.amount),
                    "description": exp.description,
                    "date": exp.expense_date.strftime("%Y-%m-%d") if exp.expense_date else None
                } for exp in expenses_records
            ]
        }

    def generate_full_audit_report(self) -> dict:
        """
        Compiles structural snapshot summaries of current stock volumes and rolling operations.
        """
        # Fetch current system inventory volumes
        all_inventory = self.db.query(InventoryItem).all()
        total_sku_count = len(all_inventory)
        total_stock_units = sum(item.quantity for item in all_inventory)
        
        # Capture current day boundary context
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        return {
            "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "inventory_summary": {
                "total_unique_items": total_sku_count,
                "total_stock_units": total_stock_units
            },
            "low_stock_report": self.generate_low_stock_report(),
            "daily_sales_performance": self.generate_sales_report(start_date=today_start),
            "daily_expenditures": self.generate_expenditure_report(start_date=today_start)
        }