from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from database import get_db
from models import User, Expense
from schemas import Expense as ExpenseSchema, ExpenseCreate
from auth import get_current_active_user
from activity import log_activity

router = APIRouter()


@router.post("/", response_model=ExpenseSchema, status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense: ExpenseCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new expense"""
    new_expense = Expense(
        category=expense.category,
        amount=expense.amount,
        description=expense.description,
        expense_date=expense.expense_date or datetime.utcnow(),
        created_by=current_user.username
    )
    
    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)
    
    # Log activity
    await log_activity(
        db=db,
        user=current_user.username,
        action="CREATE_EXPENSE",
        details=f"Recorded expense of {expense.amount} in category: {expense.category}"
    )
    
    return new_expense


@router.get("/", response_model=List[ExpenseSchema])
async def get_expenses(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all expenses with optional filters"""
    query = db.query(Expense)
    
    if category:
        query = query.filter(Expense.category == category)
    
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)
    
    expenses = query.order_by(Expense.expense_date.desc()).offset(skip).limit(limit).all()
    return expenses


@router.get("/{expense_id}", response_model=ExpenseSchema)
async def get_expense(
    expense_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific expense by ID"""
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    return expense


@router.get("/categories/list")
async def get_expense_categories(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all unique expense categories"""
    categories = db.query(Expense.category)\
        .distinct()\
        .all()
    
    return [category[0] for category in categories]


@router.get("/stats/summary")
async def get_expenses_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get expenses summary statistics"""
    query = db.query(Expense)
    
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)
    
    expenses = query.all()
    
    total_expenses = len(expenses)
    total_amount = sum(expense.amount for expense in expenses)
    
    # Group by category
    category_breakdown = {}
    for expense in expenses:
        category_breakdown[expense.category] = category_breakdown.get(expense.category, 0) + expense.amount
    
    return {
        "total_expenses": total_expenses,
        "total_amount": total_amount,
        "category_breakdown": category_breakdown,
        "period_start": start_date,
        "period_end": end_date
    }


@router.put("/{expense_id}", response_model=ExpenseSchema)
async def update_expense(
    expense_id: int,
    expense_update: ExpenseCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an expense"""
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    # Update fields
    expense.category = expense_update.category
    expense.amount = expense_update.amount
    expense.description = expense_update.description
    if expense_update.expense_date:
        expense.expense_date = expense_update.expense_date
    
    db.commit()
    db.refresh(expense)
    
    # Log activity
    await log_activity(
        db=db,
        user=current_user.username,
        action="UPDATE_EXPENSE",
        details=f"Updated expense ID {expense_id}"
    )
    
    return expense


@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an expense"""
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    expense_details = f"Expense of {expense.amount} in category: {expense.category}"
    db.delete(expense)
    db.commit()
    
    # Log activity
    await log_activity(
        db=db,
        user=current_user.username,
        action="DELETE_EXPENSE",
        details=f"Deleted expense: {expense_details}"
    )
    
    return {"message": "Expense deleted successfully"}
