"""
One-off migration: adds customer_address and customer_tin to the sales table.
Safe to run multiple times (uses IF NOT EXISTS).

Usage:
    python migrate_add_customer_fields.py
"""
from sqlalchemy import text
from database import engine

STATEMENTS = [
    "ALTER TABLE sales ADD COLUMN IF NOT EXISTS customer_address TEXT;",
    "ALTER TABLE sales ADD COLUMN IF NOT EXISTS customer_tin VARCHAR(50);",
    "ALTER TABLE sales ALTER COLUMN customer_name TYPE VARCHAR(200);",
]


def run():
    with engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"Running: {stmt}")
            conn.execute(text(stmt))
    print("Migration complete.")


if __name__ == "__main__":
    run()
