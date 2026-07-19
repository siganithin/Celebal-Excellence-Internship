-- aggregations.sql
-- ---------------------------------------------------------------------
-- Step 4: Joins & Aggregations
-- These queries answer basic but essential business questions using
-- JOINs and GROUP BY across customers / orders / order_items / products.
-- Only 'completed' orders are counted as revenue unless noted otherwise.
-- ---------------------------------------------------------------------

-- 1. Total revenue per customer
SELECT
    c.customer_id,
    c.name,
    c.segment,
    ROUND(SUM(oi.line_total), 2) AS total_revenue,
    COUNT(DISTINCT o.order_id)   AS total_orders
FROM customers c
JOIN orders o       ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id    = oi.order_id
WHERE o.status = 'completed'
GROUP BY c.customer_id, c.name, c.segment
ORDER BY total_revenue DESC;


-- 2. Total revenue per product category
SELECT
    p.category,
    ROUND(SUM(oi.line_total), 2) AS total_revenue,
    SUM(oi.quantity)             AS units_sold
FROM order_items oi
JOIN orders o    ON oi.order_id   = o.order_id
JOIN products p  ON oi.product_id = p.product_id
WHERE o.status = 'completed'
GROUP BY p.category
ORDER BY total_revenue DESC;


-- 3. Total revenue per month
SELECT
    strftime('%Y-%m', o.order_date) AS month,
    ROUND(SUM(oi.line_total), 2)    AS total_revenue,
    COUNT(DISTINCT o.order_id)      AS orders_count
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.status = 'completed'
GROUP BY month
ORDER BY month;


-- 4. Top 10 products by quantity sold
SELECT
    p.product_id,
    p.product_name,
    p.category,
    SUM(oi.quantity)             AS total_units_sold,
    ROUND(SUM(oi.line_total), 2) AS total_revenue
FROM order_items oi
JOIN orders o   ON oi.order_id   = o.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE o.status = 'completed'
GROUP BY p.product_id, p.product_name, p.category
ORDER BY total_units_sold DESC
LIMIT 10;


-- 5. Top 10 products by revenue
SELECT
    p.product_id,
    p.product_name,
    p.category,
    ROUND(SUM(oi.line_total), 2) AS total_revenue,
    SUM(oi.quantity)             AS total_units_sold
FROM order_items oi
JOIN orders o   ON oi.order_id   = o.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE o.status = 'completed'
GROUP BY p.product_id, p.product_name, p.category
ORDER BY total_revenue DESC
LIMIT 10;


-- 6. Average order value (AOV) by customer segment
WITH order_totals AS (
    SELECT
        o.order_id,
        c.segment,
        SUM(oi.line_total) AS order_value
    FROM orders o
    JOIN customers c    ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id    = oi.order_id
    WHERE o.status = 'completed'
    GROUP BY o.order_id, c.segment
)
SELECT
    segment,
    COUNT(order_id)             AS num_orders,
    ROUND(AVG(order_value), 2)  AS avg_order_value
FROM order_totals
GROUP BY segment
ORDER BY avg_order_value DESC;


-- 7. Order status breakdown (operational health check)
SELECT
    status,
    COUNT(*) AS num_orders,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM orders), 2) AS pct_of_all_orders
FROM orders
GROUP BY status
ORDER BY num_orders DESC;
