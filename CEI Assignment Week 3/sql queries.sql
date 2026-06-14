-- creating database for superstore database
CREATE DATABASE superstore_db;

-- using the created databse
USE superstore_db;

-- creating table for raw superstore data
CREATE TABLE superstore_raw (
    row_id INT,
    order_id VARCHAR(30),
    order_date VARCHAR(20),
    ship_date VARCHAR(20),
    ship_mode VARCHAR(50),

    customer_id VARCHAR(20),
    customer_name VARCHAR(100),
    segment VARCHAR(50),

    country VARCHAR(50),
    city VARCHAR(50),
    state VARCHAR(50),
    postal_code INT,
    region VARCHAR(50),

    product_id VARCHAR(30),
    category VARCHAR(50),
    sub_category VARCHAR(50),
    product_name VARCHAR(255),

    sales DECIMAL(10,2),
    quantity INT,
    discount DECIMAL(5,2),
    profit DECIMAL(10,2)
);

SELECT COUNT(*) FROM superstore_raw;


SELECT * FROM superstore_raw;


-- Creating customers table
CREATE TABLE customers (
    customer_id VARCHAR(20) PRIMARY KEY,
    customer_name VARCHAR(100),
    segment VARCHAR(50)
);

-- inserting data into customers table by  DISTINCT
INSERT INTO customers
SELECT DISTINCT
       customer_id,
       customer_name,
       segment
FROM superstore_raw;

SELECT COUNT(*) FROM customers;

SELECT * FROM customers LIMIT 10;

-- Creating products table
CREATE TABLE products (
    product_id VARCHAR(30) PRIMARY KEY,
    product_name VARCHAR(255),
    category VARCHAR(50),
    sub_category VARCHAR(50)
);

-- inserting data into products
INSERT INTO products
SELECT DISTINCT
       product_id,
       product_name,
       category,
       sub_category
FROM superstore_raw;

-- showing error with distinct

-- so drop the table and lets insert by grouping with product id

DROP TABLE IF EXISTS products;

CREATE TABLE products (
    product_id VARCHAR(30) PRIMARY KEY,
    product_name VARCHAR(255),
    category VARCHAR(50),
    sub_category VARCHAR(50)
);

INSERT INTO products
SELECT
    product_id,
    MAX(product_name),
    MAX(category),
    MAX(sub_category)
FROM superstore_raw
GROUP BY product_id;

SELECT * FROM products;

-- creating the orders table
CREATE TABLE orders (
    row_id INT,
    order_id VARCHAR(30),
    order_date VARCHAR(20),
    customer_id VARCHAR(20),
    product_id VARCHAR(30),
    sales DECIMAL(10,2),
    quantity INT,
    discount DECIMAL(5,2),
    profit DECIMAL(10,2)
);

INSERT INTO orders
SELECT
    row_id,
    order_id,
    order_date,
    customer_id,
    product_id,
    sales,
    quantity,
    discount,
    profit
FROM superstore_raw;

SELECT COUNT(*) AS total_orders
FROM orders;

SELECT * FROM orders
LIMIT 10;

-- TASK 1
-- Find all orders where sales are greater than average sales (Subquery)
SELECT *
FROM orders
WHERE sales >
(
    SELECT AVG(sales)
    FROM orders
);

-- Find the highest sales order for each customer (Subquery)
SELECT
    customer_id,
    MAX(sales) AS highest_order_value
FROM orders
GROUP BY customer_id;

-- Calculate Total Sales for Each Customer (CTE)
WITH customer_sales AS
(
    SELECT
        customer_id,
        SUM(sales) AS total_sales
    FROM orders
    GROUP BY customer_id
)
SELECT *
FROM customer_sales;

-- Customers Whose Total Sales Are Above Average
WITH customer_sales AS
(
    SELECT
        customer_id,
        SUM(sales) AS total_sales
    FROM orders
    GROUP BY customer_id
)
SELECT *
FROM customer_sales
WHERE total_sales >
(
    SELECT AVG(total_sales)
    FROM customer_sales
);

-- Rank all customers based on total sales (Window Function)
WITH customer_sales AS
(
    SELECT
        customer_id,
        SUM(sales) AS total_sales
    FROM orders
    GROUP BY customer_id
)
SELECT
    customer_id,
    total_sales,
    RANK() OVER(ORDER BY total_sales DESC) AS customer_rank
FROM customer_sales;


-- Assign row numbers to each order within a customer.(window function + partition by)
SELECT
    customer_id,
    order_id,
    sales,
    ROW_NUMBER() OVER
    (
        PARTITION BY customer_id
        ORDER BY sales DESC
    ) AS row_num
FROM orders;

-- Display Top 3 Customers Based on Total Sales
WITH customer_sales AS
(
    SELECT
        customer_id,
        SUM(sales) AS total_sales
    FROM orders
    GROUP BY customer_id
),
ranked_customers AS
(
    SELECT
        customer_id,
        total_sales,
        RANK() OVER(ORDER BY total_sales DESC) AS customer_rank
    FROM customer_sales
)
SELECT *
FROM ranked_customers
WHERE customer_rank <= 3;

-- Final Combined Query
-- Write one final query that shows: 
-- Customer Name  
-- Total Sales  
-- Rank  
-- (Use JOIN + CTE + Window Function together) 
WITH customer_sales AS
(
    SELECT
        customer_id,
        SUM(sales) AS total_sales
    FROM orders
    GROUP BY customer_id
)
SELECT
    c.customer_name,
    cs.total_sales,
    RANK() OVER(ORDER BY cs.total_sales DESC) AS customer_rank
FROM customer_sales cs
JOIN customers c
ON cs.customer_id = c.customer_id;

-- Mini Project
-- Top 5 Customers
WITH customer_sales AS
(
    SELECT
        customer_id,
        SUM(sales) AS total_sales
    FROM orders
    GROUP BY customer_id
)
SELECT *
FROM customer_sales
ORDER BY total_sales DESC
LIMIT 5;

-- Bottom 5 Customers
WITH customer_sales AS
(
    SELECT
        customer_id,
        SUM(sales) AS total_sales
    FROM orders
    GROUP BY customer_id
)
SELECT *
FROM customer_sales
ORDER BY total_sales ASC
LIMIT 5;

-- Customers Who Made Only One Order
SELECT
    customer_id,
    COUNT(DISTINCT order_id) AS total_orders
FROM orders
GROUP BY customer_id
HAVING COUNT(DISTINCT order_id) = 1;

-- Customers With Above Average Sales
WITH customer_sales AS
(
    SELECT
        customer_id,
        SUM(sales) AS total_sales
    FROM orders
    GROUP BY customer_id
)
SELECT *
FROM customer_sales
WHERE total_sales >
(
    SELECT AVG(total_sales)
    FROM customer_sales
);


-- Highest Order Value Per Customer
SELECT
    customer_id,
    MAX(sales) AS highest_order_value
FROM orders
GROUP BY customer_id;