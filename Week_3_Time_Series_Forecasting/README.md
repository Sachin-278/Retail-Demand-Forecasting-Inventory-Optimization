# Week 3: Time-Series Forecasting

This folder implements the Week 3 forecasting steps against the Day 6 BigQuery
`forecasting_input` view. It creates a 28-day category/store Prophet forecast and,
when an item is selected, a recursive item/store LightGBM forecast.

## Setup

From the repository root, install the forecasting dependencies and authenticate
with the Google account that has BigQuery access:

```powershell
python -m pip install -r Week_3_Time_Series_Forecasting/requirements.txt
gcloud auth application-default login
```

## Run

Generate an aggregate forecast for one store/category:

```powershell
python Week_3_Time_Series_Forecasting/forecast.py --store CA_1 --category FOODS
```

Include the LightGBM item/store model by specifying an item ID:

```powershell
python Week_3_Time_Series_Forecasting/forecast.py --store CA_1 --category FOODS --item FOODS_1_001
```

The default output is `forecasts.csv` in the current directory. To also append
results to `fresh-yen-508710-a0.dbt_dev_sachin.forecasts`, add
`--write-bigquery`. The BigQuery option needs create-table/write access to the
output dataset. The script reads historical features from
`dbt_dev_sachin.forecasting_input` and future dates/prices from `m5_raw.Calendar`
and `m5_raw.sell_prices`.

The Prophet interval columns are model-generated uncertainty intervals. The
LightGBM point forecast does not claim prediction intervals and leaves those
columns empty. Its future lag features are generated recursively from earlier
predictions, and future selling prices use the M5 price for the relevant week;
when no future-week price is available, the last observed item price is used.

This is a scoped starter pipeline, not a claim of validated forecast accuracy.
Evaluate against a time-based holdout and tune at the required store/item scale
before using the output for inventory decisions.