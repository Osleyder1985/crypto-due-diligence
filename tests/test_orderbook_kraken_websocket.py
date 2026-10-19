import unittest
from decimal import Decimal

from orderbook.kraken_websocket_collector import (
    BookChecksumError,
    apply_book_message,
    calculate_checksum,
    snapshot_report,
)


class KrakenWebSocketBookTests(unittest.TestCase):
    def test_snapshot_and_delta_add_update_delete(self):
        book = {"bids": {}, "asks": {}, "last_update_at": None, "checksum": None}
        snap = {"type": "snapshot", "data": [{"bids": [
            {"price": "100", "qty": "2"}, {"price": "99", "qty": "3"}],
            "asks": [{"price": "101", "qty": "4"}]}]}
        self.assertTrue(apply_book_message(book, snap))
        self.assertEqual(book["bids"]["100"], Decimal("2"))
        delta = {"type": "update", "data": [{"bids": [
            {"price": "100", "qty": "5"}, {"price": "99", "qty": "0"}],
            "asks": [{"price": "101", "qty": "0"}, {"price": "102", "qty": "1"}]}]}
        self.assertFalse(apply_book_message(book, delta))
        self.assertEqual(book["bids"]["100"], Decimal("5"))
        self.assertNotIn("99", book["bids"])
        self.assertNotIn("101", book["asks"])
        self.assertIn("102", book["asks"])

    def test_official_kraken_checksum_example(self):
        # Kraken's documented v2 example yields CRC32 3310070434.
        bids = [
            ("45283.5", "0.10000000"), ("45283.4", "1.54582015"),
            ("45282.1", "0.10000000"), ("45281.0", "0.10000000"),
            ("45280.3", "1.54592586"), ("45279.0", "0.07990000"),
            ("45277.6", "0.03310103"), ("45277.5", "0.30000000"),
            ("45277.3", "1.54602737"), ("45276.6", "0.15445238"),
        ]
        asks = [
            ("45285.2", "0.00100000"), ("45286.4", "1.54571953"),
            ("45286.6", "1.54571109"), ("45289.6", "1.54560911"),
            ("45290.2", "0.15890660"), ("45291.8", "1.54553491"),
            ("45294.7", "0.04454749"), ("45296.1", "0.35380000"),
            ("45297.5", "0.09945542"), ("45299.5", "0.18772827"),
        ]
        book = {
            "bids": {p: Decimal(q) for p, q in bids},
            "asks": {p: Decimal(q) for p, q in asks},
        }
        self.assertEqual(calculate_checksum(book), 3310070434)

    def test_checksum_mismatch_is_rejected(self):
        book = {"bids": {}, "asks": {}, "last_update_at": None, "checksum": None}
        message = {"type": "snapshot", "data": [{
            "bids": [{"price": "100", "qty": "2"}],
            "asks": [{"price": "101", "qty": "3"}],
            "checksum": 1,
        }]}
        with self.assertRaises(BookChecksumError):
            apply_book_message(book, message)

    def test_report_includes_actual_outer_limits_and_checksum_status(self):
        book = {
            "bids": {"100000": Decimal("2"), "99800": Decimal("1")},
            "asks": {"100100": Decimal("3"), "100400": Decimal("2")},
            "last_update_at": "2026-01-01T00:00:00Z",
            "checksum": 12345,
        }
        report = snapshot_report(book)
        self.assertEqual(report["venue"], "kraken_spot_ws_v2")
        self.assertEqual(report["bid_level_count"], 2)
        self.assertEqual(report["ask_level_count"], 2)
        self.assertEqual(report["mid_price"], "100050")
        self.assertEqual(report["best_bid_price"], "100000")
        self.assertEqual(report["worst_bid_price"], "99800")
        self.assertEqual(report["best_ask_price"], "100100")
        self.assertEqual(report["worst_ask_price"], "100400")
        self.assertTrue(report["book_checksum_validated"])


if __name__ == "__main__":
    unittest.main()
