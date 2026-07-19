# E-Commerce Order Analytics System

**Celebal Technologies Excellence Internship — Week 8 Mini Project**
Track: Data Engineering (DE)

## About this project

For this week's assignment I built a small end-to-end analytics pipeline for
e-commerce order data, going all the way from raw (messy) data generation to
a working command-line reporting tool backed by SQL. The goal was to
practice the full lifecycle a data engineer actually deals with day to day:

1. data doesn't arrive clean — it has nulls, duplicates, broken
   relationships and bad formatting, and you have to deal with that before
   you can trust any analysis built on top of it,
2. once it's clean, a proper relational schema with constraints keeps it
   trustworthy going forward, and
3. the whole point of collecting the data is to answer real business
   questions — revenue trends, who your best customers are, who's coming
   back and who isn't — so I wired all of that up behind a simple CLI
   instead of leaving it as one-off notebook queries.

I didn't have access to a real e-commerce dataset for this exercise (the
original project brief pointed to a resource file I couldn't open), so
instead of stalling on that I generated a synthetic dataset myself using
Faker — but I made sure it isn't a "clean" toy dataset. I deliberately
seeded it with the kind of problems real data actually has (see
[Data quality issues injected](#data-quality-issues-injected-on-purpose)
below), so the cleaning step in this project is solving a real problem, not
just running `.dropna()` on data that never needed it.

## System architecture

```
Raw CSV generation (Faker)
        │
        ▼
Pandas cleaning & validation  ──►  data/cleaned/*.csv
        │
        ▼
SQLite schema (PK / FK / CHECK constraints)  ──►  ecommerce.db
        │
        ▼
SQL analytics (joins, CTEs, window functions, cohort analysis)
        │
        ▼
CLI reporting tool (report_cli.py)  ──►  formatted tables in the terminal
```

Each stage writes its output to disk before the next stage reads it, so you
can inspect the data at any point in the pipeline — nothing is a black box.

### Why these 4 tables

- **customers** — one row per shopper: name, email, country, signup date,
  and a segment (Regular / Premium / VIP) assigned at signup.
- **products** — the catalog: name, category, price, and whether it's
  still active/for sale.
- **orders** — one row per order: which customer placed it, when, and its
  status (completed / cancelled / returned / pending).
- **order_items** — the line items inside each order (product, quantity,
  unit price). Revenue is always computed from here, not from `orders`,
  since a single order can contain several products.

This is a standard star-like structure: `order_items` is the fact table
that fans out revenue, `orders`/`customers`/`products` are the surrounding
dimension-ish tables.

## Data quality issues injected on purpose

So the cleaning step in `clean_data.py` has real work to do, `generate_data.py`
intentionally introduces:

| Issue | Where |
|---|---|
| Missing values (nulls) | emails, countries, signup dates, prices, categories |
| Duplicate rows | duplicate customers, duplicate orders |
| Inconsistent formatting | stray whitespace / mixed case in emails |
| Orphan foreign keys | orders pointing at customer IDs that don't exist; order_items pointing at order IDs that don't exist |
| Invalid / impossible dates | malformed date strings, future-dated orders |
| Bad numeric values | zero/negative quantities, negative prices |

`clean_data.py` handles every one of these explicitly (see the docstring at
the top of that file for the full list of rules), and prints a before/after
row count for each table so you can see exactly how much was removed and
why.

## Project structure

```
## Project structure

```
ecommerce-analytics-system/
│── data/
│   ├── raw/
│   │   ├── customers.csv
│   │   ├── products.csv
│   │   ├── orders.csv
│   │   └── order_items.csv
│   ├── cleaned/
│   │   ├── customers_clean.csv
│   │   ├── products_clean.csv
│   │   ├── orders_clean.csv
│   │   └── order_items_clean.csv
│
│── output/
│   ├── revenue_by_customer.txt
│   ├── revenue_by_category.txt
│   ├── revenue_by_month.txt
│   ├── top_products.txt
│   ├── top_customers.txt
│   ├── aov_by_segment.txt
│   ├── running_total.txt
│   ├── growth_rate.txt
│   ├── cohort_retention.txt
│   ├── frequency_segments.txt
│   ├── spend_tiers.txt
│   ├── rfm.txt
│   └── order_status.txt
│
│── scripts/
│   ├── generate_data.py
│   ├── clean_data.py
│   ├── load_to_db.py
│   └── report_cli.py
│
│── sql/
│   ├── schema.sql
│   ├── aggregations.sql
│   ├── window_functions.sql
│   └── cohort_analysis.sql
│
│── ecommerce.db
└── README.md
```

## How to run it end to end

From the `scripts/` folder, run these four steps in order:

```bash
# 1. install dependencies
pip install faker pandas tabulate

# 2. generate the raw (intentionally messy) dataset
python generate_data.py

# 3. clean it and validate referential integrity
python clean_data.py

# 4. build the SQLite schema and load the cleaned data
python load_to_db.py
```

After that, `ecommerce.db` exists in the project root and you can query it
directly, or use the CLI tool below.

### Using the CLI reporting tool

```bash
# see every report that's available
python report_cli.py --list

# run a report
python report_cli.py --report revenue_by_month

# reports that rank/limit results support --limit (default 10)
python report_cli.py --report top_customers --limit 5

# save a report to a text file as well as printing it
python report_cli.py --report rfm --limit 20 --out ../output/rfm_top20.txt
``````

**Available reports:**

| Report name | What it shows |
|---|---|
| `revenue_by_customer` | Revenue & order count per customer |
| `revenue_by_category` | Revenue per product category |
| `revenue_by_month` | Revenue per calendar month |
| `top_products` | Top N products by revenue |
| `top_customers` | Top N customers by lifetime value, ranked with `RANK()` |
| `aov_by_segment` | Average order value by Regular/Premium/VIP segment |
| `running_total` | Monthly revenue with running total + 3-month moving average |
| `growth_rate` | Month-over-month revenue growth % |
| `cohort_retention` | Retention % per signup-month cohort, month by month |
| `frequency_segments` | Customers split into one-time / occasional / loyal |
| `spend_tiers` | Customers split into low / medium / high spend tiers |
| `rfm` | Full Recency-Frequency-Monetary scoring & segment labels |
| `order_status` | Breakdown of orders by status (completed/cancelled/etc.) |

Sample output for every report above is included in the `output/` folder so you can review the generated reports without rerunning the pipeline.

## Edge cases the CLI tool handles

I specifically tested and handled these, since a reporting tool that
crashes on bad input isn't very useful:

- **Missing database** — if `ecommerce.db` doesn't exist yet (pipeline not
  run), the tool prints a clear message telling you to run `load_to_db.py`
  first, instead of a raw traceback.
