// ============================================================
// Wollaston's Campus Market — Power BI Power Query M Scripts
// Paste each query into Power BI Desktop > Transform Data > Advanced Editor
// Connection: PostgreSQL localhost:5432 / database: wollastons
// ============================================================

// ---- Table: Products ----------------------------------------
let
    Source        = PostgreSQL.Database("localhost", "wollastons"),
    products_raw  = Source{[Schema="public", Item="products"]}[Data],
    renamed       = Table.RenameColumns(products_raw, {
                        {"product_id",    "ProductID"},
                        {"name",          "ProductName"},
                        {"sku",           "SKU"},
                        {"unit_price",    "UnitPrice"},
                        {"cost_price",    "CostPrice"},
                        {"reorder_level", "ReorderLevel"},
                        {"reorder_qty",   "ReorderQty"}
                    }),
    typed         = Table.TransformColumnTypes(renamed, {
                        {"UnitPrice",  Currency.Type},
                        {"CostPrice",  Currency.Type}
                    })
in
    typed


// ---- Table: Transactions (with date dimension) --------------
let
    Source       = PostgreSQL.Database("localhost", "wollastons"),
    txn_raw      = Source{[Schema="public", Item="transactions"]}[Data],
    add_date     = Table.AddColumn(txn_raw, "TxnDate",   each Date.From([txn_time]),   type date),
    add_hour     = Table.AddColumn(add_date, "TxnHour",  each Time.Hour([txn_time]),   type number),
    add_weekday  = Table.AddColumn(add_hour, "Weekday",  each Date.DayOfWeekName([TxnDate]), type text),
    renamed      = Table.RenameColumns(add_weekday, {
                       {"txn_id",       "TxnID"},
                       {"total_amount", "TotalAmount"},
                       {"method_id",    "PaymentMethodID"}
                   }),
    typed        = Table.TransformColumnTypes(renamed, {
                       {"TotalAmount", Currency.Type}
                   })
in
    typed


// ---- Table: Transaction Items --------------------------------
let
    Source   = PostgreSQL.Database("localhost", "wollastons"),
    raw      = Source{[Schema="public", Item="transaction_items"]}[Data],
    renamed  = Table.RenameColumns(raw, {
                   {"item_id",    "ItemID"},
                   {"txn_id",     "TxnID"},
                   {"product_id", "ProductID"},
                   {"qty",        "Quantity"},
                   {"unit_price", "SalePrice"}
               }),
    add_line = Table.AddColumn(renamed, "LineRevenue", each [Quantity] * [SalePrice], Currency.Type)
in
    add_line


// ---- Table: Inventory Snapshot ------------------------------
let
    Source   = PostgreSQL.Database("localhost", "wollastons"),
    raw      = Source{[Schema="public", Item="inventory"]}[Data],
    products = PostgreSQL.Database("localhost", "wollastons"){[Schema="public", Item="products"]}[Data],
    joined   = Table.Join(raw, "product_id", products, "product_id"),
    keep     = Table.SelectColumns(joined, {"product_id", "name", "qty_on_hand", "reorder_level", "last_updated"}),
    add_flag = Table.AddColumn(keep, "NeedsReorder",
                   each if [qty_on_hand] <= [reorder_level] then "Yes" else "No",
                   type text)
in
    add_flag


// ---- Table: Payment Methods ---------------------------------
let
    Source  = PostgreSQL.Database("localhost", "wollastons"),
    raw     = Source{[Schema="public", Item="payment_methods"]}[Data],
    renamed = Table.RenameColumns(raw, {
                  {"method_id",   "PaymentMethodID"},
                  {"method_name", "PaymentMethod"}
              })
in
    renamed


// ---- Table: Categories --------------------------------------
let
    Source  = PostgreSQL.Database("localhost", "wollastons"),
    raw     = Source{[Schema="public", Item="categories"]}[Data],
    renamed = Table.RenameColumns(raw, {
                  {"category_id", "CategoryID"},
                  {"name",        "CategoryName"}
              })
in
    renamed
