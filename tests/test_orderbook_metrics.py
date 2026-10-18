import unittest
from decimal import Decimal

from orderbook.binance_spot_collector import apply_depth_event, calculate_metrics, _levels


class OrderBookMetricsTests(unittest.TestCase):
    def test_depth_updates_replace_and_delete_levels(self):
        bids = _levels([["100", "2"], ["99", "3"]])
        asks = _levels([["101", "4"]])
        apply_depth_event(bids, asks, {"b": [["100", "0"], ["99", "5"]], "a": [["101", "1"]]})
        self.assertNotIn(Decimal("100"), bids)
        self.assertEqual(bids[Decimal("99")], Decimal("5"))
        self.assertEqual(asks[Decimal("101")], Decimal("1"))

    def test_spread_and_balanced_imbalance(self):
        bids = {Decimal("99"): Decimal("10")}
        asks = {Decimal("101"): Decimal("10")}
        metrics = calculate_metrics(bids, asks, Decimal("2"), Decimal("100"))
        self.assertEqual(metrics["status"], "OK")
        self.assertEqual(Decimal(metrics["spread"]), Decimal("2"))
        self.assertEqual(Decimal(metrics["obi_base_quantity"]), Decimal("0"))
        self.assertTrue(metrics["slippage_buy_quote"]["fully_filled"])
        self.assertTrue(metrics["slippage_sell_quote"]["fully_filled"])

    def test_imbalance_sign_tracks_bid_pressure(self):
        bids = {Decimal("100"): Decimal("20")}
        asks = {Decimal("101"): Decimal("5")}
        metrics = calculate_metrics(bids, asks, Decimal("2"), Decimal("100"))
        self.assertGreater(Decimal(metrics["obi_base_quantity"]), Decimal("0"))

    def test_insufficient_depth_reports_unfilled_size(self):
        bids = {Decimal("100"): Decimal("0.1")}
        asks = {Decimal("101"): Decimal("0.1")}
        metrics = calculate_metrics(bids, asks, Decimal("1"), Decimal("1000"))
        self.assertFalse(metrics["slippage_buy_quote"]["fully_filled"])
        self.assertGreater(Decimal(metrics["slippage_buy_quote"]["unfilled_quote"]), Decimal("0"))

    def test_empty_book_is_not_silently_scored(self):
        self.assertEqual(calculate_metrics({}, {})["status"], "BOOK_EMPTY")


if __name__ == "__main__":
    unittest.main()
