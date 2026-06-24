from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import InventoryItem, Sale, Expense

class ReportGenerator:
    def __init__(self, db: Session):
        """
        Initialize ReportGenerator exclusively via SQLAlchemy database contexts,
        eliminating local system file dependencies entirely.
        """
        self.db = db

    def generate_low_stock_report(self) -> dict:
        """
        Queries and transforms low stock rows using dot-notation ORM access safely.
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
        Aggregates financial sales pipelines directly using memory-bounded relational filters.
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
        Aggregates operational expenses using exact SQL GROUP BY calculations.
        """
        query = self.db.query(Expense)
        if start_date:
            query = query.filter(Expense.expense_date >= start_date)
        if end_date:
            query = query.filter(Expense.expense_date <= end_date)
            
        expenses_records = query.all()
        total_expenses = sum(exp.amount for exp in expenses_records)
        
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
        Compiles structural performance metrics synchronized with uniform UTC time calculations.
        """
        all_inventory = self.db.query(InventoryItem).all()
        total_sku_count = len(all_inventory)
        total_stock_units = sum(item.quantity for item in all_inventory)
        
        # Timezone validation compliance fix
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        return {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "inventory_summary": {
                "total_unique_items": total_sku_count,
                "total_stock_units": total_stock_units
            },
            "low_stock_report": self.generate_low_stock_report(),
            "daily_sales_performance": self.generate_sales_report(start_date=today_start),
            "daily_expenditures": self.generate_expenditure_report(start_date=today_start)
        }