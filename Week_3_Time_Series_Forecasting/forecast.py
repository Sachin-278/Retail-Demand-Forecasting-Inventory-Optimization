"""Week 3 demand forecasting models for the M5 forecasting input mart."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from prophet import Prophet


TARGET = "sales_quantity"
SERIES_KEYS = ("item_id", "store_id")
DIMENSION_COLUMNS = ("item_id", "store_id", "state_id", "cat_id", "dept_id")
NUMERIC_FEATURES = (
    "lag_7",
    "lag_28",
    "rolling_mean_7",
    "rolling_mean_28",
    "rolling_std_28",
    "weekday",
    "month",
    "is_holiday",
    "is_snap",
    "sell_price",
)


@dataclass
class LightGBMForecaster:
    model: LGBMRegressor
    feature_columns: list[str]
    category_values: dict[str, list[str]]


def _prepare_history(data: pd.DataFrame) -> pd.DataFrame:
    required = {"item_id", "store_id", "date", TARGET}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing required forecasting columns: {sorted(missing)}")

    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame[TARGET] = pd.to_numeric(frame[TARGET], errors="coerce")
    if "sell_price" not in frame:
        frame["sell_price"] = np.nan
    frame["sell_price"] = pd.to_numeric(frame["sell_price"], errors="coerce")
    return frame.sort_values([*SERIES_KEYS, "date"]).reset_index(drop=True)


def build_lightgbm_features(data: pd.DataFrame) -> pd.DataFrame:
    """Build lagged features; every rolling value uses sales before that date."""
    frame = _prepare_history(data)
    groups = frame.groupby(list(SERIES_KEYS), sort=False, observed=True)[TARGET]

    for lag in (7, 28):
        frame[f"lag_{lag}"] = groups.shift(lag)

    prior_sales = groups.shift(1)
    for window in (7, 28):
        rolling = prior_sales.groupby(
            [frame[key] for key in SERIES_KEYS], sort=False, observed=True
        )
        frame[f"rolling_mean_{window}"] = rolling.transform(
            lambda values: values.rolling(window, min_periods=window).mean()
        )
    frame["rolling_std_28"] = prior_sales.groupby(
        [frame[key] for key in SERIES_KEYS], sort=False, observed=True
    ).transform(lambda values: values.rolling(28, min_periods=2).std())

    frame["weekday"] = frame["date"].dt.dayofweek
    frame["month"] = frame["date"].dt.month
    event_columns = [name for name in ("event_name_1", "event_name_2") if name in frame]
    frame["is_holiday"] = (
        frame[event_columns].notna().any(axis=1).astype("int8")
        if event_columns
        else 0
    )
    snap_columns = [
        f"snap_{state}"
        for state in frame.get("state_id", pd.Series(dtype=str)).dropna().astype(str).unique()
        if f"snap_{state}" in frame
    ]
    if snap_columns:
        frame["is_snap"] = frame[snap_columns].fillna(0).astype(bool).any(axis=1).astype("int8")
    else:
        frame["is_snap"] = 0

    frame["sell_price"] = frame["sell_price"].fillna(-1)
    return frame.dropna(subset=["lag_7", "lag_28", "rolling_mean_7", "rolling_mean_28"])


def train_lightgbm(data: pd.DataFrame) -> LightGBMForecaster:
    """Train one pooled LightGBM regressor across item-store series."""
    features = build_lightgbm_features(data)
    if features.empty:
        raise ValueError("At least 29 daily observations per series are needed to train.")

    dimensions = [column for column in DIMENSION_COLUMNS if column in features.columns]
    feature_columns = [*NUMERIC_FEATURES, *dimensions]
    category_values = {
        column: sorted(features[column].fillna("unknown").astype(str).unique().tolist())
        for column in dimensions
    }
    training = features[feature_columns].copy()
    for column, categories in category_values.items():
        training[column] = pd.Categorical(
            training[column].fillna("unknown").astype(str), categories=categories
        )

    model = LGBMRegressor(
        objective="regression",
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        random_state=42,
        verbosity=-1,
    )
    model.fit(training, features[TARGET].clip(lower=0), categorical_feature=dimensions)
    return LightGBMForecaster(model, feature_columns, category_values)


def forecast_lightgbm(
    forecaster: LightGBMForecaster,
    history: pd.DataFrame,
    horizon: int = 28,
    future_features: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Recursively forecast each item-store series, optionally using known covariates."""
    if horizon < 1:
        raise ValueError("horizon must be at least 1")
    history = _prepare_history(history)
    future_lookup: dict[tuple[object, ...], dict[str, object]] = {}
    if future_features is not None:
        required_future = {"item_id", "store_id", "date"}
        if not required_future.issubset(future_features.columns):
            raise ValueError("future_features must include item_id, store_id, and date")
        for row in future_features.to_dict("records"):
            key = (row["item_id"], row["store_id"], pd.Timestamp(row["date"]).normalize())
            future_lookup[key] = row

    forecast_rows: list[dict[str, object]] = []
    dimensions = [column for column in DIMENSION_COLUMNS if column in forecaster.category_values]
    for _, series in history.groupby(list(SERIES_KEYS), sort=False, observed=True):
        series = series.sort_values("date").copy()
        if len(series) < 28:
            continue
        latest = series.iloc[-1]
        sales = series[TARGET].astype(float).tolist()
        last_date = pd.Timestamp(latest["date"]).normalize()

        for step in range(1, horizon + 1):
            forecast_date = last_date + pd.Timedelta(days=step)
            key = (latest["item_id"], latest["store_id"], forecast_date)
            covariates = future_lookup.get(key, {})
            row: dict[str, object] = {
                column: covariates.get(column, latest.get(column, "unknown"))
                for column in dimensions
            }
            event_values = [covariates.get(name) for name in ("event_name_1", "event_name_2")]
            state_id = latest.get("state_id")
            snap_value = covariates.get(f"snap_{state_id}", 0)
            price = covariates.get("sell_price", latest.get("sell_price", -1))
            row.update(
                {
                    "lag_7": sales[-7],
                    "lag_28": sales[-28],
                    "rolling_mean_7": float(np.mean(sales[-7:])),
                    "rolling_mean_28": float(np.mean(sales[-28:])),
                    "rolling_std_28": float(np.std(sales[-28:], ddof=1)),
                    "weekday": forecast_date.dayofweek,
                    "month": forecast_date.month,
                    "is_holiday": int(any(pd.notna(value) and bool(value) for value in event_values)),
                    "is_snap": int(pd.notna(snap_value) and bool(snap_value)),
                    "sell_price": -1.0 if pd.isna(price) else float(price),
                }
            )
            model_input = pd.DataFrame([row], columns=forecaster.feature_columns)
            for column, categories in forecaster.category_values.items():
                model_input[column] = pd.Categorical(
                    model_input[column].fillna("unknown").astype(str), categories=categories
                )
            prediction = max(0.0, float(forecaster.model.predict(model_input)[0]))
            sales.append(prediction)
            forecast_rows.append(
                {
                    "item_id": latest["item_id"],
                    "store_id": latest["store_id"],
                    "state_id": latest.get("state_id"),
                    "dept_id": latest.get("dept_id"),
                    "date": forecast_date,
                    "actual_quantity": None,
                    "forecast_quantity": prediction,
                    "forecast_lower": None,
                    "forecast_upper": None,
                    "model_name": "lightgbm_global",
                }
            )
    return pd.DataFrame(forecast_rows)


