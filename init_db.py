"""
Database initialization script.
Creates the database tables and seeds initial data.
"""
import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base, SessionLocal
from models import User
from auth import get_password_hash


def init_database():
    """Create all database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


def seed_admin_user():
    """Create default admin user if it doesn't exist"""
    db = SessionLocal()
    try:
        # Check if admin user already exists
        admin_user = db.query(User).filter(User.username == "admin").first()
        
        if admin_user:
            print("Admin user already exists. Skipping creation.")
            return
        
        # Create default admin user
        admin = User(
            username="admin",
            email="admin@shopmanagement.com",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(admin)
        db.commit()
        print("Default admin user created successfully!")
        print("Username: admin")
        print("Password: admin123")
        print("⚠️  IMPORTANT: Please change the default password after first login!")
        
    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    """Main initialization function"""
    print("=" * 50)
    print("Shop Management System - Database Initialization")
    print("=" * 50)
    
    try:
        init_database()
        seed_admin_user()
        
        print("\n" + "=" * 50)
        print("Database initialization completed successfully!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()