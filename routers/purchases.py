from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from database import get_db
from models import User, Purchase, InventoryItem
from schemas import Purchase as PurchaseSchema, PurchaseCreate
from auth import get_current_active_user
from activity import log_activity

router = APIRouter()


@router.post("/", response_model=PurchaseSchema, status_code=status.HTTP_201_CREATED)
async def create_purchase(
    purchase: PurchaseCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new purchase"""
    # Check if inventory item exists
    item = db.query(InventoryItem).filter(InventoryItem.id == purchase.item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    # Calculate total cost
    total_cost = purchase.quantity * purchase.unit_cost
    
    # Create purchase record
    new_purchase = Purchase(
        item_id=purchase.item_id,
        quantity=purchase.quantity,
        unit_cost=purchase.unit_cost,
        total_cost=total_cost,
        supplier_name=purchase.supplier_name,
        purchase_date=datetime.utcnow(),
        created_by=current_user.username
    )
    
    # Update inventory quantity and price
    item.quantity += purchase.quantity
    item.buying_price = purchase.unit_cost  # Update buying price, not selling price
    item.updated_at = datetime.utcnow()
    
    db.add(new_purchase)
    db.commit()
    db.refresh(new_purchase)
    
    # Log activity
    await log_activity(
        db=db,
        user=current_user.username,
        action="CREATE_PURCHASE",
        details=f"Purchased {purchase.quantity} units of {item.name} for {total_cost}"
    )
    
    return new_purchase


@router.get("/", response_model=List[PurchaseSchema])
async def get_purchases(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all purchases with optional date filtering"""
    query = db.query(Purchase)
    
    if start_date:
        query = query.filter(Purchase.purchase_date >= start_date)
    if end_date:
        query = query.filter(Purchase.purchase_date <= end_date)
    
    purchases = query.order_by(Purchase.purchase_date.desc()).offset(skip).limit(limit).all()
    return purchases


@router.get("/{purchase_id}", response_model=PurchaseSchema)
async def get_purchase(
    purchase_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific purchase by ID"""
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase not found"
        )
    return purchase


@router.get("/stats/summary")
async def get_purchases_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get purchases summary statistics"""
    query = db.query(Purchase)
    
    if start_date:
        query = query.filter(Purchase.purchase_date >= start_date)
    if end_date:
        query = query.filter(Purchase.purchase_date <= end_date)
    
    purchases = query.all()
    
    total_purchases = len(purchases)
    total_cost = sum(purchase.total_cost for purchase in purchases)
    total_quantity = sum(purchase.quantity for purchase in purchases)
    
    # Average order value
    avg_order_value = total_cost / total_purchases if total_purchases > 0 else 0
    
    return {
        "total_purchases": total_purchases,
        "total_cost": total_cost,
        "total_quantity_purchased": total_quantity,
        "average_order_value": avg_order_value,
        "period_start": start_date,
        "period_end": end_date
    }


@router.get("/by-item/{item_id}", response_model=List[PurchaseSchema])
async def get_purchases_by_item(
    item_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all purchases for a specific item"""
    purchases = db.query(Purchase)\
        .filter(Purchase.item_id == item_id)\
        .order_by(Purchase.purchase_date.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return purchases


@router.delete("/{purchase_id}")
async def delete_purchase(
    purchase_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a purchase (and adjust inventory)"""
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase not found"
        )
    
    # Adjust inventory quantity
    item = db.query(InventoryItem).filter(InventoryItem.id == purchase.item_id).first()
    if item:
        # Ensure we don't go below zero
        if item.quantity >= purchase.quantity:
            item.quantity -= purchase.quantity
            item.updated_at = datetime.utcnow()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete purchase: insufficient inventory to adjust"
            )
    
    purchase_details = f"Purchase of {purchase.quantity} units for {purchase.total_cost}"
    db.delete(purchase)
    db.commit()
    
    # Log activity
    await log_activity(
        db=db,
        user=current_user.username,
        action="DELETE_PURCHASE",
        details=f"Deleted purchase: {purchase_details}"
    )
    
    return {"message": "Purchase deleted successfully and inventory adjusted"}
