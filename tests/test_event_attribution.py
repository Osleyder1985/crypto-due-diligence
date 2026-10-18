import unittest
from datetime import datetime, timedelta, timezone

from event_attribution import analyze_event_reactions, parse_utc


def candles(count=40):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for i in range(count):
        close = 100 + i
        rows.append({"timestamp": (start + timedelta(hours=i)).isoformat().replace("+00:00", "Z"),
                     "open": close, "high": close + 1, "low": close - 1,
                     "close": close, "volume": 10 if i < 10 else 20})
    return rows


class EventAttributionTests(unittest.TestCase):
    def test_parse_utc_rejects_naive_timestamp(self):
        self.assertIsNone(parse_utc("2026-01-01T00:00:00"))
        self.assertIsNotNone(parse_utc("2026-01-01T00:00:00Z"))

    def test_reaction_metrics_and_timestamp_proxy(self):
        events = [{"title": "Example headline", "publisher": "Example",
                   "published_at": "2026-01-01T10:00:00Z", "url": "https://example.test"}]
        result = analyze_event_reactions(events, candles(), windows_hours=(1, 6))
        item = result["timeline"][0]
        self.assertEqual("publication_timestamp_proxy", item["timestamp_source"])
        self.assertEqual("LOW", item["timestamp_confidence"])
        self.assertEqual("COMPUTED", item["reactions"]["1h"]["status"])
        self.assertGreater(item["reactions"]["1h"]["return_pct"], 0)
        self.assertIn("does not prove", item["assessment_note"])

    def test_missing_timestamp_and_short_coverage_are_explicit(self):
        result = analyze_event_reactions([{"title": "No time"}], candles(2), windows_hours=(24,))
        self.assertEqual("UNAVAILABLE_TIMESTAMP", result["timeline"][0]["reactions"]["24h"]["status"])
        result = analyze_event_reactions([{"published_at": "2026-01-01T00:00:00Z"}],
                                         candles(2), windows_hours=(24,))
        self.assertEqual("INSUFFICIENT_FORWARD_COVERAGE", result["timeline"][0]["reactions"]["24h"]["status"])

    def test_invalid_windows_rejected(self):
        with self.assertRaises(ValueError):
            analyze_event_reactions([], candles(), windows_hours=(0,))


if __name__ == "__main__":
    unittest.main()
