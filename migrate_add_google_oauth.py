"""
Migration: Add Google OAuth fields to users table
Run once:  python migrate_add_google_oauth.py
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/shop_management")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

migrations = [
    # Make hashed_password nullable (Google users won't have one)
    "ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL;",
    # Add google_id column (skip if already exists)
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='users' AND column_name='google_id'
        ) THEN
            ALTER TABLE users ADD COLUMN google_id VARCHAR(100) UNIQUE;
            CREATE INDEX IF NOT EXISTS ix_users_google_id ON users(google_id);
        END IF;
    END $$;
    """,
    # Add auth_provider column (skip if already exists)
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='users' AND column_name='auth_provider'
        ) THEN
            ALTER TABLE users ADD COLUMN auth_provider VARCHAR(20) DEFAULT 'local';
        END IF;
    END $$;
    """,
]

with engine.connect() as conn:
    for sql in migrations:
        conn.execute(text(sql))
    conn.commit()

print("✅  Migration complete: google_id and auth_provider columns added.")
