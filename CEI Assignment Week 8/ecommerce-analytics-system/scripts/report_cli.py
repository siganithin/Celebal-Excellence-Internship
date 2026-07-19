"""
report_cli.py
-------------
Command-line reporting tool for the E-Commerce Order Analytics System.

Connects to the SQLite database (ecommerce.db) and runs a named report,
printing the result as a formatted table using `tabulate`.

Usage:
    python report_cli.py --report revenue_by_month
    python report_cli.py --report top_customers --limit 5
    python report_cli.py --report retention
    python report_cli.py --list

Available reports:
    revenue_by_customer   Total revenue & order count per customer
    revenue_by_category   Total revenue per product category
    revenue_by_month      Total revenue per calendar month
    top_products          Top N products by revenue
    top_customers         Top N customers by lifetime value (RANK)
    aov_by_segment        Average order value by customer segment
    running_total         Monthly revenue running total + moving average
    growth_rate           Month-over-month revenue growth %
    cohort_retention      Monthly retention % per signup cohort
    frequency_segments    Customers grouped by purchase frequency
    spend_tiers           Customers grouped by spend tier
    rfm                   Full RFM segmentation
    order_status          Breakdown of orders by status
"""

import argparse
import os
import sqlite3
import sys

from tabulate import tabulate

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "ecommerce.db")