- **Unknown report name** — prints an error and points you to `--list`.
- **Invalid `--limit`** (zero or negative) — rejected with a clear message
  before it ever reaches the database.
- **No arguments given** — prints usage/help instead of failing silently.
- **Empty result sets** — e.g. querying a report on a database state where
  a segment has no customers — prints `(no data available for this
  report)` instead of an empty/broken table.
- **Database connection errors** — wrapped in a try/except with a readable
  error message instead of a raw stack trace.
- I also validated the pipeline itself against edge cases like orders with
  zero valid line items after cleaning (they get dropped so they don't
  distort revenue numbers) and orphaned foreign keys on both `orders` and
  `order_items` (verified as zero after loading, see the console output of
  `load_to_db.py`).

## Sample output

Here's what `top_customers` looks like when you run it:

```
Report: top_customers  -  Top N customers by lifetime value, with RANK
======================================================================
+---------------+------------------+-----------+------------------+------------+
|   customer_id | name             | segment   |   lifetime_value |   ltv_rank |
+===============+==================+===========+==================+============+
|            76 | Sandra Sanchez   | Regular   |          34241.9 |          1 |
+---------------+------------------+-----------+------------------+------------+
|           452 | Catherine Miller | Premium   |          31044.7 |          2 |
+---------------+------------------+-----------+------------------+------------+
|            73 | Michael Elliott  | Regular   |          30650.5 |          3 |
+---------------+------------------+-----------+------------------+------------+
```
More full examples (all 13 reports) are saved as plain text in the
`output/` folder.

## Tech used

Python 3, Pandas, Faker, SQLite3, `tabulate`, argparse.
