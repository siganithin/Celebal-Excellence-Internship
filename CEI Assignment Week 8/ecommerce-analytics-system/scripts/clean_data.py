"""
clean_data.py
-------------
Loads the raw CSVs produced by generate_data.py, cleans them, validates
referential integrity across the four tables, and writes cleaned CSVs to
data/cleaned/.

Cleaning steps performed (mirrors a real-world pandas cleaning pipeline):
  customers
    - trim whitespace / lowercase emails, drop exact duplicate rows
    - drop rows with completely missing email (can't identify the customer)
    - parse signup_date, drop rows where it fails to parse
    - fill missing country with "Unknown"
  products
    - drop rows with missing or non-positive price (can't compute revenue)
    - fill missing category with "Uncategorized"
  orders
    - drop exact duplicate rows
    - parse order_date, drop rows with unparseable / impossible dates
    - drop rows with order_date in the future relative to "today" in the
      dataset's own time range (treated as invalid)
    - drop orders referencing a customer_id not present in customers
      (orphan foreign key)
  order_items
    - drop rows with quantity <= 0 (bad manual entry)
    - drop rows referencing an order_id not present in the cleaned orders
      table, or a product_id not present in the cleaned products table
      (referential integrity)
    - recompute line_total = quantity * unit_price for downstream use

At the end, the script prints a before/after row-count summary so the
impact of cleaning is visible and auditable.

Run:
    python clean_data.py
"""

import os

import pandas as pd

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
CLEAN_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned")
os.makedirs(CLEAN_DIR, exist_ok=True)


def load_raw():
    customers = pd.read_csv(os.path.join(RAW_DIR, "customers.csv"))
    products = pd.read_csv(os.path.join(RAW_DIR, "products.csv"))
    orders = pd.read_csv(os.path.join(RAW_DIR, "orders.csv"))
    order_items = pd.read_csv(os.path.join(RAW_DIR, "order_items.csv"))
    return customers, products, orders, order_items


def clean_customers(df):
    before = len(df)

    df = df.copy()
    df["email"] = df["email"].astype(str).str.strip().str.lower()
    df.loc[df["email"].isin(["nan", "none", ""]), "email"] = pd.NA

    # drop exact duplicate rows (same customer_id + email etc.)
    df = df.drop_duplicates()
    # drop duplicate customer_id, keep first occurrence
    df = df.drop_duplicates(subset="customer_id", keep="first")

    # can't do much with a customer we can't email/identify -> drop
    df = df.dropna(subset=["email"])

    df["country"] = df["country"].fillna("Unknown")

    df["signup_date"] = pd.to_datetime(df["signup_date"], errors="coerce")
    df = df.dropna(subset=["signup_date"])

    df["name"] = df["name"].astype(str).str.strip()

    after = len(df)
    print(f"customers: {before} -> {after} rows ({before - after} removed)")
    return df.reset_index(drop=True)


def clean_products(df):
    before = len(df)
    df = df.copy()

    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["price"])
    df = df[df["price"] > 0]

    df["category"] = df["category"].fillna("Uncategorized")
    df = df.drop_duplicates(subset="product_id", keep="first")

    after = len(df)
    print(f"products: {before} -> {after} rows ({before - after} removed)")
    return df.reset_index(drop=True)


def clean_orders(df, valid_customer_ids):
    before = len(df)
    df = df.copy()

    df = df.drop_duplicates()
    df = df.drop_duplicates(subset="order_id", keep="first")

    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df = df.dropna(subset=["order_date"])

    # drop future-dated orders (bad test/entry data) - use max plausible
    # date as a cutoff, since this is historical data generation, not "today"
    cutoff = pd.Timestamp("2025-12-31")
    df = df[df["order_date"] <= cutoff]

    # referential integrity: order must belong to a real customer
    df = df[df["customer_id"].isin(valid_customer_ids)]

    valid_status = {"completed", "cancelled", "returned", "pending"}
    df = df[df["status"].isin(valid_status)]

    after = len(df)
    print(f"orders: {before} -> {after} rows ({before - after} removed)")
    return df.reset_index(drop=True)


def clean_order_items(df, valid_order_ids, valid_product_ids):
    before = len(df)
    df = df.copy()

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df = df.dropna(subset=["quantity", "unit_price"])
    df = df[df["quantity"] > 0]
    df = df[df["unit_price"] > 0]

    # referential integrity
    df = df[df["order_id"].isin(valid_order_ids)]
    df = df[df["product_id"].isin(valid_product_ids)]

    df = df.drop_duplicates(subset="order_item_id", keep="first")

    df["line_total"] = (df["quantity"] * df["unit_price"]).round(2)

    after = len(df)
    print(f"order_items: {before} -> {after} rows ({before - after} removed)")
    return df.reset_index(drop=True)


def main():
    customers, products, orders, order_items = load_raw()

    print("Cleaning tables (before -> after row counts):\n")
    customers_clean = clean_customers(customers)
    products_clean = clean_products(products)
    orders_clean = clean_orders(orders, set(customers_clean["customer_id"]))
    order_items_clean = clean_order_items(
        order_items,
        set(orders_clean["order_id"]),
        set(products_clean["product_id"]),
    )

    # final safety check: every order in orders_clean should have >=1 item.
    # orders with zero items (e.g. all items were bad rows) are dropped
    # too, since an order with nothing in it isn't analytically useful.
    orders_with_items = set(order_items_clean["order_id"])
    dropped_empty_orders = len(orders_clean) - orders_clean["order_id"].isin(orders_with_items).sum()
    if dropped_empty_orders:
        print(f"orders: additionally dropping {dropped_empty_orders} orders with no valid line items")
    orders_clean = orders_clean[orders_clean["order_id"].isin(orders_with_items)].reset_index(drop=True)

    customers_clean.to_csv(os.path.join(CLEAN_DIR, "customers_clean.csv"), index=False)
    products_clean.to_csv(os.path.join(CLEAN_DIR, "products_clean.csv"), index=False)
    orders_clean.to_csv(os.path.join(CLEAN_DIR, "orders_clean.csv"), index=False)
    order_items_clean.to_csv(os.path.join(CLEAN_DIR, "order_items_clean.csv"), index=False)

    print("\nCleaned files written to data/cleaned/")
    print(f"  customers_clean.csv   : {len(customers_clean)} rows")
    print(f"  products_clean.csv    : {len(products_clean)} rows")
    print(f"  orders_clean.csv      : {len(orders_clean)} rows")
    print(f"  order_items_clean.csv : {len(order_items_clean)} rows")


if __name__ == "__main__":
    main()
