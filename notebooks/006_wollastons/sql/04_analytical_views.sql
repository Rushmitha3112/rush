-- ============================================================
-- Wollaston's Campus Market
-- Analytical Views
-- ============================================================

-- ------------------------------------------------------------
-- 1. Top-selling products  (units and revenue)
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW vw_top_selling AS
SELECT
    p.sku,
    p.name,
    c.name                                    AS category,
    SUM(ti.qty)                               AS units_sold,
    ROUND(SUM(ti.qty * ti.unit_price), 2)     AS revenue,
    ROUND(SUM(ti.qty * (p.unit_price - p.cost_price)), 2) AS gross_profit
FROM transaction_items ti
JOIN products  p ON ti.product_id = p.product_id
JOIN categories c ON p.category_id = c.category_id
GROUP BY p.product_id, p.sku, p.name, c.name
ORDER BY units_sold DESC;


-- ------------------------------------------------------------
-- 2. Dead stock  (products with zero sales)
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dead_stock AS
SELECT
    p.sku,
    p.name,
    c.name          AS category,
    i.qty_on_hand,
    i.last_updated,
    ROUND(i.qty_on_hand * p.cost_price, 2) AS tied_up_cost
FROM inventory i
JOIN products  p ON i.product_id = p.product_id
JOIN categories c ON p.category_id = c.category_id
WHERE p.product_id NOT IN (SELECT DISTINCT product_id FROM transaction_items)
  AND p.is_active = TRUE
ORDER BY tied_up_cost DESC;


-- ------------------------------------------------------------
-- 3. Low stock  (below reorder threshold)
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW vw_low_stock AS
SELECT
    p.sku,
    p.name,
    c.name             AS category,
    i.qty_on_hand,
    p.reorder_level,
    p.reorder_qty,
    s.name             AS supplier,
    s.lead_days,
    CURRENT_DATE + s.lead_days * INTERVAL '1 day' AS expected_delivery
FROM inventory i
JOIN products  p ON i.product_id = p.product_id
JOIN categories c ON p.category_id = c.category_id
JOIN suppliers  s ON p.supplier_id = s.supplier_id
WHERE i.qty_on_hand <= p.reorder_level
ORDER BY (i.qty_on_hand::FLOAT / NULLIF(p.reorder_level, 0));


-- ------------------------------------------------------------
-- 4. Revenue and margin by category
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW vw_revenue_by_category AS
SELECT
    c.name                                             AS category,
    COUNT(DISTINCT ti.txn_id)                         AS num_transactions,
    SUM(ti.qty)                                       AS units_sold,
    ROUND(SUM(ti.qty * ti.unit_price), 2)             AS revenue,
    ROUND(SUM(ti.qty * (p.unit_price - p.cost_price)), 2) AS gross_profit,
    ROUND(
        SUM(ti.qty * (p.unit_price - p.cost_price)) /
        NULLIF(SUM(ti.qty * ti.unit_price), 0) * 100,
        1
    )                                                  AS margin_pct
FROM transaction_items ti
JOIN products   p ON ti.product_id = p.product_id
JOIN categories c ON p.category_id = c.category_id
GROUP BY c.category_id, c.name
ORDER BY revenue DESC;


-- ------------------------------------------------------------
-- 5. Payment method mix
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW vw_payment_mix AS
SELECT
    pm.method_name,
    COUNT(t.txn_id)                      AS num_transactions,
    ROUND(SUM(t.total_amount), 2)        AS total_revenue,
    ROUND(AVG(t.total_amount), 2)        AS avg_basket_size,
    ROUND(SUM(t.total_amount) /
          NULLIF((SELECT SUM(total_amount) FROM transactions), 0) * 100, 1) AS pct_of_revenue
FROM transactions t
JOIN payment_methods pm ON t.method_id = pm.method_id
GROUP BY pm.method_id, pm.method_name
ORDER BY total_revenue DESC;


-- ------------------------------------------------------------
-- 6. Hourly sales trend  (useful for staffing decisions)
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW vw_hourly_sales AS
SELECT
    EXTRACT(DOW  FROM t.txn_time)  AS day_of_week,   -- 0=Sun
    EXTRACT(HOUR FROM t.txn_time)  AS hour_of_day,
    COUNT(t.txn_id)                AS num_transactions,
    ROUND(SUM(t.total_amount), 2)  AS revenue
FROM transactions t
GROUP BY 1, 2
ORDER BY 1, 2;


-- ------------------------------------------------------------
-- 7. Inventory turnover ratio  (last 30 days)
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW vw_inventory_turnover AS
SELECT
    p.sku,
    p.name,
    COALESCE(SUM(ti.qty), 0)                             AS units_sold_30d,
    i.qty_on_hand                                        AS current_stock,
    ROUND(
        COALESCE(SUM(ti.qty), 0)::NUMERIC /
        NULLIF((i.qty_on_hand + COALESCE(SUM(ti.qty), 0)) / 2.0, 0),
        2
    )                                                    AS turnover_ratio
FROM products  p
JOIN inventory i ON p.product_id = i.product_id
LEFT JOIN transaction_items ti ON p.product_id = ti.product_id
LEFT JOIN transactions t ON ti.txn_id = t.txn_id
    AND t.txn_time >= NOW() - INTERVAL '30 days'
GROUP BY p.product_id, p.sku, p.name, i.qty_on_hand
ORDER BY turnover_ratio DESC NULLS LAST;
