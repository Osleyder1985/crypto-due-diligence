import unittest
from decimal import Decimal

from orderbook.lifecycle import CVDAccumulator, LevelLifecycleTracker


class LevelLifecycleTests(unittest.TestCase):
    def test_level_add_update_remove_preserves_first_observed_time(self):
        tracker = LevelLifecycleTracker()
        tracker.seed(
            {Decimal("100"): Decimal("2")},
            {Decimal("101"): Decimal("3")},
            "2026-01-01T00:00:00Z",
        )
        changed = tracker.apply_event(
            {"b": [["100", "4"], ["99", "1"]], "a": []},
            "2026-01-01T00:00:02Z",
        )
        self.assertEqual([row["event_type"] for row in changed], ["quantity_changed", "added"])
        self.assertEqual(changed[0]["observed_lifetime_ms"], 2000)
        self.assertEqual(changed[0]["first_observed_at"], "2026-01-01T00:00:00Z")
        removed = tracker.apply_event(
            {"b": [["100", "0"]], "a": []},
            "2026-01-01T00:00:03Z",
        )
        self.assertEqual(removed[0]["event_type"], "removed")
        self.assertEqual(removed[0]["observed_lifetime_ms"], 3000)

    def test_repeated_removal_does_not_emit_false_lifecycle_event(self):
        tracker = LevelLifecycleTracker()
        tracker.seed({Decimal("100"): Decimal("1")}, {}, "2026-01-01T00:00:00Z")
        tracker.apply_event({"b": [["100", "0"]]}, "2026-01-01T00:00:01Z")
        self.assertEqual(tracker.apply_event({"b": [["100", "0"]]}, "2026-01-01T00:00:02Z"), [])

    def test_cvd_uses_binance_buyer_maker_flag(self):
        cvd = CVDAccumulator()
        buy = cvd.add_trade("100", "2", False)
        self.assertEqual(buy["aggressor_side_inferred"], "BUY")
        self.assertEqual(buy["cvd_base"], "2")
        sell = cvd.add_trade("110", "1", True)
        self.assertEqual(sell["aggressor_side_inferred"], "SELL")
        self.assertEqual(sell["cvd_base"], "1")
        self.assertEqual(sell["cvd_quote"], "90")


if __name__ == "__main__":
    unittest.main()
