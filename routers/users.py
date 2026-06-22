from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import User
from schemas import User as UserSchema, UserCreate, UserUpdate
from auth import get_current_active_user, require_admin, get_password_hash
from activity import log_activity

router = APIRouter()


@router.get("/", response_model=List[UserSchema])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all users (admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/{username}", response_model=UserSchema)
async def get_user(
    username: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific user by username"""
    # Regular users can only see their own profile
    if current_user.role != "admin" and current_user.username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/{username}", response_model=UserSchema)
async def update_user(
    username: str,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user information"""
    # Regular users can only update their own profile
    if current_user.role != "admin" and current_user.username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    if user_update.email is not None:
        # Check if email is already taken by another user
        existing_email = db.query(User).filter(
            User.email == user_update.email,
            User.username != username
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        user.email = user_update.email
    
    if user_update.role is not None and current_user.role == "admin":
        user.role = user_update.role
    
    if user_update.password is not None:
        user.hashed_password = get_password_hash(user_update.password)
    
    db.commit()
    db.refresh(user)
    
    # Log activity
    await log_activity(
        db=db,
        user=current_user.username,
        action="UPDATE_USER",
        details=f"Updated user {username}"
    )
    
    return user


@router.delete("/{username}")
async def delete_user(
    username: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a user (admin only)"""
    if current_user.username == username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(user)
    db.commit()
    
    # Log activity
    await log_activity(
        db=db,
        user=current_user.username,
        action="DELETE_USER",
        details=f"Deleted user {username}"
    )
    
    return {"message": f"User {username} deleted successfully"}


@router.put("/{username}/activate")
async def activate_user(
    username: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Activate a user account (admin only)"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = True
    db.commit()
    
    # Log activity
    await log_activity(
        db=db,
        user=current_user.username,
        action="ACTIVATE_USER",
        details=f"Activated user {username}"
    )
    
    return {"message": f"User {username} activated successfully"}


@router.put("/{username}/deactivate")
async def deactivate_user(
    username: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Deactivate a user account (admin only)"""
    if current_user.username == username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = False
    db.commit()
    
    # Log activity
    await log_activity(
        db=db,
        user=current_user.username,
        action="DEACTIVATE_USER",
        details=f"Deactivated user {username}"
    )
    
    return {"message": f"User {username} deactivated successfully"}