# ---------------------------------------------------------------------------
# Report registry: name -> (description, SQL, supports_limit)
# ---------------------------------------------------------------------------
REPORTS = {
    "revenue_by_customer": (
        "Total revenue and order count per customer",
        """
        SELECT c.customer_id, c.name, c.segment,
               ROUND(SUM(oi.line_total), 2) AS total_revenue,
               COUNT(DISTINCT o.order_id)   AS total_orders
        FROM customers c
        JOIN orders o       ON c.customer_id = o.customer_id
        JOIN order_items oi ON o.order_id    = oi.order_id
        WHERE o.status = 'completed'
        GROUP BY c.customer_id, c.name, c.segment
        ORDER BY total_revenue DESC
        {limit_clause}
        """,
        True,
    ),
    "revenue_by_category": (
        "Total revenue per product category",
        """
        SELECT p.category,
               ROUND(SUM(oi.line_total), 2) AS total_revenue,
               SUM(oi.quantity)             AS units_sold
        FROM order_items oi
        JOIN orders o   ON oi.order_id   = o.order_id
        JOIN products p ON oi.product_id = p.product_id
        WHERE o.status = 'completed'
        GROUP BY p.category
        ORDER BY total_revenue DESC
        """,
        False,
    ),
    "revenue_by_month": (
        "Total revenue per calendar month",
        """
        SELECT strftime('%Y-%m', o.order_date) AS month,
               ROUND(SUM(oi.line_total), 2)    AS total_revenue,
               COUNT(DISTINCT o.order_id)      AS orders_count
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.status = 'completed'
        GROUP BY month
        ORDER BY month
        """,
        False,
    ),
    "top_products": (
        "Top N products by revenue",
        """
        SELECT p.product_id, p.product_name, p.category,
               ROUND(SUM(oi.line_total), 2) AS total_revenue,
               SUM(oi.quantity)             AS total_units_sold
        FROM order_items oi
        JOIN orders o   ON oi.order_id   = o.order_id
        JOIN products p ON oi.product_id = p.product_id
        WHERE o.status = 'completed'
        GROUP BY p.product_id, p.product_name, p.category
        ORDER BY total_revenue DESC
        {limit_clause}
        """,
        True,
    ),
    "top_customers": (
        "Top N customers by lifetime value, with RANK",
        """
        WITH customer_ltv AS (
            SELECT c.customer_id, c.name, c.segment,
                   ROUND(SUM(oi.line_total), 2) AS lifetime_value
            FROM customers c
            JOIN orders o       ON c.customer_id = o.customer_id
            JOIN order_items oi ON o.order_id    = oi.order_id
            WHERE o.status = 'completed'
            GROUP BY c.customer_id, c.name, c.segment
        )
        SELECT customer_id, name, segment, lifetime_value,
               RANK() OVER (ORDER BY lifetime_value DESC) AS ltv_rank
        FROM customer_ltv
        ORDER BY lifetime_value DESC
        {limit_clause}
        """,
        True,
    ),
    "aov_by_segment": (
        "Average order value (AOV) by customer segment",
        """
        WITH order_totals AS (
            SELECT o.order_id, c.segment, SUM(oi.line_total) AS order_value
            FROM orders o
            JOIN customers c    ON o.customer_id = c.customer_id
            JOIN order_items oi ON o.order_id    = oi.order_id
            WHERE o.status = 'completed'
            GROUP BY o.order_id, c.segment
        )
        SELECT segment, COUNT(order_id) AS num_orders,
               ROUND(AVG(order_value), 2) AS avg_order_value
        FROM order_totals
        GROUP BY segment
        ORDER BY avg_order_value DESC
        """,
        False,
    ),
    "running_total": (
        "Monthly revenue with running total and 3-month moving average",
        """
        WITH monthly_revenue AS (
            SELECT strftime('%Y-%m', o.order_date) AS month,
                   ROUND(SUM(oi.line_total), 2) AS revenue
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.status = 'completed'
            GROUP BY month
        )
        SELECT month, revenue,
               ROUND(SUM(revenue) OVER (ORDER BY month), 2) AS running_total,
               ROUND(AVG(revenue) OVER (
                   ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
               ), 2) AS moving_avg_3mo
        FROM monthly_revenue
        ORDER BY month
        """,
        False,
    ),
    "growth_rate": (
        "Month-over-month revenue growth rate",
        """
        WITH monthly_revenue AS (
            SELECT strftime('%Y-%m', o.order_date) AS month,
                   SUM(oi.line_total) AS revenue
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.status = 'completed'
            GROUP BY month
        ),
        revenue_with_lag AS (
            SELECT month, revenue,
                   LAG(revenue) OVER (ORDER BY month) AS prev_month_revenue
            FROM monthly_revenue
        )
        SELECT month, ROUND(revenue, 2) AS revenue,
               ROUND(prev_month_revenue, 2) AS prev_month_revenue,
               CASE
                   WHEN prev_month_revenue IS NULL OR prev_month_revenue = 0 THEN NULL
                   ELSE ROUND(100.0 * (revenue - prev_month_revenue) / prev_month_revenue, 2)
               END AS mom_growth_pct
        FROM revenue_with_lag
        ORDER BY month
        """,
        False,
    ),
    "cohort_retention": (
        "Monthly retention percentage per signup cohort",
        """
        WITH first_purchase AS (
            SELECT c.customer_id, MIN(strftime('%Y-%m', o.order_date)) AS cohort_month
            FROM customers c
            JOIN orders o ON c.customer_id = o.customer_id
            WHERE o.status = 'completed'
            GROUP BY c.customer_id
        ),
        customer_activity AS (
            SELECT DISTINCT o.customer_id, strftime('%Y-%m', o.order_date) AS activity_month
            FROM orders o
            WHERE o.status = 'completed'
        ),
        cohort_activity AS (
            SELECT fp.cohort_month, fp.customer_id, ca.activity_month,
                   (CAST(strftime('%Y', ca.activity_month || '-01') AS INTEGER) * 12 +
                    CAST(strftime('%m', ca.activity_month || '-01') AS INTEGER))
                   -
                   (CAST(strftime('%Y', fp.cohort_month || '-01') AS INTEGER) * 12 +
                    CAST(strftime('%m', fp.cohort_month || '-01') AS INTEGER)) AS month_index
            FROM first_purchase fp
            JOIN customer_activity ca ON fp.customer_id = ca.customer_id
        ),
        cohort_sizes AS (
            SELECT cohort_month, COUNT(*) AS cohort_size
            FROM first_purchase
            GROUP BY cohort_month
        )
        SELECT ca.cohort_month, ca.month_index,
               COUNT(DISTINCT ca.customer_id) AS active_customers,
               cs.cohort_size,
               ROUND(100.0 * COUNT(DISTINCT ca.customer_id) / cs.cohort_size, 2) AS retention_pct
        FROM cohort_activity ca
        JOIN cohort_sizes cs ON ca.cohort_month = cs.cohort_month
        GROUP BY ca.cohort_month, ca.month_index
        ORDER BY ca.cohort_month, ca.month_index
        """,
        False,
    ),
    "frequency_segments": (
        "Customers grouped by purchase frequency (one-time / occasional / loyal)",
        """
        WITH customer_orders AS (
            SELECT customer_id, COUNT(order_id) AS num_orders
            FROM orders
            WHERE status = 'completed'
            GROUP BY customer_id
        )
        SELECT
            CASE
                WHEN num_orders = 1 THEN 'one-time'
                WHEN num_orders BETWEEN 2 AND 4 THEN 'occasional'
                ELSE 'loyal'
            END AS frequency_segment,
            COUNT(*) AS num_customers
        FROM customer_orders
        GROUP BY frequency_segment
        ORDER BY num_customers DESC
        """,
        False,
    ),
    "spend_tiers": (
        "Customers grouped by spend tier (low / medium / high)",
        """
        WITH customer_spend AS (
            SELECT c.customer_id, SUM(oi.line_total) AS total_spend
            FROM customers c
            JOIN orders o       ON c.customer_id = o.customer_id
            JOIN order_items oi ON o.order_id    = oi.order_id
            WHERE o.status = 'completed'
            GROUP BY c.customer_id
        )
        SELECT
            CASE
                WHEN total_spend < 100  THEN 'low'
                WHEN total_spend < 500  THEN 'medium'
                ELSE 'high'
            END AS spend_tier,
            COUNT(*) AS num_customers,
            ROUND(AVG(total_spend), 2) AS avg_spend_in_tier
        FROM customer_spend
        GROUP BY spend_tier
        ORDER BY avg_spend_in_tier DESC
        """,
        False,
    ),
    "rfm": (
        "Full RFM (Recency, Frequency, Monetary) customer segmentation",
        """
        WITH dataset_bounds AS (
            SELECT MAX(order_date) AS max_date FROM orders WHERE status = 'completed'
        ),
        rfm_raw AS (
            SELECT c.customer_id, c.name,
                   CAST(julianday((SELECT max_date FROM dataset_bounds)) - julianday(MAX(o.order_date)) AS INTEGER) AS recency_days,
                   COUNT(DISTINCT o.order_id) AS frequency,
                   ROUND(SUM(oi.line_total), 2) AS monetary
            FROM customers c
            JOIN orders o       ON c.customer_id = o.customer_id
            JOIN order_items oi ON o.order_id    = oi.order_id
            WHERE o.status = 'completed'
            GROUP BY c.customer_id, c.name
        ),
        rfm_scored AS (
            SELECT *,
                   NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
                   NTILE(5) OVER (ORDER BY frequency ASC)      AS f_score,
                   NTILE(5) OVER (ORDER BY monetary ASC)       AS m_score
            FROM rfm_raw
        )
        SELECT customer_id, name, recency_days, frequency, monetary,
               r_score, f_score, m_score, (r_score + f_score + m_score) AS rfm_total,
               CASE
                   WHEN (r_score + f_score + m_score) >= 13 THEN 'Champions'
                   WHEN (r_score + f_score + m_score) >= 10 THEN 'Loyal Customers'
                   WHEN (r_score + f_score + m_score) >= 7  THEN 'Potential Loyalists'
                   WHEN (r_score + f_score + m_score) >= 4  THEN 'At Risk'
                   ELSE 'Lost'
               END AS rfm_segment
        FROM rfm_scored
        ORDER BY rfm_total DESC
        {limit_clause}
        """,
        True,
    ),
    "order_status": (
        "Breakdown of all orders by status",
        """
        SELECT status, COUNT(*) AS num_orders,
               ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM orders), 2) AS pct_of_all_orders
        FROM orders
        GROUP BY status
        ORDER BY num_orders DESC
        """,
        False,
    ),
}


