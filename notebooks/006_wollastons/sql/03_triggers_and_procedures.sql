-- ============================================================
-- Wollaston's Campus Market
-- Triggers and Stored Procedures  (PostgreSQL / PL/pgSQL)
-- ============================================================

-- ------------------------------------------------------------
-- FUNCTION: decrement inventory after a sale
-- Called by trigger trg_after_sale_item
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_decrement_inventory()
RETURNS TRIGGER AS $$
DECLARE
    v_qty_after INT;
    v_reorder   INT;
BEGIN
    -- subtract sold quantity
    UPDATE inventory
       SET qty_on_hand = qty_on_hand - NEW.qty,
           last_updated = NOW()
     WHERE product_id = NEW.product_id
    RETURNING qty_on_hand INTO v_qty_after;

    -- audit log every movement
    INSERT INTO stock_audit_log (product_id, change_qty, qty_after, reason)
    VALUES (NEW.product_id, -NEW.qty, v_qty_after, 'sale txn #' || NEW.txn_id);

    -- check if we just crossed the reorder threshold
    SELECT reorder_level INTO v_reorder
      FROM products WHERE product_id = NEW.product_id;

    IF v_qty_after <= v_reorder THEN
        -- only fire one alert per crossing (not if already active)
        IF NOT EXISTS (
            SELECT 1 FROM reorder_alerts
             WHERE product_id = NEW.product_id
               AND resolved = FALSE
        ) THEN
            INSERT INTO reorder_alerts (product_id, qty_at_alert)
            VALUES (NEW.product_id, v_qty_after);
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_after_sale_item
AFTER INSERT ON transaction_items
FOR EACH ROW EXECUTE FUNCTION fn_decrement_inventory();


-- ------------------------------------------------------------
-- FUNCTION: update transaction total after each item insert
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_update_txn_total()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE transactions
       SET total_amount = (
               SELECT COALESCE(SUM(qty * unit_price), 0)
                 FROM transaction_items
                WHERE txn_id = NEW.txn_id
           )
     WHERE txn_id = NEW.txn_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_txn_total
AFTER INSERT ON transaction_items
FOR EACH ROW EXECUTE FUNCTION fn_update_txn_total();


-- ------------------------------------------------------------
-- PROCEDURE: receive_stock  (manual stock-in from delivery)
-- Usage: CALL receive_stock(product_id, quantity_received, 'Aramark delivery');
-- ------------------------------------------------------------
CREATE OR REPLACE PROCEDURE receive_stock(
    p_product_id  INT,
    p_qty         INT,
    p_reason      VARCHAR DEFAULT 'stock replenishment'
)
LANGUAGE plpgsql AS $$
DECLARE
    v_qty_after INT;
BEGIN
    UPDATE inventory
       SET qty_on_hand = qty_on_hand + p_qty,
           last_updated = NOW()
     WHERE product_id = p_product_id
    RETURNING qty_on_hand INTO v_qty_after;

    INSERT INTO stock_audit_log (product_id, change_qty, qty_after, reason)
    VALUES (p_product_id, p_qty, v_qty_after, p_reason);

    -- resolve any open reorder alert for this product
    UPDATE reorder_alerts
       SET resolved = TRUE, resolved_at = NOW()
     WHERE product_id = p_product_id
       AND resolved = FALSE;

    RAISE NOTICE 'Stock received: product %, new qty = %', p_product_id, v_qty_after;
END;
$$;


-- ------------------------------------------------------------
-- PROCEDURE: process_transaction
-- Creates the transaction header + items in one call
-- Usage: CALL process_transaction(ARRAY[(1,1),(4,2)], 1);
--        means: product 1 qty 1, product 4 qty 2, paid by method 1
-- ------------------------------------------------------------
CREATE OR REPLACE PROCEDURE process_transaction(
    p_items       INT[][],   -- array of [product_id, qty] pairs
    p_method_id   INT,
    p_cashier_id  INT DEFAULT NULL
)
LANGUAGE plpgsql AS $$
DECLARE
    v_txn_id INT;
    v_pair   INT[];
    v_price  NUMERIC(8,2);
BEGIN
    -- create transaction header
    INSERT INTO transactions (cashier_id, method_id, total_amount)
    VALUES (p_cashier_id, p_method_id, 0)
    RETURNING txn_id INTO v_txn_id;

    -- insert each item (triggers handle inventory + audit + reorder)
    FOREACH v_pair SLICE 1 IN ARRAY p_items LOOP
        SELECT unit_price INTO v_price
          FROM products WHERE product_id = v_pair[1];

        INSERT INTO transaction_items (txn_id, product_id, qty, unit_price)
        VALUES (v_txn_id, v_pair[1], v_pair[2], v_price);
    END LOOP;

    RAISE NOTICE 'Transaction % processed, total = %',
        v_txn_id,
        (SELECT total_amount FROM transactions WHERE txn_id = v_txn_id);
END;
$$;
