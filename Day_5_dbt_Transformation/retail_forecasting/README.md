# Day 5 — dbt Staging & Data Transformation

This package continues the Retail Demand Forecasting & Inventory Optimization project.

## What Day 5 does

1. Converts the M5 wide sales table (`d_1` ... `d_1913`) into a long daily format.
2. Joins sales with the M5 calendar to obtain real dates.
3. Builds weekly sales aggregation.
4. Builds monthly sales aggregation.
5. Builds a `forecasting_input` data mart containing:
   - item/store identifiers
   - date
   - sales quantity
   - price
   - calendar attributes
   - event fields
   - SNAP indicators
6. Adds basic dbt schema tests for important fields.

## Expected dbt flow

Raw M5 tables
→ staging models
→ `int_daily_sales`
→ weekly/monthly aggregation
→ `forecasting_input`
→ Week 3 forecasting models

## Folder structure

```text
retail_forecasting/
├── dbt_project.yml
├── models/
│   ├── staging/
│   │   ├── sources.yml
│   │   ├── stg_calendar.sql
│   │   ├── stg_sell_prices.sql
│   │   ├── stg_sales_validation.sql
│   │   ├── stg_sales_long.sql
│   │   └── schema.yml
│   ├── intermediate/
│   │   ├── int_daily_sales.sql
│   │   ├── int_weekly_sales.sql
│   │   └── int_monthly_sales.sql
│   └── marts/
│       └── forecasting_input.sql
└── README.md
```

## Important

- The project is configured for BigQuery project `fresh-yen-508710-a0` and dataset `m5_raw`, matching the existing raw setup.
- Do not upload BigQuery credentials or `profiles.yml` to GitHub.
- This package is prepared for the project structure; it has not been executed against the user's live BigQuery environment here. Run dbt in the configured environment before claiming runtime success.
