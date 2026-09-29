# Week 3: Time-Series Forecasting

This module consumes the `forecasting_input` mart produced by the Day 5/6 dbt project.

## Models

- `forecast_prophet_aggregates` fits a Prophet model for each state/department aggregate, using M5 event dates as holiday regressors. It returns point forecasts and Prophet uncertainty bounds.
- `train_lightgbm` builds one pooled item-store model using 7/28-day lags, rolling statistics, calendar fields, event/SNAP flags, selling price, and available hierarchy IDs.
- `forecast_lightgbm` recursively predicts each item-store series. Pass `future_features` with known future prices, event names, and SNAP flags to improve forecasts; absent future covariates default to the last known price and no event/SNAP flag.
- `evaluate_lightgbm` uses a time-ordered holdout and reports MAE, RMSE, and WAPE without training on future target values.
- `evaluate_prophet_aggregates` evaluates state/department forecasts on the same time-ordered holdout.
- `write_forecasts_to_bigquery` appends future forecasts and held-out predictions (with actual quantities) to a BigQuery table with optional bounds, model name, and generation timestamp.
- `write_metrics_to_bigquery` appends each model's holdout horizon, MAE, RMSE, WAPE, and evaluated row count to `dbt_dev_sachin.forecast_metrics`.

The CLI defaults to a deterministic sample of 100 item-store series to keep local runtime and BigQuery query costs bounded. Increase `--max-series` to scale up, or set it to `0` to process the full mart; the full M5 mart can require substantial memory and compute.

## Run from VS Code

Activate the repository virtual environment and authenticate as a Google account with BigQuery Job User, BigQuery Data Viewer on `m5_raw`, and BigQuery Data Editor on `dbt_dev_sachin`:

```powershell
gcloud auth application-default login
python -m pip install -r Week_3_Time_Series_Forecasting/requirements.txt
python Week_3_Time_Series_Forecasting/forecast.py --horizon 28 --max-series 100
```

Override the mart/output table names as needed:

```powershell
python Week_3_Time_Series_Forecasting/forecast.py `
  --input-table fresh-yen-508710-a0.dbt_dev_sachin.forecasting_input `
  --output-table dbt_dev_sachin.forecasts `
  --horizon 28 `
  --max-series 100
```

## Test

```powershell
python -m unittest discover -s Week_3_Time_Series_Forecasting/tests -v
```

The CLI requires BigQuery Job User and Service Usage Consumer on the query project, Data Viewer on `m5_raw`, and Data Editor on the output dataset. Live execution also requires ADC credentials configured for the same Google account that has those roles.