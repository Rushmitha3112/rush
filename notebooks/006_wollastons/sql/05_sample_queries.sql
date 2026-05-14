-- ============================================================
-- Wollaston's Campus Market
-- Sample Analytical Queries  (interview / reporting ready)
-- ============================================================

-- ---- 1. Top 10 best-selling items this week ----------------
SELECT name, units_sold, revenue, gross_profit
  FROM vw_top_selling
 LIMIT 10;


-- ---- 2. Products that need reordering today ----------------
SELECT sku, name, qty_on_hand, reorder_level, reorder_qty,
       supplier, lead_days, expected_delivery
  FROM vw_low_stock
 ORDER BY qty_on_hand;


-- ---- 3. Daily revenue for the last 14 days -----------------
SELECT DATE(txn_time)            AS sale_date,
       COUNT(*)                  AS num_transactions,
       ROUND(SUM(total_amount), 2) AS daily_revenue
  FROM transactions
 WHERE txn_time >= CURRENT_DATE - INTERVAL '14 days'
 GROUP BY DATE(txn_time)
 ORDER BY sale_date;


-- ---- 4. Category margin ranking ----------------------------
SELECT category, revenue, gross_profit, margin_pct
  FROM vw_revenue_by_category;


-- ---- 5. Dining Dollars vs credit card basket comparison ----
SELECT method_name, num_transactions, avg_basket_size, pct_of_revenue
  FROM vw_payment_mix;


-- ---- 6. Peak hours by day of week  (staffing insight) ------
SELECT
    CASE day_of_week
        WHEN 0 THEN 'Sun' WHEN 1 THEN 'Mon' WHEN 2 THEN 'Tue'
        WHEN 3 THEN 'Wed' WHEN 4 THEN 'Thu' WHEN 5 THEN 'Fri'
        ELSE 'Sat'
    END                          AS weekday,
    hour_of_day                  AS hour,
    num_transactions,
    revenue
  FROM vw_hourly_sales
 ORDER BY day_of_week, hour_of_day;


-- ---- 7. Window function: running revenue by day ------------
SELECT
    DATE(txn_time)            AS sale_date,
    ROUND(SUM(total_amount), 2) AS daily_revenue,
    ROUND(
        SUM(SUM(total_amount)) OVER (ORDER BY DATE(txn_time)),
        2
    )                         AS running_total
  FROM transactions
 GROUP BY DATE(txn_time)
 ORDER BY sale_date;


-- ---- 8. Products never sold (dead stock) -------------------
SELECT sku, name, category, qty_on_hand, tied_up_cost
  FROM vw_dead_stock;


-- ---- 9. Supplier performance: avg lead vs low-stock events -
SELECT
    s.name                              AS supplier,
    s.lead_days,
    COUNT(ra.alert_id)                  AS reorder_alerts_fired,
    COUNT(CASE WHEN ra.resolved THEN 1 END) AS alerts_resolved
  FROM suppliers s
  LEFT JOIN products p  ON s.supplier_id = p.supplier_id
  LEFT JOIN reorder_alerts ra ON p.product_id = ra.product_id
 GROUP BY s.supplier_id, s.name, s.lead_days
 ORDER BY reorder_alerts_fired DESC;


-- ---- 10. CTE: high-value customers (Dining Dollars spend) --
WITH dining_spend AS (
    SELECT t.cashier_id,
           SUM(t.total_amount) AS total_spent
      FROM transactions t
      JOIN payment_methods pm ON t.method_id = pm.method_id
     WHERE pm.method_name = 'Dining Dollars'
     GROUP BY t.cashier_id
)
SELECT cashier_id,
       total_spent,
       RANK() OVER (ORDER BY total_spent DESC) AS spend_rank
  FROM dining_spend
 WHERE cashier_id IS NOT NULL
 ORDER BY spend_rank
 LIMIT 20;
