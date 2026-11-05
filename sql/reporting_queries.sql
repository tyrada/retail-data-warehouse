-- Daily revenue trend
SELECT * FROM vw_daily_revenue ORDER BY full_date;

-- Ten products with the most revenue
SELECT * FROM vw_product_performance ORDER BY revenue DESC, product_id LIMIT 10;

-- Most active customers with at least five transactions
SELECT *
FROM vw_customer_activity
WHERE transaction_count >= 5
ORDER BY lifetime_revenue DESC, customer_id
LIMIT 20;