def forecast_prophet_aggregates(
    data: pd.DataFrame,
    horizon: int = 28,
    group_columns: Sequence[str] = ("state_id", "dept_id"),
    future_features: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Forecast department-level demand and use M5 event dates as holidays."""
    if horizon < 1:
        raise ValueError("horizon must be at least 1")
    frame = _prepare_history(data)
    groups = [column for column in group_columns if column in frame.columns]
    iterator = frame.groupby(groups, dropna=False, sort=False) if groups else [((), frame)]
    outputs: list[pd.DataFrame] = []

    for group_key, series in iterator:
        daily = series.groupby("date", as_index=False)[TARGET].sum().rename(
            columns={"date": "ds", TARGET: "y"}
        )
        if len(daily) < 2:
            continue
        event_columns = [name for name in ("event_name_1", "event_name_2") if name in series]
        holidays = None
        if event_columns:
            event_rows = []
            holiday_source = series[["date", *event_columns, *groups]].copy()
            if future_features is not None and set([*groups, "date"]).issubset(future_features.columns):
                future_holidays = future_features
                for column in groups:
                    future_holidays = future_holidays.loc[
                        future_holidays[column].eq(series[column].iloc[0])
                    ]
                holiday_source = pd.concat(
                    [
                        holiday_source,
                        future_holidays[["date", *[name for name in event_columns if name in future_holidays], *groups]],
                    ],
                    ignore_index=True,
                    sort=False,
                )
            for column in event_columns:
                if column in holiday_source:
                    event_rows.append(
                        holiday_source.loc[holiday_source[column].notna(), ["date", column]]
                        .rename(columns={"date": "ds", column: "holiday"})
                    )
            holidays = pd.concat(event_rows, ignore_index=True).drop_duplicates()
            holidays["ds"] = pd.to_datetime(holidays["ds"])
            holidays["holiday"] = holidays["holiday"].astype(str)
        model = Prophet(holidays=holidays, weekly_seasonality=True, yearly_seasonality=True)
        model.fit(daily)
        result = model.predict(model.make_future_dataframe(periods=horizon))
        result = result.tail(horizon)[["ds", "yhat", "yhat_lower", "yhat_upper"]].rename(
            columns={
                "ds": "date",
                "yhat": "forecast_quantity",
                "yhat_lower": "forecast_lower",
                "yhat_upper": "forecast_upper",
            }
        )
        key_values = group_key if isinstance(group_key, tuple) else (group_key,)
        for column, value in zip(groups, key_values):
            result[column] = value
        result["item_id"] = None
        result["store_id"] = None
        result["actual_quantity"] = None
        result["model_name"] = "prophet_aggregate"
        outputs.append(result)
    return pd.concat(outputs, ignore_index=True) if outputs else pd.DataFrame()


def forecast_accuracy(
    actual: pd.DataFrame,
    forecasts: pd.DataFrame,
    series_columns: Sequence[str] = SERIES_KEYS,
) -> dict[str, float]:
    """Calculate point-forecast MAE, RMSE, and WAPE for matched series dates."""
    keys = [*series_columns, "date"]
    required_actual = {*keys, TARGET}
    required_forecast = {*keys, "forecast_quantity"}
    if missing := required_actual.difference(actual.columns):
        raise ValueError(f"Actual data is missing columns: {sorted(missing)}")
    if missing := required_forecast.difference(forecasts.columns):
        raise ValueError(f"Forecast data is missing columns: {sorted(missing)}")

    actual_values = actual[[*keys, TARGET]].copy()
    forecast_values = forecasts[[*keys, "forecast_quantity"]].copy()
    actual_values["date"] = pd.to_datetime(actual_values["date"])
    forecast_values["date"] = pd.to_datetime(forecast_values["date"])
    matched = actual_values.merge(forecast_values, on=keys, how="inner", validate="one_to_one")
    if matched.empty:
        raise ValueError("No matching actual and forecast item-store-date rows")

    errors = matched["forecast_quantity"].to_numpy() - matched[TARGET].to_numpy()
    actual_total = float(matched[TARGET].abs().sum())
    return {
        "mae": float(np.abs(errors).mean()),
        "rmse": float(np.sqrt(np.square(errors).mean())),
        "wape": float(np.abs(errors).sum() / actual_total) if actual_total else float("nan"),
        "evaluated_rows": float(len(matched)),
    }


def evaluate_lightgbm(data: pd.DataFrame, horizon: int = 28) -> tuple[pd.DataFrame, dict[str, float]]:
    """Train before the final horizon and score against its held-out actuals."""
    if horizon < 1:
        raise ValueError("horizon must be at least 1")
    frame = _prepare_history(data)
    dates = pd.Index(frame["date"].drop_duplicates().sort_values())
    if len(dates) <= horizon + 28:
        raise ValueError("History must contain more than horizon + 28 distinct dates")

    cutoff = dates[-horizon - 1]
    training = frame.loc[frame["date"] <= cutoff]
    actual = frame.loc[frame["date"] > cutoff]
    future_features = actual.drop(columns=[TARGET])
    model = train_lightgbm(training)
    forecasts = forecast_lightgbm(
        model,
        training,
        horizon=horizon,
        future_features=future_features,
    )
    forecasts = forecasts.drop(columns=["actual_quantity"])
    forecasts = forecasts.merge(
        actual[[*SERIES_KEYS, "date", TARGET]].rename(columns={TARGET: "actual_quantity"}),
        on=[*SERIES_KEYS, "date"],
        how="inner",
        validate="one_to_one",
        suffixes=("", "_observed"),
    )
    forecasts["model_name"] = "lightgbm_global_holdout"
    return forecasts, forecast_accuracy(actual, forecasts)


def evaluate_prophet_aggregates(
    data: pd.DataFrame,
    horizon: int = 28,
    group_columns: Sequence[str] = ("state_id", "dept_id"),
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Score Prophet state/department forecasts against a time-ordered holdout."""
    if horizon < 1:
        raise ValueError("horizon must be at least 1")
    frame = _prepare_history(data)
    groups = [column for column in group_columns if column in frame]
    dates = pd.Index(frame["date"].drop_duplicates().sort_values())
    if len(dates) <= horizon + 1:
        raise ValueError("History must contain more than horizon + 1 distinct dates")

    cutoff = dates[-horizon - 1]
    training = frame.loc[frame["date"] <= cutoff]
    actual = (
        frame.loc[frame["date"] > cutoff]
        .groupby([*groups, "date"], as_index=False, dropna=False)[TARGET]
        .sum()
    )
    future_features = frame.loc[frame["date"] > cutoff].drop(columns=[TARGET])
    forecasts = forecast_prophet_aggregates(
        training,
        horizon=horizon,
        group_columns=groups,
        future_features=future_features,
    )
    forecasts = forecasts.drop(columns=["actual_quantity"])
    forecasts = forecasts.merge(
        actual.rename(columns={TARGET: "actual_quantity"}),
        on=[*groups, "date"],
        how="inner",
        validate="one_to_one",
        suffixes=("", "_observed"),
    )
    forecasts["model_name"] = "prophet_aggregate_holdout"
    return forecasts, forecast_accuracy(actual, forecasts, series_columns=groups)


def write_forecasts_to_bigquery(
    forecasts: pd.DataFrame,
    destination: str = "dbt_dev_sachin.forecasts",
    project_id: str = "fresh-yen-508710-a0-509416",
) -> None:
    """Append forecasts to BigQuery using the caller's Google credentials."""
    if forecasts.empty:
        raise ValueError("No forecast rows to write")
    import pandas_gbq

    output = forecasts.copy()
    for column in ("actual_quantity", "forecast_quantity", "forecast_lower", "forecast_upper"):
        if column in output:
            output[column] = pd.to_numeric(output[column], errors="coerce").astype("float64")
    output["date"] = pd.to_datetime(output["date"])
    output["generated_at"] = datetime.now(timezone.utc)
    pandas_gbq.to_gbq(
        output,
        destination_table=destination,
        project_id=project_id,
        if_exists="append",
        progress_bar=False,
    )


def write_metrics_to_bigquery(
    metrics: Sequence[dict[str, object]],
    destination: str = "dbt_dev_sachin.forecast_metrics",
    project_id: str = "fresh-yen-508710-a0-509416",
) -> None:
    """Append model holdout metrics for longitudinal forecast monitoring."""
    if not metrics:
        raise ValueError("No evaluation metrics to write")
    import pandas_gbq

    output = pd.DataFrame(metrics)
    output["evaluated_at"] = datetime.now(timezone.utc)
    pandas_gbq.to_gbq(
        output,
        destination_table=destination,
        project_id=project_id,
        if_exists="append",
        progress_bar=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Week 3 models and store forecasts in BigQuery.")
    parser.add_argument(
        "--input-table",
        default="fresh-yen-508710-a0-509416.dbt_dev_sachin.forecasting_input",
        help="Fully-qualified BigQuery table containing the forecasting input mart.",
    )
    parser.add_argument("--output-table", default="dbt_dev_sachin.forecasts")
    parser.add_argument("--horizon", type=int, default=28)
    parser.add_argument(
        "--max-series",
        type=int,
        default=100,
        help="Deterministically sample this many item-store series; use 0 for every series.",
    )
    args = parser.parse_args()

    import pandas_gbq

    if not re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+", args.input_table):
        parser.error("--input-table must be a fully qualified project.dataset.table identifier")
    if args.max_series < 0:
        parser.error("--max-series must be 0 or a positive integer")

    series_limit = f"LIMIT {args.max_series}" if args.max_series else ""
    data = pandas_gbq.read_gbq(
        f"""
        WITH selected_series AS (
                    SELECT item_id, store_id
          FROM `{args.input_table}`
                    GROUP BY item_id, store_id
          ORDER BY FARM_FINGERPRINT(CONCAT(CAST(item_id AS STRING), '|', CAST(store_id AS STRING)))
          {series_limit}
        )
        SELECT input.*
        FROM `{args.input_table}` AS input
        JOIN selected_series USING (item_id, store_id)
        ORDER BY input.item_id, input.store_id, input.date
        """,
        project_id="fresh-yen-508710-a0-509416",
        dialect="standard",
    )
    if data.empty:
        parser.error("The forecasting input table returned no rows")

    holdout_forecasts, holdout_metrics = evaluate_lightgbm(data, horizon=args.horizon)
    print(f"LightGBM holdout metrics: {holdout_metrics}")
    prophet_holdout_forecasts, prophet_metrics = evaluate_prophet_aggregates(
        data, horizon=args.horizon
    )
    print(f"Prophet holdout metrics: {prophet_metrics}")

    latest_date = pd.to_datetime(data["date"]).max().date().isoformat()
    end_date = (pd.Timestamp(latest_date) + pd.Timedelta(days=args.horizon)).date().isoformat()
    project_id, _, _ = args.input_table.split(".")
    future_query = f"""
        WITH calendar AS (
          SELECT
            COALESCE(SAFE_CAST(date AS DATE), SAFE.PARSE_DATE('%m/%d/%y', CAST(date AS STRING))) AS forecast_date,
            wm_yr_wk,
            event_name_1,
            event_name_2,
            snap_CA,
            snap_TX,
            snap_WI
          FROM `{project_id}.m5_raw.Calendar`
                ), series AS (
                    SELECT item_id, store_id, ANY_VALUE(state_id) AS state_id, ANY_VALUE(dept_id) AS dept_id
                    FROM `{args.input_table}`
                    GROUP BY item_id, store_id
                    ORDER BY FARM_FINGERPRINT(CONCAT(CAST(item_id AS STRING), '|', CAST(store_id AS STRING)))
                    {series_limit}
        )
        SELECT
          series.item_id,
          series.store_id,
          series.state_id,
          series.dept_id,
          calendar.forecast_date AS date,
          calendar.event_name_1,
          calendar.event_name_2,
          calendar.snap_CA,
          calendar.snap_TX,
          calendar.snap_WI,
          SAFE_CAST(prices.sell_price AS FLOAT64) AS sell_price
        FROM calendar
        CROSS JOIN series
        LEFT JOIN `{project_id}.m5_raw.sell_prices` AS prices
          ON prices.item_id = series.item_id
         AND prices.store_id = series.store_id
         AND prices.wm_yr_wk = calendar.wm_yr_wk
        WHERE calendar.forecast_date > DATE '{latest_date}'
          AND calendar.forecast_date <= DATE '{end_date}'
    """
    future_features = pandas_gbq.read_gbq(
        future_query,
        project_id=project_id,
        dialect="standard",
    )
    lightgbm_model = train_lightgbm(data)
    lightgbm_output = forecast_lightgbm(
        lightgbm_model, data, horizon=args.horizon, future_features=future_features
    )
    prophet_output = forecast_prophet_aggregates(
        data, horizon=args.horizon, future_features=future_features
    )
    print(
        f"Holdout rows: LightGBM={int(holdout_metrics['evaluated_rows'])}, "
        f"Prophet={int(prophet_metrics['evaluated_rows'])}"
    )
    all_forecasts = pd.concat(
        [holdout_forecasts, prophet_holdout_forecasts, lightgbm_output, prophet_output],
        ignore_index=True,
        sort=False,
    )
    write_forecasts_to_bigquery(
        all_forecasts,
        destination=args.output_table,
    )
    write_metrics_to_bigquery(
        [
            {"model_name": "lightgbm_global", "horizon": args.horizon, **holdout_metrics},
            {"model_name": "prophet_aggregate", "horizon": args.horizon, **prophet_metrics},
        ]
    )


if __name__ == "__main__":
    main()