-- window_functions.sql
-- ---------------------------------------------------------------------
-- Step 5: Window Functions & CTEs
-- ---------------------------------------------------------------------

-- 1. Rank customers by lifetime value (RANK vs DENSE_RANK)
WITH customer_ltv AS (
    SELECT
        c.customer_id,
        c.name,
        c.segment,
        ROUND(SUM(oi.line_total), 2) AS lifetime_value
    FROM customers c
    JOIN orders o       ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id    = oi.order_id
    WHERE o.status = 'completed'
    GROUP BY c.customer_id, c.name, c.segment
)
SELECT
    customer_id,
    name,
    segment,
    lifetime_value,
    RANK()       OVER (ORDER BY lifetime_value DESC) AS ltv_rank,
    DENSE_RANK() OVER (ORDER BY lifetime_value DESC) AS ltv_dense_rank,
    NTILE(4)     OVER (ORDER BY lifetime_value DESC) AS ltv_quartile   -- 1 = top spenders
FROM customer_ltv
ORDER BY lifetime_value DESC
LIMIT 25;


-- 2. Running total & 3-month moving average of monthly revenue
WITH monthly_revenue AS (
    SELECT
        strftime('%Y-%m', o.order_date) AS month,
        ROUND(SUM(oi.line_total), 2)    AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.status = 'completed'
    GROUP BY month
)
SELECT
    month,
    revenue,
    ROUND(SUM(revenue) OVER (ORDER BY month), 2) AS running_total,
    ROUND(AVG(revenue) OVER (
        ORDER BY month
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS moving_avg_3mo
FROM monthly_revenue
ORDER BY month;


-- 3. Month-over-month revenue growth rate (CTE -> CTE chain)
WITH monthly_revenue AS (
    SELECT
        strftime('%Y-%m', o.order_date) AS month,
        SUM(oi.line_total) AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.status = 'completed'
    GROUP BY month
),
revenue_with_lag AS (
    SELECT
        month,
        revenue,
        LAG(revenue) OVER (ORDER BY month) AS prev_month_revenue
    FROM monthly_revenue
)
SELECT
    month,
    ROUND(revenue, 2) AS revenue,
    ROUND(prev_month_revenue, 2) AS prev_month_revenue,
    CASE
        WHEN prev_month_revenue IS NULL OR prev_month_revenue = 0 THEN NULL
        ELSE ROUND(100.0 * (revenue - prev_month_revenue) / prev_month_revenue, 2)
    END AS mom_growth_pct
FROM revenue_with_lag
ORDER BY month;


-- 4. Each customer's order history with a running spend total per customer
--    (partitioned window function - useful for spotting spend acceleration)
SELECT
    c.customer_id,
    c.name,
    o.order_id,
    o.order_date,
    ROUND(order_value.value, 2) AS order_value,
    ROUND(
        SUM(order_value.value) OVER (
            PARTITION BY c.customer_id ORDER BY o.order_date
        ), 2
    ) AS running_customer_spend
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN (
    SELECT order_id, SUM(line_total) AS value
    FROM order_items
    GROUP BY order_id
) order_value ON o.order_id = order_value.order_id
WHERE o.status = 'completed'
ORDER BY c.customer_id, o.order_date
LIMIT 50;
