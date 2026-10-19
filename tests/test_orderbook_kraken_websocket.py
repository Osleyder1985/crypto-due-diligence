import unittest
from orderbook.kraken_websocket_collector import apply_book_message, snapshot_report


class KrakenWebSocketBookTests(unittest.TestCase):
    def test_snapshot_and_delta_add_update_delete(self):
        book = {"bids": {}, "asks": {}, "last_update_at": None}
        snap = {"type": "snapshot", "data": [{"bids": [
            {"price": "100", "qty": "2"}, {"price": "99", "qty": "3"}],
            "asks": [{"price": "101", "qty": "4"}]}]}
        self.assertTrue(apply_book_message(book, snap))
        self.assertEqual(book["bids"]["100"], __import__("decimal").Decimal("2"))
        delta = {"type": "update", "data": [{"bids": [
            {"price": "100", "qty": "5"}, {"price": "99", "qty": "0"}],
            "asks": [{"price": "101", "qty": "0"}, {"price": "102", "qty": "1"}]}]}
        self.assertFalse(apply_book_message(book, delta))
        self.assertEqual(book["bids"]["100"], __import__("decimal").Decimal("5"))
        self.assertNotIn("99", book["bids"])
        self.assertNotIn("101", book["asks"])
        self.assertIn("102", book["asks"])

    def test_report_aggregates_maintained_book(self):
        book = {"bids": {"100000": __import__("decimal").Decimal("2")},
                "asks": {"100100": __import__("decimal").Decimal("3")},
                "last_update_at": "2026-01-01T00:00:00Z"}
        report = snapshot_report(book)
        self.assertEqual(report["venue"], "kraken_spot_ws_v2")
        self.assertEqual(report["bid_level_count"], 1)
        self.assertEqual(report["ask_level_count"], 1)
        self.assertEqual(report["mid_price"], "100050")


if __name__ == "__main__":
    unittest.main()