def get_connection():
    """Open a connection to the database, with friendly error handling."""
    if not os.path.exists(DB_PATH):
        print(f"ERROR: database not found at '{DB_PATH}'.")
        print("Run 'python load_to_db.py' first to create and populate it.")
        sys.exit(1)
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT 1")  # cheap connectivity check
        return conn
    except sqlite3.Error as e:
        print(f"ERROR: could not connect to database -> {e}")
        sys.exit(1)


def run_report(report_name, limit=None, out_file=None):
    if report_name not in REPORTS:
        print(f"ERROR: unknown report '{report_name}'.")
        print("Use --list to see available reports.")
        sys.exit(1)

    description, sql_template, supports_limit = REPORTS[report_name]

    limit_clause = ""
    if supports_limit and limit is not None:
        if limit <= 0:
            print("ERROR: --limit must be a positive integer.")
            sys.exit(1)
        limit_clause = f"LIMIT {limit}"

    sql = sql_template.format(limit_clause=limit_clause)

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        headers = [d[0] for d in cur.description]
    except sqlite3.Error as e:
        print(f"ERROR: query failed -> {e}")
        sys.exit(1)
    finally:
        conn.close()

    print(f"\nReport: {report_name}  -  {description}")
    print("=" * 70)

    # gracefully handle empty result sets
    if not rows:
        print("(no data available for this report)")
        return

    table_str = tabulate(rows, headers=headers, tablefmt="grid")
    print(table_str)
    print(f"\n{len(rows)} row(s) returned.")

    if out_file:
        with open(out_file, "w") as f:
            f.write(f"Report: {report_name} - {description}\n")
            f.write("=" * 70 + "\n")
            f.write(table_str + "\n")
            f.write(f"\n{len(rows)} row(s) returned.\n")
        print(f"Saved report to: {out_file}")


def list_reports():
    print("\nAvailable reports:")
    print("-" * 70)
    for name, (description, _, supports_limit) in REPORTS.items():
        flag = " (supports --limit)" if supports_limit else ""
        print(f"  {name:<22} {description}{flag}")
    print()


def main():
    parser = argparse.ArgumentParser(
        prog="report_cli.py",
        description="E-Commerce Order Analytics - CLI Reporting Tool",
    )
    parser.add_argument(
        "--report", "-r",
        type=str,
        help="Name of the report to run (use --list to see all options)",
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=10,
        help="Limit number of rows for reports that support it (default: 10)",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all available reports and exit",
    )
    parser.add_argument(
        "--out", "-o",
        type=str,
        default=None,
        help="Optional file path to also save the report output as text",
    )

    args = parser.parse_args()

    if args.list:
        list_reports()
        return

    if not args.report:
        parser.print_help()
        print("\nERROR: --report is required (or use --list to see options).")
        sys.exit(1)

    run_report(args.report.strip(), limit=args.limit, out_file=args.out)


if __name__ == "__main__":
    main()
