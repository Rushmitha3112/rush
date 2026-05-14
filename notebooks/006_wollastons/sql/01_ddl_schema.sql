-- ============================================================
-- Wollaston's Campus Market -- Northeastern University
-- Schema DDL  (works in PostgreSQL; SQLite notes in comments)
-- ============================================================

-- drop in reverse dependency order for reruns
DROP TABLE IF EXISTS reorder_alerts;
DROP TABLE IF EXISTS stock_audit_log;
DROP TABLE IF EXISTS transaction_items;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS payment_methods;
DROP TABLE IF EXISTS inventory;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS suppliers;
DROP TABLE IF EXISTS categories;

-- ------------------------------------------------------------
-- Reference tables
-- ------------------------------------------------------------
CREATE TABLE categories (
    category_id   SERIAL PRIMARY KEY,       -- INTEGER PRIMARY KEY AUTOINCREMENT in SQLite
    name          VARCHAR(60)  NOT NULL UNIQUE,
    description   TEXT
);

CREATE TABLE suppliers (
    supplier_id   SERIAL PRIMARY KEY,
    name          VARCHAR(120) NOT NULL,
    contact_email VARCHAR(120),
    lead_days     SMALLINT DEFAULT 2
);

-- ------------------------------------------------------------
-- Core product catalogue
-- ------------------------------------------------------------
CREATE TABLE products (
    product_id    SERIAL PRIMARY KEY,
    name          VARCHAR(120) NOT NULL,
    sku           VARCHAR(20)  NOT NULL UNIQUE,
    category_id   INT  REFERENCES categories(category_id),
    supplier_id   INT  REFERENCES suppliers(supplier_id),
    unit_price    NUMERIC(8,2) NOT NULL,
    cost_price    NUMERIC(8,2) NOT NULL,
    reorder_level INT  DEFAULT 10,
    reorder_qty   INT  DEFAULT 24,
    is_active     BOOLEAN DEFAULT TRUE
);

-- ------------------------------------------------------------
-- Inventory  (one row per product)
-- ------------------------------------------------------------
CREATE TABLE inventory (
    inventory_id  SERIAL PRIMARY KEY,
    product_id    INT  NOT NULL UNIQUE REFERENCES products(product_id),
    qty_on_hand   INT  NOT NULL DEFAULT 0,
    last_updated  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- Transactions
-- ------------------------------------------------------------
CREATE TABLE payment_methods (
    method_id     SERIAL PRIMARY KEY,
    method_name   VARCHAR(40) NOT NULL UNIQUE   -- 'Dining Dollars', 'NUCard', 'Credit/Debit', 'Cash'
);

CREATE TABLE transactions (
    txn_id        SERIAL PRIMARY KEY,
    txn_time      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cashier_id    INT,
    method_id     INT  REFERENCES payment_methods(method_id),
    total_amount  NUMERIC(10,2) NOT NULL DEFAULT 0
);

CREATE TABLE transaction_items (
    item_id       SERIAL PRIMARY KEY,
    txn_id        INT  NOT NULL REFERENCES transactions(txn_id),
    product_id    INT  NOT NULL REFERENCES products(product_id),
    qty           INT  NOT NULL CHECK (qty > 0),
    unit_price    NUMERIC(8,2) NOT NULL
);

-- ------------------------------------------------------------
-- Audit and alerting
-- ------------------------------------------------------------
CREATE TABLE stock_audit_log (
    log_id        SERIAL PRIMARY KEY,
    product_id    INT  REFERENCES products(product_id),
    change_qty    INT  NOT NULL,
    qty_after     INT  NOT NULL,
    reason        VARCHAR(200),
    logged_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reorder_alerts (
    alert_id      SERIAL PRIMARY KEY,
    product_id    INT  REFERENCES products(product_id),
    qty_at_alert  INT  NOT NULL,
    alerted_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved      BOOLEAN DEFAULT FALSE,
    resolved_at   TIMESTAMP
);

-- ------------------------------------------------------------
-- Indexes for common query patterns
-- ------------------------------------------------------------
CREATE INDEX idx_txn_items_product ON transaction_items(product_id);
CREATE INDEX idx_txn_items_txn     ON transaction_items(txn_id);
CREATE INDEX idx_inventory_product ON inventory(product_id);
CREATE INDEX idx_audit_product     ON stock_audit_log(product_id);
CREATE INDEX idx_reorder_resolved  ON reorder_alerts(resolved, product_id);
