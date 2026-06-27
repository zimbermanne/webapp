"""
Migration script to add buying_price column to sales table
Run this to update existing databases with the new buying_price field
"""
import sys
import os
from sqlalchemy import text
from database import engine

def migrate():
    """Add buying_price column to sales table if it doesn't exist"""
    try:
        with engine.connect() as connection:
            # Check if column already exists
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'sales' 
                AND column_name = 'buying_price'
            """))
            
            if result.fetchone():
                print("Column 'buying_price' already exists in sales table")
                return
            
            # Add the column
            connection.execute(text("""
                ALTER TABLE sales 
                ADD COLUMN buying_price FLOAT
            """))
            connection.commit()
            print("Successfully added 'buying_price' column to sales table")
            
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
