import math
import unittest
from datetime import datetime, timedelta, timezone

from rolling_validation import rolling_memory_evaluate, EvaluationError


def candles(count=900):
    rows = []
    price = 100.0
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for i in range(count):
        ret = 0.0015 * math.sin(i / 5.0) + 0.0008 * math.cos(i / 13.0)
        prior = price
        price *= 1 + ret
        timestamp = (start + timedelta(hours=i)).isoformat(timespec="seconds").replace("+00:00", "Z")
        rows.append({"timestamp": timestamp, "open": prior, "high": price * 1.002,
                     "low": price * 0.998, "close": price, "volume": 100 + 20 * math.sin(i / 7.0) + i % 9})
    return rows


class RollingValidationTests(unittest.TestCase):
    def test_paired_comparison_uses_identical_timestamps_and_mature_labels(self):
        result = rolling_memory_evaluate(candles(), asset_symbol="SOL", interval="1h",
                                         lookback=12, horizon=3, min_train=40,
                                         neighbors=5, fold_size=120, round_trip_fee_bps=20)
        self.assertGreaterEqual(len(result["folds"]), 2)
        self.assertGreater(result["paired_prediction_count"], 0)
        self.assertEqual(result["metrics"]["memory_disabled_knn"]["sample_size"],
                         result["metrics"]["memory_enabled_knn"]["sample_size"])
        for row in result["paired_predictions"]:
            self.assertLess(row["timestamp"], row["target_timestamp"])
            self.assertGreaterEqual(row["memory_examples_available"], 0)
            self.assertIn(row["memory_on_prediction"], ("UP", "DOWN", "FLAT"))
            self.assertIn(row["memory_off_prediction"], ("UP", "DOWN", "FLAT"))

    def test_rejects_too_short_period(self):
        with self.assertRaises(EvaluationError):
            rolling_memory_evaluate(candles(100), asset_symbol="SOL", lookback=12,
                                    horizon=3, min_train=40, neighbors=5)

    def test_rejects_duplicate_timestamps(self):
        rows = candles(900)
        rows[10]["timestamp"] = rows[9]["timestamp"]
        with self.assertRaises(EvaluationError):
            rolling_memory_evaluate(rows, asset_symbol="SOL", lookback=12,
                                    horizon=3, min_train=40, neighbors=5)


if __name__ == "__main__":
    unittest.main()
