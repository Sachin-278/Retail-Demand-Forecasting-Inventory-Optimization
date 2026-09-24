# Day 6 – Aggregation & Data Marts

## Day 6 Work Completed

- Executed and validated the dbt aggregation models in BigQuery.
- Built/validated the daily sales intermediate model (`int_daily_sales`).
- Built/validated weekly sales aggregation (`int_weekly_sales`).
- Built/validated monthly sales aggregation (`int_monthly_sales`).
- Validated the `forecasting_input` data mart combining sales, calendar, and selling-price data.
- Resolved the BigQuery free-storage quota issue by materializing `forecasting_input` as a view instead of a table.
- Successfully executed the `forecasting_input` model.
- Previewed the final forecasting input data using dbt and confirmed that records were returned successfully.

## Day 6 Models

- `int_daily_sales`
- `int_weekly_sales`
- `int_monthly_sales`
- `forecasting_input`

## Execution Result

`forecasting_input` completed successfully:

- PASS: 1
- ERROR: 0
- Materialization: BigQuery View

## Status

Day 6 – Aggregation & Data Marts: Completed
