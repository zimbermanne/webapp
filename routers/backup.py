from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import os
import zipfile
from datetime import datetime
import shutil
from pathlib import Path

from database import get_db
from models import User
from schemas import BackupInfo
from auth import require_admin
from activity import log_activity

router = APIRouter()

BACKUP_DIR = "backups"
DATA_FILES_TO_BACKUP = [
    "shop_management.db",  # PostgreSQL doesn't use this file, but keeping for structure
    # Add any other data files that need backing up
]


def ensure_backup_dir():
    """Ensure backup directory exists"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_backup(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a backup of the database and data files"""
    ensure_backup_dir()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{timestamp}.zip"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    try:
        # Create database backup using pg_dump (PostgreSQL specific)
        # This requires pg_dump to be installed and accessible
        import subprocess
        env_backup_file = f".env_backup_{timestamp}"
        
        # Backup environment file
        if os.path.exists(".env"):
            shutil.copy(".env", env_backup_file)
        
        # Create zip file
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add environment backup
            if os.path.exists(env_backup_file):
                zipf.write(env_backup_file, os.path.basename(env_backup_file))
            
            # Add any additional data files that exist
            for data_file in DATA_FILES_TO_BACKUP:
                if os.path.exists(data_file):
                    zipf.write(data_file, os.path.basename(data_file))
            
            # Note: For PostgreSQL, you would typically use pg_dump
            # This would require additional setup and configuration
        
        # Get file size
        file_size = os.path.getsize(backup_path)
        
        # Clean up temp files
        if os.path.exists(env_backup_file):
            os.remove(env_backup_file)
        
        # Log activity
        await log_activity(
            db=db,
            user=current_user.username,
            action="CREATE_BACKUP",
            details=f"Created backup: {backup_filename}"
        )
        
        return {
            "message": "Backup created successfully",
            "backup_filename": backup_filename,
            "backup_path": backup_path,
            "file_size": file_size,
            "created_at": timestamp
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create backup: {str(e)}"
        )


@router.get("/list", response_model=List[BackupInfo])
async def list_backups(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all available backups"""
    ensure_backup_dir()
    
    backups = []
    
    for filename in os.listdir(BACKUP_DIR):
        if filename.startswith("backup_") and filename.endswith(".zip"):
            file_path = os.path.join(BACKUP_DIR, filename)
            file_stat = os.stat(file_path)
            
            # Extract timestamp from filename
            try:
                timestamp_str = filename.replace("backup_", "").replace(".zip", "")
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            except:
                timestamp = datetime.fromtimestamp(file_stat.st_mtime)
            
            # Get list of files in backup
            files_included = []
            try:
                with zipfile.ZipFile(file_path, 'r') as zipf:
                    files_included = zipf.namelist()
            except:
                pass
            
            backups.append(BackupInfo(
                filename=filename,
                created_at=timestamp,
                size=file_stat.st_size,
                files_included=files_included
            ))
    
    # Sort by creation date (newest first)
    backups.sort(key=lambda x: x.created_at, reverse=True)
    
    return backups


@router.post("/restore/{backup_filename}")
async def restore_backup(
    backup_filename: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Restore a backup"""
    ensure_backup_dir()
    
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    if not os.path.exists(backup_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup file not found"
        )
    
    try:
        # Extract backup
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            zipf.extractall(".")
        
        # Note: For PostgreSQL, you would typically use pg_restore
        # This would require additional setup and configuration
        
        # Log activity
        await log_activity(
            db=db,
            user=current_user.username,
            action="RESTORE_BACKUP",
            details=f"Restored backup: {backup_filename}"
        )
        
        return {"message": f"Backup {backup_filename} restored successfully"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore backup: {str(e)}"
        )


@router.delete("/{backup_filename}")
async def delete_backup(
    backup_filename: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a backup file"""
    ensure_backup_dir()
    
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    if not os.path.exists(backup_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup file not found"
        )
    
    try:
        os.remove(backup_path)
        
        # Log activity
        await log_activity(
            db=db,
            user=current_user.username,
            action="DELETE_BACKUP",
            details=f"Deleted backup: {backup_filename}"
        )
        
        return {"message": f"Backup {backup_filename} deleted successfully"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete backup: {str(e)}"
        )


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_backup(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Upload a backup file"""
    ensure_backup_dir()
    
    # Validate file is a zip file
    if not file.filename.endswith('.zip'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only zip files are allowed"
        )
    
    try:
        # Save uploaded file
        file_path = os.path.join(BACKUP_DIR, file.filename)
        
        with open(file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Log activity
        await log_activity(
            db=db,
            user=current_user.username,
            action="UPLOAD_BACKUP",
            details=f"Uploaded backup: {file.filename}"
        )
        
        return {"message": f"Backup {file.filename} uploaded successfully"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload backup: {str(e)}"
        )
