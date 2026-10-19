import unittest
from decimal import Decimal

from orderbook.kraken_snapshot_collector import build_report


class KrakenSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.book = {
            "bids": [["100", "2", 1], ["99", "3", 1]],
            "asks": [["101", "4", 1], ["102", "1", 1]],
        }

    def test_reports_bid_ask_concentration_and_bucket_notional(self):
        report = build_report("XBTUSD", "XXBTZUSD", self.book, Decimal("10"), 4)
        self.assertEqual(report["venue"], "kraken_spot")
        self.assertEqual(report["best_bid"], "100")
        self.assertEqual(report["best_ask"], "101")
        self.assertEqual(report["bid_level_count"], 2)
        self.assertEqual(report["ask_level_count"], 2)
        self.assertEqual(report["bid_depth_usd"], "497")
        self.assertEqual(report["ask_depth_usd"], "506")
        self.assertEqual(report["top_concentrated_levels_by_notional"][0]["side"], "ask")
        self.assertEqual(report["top_concentrated_levels_by_notional"][0]["notional_usd"], "404")
        self.assertEqual(report["price_buckets"][1]["price_bucket_start"], "100")
        self.assertEqual(report["price_buckets"][1]["ask_levels"], 2)
        self.assertEqual(report["price_buckets"][1]["bid_levels"], 1)
        self.assertIn("single snapshot", " ".join(report["limitations"]))

    def test_empty_side_rejected(self):
        with self.assertRaises(ValueError):
            build_report("XBTUSD", "XXBTZUSD", {"bids": [], "asks": [["101", "1", 1]]})

    def test_crossed_book_rejected(self):
        with self.assertRaises(ValueError):
            build_report("XBTUSD", "XXBTZUSD", {
                "bids": [["102", "1", 1]], "asks": [["101", "1", 1]]
            })

    def test_invalid_bucket_rejected(self):
        with self.assertRaises(ValueError):
            build_report("XBTUSD", "XXBTZUSD", self.book, Decimal("0"))


if __name__ == "__main__":
    unittest.main()
