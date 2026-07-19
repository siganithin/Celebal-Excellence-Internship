-- cohort_analysis.sql
-- ---------------------------------------------------------------------
-- Step 6: Cohort & Retention Analysis
-- Step 7: Customer Segmentation (frequency, spend tier, RFM)
-- ---------------------------------------------------------------------

-- 1. Assign each customer to a cohort = month of their first completed order
WITH first_purchase AS (
    SELECT
        c.customer_id,
        MIN(strftime('%Y-%m', o.order_date)) AS cohort_month
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.status = 'completed'
    GROUP BY c.customer_id
)
SELECT cohort_month, COUNT(*) AS cohort_size
FROM first_purchase
GROUP BY cohort_month
ORDER BY cohort_month;


-- 2. Monthly retention rate per cohort
--    For every cohort, what % of the original customers placed a
--    completed order N months after their first purchase?
WITH first_purchase AS (
    SELECT
        c.customer_id,
        MIN(strftime('%Y-%m', o.order_date)) AS cohort_month
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.status = 'completed'
    GROUP BY c.customer_id
),
customer_activity AS (
    SELECT DISTINCT
        o.customer_id,
        strftime('%Y-%m', o.order_date) AS activity_month
    FROM orders o
    WHERE o.status = 'completed'
),
cohort_activity AS (
    SELECT
        fp.cohort_month,
        fp.customer_id,
        ca.activity_month,
        -- month index relative to cohort start (0 = signup/first purchase month)
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
SELECT
    ca.cohort_month,
    ca.month_index,
    COUNT(DISTINCT ca.customer_id)                                    AS active_customers,
    cs.cohort_size,
    ROUND(100.0 * COUNT(DISTINCT ca.customer_id) / cs.cohort_size, 2) AS retention_pct
FROM cohort_activity ca
JOIN cohort_sizes cs ON ca.cohort_month = cs.cohort_month
GROUP BY ca.cohort_month, ca.month_index
ORDER BY ca.cohort_month, ca.month_index;


-- 3. Churned vs repeat customers
--    "repeat" = 2+ completed orders, "one-time" = exactly 1,
--    "churned" = last completed order was more than 6 months before the
--    most recent order date in the whole dataset (proxy for "today")
WITH customer_orders AS (
    SELECT
        c.customer_id,
        COUNT(o.order_id)      AS num_orders,
        MAX(o.order_date)      AS last_order_date
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.status = 'completed'
    GROUP BY c.customer_id
),
dataset_bounds AS (
    SELECT MAX(order_date) AS max_date FROM orders WHERE status = 'completed'
)
SELECT
    co.customer_id,
    co.num_orders,
    co.last_order_date,
    CASE
        WHEN co.num_orders = 1 THEN 'one-time'
        WHEN co.num_orders > 1 THEN 'repeat'
    END AS purchase_type,
    CASE
        WHEN julianday(db.max_date) - julianday(co.last_order_date) > 180 THEN 'churned'
        ELSE 'active'
    END AS churn_status
FROM customer_orders co
CROSS JOIN dataset_bounds db
ORDER BY co.num_orders DESC;


-- 4. Customer segmentation by purchase frequency
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
ORDER BY num_customers DESC;


-- 5. Customer segmentation by spend tier
WITH customer_spend AS (
    SELECT
        c.customer_id,
        SUM(oi.line_total) AS total_spend
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
    COUNT(*)                    AS num_customers,
    ROUND(AVG(total_spend), 2)  AS avg_spend_in_tier
FROM customer_spend
GROUP BY spend_tier
ORDER BY avg_spend_in_tier DESC;


-- 6. RFM analysis (Recency, Frequency, Monetary) with 1-5 scoring
WITH dataset_bounds AS (
    SELECT MAX(order_date) AS max_date FROM orders WHERE status = 'completed'
),
rfm_raw AS (
    SELECT
        c.customer_id,
        c.name,
        CAST(julianday((SELECT max_date FROM dataset_bounds)) - julianday(MAX(o.order_date)) AS INTEGER) AS recency_days,
        COUNT(DISTINCT o.order_id)          AS frequency,
        ROUND(SUM(oi.line_total), 2)        AS monetary
    FROM customers c
    JOIN orders o       ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id    = oi.order_id
    WHERE o.status = 'completed'
    GROUP BY c.customer_id, c.name
),
rfm_scored AS (
    SELECT
        *,
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,   -- lower recency_days = more recent = higher score
        NTILE(5) OVER (ORDER BY frequency ASC)      AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC)       AS m_score
    FROM rfm_raw
)
SELECT
    customer_id,
    name,
    recency_days,
    frequency,
    monetary,
    r_score,
    f_score,
    m_score,
    (r_score + f_score + m_score) AS rfm_total,
    CASE
        WHEN (r_score + f_score + m_score) >= 13 THEN 'Champions'
        WHEN (r_score + f_score + m_score) >= 10 THEN 'Loyal Customers'
        WHEN (r_score + f_score + m_score) >= 7  THEN 'Potential Loyalists'
        WHEN (r_score + f_score + m_score) >= 4  THEN 'At Risk'
        ELSE 'Lost'
    END AS rfm_segment
FROM rfm_scored
ORDER BY rfm_total DESC;
