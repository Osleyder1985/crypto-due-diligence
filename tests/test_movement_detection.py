"""Tests for deterministic OHLCV movement detection."""
import unittest

from movement_detection import DetectionConfig, detect_movements


def candles(closes, volumes):
    rows = []
    for index, (close, volume) in enumerate(zip(closes, volumes)):
        rows.append({
            "timestamp": f"2026-01-01T00:{index:02d}:00Z",
            "open": close, "high": close * 1.01, "low": close * 0.99,
            "close": close, "volume": volume,
        })
    return rows


class MovementDetectionTests(unittest.TestCase):
    def test_detects_return_and_volume_spike(self):
        rows = candles([100, 100, 101, 100, 100, 100, 108], [10, 10, 10, 10, 10, 10, 40])
        result = detect_movements(rows, DetectionConfig(return_threshold_pct=5, relative_volume_threshold=2, baseline_windows=5))
        self.assertEqual("ALERTS", result["status"])
        self.assertIn("ABSOLUTE_RETURN", result["alerts"][-1]["triggers"])
        self.assertIn("RELATIVE_VOLUME", result["alerts"][-1]["triggers"])
        self.assertEqual("1.0.0", result["alerts"][-1]["methodology_version"])

    def test_no_alert_for_small_moves_and_normal_volume(self):
        rows = candles([100, 100.1, 100, 100.1, 100, 100.1, 100], [10] * 7)
        result = detect_movements(rows, DetectionConfig())
        self.assertEqual("NO_ALERTS", result["status"])

    def test_insufficient_history_is_explicit(self):
        result = detect_movements(candles([100, 101, 102], [10, 10, 10]))
        self.assertEqual("INSUFFICIENT_COVERAGE", result["status"])

    def test_rejects_non_monotonic_timestamps(self):
        rows = candles([100, 101, 102, 103, 104, 105, 106], [10] * 7)
        rows[2]["timestamp"] = rows[1]["timestamp"]
        result = detect_movements(rows)
        self.assertEqual("INVALID_DATA", result["status"])

    def test_benchmark_relative_return_is_recorded(self):
        rows = candles([100, 100, 100, 100, 100, 100, 106], [10, 10, 10, 10, 10, 10, 10])
        benchmark = candles([100, 100, 100, 100, 100, 100, 103], [20] * 7)
        result = detect_movements(rows, DetectionConfig(baseline_windows=5), benchmark_rows=benchmark)
        self.assertAlmostEqual(3.0, result["alerts"][-1]["relative_return_pct"], places=5)


if __name__ == "__main__":
    unittest.main()
