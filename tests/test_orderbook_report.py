import unittest
from decimal import Decimal

from orderbook.liquidity_report import render_markdown, summarize


class LiquidityReportTests(unittest.TestCase):
    def test_report_separates_completed_lifetimes_and_price_buckets(self):
        lifecycle = [
            {"side": "bid", "price": "101.5", "event_type": "added", "observed_lifetime_ms": 0},
            {"side": "bid", "price": "101.5", "event_type": "removed", "observed_lifetime_ms": 1200},
            {"side": "ask", "price": "202", "event_type": "removed", "observed_lifetime_ms": 2400},
            {"side": "ask", "price": "202", "event_type": "quantity_changed", "observed_lifetime_ms": 1000},
            {"side": "other", "price": "200", "event_type": "removed", "observed_lifetime_ms": 9000},
        ]
        metrics = [
            {"received_at": "2026-01-01T00:00:00Z", "metrics": {"status": "OK",
             "mid_price": "150", "spread_pct_mid": "0.1", "obi_base_quantity": "0.2",
             "bid_depth_quote": "1000", "ask_depth_quote": "900"}},
            {"received_at": "2026-01-01T00:00:01Z", "metrics": {"status": "BOOK_EMPTY"}},
        ]
        report = summarize("BTCUSDT", lifecycle, metrics, Decimal("100"))
        self.assertEqual(report["lifecycle_event_count_valid"], 4)
        self.assertEqual(report["completed_visible_lifetime_ms"]["bid"]["median_ms"], 1200)
        self.assertEqual(report["completed_visible_lifetime_ms"]["ask"]["median_ms"], 2400)
        self.assertEqual(report["valid_book_metric_samples"], 1)
        self.assertEqual(report["latest_book_metrics"]["mid_price"], "150")
        self.assertEqual(report["price_buckets"][0]["price_bucket_start"], "100")
        self.assertEqual(report["price_buckets"][1]["price_bucket_start"], "200")
        self.assertIn("not proof of cancellation", report["limitations"][0])
        self.assertIn("Interpretation limits", render_markdown(report))

    def test_invalid_bucket_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize("BTCUSDT", [], [], Decimal("0"))


if __name__ == "__main__":
    unittest.main()
