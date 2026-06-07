create database celebal_week2;

USE celebal_week2;

SHOW databases;

SHOW tables;

RENAME TABLE `sample - superstore`
TO superstore;

SELECT COUNT(*) FROM superstore;

DESCRIBE superstore;

SELECT * 
FROM superstore 
LIMIT 10;


SELECT COUNT(*) AS null_sales
FROM superstore
WHERE Sales IS NULL;

SELECT COUNT(*) AS null_profit
FROM superstore
WHERE Profit IS NULL;

SELECT COUNT(*) AS null_customer
FROM superstore
WHERE `Customer Name` IS NULL;


-- region wise sales
SELECT Region,
       SUM(Sales) AS total_sales
FROM superstore
GROUP BY Region
ORDER BY total_sales DESC;

-- category wise sales
SELECT Category,
       SUM(Sales) AS total_sales
FROM superstore
GROUP BY Category
ORDER BY total_sales DESC;

-- top 10 customers
SELECT `Customer Name`,
       SUM(Sales) AS total_sales
FROM superstore
GROUP BY `Customer Name`
ORDER BY total_sales DESC
LIMIT 10;

-- top 10 products
SELECT `Product Name`,
       SUM(Sales) AS total_sales
FROM superstore
GROUP BY `Product Name`
ORDER BY total_sales DESC
LIMIT 10;

-- region wise profit 
SELECT Region,
       SUM(Profit) AS total_profit
FROM superstore
GROUP BY Region
ORDER BY total_profit DESC;

-- category wise profit
SELECT Category,
       SUM(Profit) AS total_profit
FROM superstore
GROUP BY Category
ORDER BY total_profit DESC;

-- top 5 loss making products
SELECT `Product Name`,
       SUM(Profit) AS total_profit
FROM superstore
GROUP BY `Product Name`
ORDER BY total_profit ASC
LIMIT 5;

-- where filter for region 
SELECT *
FROM superstore
WHERE Region = 'South';

-- where filter for category
SELECT *
FROM superstore
WHERE Category = 'Technology';

-- where filter for sales
SELECT *
FROM superstore
WHERE Sales > 1000;

-- monthly sales trend
SELECT SUBSTRING(`Order Date`, 4, 7) AS month_year,
       SUM(Sales) AS total_sales
FROM superstore
GROUP BY month_year
ORDER BY month_year;

-- duplicate checking
SELECT `Order ID`,
       COUNT(*) AS duplicate_count
FROM superstore
GROUP BY `Order ID`
HAVING COUNT(*) > 1;