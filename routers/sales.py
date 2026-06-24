from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from database import get_db
from models import User, Sale, InventoryItem
from schemas import Sale as SaleSchema, SaleCreate
from auth import get_current_active_user
from activity import log_activity

router = APIRouter()


@router.post("/", response_model=SaleSchema, status_code=status.HTTP_201_CREATED)
async def create_sale(
    sale: SaleCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new sale"""
    # Check if inventory item exists
    item = db.query(InventoryItem).filter(InventoryItem.id == sale.item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    # Check if there's enough stock
    if item.quantity < sale.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock. Available: {item.quantity}, Requested: {sale.quantity}"
        )
    
    # Calculate total amount
    total_amount = sale.quantity * sale.unit_price
    
    # Create sale record
    new_sale = Sale(
        item_id=sale.item_id,
        quantity=sale.quantity,
        unit_price=sale.unit_price,
        total_amount=total_amount,
        customer_name=sale.customer_name,
        sale_date=datetime.utcnow(),
        created_by=current_user.username
    )
    
    # Update inventory quantity
    item.quantity -= sale.quantity
    item.updated_at = datetime.utcnow()
    
    db.add(new_sale)
    db.commit()
    db.refresh(new_sale)
    
    # Log activity
    await log_activity(
        db=db,
        user=current_user.username,
        action="CREATE_SALE",
        details=f"Sold {sale.quantity} units of {item.name} for {total_amount}"
    )
    
    return new_sale


@router.get("/", response_model=List[SaleSchema])
async def get_sales(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all sales with optional date filtering"""
    query = db.query(Sale)
    
    if start_date:
        query = query.filter(Sale.sale_date >= start_date)
    if end_date:
        query = query.filter(Sale.sale_date <= end_date)
    
    sales = query.order_by(Sale.sale_date.desc()).offset(skip).limit(limit).all()
    return sales


@router.get("/{sale_id}", response_model=SaleSchema)
async def get_sale(
    sale_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific sale by ID"""
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sale not found"
        )
    return sale


@router.get("/stats/summary")
async def get_sales_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get sales summary statistics"""
    query = db.query(Sale)
    
    if start_date:
        query = query.filter(Sale.sale_date >= start_date)
    if end_date:
        query = query.filter(Sale.sale_date <= end_date)
    
    sales = query.all()
    
    total_sales = len(sales)
    total_revenue = sum(sale.total_amount for sale in sales)
    total_quantity = sum(sale.quantity for sale in sales)
    
    # Average order value
    avg_order_value = total_revenue / total_sales if total_sales > 0 else 0
    
    return {
        "total_sales": total_sales,
        "total_revenue": total_revenue,
        "total_quantity_sold": total_quantity,
        "average_order_value": avg_order_value,
        "period_start": start_date,
        "period_end": end_date
    }


@router.get("/by-item/{item_id}", response_model=List[SaleSchema])
async def get_sales_by_item(
    item_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all sales for a specific item"""
    sales = db.query(Sale)\
        .filter(Sale.item_id == item_id)\
        .order_by(Sale.sale_date.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return sales


@router.delete("/{sale_id}")
async def delete_sale(
    sale_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a sale (and restore inventory)"""
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sale not found"
        )
    
    # Restore inventory quantity
    item = db.query(InventoryItem).filter(InventoryItem.id == sale.item_id).first()
    if item:
        item.quantity += sale.quantity
        item.updated_at = datetime.utcnow()
    
    sale_details = f"Sale of {sale.quantity} units for {sale.total_amount}"
    db.delete(sale)
    db.commit()
    
    # Log activity
    await log_activity(
        db=db,
        user=current_user.username,
        action="DELETE_SALE",
        details=f"Deleted sale: {sale_details}"
    )
    
    return {"message": "Sale deleted successfully and inventory restored"}
