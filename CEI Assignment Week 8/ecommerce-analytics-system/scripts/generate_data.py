"""
generate_data.py
-----------------
Generates a synthetic (but realistic-looking) e-commerce dataset made up of
four related tables: customers, products, orders, order_items.

Why "intentional inconsistencies"?
Real e-commerce data is never clean. This script deliberately injects the
kinds of problems you'd actually run into in production data:
    - missing values (nulls) in optional and semi-optional fields
    - duplicate rows (a customer signing up twice, an order pushed twice
      by a flaky retry mechanism, etc.)
    - orphan foreign keys (an order_item pointing to an order_id that
      doesn't exist, a product_id that was deleted)
    - invalid / inconsistent date formats and impossible dates
      (order date before the customer even signed up, future-dated orders)
    - inconsistent text casing / whitespace in emails and names
    - negative or zero quantities and prices from bad manual entry

Having these problems on purpose is the whole point of the assignment -
it gives the cleaning step (clean_data.py) something real to do.

Run:
    python generate_data.py
Output:
    ../data/raw/customers.csv
    ../data/raw/products.csv
    ../data/raw/orders.csv
    ../data/raw/order_items.csv
"""

import os
import random
from datetime import datetime, timedelta

import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

N_CUSTOMERS = 500
N_PRODUCTS = 120
N_ORDERS = 2500

SEGMENT_WEIGHTS = ["Regular"] * 6 + ["Premium"] * 3 + ["VIP"] * 1
CATEGORIES = [
    "Electronics", "Home & Kitchen", "Fashion", "Books",
    "Sports & Outdoors", "Beauty", "Toys", "Grocery",
]

DATE_START = datetime(2023, 1, 1)
DATE_END = datetime(2025, 12, 31)


def random_date(start, end):
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))


# ---------------------------------------------------------------------------
# 1. CUSTOMERS
# ---------------------------------------------------------------------------
def generate_customers(n=N_CUSTOMERS):
    rows = []
    for i in range(1, n + 1):
        signup_date = random_date(DATE_START, DATE_END - timedelta(days=30))
        name = fake.name()
        email = fake.email()

        # --- inject messiness ---
        # ~4% missing email
        if random.random() < 0.04:
            email = None
        # ~3% inconsistent casing / stray whitespace in email
        elif random.random() < 0.05:
            email = f"  {email.upper()}  "

        # ~3% missing country
        country = fake.country() if random.random() > 0.03 else None

        # ~2% missing signup date (stored as empty string, common CSV issue)
        signup_str = signup_date.strftime("%Y-%m-%d") if random.random() > 0.02 else ""

        rows.append({
            "customer_id": i,
            "name": name,
            "email": email,
            "country": country,
            "signup_date": signup_str,
            "segment": random.choice(SEGMENT_WEIGHTS),
        })

    df = pd.DataFrame(rows)

    # duplicate ~1.5% of customers (simulating double sign-ups / bad imports)
    dupes = df.sample(frac=0.015, random_state=1)
    df = pd.concat([df, dupes], ignore_index=True)

    return df


