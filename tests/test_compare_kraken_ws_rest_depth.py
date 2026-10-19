import json
import tempfile
import unittest
from pathlib import Path

from orderbook.compare_kraken_ws_rest_depth import compare


class CompareKrakenDepthTests(unittest.TestCase):
    def _write(self, path, rows):
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def _row(self, timestamp, bid_count, ask_count, worst_bid, worst_ask, checksum=False):
        return {
            "captured_at": timestamp,
            "mid_price": "100.5",
            "bid_level_count": bid_count,
            "ask_level_count": ask_count,
            "worst_bid_price": str(worst_bid),
            "worst_ask_price": str(worst_ask),
            "book_checksum_validated": checksum,
        }

    def test_reports_actual_depth_and_temporal_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rest = root / "rest.jsonl"
            ws = root / "ws.jsonl"
            self._write(rest, [
                self._row("2026-10-19T10:00:00Z", 500, 499, 90, 111),
                self._row("2026-10-19T10:00:15Z", 498, 500, 89, 112),
            ])
            self._write(ws, [
                self._row("2026-10-19T10:00:05Z", 1000, 1000, 80, 120, True),
                self._row("2026-10-19T10:00:10Z", 999, 1000, 79, 121, True),
            ])
            report = compare(rest, ws, root / "out")
            self.assertTrue(report["temporal_windows_overlap"])
            self.assertEqual(report["rest"]["bid_level_count_median"], 499)
            self.assertEqual(report["websocket"]["bid_level_count_median"], 999.5)
            self.assertEqual(report["websocket"]["checksum_validated_snapshots"], 2)
            self.assertTrue((root / "out" / "kraken-ws-rest-depth-comparison.md").exists())

    def test_rejects_non_overlapping_capture_windows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rest = root / "rest.jsonl"
            ws = root / "ws.jsonl"
            self._write(rest, [
                self._row("2026-10-19T10:00:00Z", 500, 500, 90, 111),
            ])
            self._write(ws, [
                self._row("2026-10-19T10:01:00Z", 1000, 1000, 80, 120, True),
            ])
            with self.assertRaisesRegex(RuntimeError, "did not overlap"):
                compare(rest, ws, root / "out")


if __name__ == "__main__":
    unittest.main()
