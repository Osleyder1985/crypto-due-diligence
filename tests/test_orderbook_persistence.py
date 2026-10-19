import unittest

from orderbook.persistence_monitor import summarize_snapshots


def report(timestamp, buckets, levels=None):
    return {
        "captured_at": timestamp,
        "pair_returned": "XXBTZUSD",
        "price_buckets": buckets,
        "top_concentrated_levels_by_notional": levels or [],
    }


def bucket(start, bid="0", ask="0"):
    return {
        "price_bucket_start": str(start),
        "bid_notional_usd": bid,
        "ask_notional_usd": ask,
    }


class PersistenceMonitorTests(unittest.TestCase):
    def test_persistence_counts_threshold_hits_across_all_samples(self):
        reports = [
            report("t1", [bucket(82000, bid="300000")]),
            report("t2", [bucket(82000, bid="100000")]),
            report("t3", [bucket(82000, bid="400000")]),
        ]
        summary = summarize_snapshots(reports, 250000)
        row = next(x for x in summary["persistent_buckets"]
                   if x["side"] == "bid" and x["bucket_start"] == "82000")
        self.assertEqual(row["observations_above_threshold"], 2)
        self.assertEqual(row["persistence_pct"], 66.67)
        self.assertEqual(row["notional_max_usd"], "400000")

    def test_tracks_side_separately_and_exact_levels(self):
        reports = [
            report("t1", [bucket(82100, ask="500000")],
                   [{"side": "ask", "price": "82200.0", "notional_usd": "500000"}]),
            report("t2", [bucket(82100, ask="600000")],
                   [{"side": "ask", "price": "82200.0", "notional_usd": "600000"}]),
        ]
        summary = summarize_snapshots(reports, 250000)
        self.assertEqual(summary["persistent_buckets"][0]["side"], "ask")
        self.assertEqual(summary["persistent_buckets"][0]["persistence_pct"], 100.0)
        self.assertEqual(summary["repeated_top_levels"][0]["observations_seen_in_top_n"], 2)

    def test_rejects_empty_input(self):
        with self.assertRaises(ValueError):
            summarize_snapshots([])


if __name__ == "__main__":
    unittest.main()