# ---------------------------------------------------------------------------
# 2. PRODUCTS
# ---------------------------------------------------------------------------
def generate_products(n=N_PRODUCTS):
    rows = []
    for i in range(1, n + 1):
        price = round(random.uniform(4.99, 899.99), 2)
        # ~2% of products have a null/garbled price
        if random.random() < 0.02:
            price = None
        # ~1% negative price (data entry error)
        elif random.random() < 0.01:
            price = -abs(price)

        category = random.choice(CATEGORIES) if random.random() > 0.02 else None

        rows.append({
            "product_id": i,
            "product_name": fake.catch_phrase(),
            "category": category,
            "price": price,
            "active": random.choice([1, 1, 1, 0]),  # some discontinued
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. ORDERS  (+ 4. ORDER_ITEMS)
# ---------------------------------------------------------------------------
def generate_orders_and_items(customers_df, products_df, n_orders=N_ORDERS):
    valid_customer_ids = customers_df["customer_id"].unique().tolist()
    valid_product_ids = products_df["product_id"].unique().tolist()

    order_rows = []
    item_rows = []
    item_id_counter = 1

    for order_id in range(1, n_orders + 1):
        customer_id = random.choice(valid_customer_ids)

        # ~1% of orders reference a customer_id that doesn't exist
        # (e.g. account was deleted after ordering -> orphan FK)
        if random.random() < 0.01:
            customer_id = max(valid_customer_ids) + random.randint(1, 50)

        order_date = random_date(DATE_START, DATE_END)

        # ~1% impossible / invalid dates
        r = random.random()
        if r < 0.005:
            order_date_str = "2099-13-45"          # malformed date
        elif r < 0.01:
            order_date_str = "2030-01-01"           # future-dated order
        else:
            order_date_str = order_date.strftime("%Y-%m-%d")

        status = random.choices(
            ["completed", "completed", "completed", "cancelled", "returned", "pending"],
            weights=[55, 15, 10, 10, 5, 5],
        )[0]

        order_rows.append({
            "order_id": order_id,
            "customer_id": customer_id,
            "order_date": order_date_str,
            "status": status,
        })

        # each order has 1-5 line items
        n_items = random.randint(1, 5)
        chosen_products = random.sample(valid_product_ids, min(n_items, len(valid_product_ids)))
        for product_id in chosen_products:
            quantity = random.randint(1, 4)
            # ~1.5% bad quantity (0 or negative -> data entry glitch)
            if random.random() < 0.015:
                quantity = random.choice([0, -1])

            product_price_row = products_df.loc[products_df["product_id"] == product_id, "price"]
            unit_price = product_price_row.values[0] if len(product_price_row) else None
            if pd.isna(unit_price):
                unit_price = round(random.uniform(4.99, 899.99), 2)

            item_rows.append({
                "order_item_id": item_id_counter,
                "order_id": order_id,
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": unit_price,
            })
            item_id_counter += 1

    orders_df = pd.DataFrame(order_rows)
    items_df = pd.DataFrame(item_rows)

    # duplicate ~1% of orders (retry / double submission bug)
    dupes = orders_df.sample(frac=0.01, random_state=2)
    orders_df = pd.concat([orders_df, dupes], ignore_index=True)

    # inject a handful of order_items with an order_id that doesn't exist
    # in the orders table at all (broken referential integrity)
    orphan_items = []
    max_order_id = orders_df["order_id"].max()
    for _ in range(15):
        orphan_items.append({
            "order_item_id": item_id_counter,
            "order_id": max_order_id + random.randint(100, 500),
            "product_id": random.choice(valid_product_ids),
            "quantity": random.randint(1, 3),
            "unit_price": round(random.uniform(4.99, 899.99), 2),
        })
        item_id_counter += 1
    items_df = pd.concat([items_df, pd.DataFrame(orphan_items)], ignore_index=True)

    return orders_df, items_df


def main():
    print("Generating customers...")
    customers_df = generate_customers()

    print("Generating products...")
    products_df = generate_products()

    print("Generating orders and order_items...")
    orders_df, items_df = generate_orders_and_items(customers_df, products_df)

    customers_df.to_csv(os.path.join(RAW_DIR, "customers.csv"), index=False)
    products_df.to_csv(os.path.join(RAW_DIR, "products.csv"), index=False)
    orders_df.to_csv(os.path.join(RAW_DIR, "orders.csv"), index=False)
    items_df.to_csv(os.path.join(RAW_DIR, "order_items.csv"), index=False)

    print("\nDone. Row counts (raw, includes intentional issues):")
    print(f"  customers.csv   : {len(customers_df)}")
    print(f"  products.csv    : {len(products_df)}")
    print(f"  orders.csv      : {len(orders_df)}")
    print(f"  order_items.csv : {len(items_df)}")


if __name__ == "__main__":
    main()
