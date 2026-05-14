-- ============================================================
-- Wollaston's Campus Market -- Seed Data
-- Realistic product catalogue based on actual store inventory
-- ============================================================

-- ------------------------------------------------------------
-- Categories
-- ------------------------------------------------------------
INSERT INTO categories (name, description) VALUES
    ('Grab & Go',      'Pre-made refrigerated sandwiches, wraps, salads, sushi'),
    ('Beverages',      'Cold drinks, energy drinks, juice, coffee, water'),
    ('Snacks',         'Chips, granola bars, candy, nuts, crackers'),
    ('Dairy & Frozen', 'Yogurt, milk, ice cream, frozen meals'),
    ('Personal Care',  'OTC medicine, deodorant, toothpaste, shampoo, feminine care'),
    ('School Supplies','Pens, notebooks, USB cables, chargers, headphones'),
    ('Fresh Produce',  'Whole fruit — banana, apple, orange');

-- ------------------------------------------------------------
-- Suppliers  (Aramark central + standard CPG distributors)
-- ------------------------------------------------------------
INSERT INTO suppliers (name, contact_email, lead_days) VALUES
    ('Aramark Central Kitchen',   'neu-ops@aramark.com',           1),
    ('Pepsi Beverages Northeast', 'orders-ne@pepsico.com',         2),
    ('Frito-Lay Northeast',       'northeast@fritolay.com',        2),
    ('Garelick Farms / DFA',      'orders@garelickfarms.com',      1),
    ('McKesson Health Products',  'campus@mckesson.com',           3),
    ('WB Mason Co.',              'northeastern@wbmason.com',      2),
    ('Boston Produce Terminal',   'wholesale@bostonproduce.com',   1),
    ('Red Bull North America',    'retail@redbull.com',            3),
    ('Kind LLC',                  'orders@kindsnacks.com',         4);

