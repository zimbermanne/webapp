"""
Migration script to add company and invoice_no columns to debtors table
Run this to update existing databases with the new fields
"""
import sys
import os
from sqlalchemy import text
from database import engine

def migrate():
    """Add company and invoice_no columns to debtors table if they don't exist"""
    try:
        with engine.connect() as connection:
            # Check if company column exists
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'debtors' 
                AND column_name = 'company'
            """))
            
            if not result.fetchone():
                connection.execute(text("""
                    ALTER TABLE debtors 
                    ADD COLUMN company VARCHAR(200)
                """))
                print("Successfully added 'company' column to debtors table")
            else:
                print("Column 'company' already exists in debtors table")
            
            # Check if invoice_no column exists
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'debtors' 
                AND column_name = 'invoice_no'
            """))
            
            if not result.fetchone():
                connection.execute(text("""
                    ALTER TABLE debtors 
                    ADD COLUMN invoice_no VARCHAR(100)
                """))
                print("Successfully added 'invoice_no' column to debtors table")
            else:
                print("Column 'invoice_no' already exists in debtors table")
            
            connection.commit()
            
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
