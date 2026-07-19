"""
load_to_db.py
--------------
Creates the SQLite database (ecommerce.db) from sql/schema.sql, then loads
the cleaned CSVs from data/cleaned/ into their respective tables.

Because the schema enforces PK / FK / CHECK constraints, this step acts as
a final integrity gate on top of the pandas cleaning already done - if
anything slipped through, the INSERT will fail loudly instead of silently
corrupting the database.

Run:
    python load_to_db.py
"""

import os
import sqlite3

import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CLEAN_DIR = os.path.join(BASE_DIR, "data", "cleaned")
SQL_DIR = os.path.join(BASE_DIR, "sql")
DB_PATH = os.path.join(BASE_DIR, "ecommerce.db")


def build_schema(conn):
    with open(os.path.join(SQL_DIR, "schema.sql"), "r") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)


def load_table(conn, csv_name, table_name, columns):
    df = pd.read_csv(os.path.join(CLEAN_DIR, csv_name))
    df = df[columns]
    df.to_sql(table_name, conn, if_exists="append", index=False)
    return len(df)


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")

    print("Building schema...")
    build_schema(conn)

    print("Loading customers...")
    n_customers = load_table(
        conn, "customers_clean.csv", "customers",
        ["customer_id", "name", "email", "country", "signup_date", "segment"],
    )

    print("Loading products...")
    n_products = load_table(
        conn, "products_clean.csv", "products",
        ["product_id", "product_name", "category", "price", "active"],
    )

    print("Loading orders...")
    n_orders = load_table(
        conn, "orders_clean.csv", "orders",
        ["order_id", "customer_id", "order_date", "status"],
    )

    print("Loading order_items...")
    n_items = load_table(
        conn, "order_items_clean.csv", "order_items",
        ["order_item_id", "order_id", "product_id", "quantity", "unit_price", "line_total"],
    )

    conn.commit()

    # verification: row counts + a couple of relationship sanity checks
    cur = conn.cursor()
    print("\nVerification:")
    for table in ["customers", "products", "orders", "order_items"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table:<14}: {cur.fetchone()[0]} rows loaded (expected {locals().get('n_' + table)})")

    cur.execute("""
        SELECT COUNT(*) FROM order_items oi
        LEFT JOIN orders o ON oi.order_id = o.order_id
        WHERE o.order_id IS NULL
    """)
    orphan_items = cur.fetchone()[0]
    print(f"  orphan order_items (no matching order): {orphan_items}")

    cur.execute("""
        SELECT COUNT(*) FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.customer_id
        WHERE c.customer_id IS NULL
    """)
    orphan_orders = cur.fetchone()[0]
    print(f"  orphan orders (no matching customer):   {orphan_orders}")

    conn.close()
    print(f"\nDatabase ready at: {DB_PATH}")


if __name__ == "__main__":
    main()
