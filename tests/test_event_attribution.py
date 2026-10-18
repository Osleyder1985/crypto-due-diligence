import unittest
from datetime import datetime, timedelta, timezone

from event_attribution import analyze_event_reactions, deduplicate_events, parse_utc


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
        self.assertIn("not evidence of causation", item["assessment_note"])

    def test_missing_timestamp_and_short_coverage_are_explicit(self):
        result = analyze_event_reactions([{"title": "No time"}], candles(2), windows_hours=(24,))
        self.assertEqual("UNAVAILABLE_TIMESTAMP", result["timeline"][0]["reactions"]["24h"]["status"])
        result = analyze_event_reactions([{"published_at": "2026-01-01T00:00:00Z"}],
                                         candles(2), windows_hours=(24,))
        self.assertEqual("INSUFFICIENT_FORWARD_COVERAGE", result["timeline"][0]["reactions"]["24h"]["status"])

    def test_invalid_windows_rejected(self):
        with self.assertRaises(ValueError):
            analyze_event_reactions([], candles(), windows_hours=(0,))

    def test_exact_syndicated_headlines_are_grouped_and_provenance_preserved(self):
        events = [
            {"title": "Bitcoin rises after ETF inflows", "publisher": "A", "url": "https://a.test/story",
             "published_at": "2026-01-01T10:00:00Z"},
            {"title": "BITCOIN rises after ETF inflows!", "publisher": "B", "url": "https://b.test/story",
             "published_at": "2026-01-01T12:00:00Z"},
        ]
        grouped = deduplicate_events(events)
        self.assertEqual(1, len(grouped))
        self.assertEqual(2, grouped[0]["duplicate_count"])
        self.assertEqual({"A", "B"}, {x["publisher"] for x in grouped[0]["duplicate_sources"]})

    def test_near_duplicates_group_but_distinct_story_does_not(self):
        events = [
            {"title": "Bitcoin price rises sharply after large exchange fund inflows", "published_at": "2026-01-01T10:00:00Z"},
            {"title": "Bitcoin price rises sharply after large exchange fund inflows today", "published_at": "2026-01-01T11:00:00Z"},
            {"title": "Ethereum developers announce a major network upgrade", "published_at": "2026-01-01T11:00:00Z"},
        ]
        grouped = deduplicate_events(events)
        self.assertEqual(2, len(grouped))
        self.assertEqual(2, next(x for x in grouped if x["duplicate_count"] == 2)["duplicate_count"])

    def test_far_apart_republication_is_not_merged(self):
        events = [
            {"title": "Bitcoin rises after ETF inflows", "published_at": "2026-01-01T10:00:00Z"},
            {"title": "Bitcoin rises after ETF inflows", "published_at": "2026-01-10T10:00:00Z"},
        ]
        self.assertEqual(2, len(deduplicate_events(events)))

    def test_events_with_same_anchor_are_flagged_as_overlapping_observations(self):
        events = [
            {"title": "Headline A", "published_at": "2026-01-01T10:00:00Z"},
            {"title": "Headline B", "published_at": "2026-01-01T10:00:00Z"},
            {"title": "Headline C", "published_at": "2026-01-01T11:00:00Z"},
        ]
        result = analyze_event_reactions(events, candles(), windows_hours=(1, 6, 24))
        by_title = {item["title"]: item for item in result["timeline"]}
        self.assertTrue(by_title["Headline A"]["shared_reaction_window_warning"])
        self.assertEqual(2, by_title["Headline A"]["overlapping_event_count_by_window"]["1h"])
        self.assertEqual(2, by_title["Headline A"]["overlapping_event_count_by_window"]["6h"])
        self.assertIn("not be counted as independent evidence",
                      by_title["Headline A"]["shared_reaction_window_note"])
        self.assertEqual(0, by_title["Headline C"]["overlapping_event_count_by_window"]["1h"])

    def test_weak_and_unknown_asset_matches_are_flagged(self):
        weak = analyze_event_reactions([{"title": "Macro update", "published_at": "2026-01-01T10:00:00Z",
                                         "match_quality": "WEAK"}], candles(), windows_hours=(6,))
        self.assertIn("only outside the headline", weak["timeline"][0]["weak_match_warning"])
        unknown = analyze_event_reactions([{"title": "Headline", "published_at": "2026-01-01T10:00:00Z"}],
                                          candles(), windows_hours=(1,))
        self.assertEqual("UNKNOWN", unknown["timeline"][0]["match_quality"])
        self.assertIsNotNone(unknown["timeline"][0]["weak_match_warning"])

    def test_large_observed_reaction_is_not_called_causal(self):
        result = analyze_event_reactions([{"title": "Headline", "published_at": "2026-01-01T10:00:00Z",
                                           "match_quality": "STRONG"}], candles(), windows_hours=(6,))
        item = result["timeline"][0]
        self.assertEqual("observed_reaction", item["assessment"])
        self.assertIn("not evidence of causation", item["assessment_note"])
        self.assertTrue(item["alternative_explanations"])


if __name__ == "__main__":
    unittest.main()
