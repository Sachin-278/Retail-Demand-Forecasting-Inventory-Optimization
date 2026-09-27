"""Generate scoped M5 demand forecasts with Prophet and LightGBM."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

FEATURES = [
    "lag_7",
    "lag_28",
    "rolling_mean_7",
    "rolling_std_7",
    "day_of_week",
    "month",
    "is_event",
    "snap",
    "sell_price",
]


def add_training_features(frame: pd.DataFrame, snap_column: str) -> pd.DataFrame:
    """Build causal features; each rolling statistic excludes the target day."""
    result = frame.sort_values("date").copy()
    result["date"] = pd.to_datetime(result["date"])
    result["lag_7"] = result["sales_quantity"].shift(7)
    result["lag_28"] = result["sales_quantity"].shift(28)
    prior_sales = result["sales_quantity"].shift(1)
    result["rolling_mean_7"] = prior_sales.rolling(7).mean()
    result["rolling_std_7"] = prior_sales.rolling(7).std().fillna(0)
    result["day_of_week"] = result["date"].dt.dayofweek
    result["month"] = result["date"].dt.month
    result["is_event"] = result[["event_name_1", "event_name_2"]].notna().any(axis=1).astype(int)
    result["snap"] = result[snap_column].fillna(0).astype(int)
    return result.dropna(subset=["lag_7", "lag_28", "rolling_mean_7"])


def _table(project: str, dataset: str, table: str) -> str:
    for value in (project, dataset, table):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError(f"Invalid BigQuery identifier: {value}")
    return f"`{project}.{dataset}.{table}`"


def fetch_inputs(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    from google.cloud import bigquery

    client = bigquery.Client(project=args.project)
    mart = _table(args.project, args.output_dataset, "forecasting_input")
    calendar = _table(args.project, args.raw_dataset, "Calendar")
    prices = _table(args.project, args.raw_dataset, "sell_prices")
    group_job = client.query(
        f"""
        SELECT date, sales_quantity, event_name_1, event_name_2
        FROM {mart}
        WHERE store_id = @store AND cat_id = @category
        ORDER BY date
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("store", "STRING", args.store),
            bigquery.ScalarQueryParameter("category", "STRING", args.category),
        ]),
    )
    aggregate = group_job.to_dataframe()
    if aggregate.empty:
        raise ValueError("No forecasting_input rows match the requested store/category.")

    item = pd.DataFrame()
    if args.item:
        item_job = client.query(
            f"""
            SELECT date, sales_quantity, sell_price, state_id,
                   event_name_1, event_name_2,
                   snap_CA, snap_TX, snap_WI
            FROM {mart}
            WHERE store_id = @store AND item_id = @item
            ORDER BY date
            """,
            job_config=bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("store", "STRING", args.store),
                bigquery.ScalarQueryParameter("item", "STRING", args.item),
            ]),
        )
        item = item_job.to_dataframe()
        if item.empty:
            raise ValueError("No forecasting_input rows match the requested store/item.")

    max_date = pd.to_datetime(aggregate["date"]).max().date()
    future = client.query(
        f"""
        SELECT c.date, c.wday, c.month, c.event_name_1, c.event_name_2,
               c.snap_CA, c.snap_TX, c.snap_WI, c.wm_yr_wk,
               p.sell_price
        FROM {calendar} AS c
        LEFT JOIN {prices} AS p
          ON p.store_id = @store AND p.item_id = @item
         AND p.wm_yr_wk = c.wm_yr_wk
        WHERE c.date > @last_date
          AND c.date <= DATE_ADD(@last_date, INTERVAL @horizon DAY)
        ORDER BY c.date
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("store", "STRING", args.store),
            bigquery.ScalarQueryParameter("item", "STRING", args.item or ""),
            bigquery.ScalarQueryParameter("last_date", "DATE", max_date),
            bigquery.ScalarQueryParameter("horizon", "INT64", args.horizon),
        ]),
    ).to_dataframe()
    if len(future) != args.horizon:
        raise ValueError(f"Expected {args.horizon} future calendar rows; found {len(future)}.")
    return aggregate, item, future


def prophet_forecast(aggregate: pd.DataFrame, future: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    from prophet import Prophet

    history = aggregate.copy()
    history["date"] = pd.to_datetime(history["date"])
    training = history.groupby("date", as_index=False)["sales_quantity"].sum()
    training = training.rename(columns={"date": "ds", "sales_quantity": "y"})
    event_rows = []
    for event_column in ("event_name_1", "event_name_2"):
        events = history.loc[history[event_column].notna(), ["date", event_column]]
        event_rows.append(events.rename(columns={"date": "ds", event_column: "holiday"}))
    future_events = []
    for event_column in ("event_name_1", "event_name_2"):
        events = future.loc[future[event_column].notna(), ["date", event_column]]
        future_events.append(events.rename(columns={"date": "ds", event_column: "holiday"}))
    holidays = pd.concat(event_rows + future_events, ignore_index=True).drop_duplicates()

    model = Prophet(holidays=holidays, yearly_seasonality=True, weekly_seasonality=True)
    model.fit(training)
    prediction = model.predict(pd.DataFrame({"ds": pd.to_datetime(future["date"])}))
    return pd.DataFrame({
        "date": prediction["ds"].dt.date,
        "store_id": args.store,
        "category_id": args.category,
        "item_id": None,
        "forecast_model": "prophet_category_store",
        "predicted_sales": prediction["yhat"].clip(lower=0),
        "lower_bound": prediction["yhat_lower"].clip(lower=0),
        "upper_bound": prediction["yhat_upper"].clip(lower=0),
    })


def lightgbm_forecast(item: pd.DataFrame, future: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    from lightgbm import LGBMRegressor

    state = str(item["state_id"].iloc[0])
    snap_column = f"snap_{state}"
    if snap_column not in item.columns or snap_column not in future.columns:
        raise ValueError(f"No M5 SNAP feature is available for state {state}.")
    training = add_training_features(item, snap_column)
    if len(training) < 30:
        raise ValueError("At least 58 days of item history are required for LightGBM features.")

    model = LGBMRegressor(n_estimators=250, learning_rate=0.04, num_leaves=15, random_state=42, verbosity=-1)
    model.fit(training[FEATURES], training["sales_quantity"])
    values = item.sort_values("date")["sales_quantity"].astype(float).tolist()
    fallback_price = float(item["sell_price"].dropna().iloc[-1])
    predictions = []
    for row in future.itertuples(index=False):
        current = {
            "lag_7": values[-7],
            "lag_28": values[-28],
            "rolling_mean_7": pd.Series(values[-7:]).mean(),
            "rolling_std_7": pd.Series(values[-7:]).std(ddof=1),
            "day_of_week": pd.Timestamp(row.date).dayofweek,
            "month": int(row.month),
            "is_event": int(pd.notna(row.event_name_1) or pd.notna(row.event_name_2)),
            "snap": int(getattr(row, snap_column) or 0),
            "sell_price": float(row.sell_price) if pd.notna(row.sell_price) else fallback_price,
        }
        prediction = max(float(model.predict(pd.DataFrame([current])[FEATURES])[0]), 0.0)
        predictions.append(prediction)
        values.append(prediction)
    return pd.DataFrame({
        "date": pd.to_datetime(future["date"]).dt.date,
        "store_id": args.store,
        "category_id": args.category,
        "item_id": args.item,
        "forecast_model": "lightgbm_item_store",
        "predicted_sales": predictions,
        "lower_bound": None,
        "upper_bound": None,
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="fresh-yen-508710-a0")
    parser.add_argument("--output-dataset", default="dbt_dev_sachin")
    parser.add_argument("--raw-dataset", default="m5_raw")
    parser.add_argument("--store", required=True, help="M5 store ID, for example CA_1")
    parser.add_argument("--category", required=True, help="M5 category ID, for example FOODS")
    parser.add_argument("--item", help="Optional M5 item ID; enables item/store LightGBM forecast")
    parser.add_argument("--horizon", type=int, default=28)
    parser.add_argument("--output", type=Path, default=Path("forecasts.csv"))
    parser.add_argument("--write-bigquery", action="store_true", help="Append forecast rows to output_dataset.forecasts")
    args = parser.parse_args()
    if not 1 <= args.horizon <= 56:
        parser.error("--horizon must be between 1 and 56 days")

    aggregate, item, future = fetch_inputs(args)
    forecasts = [prophet_forecast(aggregate, future, args)]
    if args.item:
        forecasts.append(lightgbm_forecast(item, future, args))
    output = pd.concat(forecasts, ignore_index=True)
    output["item_id"] = output["item_id"].astype("string")
    output["generated_at"] = pd.Timestamp.now(tz="UTC")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False)
    print(f"Wrote {len(output)} forecast rows to {args.output}")

    if args.write_bigquery:
        from google.cloud import bigquery

        client = bigquery.Client(project=args.project)
        destination = f"{args.project}.{args.output_dataset}.forecasts"
        job = client.load_table_from_dataframe(
            output,
            destination,
            job_config=bigquery.LoadJobConfig(write_disposition="WRITE_APPEND"),
        )
        job.result()
        print(f"Appended forecasts to {destination}")


if __name__ == "__main__":
    main()