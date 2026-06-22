from sqlalchemy.orm import Session
from models import ActivityLog
from datetime import datetime


async def log_activity(db: Session, user: str, action: str, details: str = ""):
    """Log user activity to the database"""
    try:
        activity_log = ActivityLog(
            user=user,
            action=action,
            details=details,
            timestamp=datetime.utcnow()
        )
        db.add(activity_log)
        db.commit()
    except Exception as e:
        # Log activity shouldn't break the main flow
        print(f"Error logging activity: {e}")
