import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from forecast import (
    build_lightgbm_features,
    evaluate_lightgbm,
    forecast_accuracy,
    forecast_lightgbm,
    train_lightgbm,
    write_forecasts_to_bigquery,
    write_metrics_to_bigquery,
)


def sample_history(days=70):
    dates = pd.date_range("2023-01-01", periods=days, freq="D")
    records = []
    for item_id, offset in (("item_a", 2), ("item_b", 5)):
        for index, date in enumerate(dates):
            records.append(
                {
                    "item_id": item_id,
                    "store_id": "store_1",
                    "state_id": "CA",
                    "dept_id": "dept_1",
                    "date": date,
                    "sales_quantity": offset + index % 7,
                    "sell_price": 3.5,
                    "event_name_1": "Holiday" if index == 35 else None,
                    "snap_CA": index % 2,
                }
            )
    return pd.DataFrame(records)


class ForecastFeatureTests(unittest.TestCase):
    def test_features_use_only_sales_before_current_date(self):
        history = sample_history()
        features = build_lightgbm_features(history)
        row = features.loc[(features.item_id == "item_a") & (features.date == pd.Timestamp("2023-02-01"))].iloc[0]
        expected_lag_7 = history.loc[
            (history.item_id == "item_a") & (history.date == pd.Timestamp("2023-01-25")),
            "sales_quantity",
        ].iloc[0]
        self.assertEqual(row.lag_7, expected_lag_7)
        self.assertEqual(row.is_holiday, 0)

    def test_forecast_returns_nonnegative_rows_for_each_series(self):
        history = sample_history()
        model = train_lightgbm(history)
        forecast = forecast_lightgbm(model, history, horizon=3)
        self.assertEqual(len(forecast), 6)
        self.assertEqual(forecast.groupby("item_id").size().to_dict(), {"item_a": 3, "item_b": 3})
        self.assertTrue(np.isfinite(forecast.forecast_quantity).all())
        self.assertTrue((forecast.forecast_quantity >= 0).all())
        self.assertEqual(forecast.model_name.unique().tolist(), ["lightgbm_global"])

    def test_time_based_evaluation_scores_only_held_out_dates(self):
        history = sample_history(days=70)
        forecasts, metrics = evaluate_lightgbm(history, horizon=7)
        self.assertEqual(len(forecasts), 14)
        self.assertEqual(metrics["evaluated_rows"], 14)
        self.assertTrue(np.isfinite([metrics["mae"], metrics["rmse"], metrics["wape"]]).all())
        self.assertTrue(forecasts["actual_quantity"].notna().all())
        self.assertEqual(forecasts.model_name.unique().tolist(), ["lightgbm_global_holdout"])

    def test_accuracy_rejects_unmatched_forecasts(self):
        history = sample_history(days=35)
        with self.assertRaisesRegex(ValueError, "No matching actual"):
            forecast_accuracy(history, pd.DataFrame(columns=[
                "item_id", "store_id", "date", "forecast_quantity"
            ]))

    def test_accuracy_reports_mae_rmse_and_wape(self):
        actual = pd.DataFrame(
            {
                "item_id": ["item_a", "item_a"],
                "store_id": ["store_1", "store_1"],
                "date": pd.date_range("2024-01-01", periods=2),
                "sales_quantity": [10.0, 20.0],
            }
        )
        forecasts = actual.assign(forecast_quantity=[12.0, 18.0])

        metrics = forecast_accuracy(actual, forecasts)

        self.assertEqual(metrics["mae"], 2.0)
        self.assertEqual(metrics["rmse"], 2.0)
        self.assertAlmostEqual(metrics["wape"], 4 / 30)
        self.assertEqual(metrics["evaluated_rows"], 2.0)

    @patch("pandas_gbq.to_gbq")
    def test_forecast_writer_appends_actuals_predictions_and_timestamp(self, to_gbq):
        forecasts = pd.DataFrame(
            {
                "item_id": ["item_a"],
                "store_id": ["store_1"],
                "date": [pd.Timestamp("2024-01-01")],
                "actual_quantity": [10],
                "forecast_quantity": [12],
                "forecast_lower": [9],
                "forecast_upper": [14],
                "model_name": ["lightgbm_global_holdout"],
            }
        )

        write_forecasts_to_bigquery(forecasts)

        written, = to_gbq.call_args.args
        self.assertEqual(to_gbq.call_args.kwargs["destination_table"], "dbt_dev_sachin.forecasts")
        self.assertEqual(to_gbq.call_args.kwargs["project_id"], "fresh-yen-508710-a0-509416")
        self.assertEqual(to_gbq.call_args.kwargs["if_exists"], "append")
        self.assertEqual(written.loc[0, "actual_quantity"], 10.0)
        self.assertEqual(written.loc[0, "forecast_quantity"], 12.0)
        self.assertIn("generated_at", written.columns)

    @patch("pandas_gbq.to_gbq")
    def test_metrics_writer_appends_metrics_with_evaluation_timestamp(self, to_gbq):
        metrics = [{"model_name": "lightgbm_global", "mae": 1.5, "rmse": 2.0, "wape": 0.1}]

        write_metrics_to_bigquery(metrics)

        written, = to_gbq.call_args.args
        self.assertEqual(to_gbq.call_args.kwargs["destination_table"], "dbt_dev_sachin.forecast_metrics")
        self.assertEqual(to_gbq.call_args.kwargs["if_exists"], "append")
        self.assertEqual(written.loc[0, "mae"], 1.5)
        self.assertIn("evaluated_at", written.columns)


if __name__ == "__main__":
    unittest.main()