# M5 Dataset Structure

## Overview

The M5 Walmart dataset is used for retail demand forecasting and inventory optimization. It contains historical sales, calendar information, and selling prices.

## Dataset Files

| File | Purpose |
|---|---|
| sales_train_validation.csv | Historical daily sales data |
| sales_train_evaluation.csv | Sales data used for evaluation/forecasting |
| calendar.csv | Dates, weekdays, months, years, events and SNAP information |
| sell_prices.csv | Product selling prices by store and week |
| sample_submission.csv | Submission format provided with the dataset |

## 1. Sales Dataset

**File:** `sales_train_validation.csv`

**Shape:** 30,490 rows × 1,919 columns

### Identifier Columns

- `id` – Unique item-store identifier
- `item_id` – Product identifier
- `dept_id` – Department identifier
- `cat_id` – Product category
- `store_id` – Store identifier
- `state_id` – State identifier

### Daily Sales Columns

Columns from `d_1` to `d_1913` represent daily unit sales.

Each row represents an item-store combination, while the daily columns contain the number of units sold on each day.

## 2. Calendar Dataset

**File:** `calendar.csv`

**Shape:** 1,969 rows × 14 columns

Important columns include:

- `date` – Calendar date
- `wm_yr_wk` – Walmart year-week identifier
- `weekday` – Day of the week
- `wday` – Numeric weekday
- `month` – Month number
- `year` – Year
- `d` – Dataset day identifier
- `event_name_1`, `event_type_1` – Primary event information
- `event_name_2`, `event_type_2` – Secondary event information
- `snap_CA`, `snap_TX`, `snap_WI` – SNAP availability indicators for each state

## 3. Sell Prices Dataset

**File:** `sell_prices.csv`

**Shape:** 6,841,121 rows × 4 columns

Columns:

- `store_id` – Store identifier
- `item_id` – Product identifier
- `wm_yr_wk` – Walmart year-week identifier
- `sell_price` – Product selling price

## Dataset Relationships

The datasets are connected through common identifiers:

- Sales ↔ Calendar: `d`
- - Sales ↔ Sell Prices: `store_id`, `item_id`, and `wm_yr_wk`
- Calendar ↔ Sell Prices: `wm_yr_wk`

These relationships will be important during the ETL and transformation stages.

## Data Quality Summary

Initial inspection and cleaning checks were performed on the three core datasets.

- Calendar `date` was converted to datetime format.
- Missing event values were replaced with `"No Event"`.
- Sales data contained no missing values.
- Sales data contained no negative values.
- Sell prices contained no missing, zero, or negative values.
- Duplicate checks were performed on the relevant dataset keys.
- No unnecessary rows were removed because the validation checks did not identify invalid records.

## ETL Relevance

The M5 datasets will be used as the raw data layer for the ETL pipeline.

- Sales data provides historical daily demand.
- Calendar data provides dates, weekdays, events and SNAP information.
- Sell prices provides product prices by store and week.
- These datasets will be integrated using their common identifiers during the transformation stage.