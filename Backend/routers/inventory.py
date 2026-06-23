from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import statistics

from database import get_db
from models import User, InventoryItem
from schemas import (
    InventoryItem as InventoryItemSchema,
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryMetrics
)
from auth import get_current_active_user
from activity import log_activity

router = APIRouter()


@router.post("/", response_model=InventoryItemSchema, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    item: InventoryItemCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new inventory item"""
    new_item = InventoryItem(**item.dict())
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    # Log activity
    await log_activity(
        db=db,
        user=current_user.username,
        action="CREATE_ITEM",
        details=f"Created inventory item: {item.name}"
    )
    
    return new_item


@router.get("/", response_model=List[InventoryItemSchema])
async def get_inventory_items(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    low_stock_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all inventory items with optional filters"""
    query = db.query(InventoryItem)
    
    if category:
        query = query.filter(InventoryItem.category == category)
    
    if low_stock_only:
        query = query.filter(InventoryItem.quantity <= InventoryItem.reorder_point)
    
    items = query.offset(skip).limit(limit).all()
    return items


@router.get("/metrics", response_model=InventoryMetrics)
async def get_inventory_metrics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get inventory metrics and analytics"""
    items = db.query(InventoryItem).all()
    
    if not items:
        return InventoryMetrics(
            total_items=0,
            total_value=0.0,
            average_price=0.0,
            low_stock_items=0
        )
    
    total_items = len(items)
    total_value = sum(item.quantity * item.price for item in items)
    average_price = statistics.mean(item.price for item in items) if items else 0.0
    low_stock_items = len([item for item in items if item.quantity <= item.reorder_point])
    
    return InventoryMetrics(
        total_items=total_items,
        total_value=total_value,
        average_price=average_price,
        low_stock_items=low_stock_items
    )


@router.get("/{item_id}", response_model=InventoryItemSchema)
async def get_inventory_item(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific inventory item by ID"""
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    return item


@router.put("/{item_id}", response_model=InventoryItemSchema)
async def update_inventory_item(
    item_id: int,
    item_update: InventoryItemUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an inventory item"""
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    # Update fields
    update_data = item_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    
    # Log activity
    await log_activity(
        db=db,
        user=current_user.username,
        action="UPDATE_ITEM",
        details=f"Updated inventory item ID {item_id}"
    )
    
    return item


@router.delete("/{item_id}")
async def delete_inventory_item(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an inventory item"""
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    item_name = item.name
    db.delete(item)
    db.commit()
    
    # Log activity
    await log_activity(
        db=db,
        user=current_user.username,
        action="DELETE_ITEM",
        details=f"Deleted inventory item: {item_name}"
    )
    
    return {"message": f"Inventory item {item_name} deleted successfully"}


@router.post("/batch", response_model=List[InventoryItemSchema])
async def create_inventory_batch(
    items: List[InventoryItemCreate],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create multiple inventory items at once"""
    new_items = []
    for item_data in items:
        new_item = InventoryItem(**item_data.dict())
        db.add(new_item)
        new_items.append(new_item)
    
    db.commit()
    
    for item in new_items:
        db.refresh(item)
    
    # Log activity
    await log_activity(
        db=db,
        user=current_user.username,
        action="BATCH_CREATE_ITEMS",
        details=f"Created {len(items)} inventory items"
    )
    
    return new_items


@router.get("/categories/list")
async def get_categories(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all unique categories"""
    categories = db.query(InventoryItem.category)\
        .filter(InventoryItem.category.isnot(None))\
        .distinct()\
        .all()
    
    return [category[0] for category in categories]


@router.get("/low-stock/alerts")
async def get_low_stock_alerts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get items that are below reorder point"""
    low_stock_items = db.query(InventoryItem)\
        .filter(InventoryItem.quantity <= InventoryItem.reorder_point)\
        .all()
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "current_quantity": item.quantity,
            "reorder_point": item.reorder_point,
            "unit_price": item.price
        }
        for item in low_stock_items
    ]
