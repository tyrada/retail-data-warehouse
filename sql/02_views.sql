CREATE OR REPLACE VIEW vw_daily_revenue AS
SELECT d.full_date,
       COUNT(*) AS line_count,
       SUM(f.quantity) AS units_sold,
       SUM(f.revenue) AS revenue
FROM fact_sales f
JOIN dim_date d ON d.date_key = f.date_key
GROUP BY d.full_date;

CREATE OR REPLACE VIEW vw_product_performance AS
SELECT p.product_id,
       p.product_name,
       p.category,
       COUNT(DISTINCT f.transaction_id) AS transaction_count,
       SUM(f.quantity) AS units_sold,
       SUM(f.revenue) AS revenue
FROM fact_sales f
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.product_id, p.product_name, p.category;

CREATE OR REPLACE VIEW vw_customer_activity AS
SELECT c.customer_id,
       c.customer_name,
       c.segment,
       COUNT(DISTINCT f.transaction_id) AS transaction_count,
       MIN(d.full_date) AS first_purchase_date,
       MAX(d.full_date) AS latest_purchase_date,
       SUM(f.revenue) AS lifetime_revenue
FROM fact_sales f
JOIN dim_customer c ON c.customer_key = f.customer_key
JOIN dim_date d ON d.date_key = f.date_key
GROUP BY c.customer_id, c.customer_name, c.segment;

