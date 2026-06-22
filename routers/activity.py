from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from database import get_db
from models import User, ActivityLog
from schemas import ActivityLog as ActivityLogSchema
from auth import require_manager_or_admin

router = APIRouter()


@router.get("/", response_model=List[ActivityLogSchema])
async def get_activity_logs(
    skip: int = 0,
    limit: int = 100,
    user: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Get activity logs (manager/admin only)"""
    query = db.query(ActivityLog)
    
    # Filter by user if specified
    if user:
        query = query.filter(ActivityLog.user == user)
    
    # Filter by action if specified
    if action:
        query = query.filter(ActivityLog.action == action)
    
    # Filter by date range if specified
    if start_date:
        query = query.filter(ActivityLog.timestamp >= start_date)
    if end_date:
        query = query.filter(ActivityLog.timestamp <= end_date)
    
    # Order by timestamp descending
    query = query.order_by(ActivityLog.timestamp.desc())
    
    logs = query.offset(skip).limit(limit).all()
    return logs


@router.get("/stats")
async def get_activity_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Get activity statistics (manager/admin only)"""
    query = db.query(ActivityLog)
    
    # Default to last 7 days if no dates specified
    if not start_date and not end_date:
        start_date = datetime.utcnow() - timedelta(days=7)
        query = query.filter(ActivityLog.timestamp >= start_date)
    else:
        if start_date:
            query = query.filter(ActivityLog.timestamp >= start_date)
        if end_date:
            query = query.filter(ActivityLog.timestamp <= end_date)
    
    total_logs = query.count()
    
    # Get logs by user
    user_counts = {}
    for log in query.all():
        user_counts[log.user] = user_counts.get(log.user, 0) + 1
    
    # Get logs by action
    action_counts = {}
    for log in query.all():
        action_counts[log.action] = action_counts.get(log.action, 0) + 1
    
    return {
        "total_logs": total_logs,
        "user_counts": user_counts,
        "action_counts": action_counts,
        "period_start": start_date or datetime.utcnow(),
        "period_end": end_date or datetime.utcnow()
    }


@router.get("/user/{username}", response_model=List[ActivityLogSchema])
async def get_user_activity_logs(
    username: str,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Get activity logs for a specific user (manager/admin only)"""
    logs = db.query(ActivityLog)\
        .filter(ActivityLog.user == username)\
        .order_by(ActivityLog.timestamp.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return logs
