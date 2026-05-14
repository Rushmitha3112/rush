// ============================================================
// IEX India DAM Price Forecasting — Power BI Power Query M Scripts
// Paste each query into Power BI Desktop > Transform Data > Advanced Editor
// Source file: data/iex/iex_dam_merged.csv  (run notebook first to generate)
// ============================================================

// ---- Table: IEX DAM Raw (merged 2015-2022) ------------------
let
    Source        = Csv.Document(File.Contents("../../data/iex/iex_dam_merged.csv"),
                        [Delimiter=",", Columns=3, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    promoted      = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    typed         = Table.TransformColumnTypes(promoted, {
                        {"date",  type date},
                        {"block", Int64.Type},
                        {"mcp",   type number}
                    }),
    // derive datetime from date + 15-min block
    add_dt        = Table.AddColumn(typed, "BlockDateTime",
                        each DateTime.From([date]) + #duration(0, 0, ([block] - 1) * 15, 0),
                        type datetime),
    // hour of day (0-23)
    add_hour      = Table.AddColumn(add_dt, "HourOfDay",
                        each Number.IntegerDivide(([block] - 1) * 15, 60),
                        Int64.Type),
    // day of week name
    add_dow       = Table.AddColumn(add_hour, "DayOfWeek",
                        each Date.DayOfWeekName([date]),
                        type text),
    // weekend flag
    add_weekend   = Table.AddColumn(add_dow, "IsWeekend",
                        each Date.DayOfWeek([date], Day.Monday) >= 5,
                        type logical),
    // peak hour flag (08:00-16:00)
    add_peak      = Table.AddColumn(add_weekend, "IsPeakHour",
                        each [HourOfDay] >= 8 and [HourOfDay] < 16,
                        type logical),
    // COVID period flag
    add_covid     = Table.AddColumn(add_peak, "IsCOVIDPeriod",
                        each [date] >= #date(2020, 3, 25) and [date] <= #date(2020, 9, 30),
                        type logical)
in
    add_covid


// ---- Table: Daily Aggregates --------------------------------
let
    Source      = iex_dam,  // references the table above
    grouped     = Table.Group(Source, {"date"}, {
                      {"AvgMCP",    each List.Average([mcp]),  type number},
                      {"MaxMCP",    each List.Max([mcp]),      type number},
                      {"MinMCP",    each List.Min([mcp]),      type number},
                      {"StdDevMCP", each List.StandardDeviation([mcp]), type number},
                      {"Blocks",    each Table.RowCount(_),    Int64.Type}
                  }),
    add_year    = Table.AddColumn(grouped,  "Year",  each Date.Year([date]),  Int64.Type),
    add_month   = Table.AddColumn(add_year, "Month", each Date.Month([date]), Int64.Type),
    add_dow     = Table.AddColumn(add_month, "DayOfWeek",
                      each Date.DayOfWeekName([date]), type text),
    sorted      = Table.Sort(add_dow, {{"date", Order.Ascending}})
in
    sorted


// ---- Table: Monthly Aggregates ------------------------------
let
    Source      = iex_dam,
    add_year    = Table.AddColumn(Source,   "Year",  each Date.Year([date]),  Int64.Type),
    add_month   = Table.AddColumn(add_year, "Month", each Date.Month([date]), Int64.Type),
    grouped     = Table.Group(add_month, {"Year", "Month"}, {
                      {"AvgMCP",      each List.Average([mcp]),  type number},
                      {"MedianMCP",   each List.Median([mcp]),   type number},
                      {"MaxMCP",      each List.Max([mcp]),      type number},
                      {"TradingDays", each List.Count(List.Distinct([date])), Int64.Type}
                  }),
    add_key     = Table.AddColumn(grouped, "YearMonth",
                      each Text.From([Year]) & "-" & Text.PadStart(Text.From([Month]), 2, "0"),
                      type text),
    sorted      = Table.Sort(add_key, {{"Year", Order.Ascending}, {"Month", Order.Ascending}})
in
    sorted


// ---- Table: Intraday Profile (Block × DayType) -------------
let
    Source      = iex_dam,
    add_daytype = Table.AddColumn(Source, "DayType",
                      each if Date.DayOfWeek([date], Day.Monday) >= 5
                           then "Weekend" else "Weekday",
                      type text),
    grouped     = Table.Group(add_daytype, {"block", "DayType", "HourOfDay"}, {
                      {"AvgMCP",  each List.Average([mcp]),  type number},
                      {"Blocks",  each Table.RowCount(_),    Int64.Type}
                  }),
    sorted      = Table.Sort(grouped, {{"block", Order.Ascending}, {"DayType", Order.Ascending}})
in
    sorted


// ---- Table: Dates (Calendar dimension) ----------------------
let
    start_date  = #date(2015, 1, 1),
    end_date    = #date(2022, 12, 31),
    day_count   = Duration.Days(end_date - start_date) + 1,
    date_list   = List.Dates(start_date, day_count, #duration(1, 0, 0, 0)),
    date_table  = Table.FromList(date_list, Splitter.SplitByNothing(), {"date"}),
    typed       = Table.TransformColumnTypes(date_table, {{"date", type date}}),
    add_year    = Table.AddColumn(typed,    "Year",        each Date.Year([date]),              Int64.Type),
    add_month   = Table.AddColumn(add_year, "Month",       each Date.Month([date]),             Int64.Type),
    add_mname   = Table.AddColumn(add_month,"MonthName",   each Date.MonthName([date]),         type text),
    add_qtr     = Table.AddColumn(add_mname,"Quarter",     each Date.QuarterOfYear([date]),     Int64.Type),
    add_dow     = Table.AddColumn(add_qtr,  "DayOfWeek",   each Date.DayOfWeekName([date]),     type text),
    add_downum  = Table.AddColumn(add_dow,  "DayOfWeekNum",each Date.DayOfWeek([date], Day.Monday), Int64.Type),
    add_weekend = Table.AddColumn(add_downum,"IsWeekend",  each [DayOfWeekNum] >= 5,            type logical),
    add_yearmo  = Table.AddColumn(add_weekend,"YearMonth", each Text.From([Year]) & "-" & Text.PadStart(Text.From([Month]), 2, "0"), type text)
in
    add_yearmo
