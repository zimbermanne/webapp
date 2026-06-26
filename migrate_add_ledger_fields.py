"""
One-off migration: adds company to debtors and invoice_no to creditors,
so the /api/ledgers endpoints in main.py can be backed by the real tables.
Safe to run multiple times (uses IF NOT EXISTS).

Usage:
    python migrate_add_ledger_fields.py
"""
from sqlalchemy import text
from database import engine

STATEMENTS = [
    "ALTER TABLE debtors ADD COLUMN IF NOT EXISTS company VARCHAR(200);",
    "ALTER TABLE creditors ADD COLUMN IF NOT EXISTS invoice_no VARCHAR(100);",
]


def run():
    with engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"Running: {stmt}")
            conn.execute(text(stmt))
    print("Migration complete.")


if __name__ == "__main__":
    run()
