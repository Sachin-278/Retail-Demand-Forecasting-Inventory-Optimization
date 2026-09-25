# Day 7 — dbt Documentation & Data Lineage

## Objective
Document the dbt transformation pipeline and make model dependencies easy to understand.

## Intended lineage

Raw M5 tables
→ staging models
→ daily sales transformation
→ weekly/monthly aggregations
→ forecasting_input
→ Week 3 forecasting models

### Main dependencies

- `stg_sales_long` → `int_daily_sales`
- `stg_calendar` → `int_daily_sales`
- `int_daily_sales` → `int_weekly_sales`
- `int_daily_sales` → `int_monthly_sales`
- `int_daily_sales` → `forecasting_input`
- `stg_calendar` → `forecasting_input`
- `stg_sell_prices` → `forecasting_input`

## Why lineage matters

Lineage helps trace a forecast input back to its source and transformation.
It also makes debugging easier when dates, sales, prices or joins produce
unexpected results.

## Generate dbt documentation

Run these commands from the dbt project directory:

```bash
dbt docs generate
dbt docs serve
```

Then review the generated DAG and model documentation.

## Day 7 checklist

- Model descriptions added.
- Important columns documented.
- Raw → staging → mart lineage documented.
- dbt documentation generated.
- DAG reviewed.
- No credentials or `profiles.yml` committed.
