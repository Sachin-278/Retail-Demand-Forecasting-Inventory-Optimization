import unittest

import pandas as pd

from forecast import add_training_features


class TrainingFeatureTests(unittest.TestCase):
    def test_lags_and_rolling_features_use_only_prior_sales(self):
        frame = pd.DataFrame({
            "date": pd.date_range("2020-01-01", periods=40),
            "sales_quantity": range(40),
            "event_name_1": [None] * 40,
            "event_name_2": [None] * 40,
            "snap_CA": [0] * 40,
        })

        featured = add_training_features(frame, "snap_CA")
        first = featured.iloc[0]

        self.assertEqual(len(featured), 12)
        self.assertEqual(first["sales_quantity"], 28)
        self.assertEqual(first["lag_7"], 21)
        self.assertEqual(first["lag_28"], 0)
        self.assertEqual(first["rolling_mean_7"], 24)
        self.assertEqual(first["is_event"], 0)


if __name__ == "__main__":
    unittest.main()