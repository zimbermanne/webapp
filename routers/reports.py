from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from database import get_db
from models import User, Sale, Purchase, Expense, InventoryItem, Debtor, Creditor
from schemas import FinancialSummary, TransactionProfitLoss, TransactionProfitLossReport
from auth import get_current_active_user
from activity import log_activity

router = APIRouter()


class DateRange(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@router.get("/financial-summary", response_model=FinancialSummary)
async def get_financial_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive financial summary including profit/loss"""
    # Default to current month if no dates specified
    if not start_date and not end_date:
        now = datetime.utcnow()
        start_date = datetime(now.year, now.month, 1)
        end_date = now
    
    query_sales = db.query(Sale)
    query_purchases = db.query(Purchase)
    query_expenses = db.query(Expense)
    
    if start_date:
        query_sales = query_sales.filter(Sale.sale_date >= start_date)
        query_purchases = query_purchases.filter(Purchase.purchase_date >= start_date)
        query_expenses = query_expenses.filter(Expense.expense_date >= start_date)
    
    if end_date:
        query_sales = query_sales.filter(Sale.sale_date <= end_date)
        query_purchases = query_purchases.filter(Purchase.purchase_date <= end_date)
        query_expenses = query_expenses.filter(Expense.expense_date <= end_date)
    
    sales = query_sales.all()
    total_sales = sum(sale.total_amount for sale in sales)
    total_purchases = sum(purchase.total_cost for purchase in query_purchases.all())
    total_expenses = sum(expense.amount for expense in query_expenses.all())
    
    # Improved profit/loss calculation using actual cost of goods sold
    total_cost_of_goods_sold = 0.0
    for sale in sales:
        buying_price = sale.buying_price
        if buying_price:
            total_cost_of_goods_sold += buying_price * sale.quantity
        else:
            # Fallback to inventory buying price if sale doesn't have it
            item = db.query(InventoryItem).filter(InventoryItem.id == sale.item_id).first()
            if item and item.buying_price:
                total_cost_of_goods_sold += item.buying_price * sale.quantity
            else:
                # Last resort: use unit price as cost
                total_cost_of_goods_sold += sale.unit_price * sale.quantity
    
    # Calculate profit/loss: Revenue - Cost of Goods Sold - Operating Expenses
    profit_loss = total_sales - total_cost_of_goods_sold - total_expenses
    
    return FinancialSummary(
        total_sales=total_sales,
        total_purchases=total_purchases,
        total_expenses=total_expenses,
        cost_of_goods_sold=total_cost_of_goods_sold,
        profit_loss=profit_loss,
        period_start=start_date or datetime.utcnow(),
        period_end=end_date or datetime.utcnow()
    )


@router.get("/profit-loss")
async def get_profit_loss_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detailed profit and loss report"""
    if not start_date and not end_date:
        now = datetime.utcnow()
        start_date = datetime(now.year, now.month, 1)
        end_date = now
    
    # Get sales data
    sales_query = db.query(Sale)
    purchases_query = db.query(Purchase)
    expenses_query = db.query(Expense)
    
    if start_date:
        sales_query = sales_query.filter(Sale.sale_date >= start_date)
        purchases_query = purchases_query.filter(Purchase.purchase_date >= start_date)
        expenses_query = expenses_query.filter(Expense.expense_date >= start_date)
    
    if end_date:
        sales_query = sales_query.filter(Sale.sale_date <= end_date)
        purchases_query = purchases_query.filter(Purchase.purchase_date <= end_date)
        expenses_query = expenses_query.filter(Expense.expense_date <= end_date)
    
    sales = sales_query.all()
    purchases = purchases_query.all()
    expenses = expenses_query.all()
    
    # Revenue by category (based on item categories)
    revenue_by_category = {}
    for sale in sales:
        item = db.query(InventoryItem).filter(InventoryItem.id == sale.item_id).first()
        if item:
            category = item.category or "Uncategorized"
            revenue_by_category[category] = revenue_by_category.get(category, 0) + sale.total_amount
    
    # Expenses by category
    expenses_by_category = {}
    for expense in expenses:
        expenses_by_category[expense.category] = expenses_by_category.get(expense.category, 0) + expense.amount
    
    total_revenue = sum(sale.total_amount for sale in sales)
    total_operating_expenses = sum(expense.amount for expense in expenses)

    
    # Calculate actual cost of goods sold using buying prices
    total_cost_of_goods = 0.0
    for sale in sales:
        buying_price = sale.buying_price
        if buying_price:
            total_cost_of_goods += buying_price * sale.quantity
        else:
            # Fallback to inventory buying price
            item = db.query(InventoryItem).filter(InventoryItem.id == sale.item_id).first()
            if item and item.buying_price:
                total_cost_of_goods += item.buying_price * sale.quantity
            else:
                # Last resort: use unit price
                total_cost_of_goods += sale.unit_price * sale.quantity
    



    

    gross_profit = total_revenue - total_cost_of_goods
    net_profit = gross_profit - total_operating_expenses
    
    return {
        "period_start": start_date,
        "period_end": end_date,
        "revenue": {
            "total": total_revenue,
            "by_category": revenue_by_category,
            "number_of_sales": len(sales)
        },
        "cost_of_goods_sold": {
            "total": total_cost_of_goods,
            "number_of_purchases": len(purchases)
        },
        "operating_expenses": {
            "total": total_operating_expenses,
            "by_category": expenses_by_category,
            "number_of_expenses": len(expenses)
        },
        "profit_summary": {
            "gross_profit": gross_profit,
            "net_profit": net_profit,
            "profit_margin": (net_profit / total_revenue * 100) if total_revenue > 0 else 0
        }
    }


@router.get("/debtors")
async def get_debtors_report(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get debtors report"""
    debtors = db.query(Debtor).all()
    
    total_owed = sum(debtor.amount for debtor in debtors)
    
    # Break down by status
    by_status = {"pending": 0, "paid": 0, "partial": 0}
    for debtor in debtors:
        by_status[debtor.status] = by_status.get(debtor.status, 0) + debtor.amount
    
    return {
        "total_debtors": len(debtors),
        "total_amount_owed": total_owed,
        "by_status": by_status,
        "debtors": [
            {
                "id": debtor.id,
                "name": debtor.name,
                "amount": debtor.amount,
                "contact": debtor.contact,
                "date_owed": debtor.date_owed,
                "status": debtor.status
            }
            for debtor in debtors
        ]
    }


@router.get("/creditors")
async def get_creditors_report(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get creditors report"""
    creditors = db.query(Creditor).all()
    
    total_owed = sum(creditor.amount for creditor in creditors)
    
    # Break down by status
    by_status = {"pending": 0, "paid": 0, "partial": 0}
    for creditor in creditors:
        by_status[creditor.status] = by_status.get(creditor.status, 0) + creditor.amount
    
    return {
        "total_creditors": len(creditors),
        "total_amount_owed": total_owed,
        "by_status": by_status,
        "creditors": [
            {
                "id": creditor.id,
                "name": creditor.name,
                "amount": creditor.amount,
                "contact": creditor.contact,
                "date_owed": creditor.date_owed,
                "status": creditor.status
            }
            for creditor in creditors
        ]
    }


@router.get("/inventory-valuation")
async def get_inventory_valuation_report(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get inventory valuation report"""
    items = db.query(InventoryItem).all()
    
    total_items = len(items)
    total_quantity = sum(item.quantity for item in items)
    total_value = sum(item.quantity * item.price for item in items)
    
    # Break down by category
    by_category = {}
    for item in items:
        category = item.category or "Uncategorized"
        category_value = item.quantity * item.price
        by_category[category] = by_category.get(category, 0) + category_value
    
    # Low stock items
    low_stock_items = [
        {
            "id": item.id,
            "name": item.name,
            "current_quantity": item.quantity,
            "reorder_point": item.reorder_point,
            "value": item.quantity * item.price
        }
        for item in items if item.quantity <= item.reorder_point
    ]
    
    return {
        "total_items": total_items,
        "total_quantity": total_quantity,
        "total_value": total_value,
        "by_category": by_category,
        "low_stock_items": low_stock_items,
        "low_stock_count": len(low_stock_items)
    }


@router.post("/add-debtor")
async def add_debtor(
    name: str,
    amount: float,
    contact: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a new debtor"""
    new_debtor = Debtor(
        name=name,
        amount=amount,
        contact=contact,
        date_owed=datetime.utcnow(),
        status="pending"
    )
    
    db.add(new_debtor)
    db.commit()
    db.refresh(new_debtor)
    
    # Log activity
    await log_activity(
        db=db,
        user=current_user.username,
        action="ADD_DEBTOR",
        details=f"Added debtor: {name} with amount {amount}"
    )
    
    return {"message": "Debtor added successfully", "debtor_id": new_debtor.id}


@router.post("/add-creditor")
async def add_creditor(
    name: str,
    amount: float,
    contact: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a new creditor"""
    new_creditor = Creditor(
        name=name,
        amount=amount,
        contact=contact,
        date_owed=datetime.utcnow(),
        status="pending"
    )
    
    db.add(new_creditor)
    db.commit()
    db.refresh(new_creditor)
    
    # Log activity
    await log_activity(
        db=db,
        user=current_user.username,
        action="ADD_CREDITOR",
        details=f"Added creditor: {name} with amount {amount}"
    )
    
    return {"message": "Creditor added successfully", "creditor_id": new_creditor.id}


@router.get("/transaction-profit-loss", response_model=TransactionProfitLossReport)
async def get_transaction_profit_loss(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    item_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detailed transaction-level profit and loss analysis"""
    # Default to current month if no dates specified
    if not start_date and not end_date:
        now = datetime.utcnow()
        start_date = datetime(now.year, now.month, 1)
        end_date = now
    
    # Build sales query
    sales_query = db.query(Sale)
    if start_date:
        sales_query = sales_query.filter(Sale.sale_date >= start_date)
    if end_date:
        sales_query = sales_query.filter(Sale.sale_date <= end_date)
    if item_id:
        sales_query = sales_query.filter(Sale.item_id == item_id)
    
    sales = sales_query.all()
    
    # Build purchases query
    purchases_query = db.query(Purchase)
    if start_date:
        purchases_query = purchases_query.filter(Purchase.purchase_date >= start_date)
    if end_date:
        purchases_query = purchases_query.filter(Purchase.purchase_date <= end_date)
    if item_id:
        purchases_query = purchases_query.filter(Purchase.item_id == item_id)
    
    purchases = purchases_query.all()
    
    # Calculate transaction-level profit/loss
    transactions = []
    total_profit = 0.0
    total_loss = 0.0
    
    # Process sales transactions
    for sale in sales:
        item = db.query(InventoryItem).filter(InventoryItem.id == sale.item_id).first()
        item_name = item.name if item else "Unknown Item"
        
        buying_price = sale.buying_price or (item.buying_price if item else sale.unit_price)
        selling_price = sale.unit_price
        profit_loss = (selling_price - buying_price) * sale.quantity
        
        if profit_loss >= 0:
            total_profit += profit_loss
        else:
            total_loss += abs(profit_loss)
        
        transactions.append(TransactionProfitLoss(
            transaction_id=sale.id,
            transaction_type="sale",
            item_name=item_name,
            quantity=sale.quantity,
            buying_price=buying_price,
            selling_price=selling_price,
            profit_loss=profit_loss,
            transaction_date=sale.sale_date,
            customer_name=sale.customer_name,
            supplier_name=None
        ))
    
    # Process purchase transactions (these are cost, not profit/loss directly)
    for purchase in purchases:
        item = db.query(InventoryItem).filter(InventoryItem.id == purchase.item_id).first()
        item_name = item.name if item else "Unknown Item"
        
        # Purchases don't directly contribute to profit/loss but we track them
        # The profit is realized when the purchased items are sold
        buying_price = purchase.unit_cost
        selling_price = item.price if item else purchase.unit_cost
        profit_loss = 0  # Purchases don't realize profit until sold
        
        transactions.append(TransactionProfitLoss(
            transaction_id=purchase.id,
            transaction_type="purchase",
            item_name=item_name,
            quantity=purchase.quantity,
            buying_price=buying_price,
            selling_price=selling_price,
            profit_loss=profit_loss,
            transaction_date=purchase.purchase_date,
            customer_name=None,
            supplier_name=purchase.supplier_name
        ))
    
    # Sort by date descending
    transactions.sort(key=lambda x: x.transaction_date, reverse=True)
    
    net_profit = total_profit - total_loss
    
    return TransactionProfitLossReport(
        period_start=start_date,
        period_end=end_date,
        total_transactions=len(transactions),
        total_profit=total_profit,
        total_loss=total_loss,
        net_profit=net_profit,
        transactions=transactions
    )


@router.get("/profit-loss-by-item")
async def get_profit_loss_by_item(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get profit/loss analysis grouped by item"""
    if not start_date and not end_date:
        now = datetime.utcnow()
        start_date = datetime(now.year, now.month, 1)
        end_date = now
    
    # Get all sales in period
    sales_query = db.query(Sale)
    if start_date:
        sales_query = sales_query.filter(Sale.sale_date >= start_date)
    if end_date:
        sales_query = sales_query.filter(Sale.sale_date <= end_date)
    
    sales = sales_query.all()
    
    # Group by item
    item_profit_loss = {}
    
    for sale in sales:
        item = db.query(InventoryItem).filter(InventoryItem.id == sale.item_id).first()
        if not item:
            continue
            
        item_name = item.name
        buying_price = sale.buying_price or (item.buying_price or sale.unit_price)
        selling_price = sale.unit_price
        profit_loss = (selling_price - buying_price) * sale.quantity
        
        if item_name not in item_profit_loss:
            item_profit_loss[item_name] = {
                "item_id": item.id,
                "item_name": item_name,
                "quantity_sold": 0,
                "total_revenue": 0.0,
                "total_cost": 0.0,
                "total_profit": 0.0,
                "profit_margin": 0.0
            }
        
        item_profit_loss[item_name]["quantity_sold"] += sale.quantity
        item_profit_loss[item_name]["total_revenue"] += sale.total_amount
        item_profit_loss[item_name]["total_cost"] += buying_price * sale.quantity
        item_profit_loss[item_name]["total_profit"] += profit_loss
    
    # Calculate profit margins
    for item_data in item_profit_loss.values():
        if item_data["total_revenue"] > 0:
            item_data["profit_margin"] = (item_data["total_profit"] / item_data["total_revenue"]) * 100
    
    return {
        "period_start": start_date,
        "period_end": end_date,
        "items": list(item_profit_loss.values()),
        "total_items": len(item_profit_loss)
    }
