-- =====================================================================
-- database.sql
-- Schema for Zimbermanne Retail OS Engine (webapp)
-- Generated to match models.py exactly. PostgreSQL 12+.
--
-- Usage:
--   For a FRESH database: psql -d shop_management -f database.sql
--   For an EXISTING database that's missing only the new sale fields,
--   use migrate_add_customer_fields.py instead -- running this file
--   against an existing DB is safe (IF NOT EXISTS guards) but won't
--   alter columns that already exist with different types.
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50)  NOT NULL UNIQUE,
    email           VARCHAR(100) UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    role            VARCHAR(20)  NOT NULL DEFAULT 'employee',  -- admin, manager, employee
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_users_username ON users (username);
CREATE INDEX IF NOT EXISTS ix_users_email    ON users (email);

-- ---------------------------------------------------------------------
-- inventory
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inventory (
    id             SERIAL PRIMARY KEY,
    name           VARCHAR(200) NOT NULL,
    quantity       INTEGER      NOT NULL DEFAULT 0,
    price          FLOAT        NOT NULL,
    buying_price   FLOAT,
    category       VARCHAR(100),
    reorder_point  INTEGER      NOT NULL DEFAULT 10,
    created_at     TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_inventory_name ON inventory (name);

-- ---------------------------------------------------------------------
-- sales
-- (customer_address / customer_tin are the fields added for the
--  customer-details-on-sale feature)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sales (
    id                SERIAL PRIMARY KEY,
    item_id           INTEGER      NOT NULL REFERENCES inventory(id),
    quantity          INTEGER      NOT NULL,
    unit_price        FLOAT        NOT NULL,
    buying_price      FLOAT,
    total_amount      FLOAT        NOT NULL,
    customer_name     VARCHAR(200),
    customer_address  TEXT,
    customer_tin      VARCHAR(50),
    sale_date         TIMESTAMP    NOT NULL DEFAULT NOW(),
    created_by        VARCHAR(50)  NOT NULL REFERENCES users(username)
);

CREATE INDEX IF NOT EXISTS ix_sales_sale_date ON sales (sale_date);
CREATE INDEX IF NOT EXISTS ix_sales_item_id   ON sales (item_id);

-- ---------------------------------------------------------------------
-- purchases
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS purchases (
    id             SERIAL PRIMARY KEY,
    item_id        INTEGER      NOT NULL REFERENCES inventory(id),
    quantity       INTEGER      NOT NULL,
    unit_cost      FLOAT        NOT NULL,
    total_cost     FLOAT        NOT NULL,
    supplier_name  VARCHAR(100),
    purchase_date  TIMESTAMP    NOT NULL DEFAULT NOW(),
    created_by     VARCHAR(50)  NOT NULL REFERENCES users(username)
);

CREATE INDEX IF NOT EXISTS ix_purchases_purchase_date ON purchases (purchase_date);

-- ---------------------------------------------------------------------
-- expenses
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS expenses (
    id            SERIAL PRIMARY KEY,
    category      VARCHAR(100) NOT NULL,
    amount        FLOAT        NOT NULL,
    description   TEXT,
    expense_date  TIMESTAMP    NOT NULL DEFAULT NOW(),
    created_by    VARCHAR(50)  NOT NULL REFERENCES users(username)
);

CREATE INDEX IF NOT EXISTS ix_expenses_category      ON expenses (category);
CREATE INDEX IF NOT EXISTS ix_expenses_expense_date   ON expenses (expense_date);

-- ---------------------------------------------------------------------
-- activity_logs
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_logs (
    id         SERIAL PRIMARY KEY,
    "user"     VARCHAR(50)  NOT NULL,
    action     VARCHAR(100) NOT NULL,
    details    TEXT,
    timestamp  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_activity_logs_user      ON activity_logs ("user");
CREATE INDEX IF NOT EXISTS ix_activity_logs_timestamp ON activity_logs (timestamp);

-- ---------------------------------------------------------------------
-- debtors
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS debtors (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    company     VARCHAR(200),
    invoice_no  VARCHAR(100),
    amount      FLOAT        NOT NULL,
    contact     VARCHAR(20),
    date_owed   TIMESTAMP    NOT NULL DEFAULT NOW(),
    status      VARCHAR(20)  NOT NULL DEFAULT 'pending',  -- pending, paid, partial
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- creditors
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS creditors (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    invoice_no  VARCHAR(100),
    amount      FLOAT        NOT NULL,
    contact     VARCHAR(20),
    date_owed   TIMESTAMP    NOT NULL DEFAULT NOW(),
    status      VARCHAR(20)  NOT NULL DEFAULT 'pending',  -- pending, paid, partial
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

COMMIT;

-- =====================================================================
-- Seed data
-- Don't hardcode a bcrypt hash here -- it can't be verified outside the
-- running app and a wrong hash would silently lock you out. Seed the
-- admin user one of these ways instead:
--
--   1. Run the project's own seeder (recommended):
--        python init_db.py
--      This creates admin/admin123 using the app's real password hasher.
--
--   2. Or register via the API after deploy:
--        POST /api/auth/register
--        {"username": "admin", "password": "your-password", "role": "admin"}
--
-- Either way, change the password immediately after first login.
-- =====================================================================

