# Day 4 — dbt Setup

Project: Retail Demand Forecasting & Inventory Optimization

This folder starts the Week 2 dbt phase.

## BigQuery configuration

Project:
`fresh-yen-508710-a0`

Raw dataset:
`m5_raw`

dbt target dataset:
`m5_dbt`

## Included

- `dbt_project.yml`
- `models/staging/sources.yml`
- `stg_calendar.sql`
- `stg_sell_prices.sql`
- `stg_sales_validation.sql`

## Important

Do not upload local Google credentials or `profiles.yml` to GitHub.

The local dbt profile should point to:

- project: `fresh-yen-508710-a0`
- dataset: `m5_dbt`
- method: OAuth
- location: US

## Purpose

The raw M5 tables are registered as dbt sources and initial staging models are provided for the next transformation phase.
