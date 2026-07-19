-- schema.sql
-- ---------------------------------------------------------------------
-- Database schema for the E-Commerce Order Analytics System.
-- Target engine: SQLite (works unmodified on MySQL/Postgres with minor
-- type tweaks, e.g. AUTOINCREMENT -> AUTO_INCREMENT / SERIAL).
-- ---------------------------------------------------------------------

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id   INTEGER PRIMARY KEY,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    country       TEXT    NOT NULL DEFAULT 'Unknown',
    signup_date   DATE    NOT NULL,
    segment       TEXT    NOT NULL CHECK (segment IN ('Regular', 'Premium', 'VIP'))
);

CREATE TABLE products (
    product_id    INTEGER PRIMARY KEY,
    product_name  TEXT    NOT NULL,
    category      TEXT    NOT NULL DEFAULT 'Uncategorized',
    price         REAL    NOT NULL CHECK (price > 0),
    active        INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE orders (
    order_id      INTEGER PRIMARY KEY,
    customer_id   INTEGER NOT NULL,
    order_date    DATE    NOT NULL,
    status        TEXT    NOT NULL CHECK (status IN ('completed', 'cancelled', 'returned', 'pending')),
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);

CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id      INTEGER NOT NULL,
    product_id    INTEGER NOT NULL,
    quantity      INTEGER NOT NULL CHECK (quantity > 0),
    unit_price    REAL    NOT NULL CHECK (unit_price > 0),
    line_total    REAL    NOT NULL,
    FOREIGN KEY (order_id)   REFERENCES orders (order_id),
    FOREIGN KEY (product_id) REFERENCES products (product_id)
);

CREATE INDEX idx_orders_customer_id   ON orders (customer_id);
CREATE INDEX idx_orders_order_date    ON orders (order_date);
CREATE INDEX idx_items_order_id       ON order_items (order_id);
CREATE INDEX idx_items_product_id     ON order_items (product_id);