-- ------------------------------------------------------------
-- Products  (sku, category, supplier, unit_price, cost, reorder_level, reorder_qty)
-- ------------------------------------------------------------
INSERT INTO products (name, sku, category_id, supplier_id, unit_price, cost_price, reorder_level, reorder_qty) VALUES
    -- Grab & Go  (cat 1, supplier 1 = Aramark)
    ('Chicken Caesar Wrap',          'GG-001', 1, 1,  8.49, 3.20,  8, 12),
    ('Spicy Tuna Sushi Roll',        'GG-002', 1, 1,  7.99, 2.80,  6, 12),
    ('Caprese Sandwich',             'GG-003', 1, 1,  6.49, 2.40,  6, 12),
    ('Greek Salad Cup',              'GG-004', 1, 1,  6.99, 2.50,  5, 10),
    ('Turkey & Swiss Wrap',          'GG-005', 1, 1,  8.99, 3.40,  6, 12),

    -- Beverages  (cat 2, suppliers 2 and 8)
    ('Pepsi 20oz',                   'BV-001', 2, 2,  2.49, 0.80, 24, 48),
    ('Diet Coke 20oz',               'BV-002', 2, 2,  2.49, 0.80, 24, 48),
    ('Gatorade Glacier Freeze 32oz', 'BV-003', 2, 2,  3.29, 1.10, 18, 36),
    ('Gatorade Lemon-Lime 32oz',     'BV-004', 2, 2,  3.29, 1.10, 18, 36),
    ('Red Bull 8.4oz',               'BV-005', 2, 8,  3.99, 1.50, 12, 24),
    ('Red Bull Sugar Free 8.4oz',    'BV-006', 2, 8,  3.99, 1.50, 12, 24),
    ('Vita Coco Coconut Water',      'BV-007', 2, 2,  3.49, 1.20, 12, 24),
    ('Poland Spring Water 1L',       'BV-008', 2, 2,  1.99, 0.50, 36, 72),

    -- Snacks  (cat 3, suppliers 3 and 9)
    ('Lays Classic Chips 1oz',       'SN-001', 3, 3,  1.99, 0.70, 36, 72),
    ('Doritos Nacho Cheese 1.75oz',  'SN-002', 3, 3,  2.29, 0.80, 36, 72),
    ('Cheez-It Original 3oz',        'SN-003', 3, 3,  2.49, 0.90, 24, 48),
    ('KIND Bar Peanut Butter',       'SN-004', 3, 9,  2.49, 0.90, 24, 48),
    ('KIND Bar Dark Chocolate Nuts', 'SN-005', 3, 9,  2.49, 0.90, 24, 48),
    ('Nature Valley Granola Bar',    'SN-006', 3, 3,  1.79, 0.65, 24, 48),
    ('M&Ms Peanut 1.74oz',           'SN-007', 3, 3,  1.79, 0.65, 36, 72),
    ('Reeses PB Cups 1.5oz',         'SN-008', 3, 3,  1.79, 0.65, 36, 72),
    ('Skinny Pop Popcorn 1oz',       'SN-009', 3, 3,  1.99, 0.70, 24, 48),

    -- Dairy & Frozen  (cat 4, supplier 4)
    ('Chobani Greek Yogurt 5.3oz',   'DF-001', 4, 4,  2.29, 0.85, 15, 30),
    ('Yoplait Original Strawberry',  'DF-002', 4, 4,  1.79, 0.60, 12, 24),
    ('Garelick 2% Milk Pint',        'DF-003', 4, 4,  1.99, 0.70, 15, 30),
    ('Haagen-Dazs Vanilla Bar',      'DF-004', 4, 4,  3.99, 1.60, 10, 20),
    ('Ben & Jerrys Cup 4oz',         'DF-005', 4, 4,  4.49, 1.80,  8, 16),

    -- Personal Care  (cat 5, supplier 5)
    ('Advil Ibuprofen 24ct',         'PC-001', 5, 5,  9.99, 4.50,  5, 12),
    ('Tylenol Extra Strength 24ct',  'PC-002', 5, 5,  9.99, 4.50,  5, 12),
    ('Colgate Toothpaste Travel',    'PC-003', 5, 5,  3.49, 1.20,  8, 16),
    ('Secret Deodorant 1oz',         'PC-004', 5, 5,  6.49, 2.80,  6, 12),
    ('Band-Aid Variety 20ct',        'PC-005', 5, 5,  5.99, 2.50,  5, 10),
    ('Tampax Regular 10ct',          'PC-006', 5, 5,  7.99, 3.50,  5, 10),

    -- School Supplies  (cat 6, supplier 6)
    ('BIC Ballpoint Pen 4pk',        'SS-001', 6, 6,  3.99, 1.30, 10, 24),
    ('Mead Composition Notebook',    'SS-002', 6, 6,  4.99, 1.80,  8, 16),
    ('Post-it Notes 3x3 50ct',       'SS-003', 6, 6,  3.49, 1.20,  8, 16),
    ('USB-C Charging Cable 3ft',     'SS-004', 6, 6, 14.99, 5.50,  4,  8),
    ('Highlighter 4-Color Set',      'SS-005', 6, 6,  3.49, 1.20,  8, 16),

    -- Fresh Produce  (cat 7, supplier 7)
    ('Banana (each)',                'PR-001', 7, 7,  0.79, 0.25, 20, 50),
    ('Fuji Apple (each)',            'PR-002', 7, 7,  1.29, 0.45, 15, 40),
    ('Navel Orange (each)',          'PR-003', 7, 7,  1.29, 0.45, 12, 30);

-- ------------------------------------------------------------
-- Initial inventory stock levels
-- ------------------------------------------------------------
INSERT INTO inventory (product_id, qty_on_hand)
SELECT product_id,
       CASE
           WHEN sku LIKE 'GG-%' THEN 15
           WHEN sku LIKE 'BV-%' THEN 60
           WHEN sku LIKE 'SN-%' THEN 80
           WHEN sku LIKE 'DF-%' THEN 30
           WHEN sku LIKE 'PC-%' THEN 15
           WHEN sku LIKE 'SS-%' THEN 20
           WHEN sku LIKE 'PR-%' THEN 40
           ELSE 20
       END
FROM products;

-- ------------------------------------------------------------
-- Payment methods  (Aramark/Northeastern payment types)
-- ------------------------------------------------------------
INSERT INTO payment_methods (method_name) VALUES
    ('Dining Dollars'),
    ('NUCard'),
    ('Credit/Debit'),
    ('Cash');
