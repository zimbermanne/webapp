from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# 1. Fallback to your internal Railway link if the env variable isn't injected yet, 
# or use localhost for your local machine development.
if not DATABASE_URL:
    # Check if you are running locally or inside Railway
    if os.getenv("RAILWAY_ENVIRONMENT_NAME"): 
        # Inside Railway, use the internal link provided (replace user/pass/db as configured)
        DATABASE_URL = "postgresql://postgres:YOUR_PASSWORD@postgres-w6id.railway.internal:5432/shop_management"
    else:
        # Local machine development
        DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/shop_management"

# 2. Fix the "postgres://" to "postgresql://" protocol mismatch for SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    
