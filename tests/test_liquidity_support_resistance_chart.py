import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orderbook.liquidity_support_resistance_chart import read_records, _merge, _num, _captured_bounds, main


class ChartInputTests(unittest.TestCase):
    def test_reads_jsonl_snapshots(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "snapshots.jsonl"
            a = {"mid_price": "100000", "price_buckets": []}
            b = {"mid_price": "101000", "price_buckets": []}
            path.write_text(json.dumps(a) + "\n" + json.dumps(b) + "\n", encoding="utf-8")
            records = read_records(path)
            self.assertEqual(len(records), 2)
            self.assertEqual(records[-1]["mid_price"], "101000")

    def test_reads_json_object(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "snapshot.json"
            path.write_text(json.dumps({"mid_price": "100000"}), encoding="utf-8")
            self.assertEqual(read_records(path), [{"mid_price": "100000"}])

    def test_rejects_empty_input(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "empty.json"
            path.write_text("", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_records(path)

    def test_merges_observed_intervals_but_preserves_internal_gaps(self):
        self.assertEqual(_merge([(100, 200), (200, 300), (500, 600)]),
                         [(100, 300), (500, 600)])

    def test_reads_explicit_book_bounds_without_guessing(self):
        record = {"best_bid_price": "100000", "worst_bid_price": "99000",
                  "best_ask_price": "100100", "worst_ask_price": "101500"}
        self.assertEqual(_num(record, "best_bid_price", "best_bid"), 100000.0)
        self.assertEqual(_num(record, "worst_ask_price"), 101500.0)
        self.assertIsNone(_num({"best_bid": "100000"}, "worst_bid_price"))

    def test_captured_bounds_union_all_snapshots_not_only_last(self):
        records = [
            {"best_bid_price": "100000", "worst_bid_price": "97000",
             "best_ask_price": "100100", "worst_ask_price": "104000"},
            {"best_bid_price": "101000", "worst_bid_price": "99500",
             "best_ask_price": "101100", "worst_ask_price": "102000"},
        ]
        self.assertEqual(_captured_bounds(records), (97000.0, 101000.0,
                                                       100100.0, 104000.0,
                                                       97000.0, 104000.0))

    def test_generates_png_from_captured_range_and_candidate_zones(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            snapshot = {
                "mid_price": "100050",
                "best_bid_price": "100000", "worst_bid_price": "99000",
                "best_ask_price": "100100", "worst_ask_price": "101000",
                "price_buckets": [
                    {"price_bucket_start": "99000", "price_bucket_end_exclusive": "99100",
                     "bid_notional_usd": "250000", "ask_notional_usd": "0"},
                    {"price_bucket_start": "100000", "price_bucket_end_exclusive": "100100",
                     "bid_notional_usd": "500000", "ask_notional_usd": "0"},
                    {"price_bucket_start": "100100", "price_bucket_end_exclusive": "100200",
                     "bid_notional_usd": "0", "ask_notional_usd": "450000"},
                    {"price_bucket_start": "101000", "price_bucket_end_exclusive": "101100",
                     "bid_notional_usd": "0", "ask_notional_usd": "300000"},
                ],
            }
            snapshots_path = root / "snapshots.jsonl"
            snapshots_path.write_text(json.dumps(snapshot) + "\n", encoding="utf-8")
            zones_path = root / "zones.json"
            zones_path.write_text(json.dumps({"zones": [
                {"type": "candidate_support", "price_low": 99000,
                 "price_high_exclusive": 99100, "persistence_pct": 80,
                 "max_visible_notional_usd": 250000},
                {"type": "candidate_resistance", "price_low": 100900,
                 "price_high_exclusive": 101000, "persistence_pct": 70,
                 "max_visible_notional_usd": 300000},
            ]}), encoding="utf-8")
            output_path = root / "chart.png"
            with patch("sys.argv", ["liquidity_support_resistance_chart",
                                    "--input", str(snapshots_path),
                                    "--zones", str(zones_path),
                                    "--output", str(output_path)]):
                main()
            self.assertTrue(output_path.is_file())
            self.assertGreater(output_path.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
