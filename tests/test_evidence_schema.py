"""Contract tests for the CryptoDueDiligence evidence JSON Schema."""

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "evidence.schema.json"


def load_schema():
    with SCHEMA_PATH.open(encoding="utf-8") as handle:
        schema = json.load(handle)
    Draft202012Validator.check_schema(schema)
    return schema


class EvidenceSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_schema()
        cls.validator = Draft202012Validator(
            cls.schema, format_checker=FormatChecker()
        )

    def assert_valid(self, instance):
        errors = list(self.validator.iter_errors(instance))
        self.assertEqual([], errors, "\n".join(error.message for error in errors))

    def assert_invalid(self, instance):
        self.assertTrue(list(self.validator.iter_errors(instance)))

    def envelope(self, record_type, record):
        return {
            "schema_version": "1.0.0",
            "record_type": record_type,
            "record": record,
        }

    def test_valid_event_with_unknown_effect(self):
        event = {
            "schema_version": "1.0.0",
            "event_id": "evt_example",
            "asset_id": "chain:example:asset:token",
            "event_type": "PROJECT_FUNDAMENTALS",
            "title": "Example announcement",
            "summary": "An example announcement; implementation is not independently confirmed.",
            "occurred_at": None,
            "published_at": "2026-10-18T14:00:00Z",
            "captured_at": "2026-10-18T14:05:00Z",
            "recorded_at": "2026-10-18T14:10:00Z",
            "verification_status": "PARTIALLY_VERIFIED",
            "event_status": "ANNOUNCED",
            "source_ids": ["src_example"],
            "evidence_ids": ["evd_example"],
            "observed_price_effect": {
                "direction": "UNKNOWN",
                "return_pct": None,
                "window_start": None,
                "window_end": None,
                "methodology_version": None,
            },
            "duplicate_of": None,
            "notes": "No causal price effect asserted.",
        }
        self.assert_valid(self.envelope("Event", event))

    def test_valid_source(self):
        source = {
            "source_id": "src_example",
            "source_type": "OFFICIAL_ANNOUNCEMENT",
            "publisher": "Example project",
            "title": None,
            "url": "https://example.org/announcement",
            "published_at": None,
            "retrieved_at": "2026-10-18T14:05:00Z",
        }
        self.assert_valid(self.envelope("Source", source))

    def test_valid_evidence(self):
        evidence = {
            "evidence_id": "evd_example",
            "source_id": "src_example",
            "claim": "The announcement was published.",
            "evidence_role": "SUPPORTS",
            "captured_at": "2026-10-18T14:05:00Z",
            "verification_method": "Compared with the primary publication.",
            "verification_status": "VERIFIED",
        }
        self.assert_valid(self.envelope("Evidence", evidence))

    def test_valid_market_observation(self):
        observation = {
            "observation_id": "obs_example",
            "asset_id": "chain:example:asset:token",
            "metric": "price_return",
            "value": 2.4,
            "unit": "percent",
            "window_start": "2026-10-18T14:00:00Z",
            "window_end": "2026-10-18T15:00:00Z",
            "venue_or_dataset": "example-dataset",
            "methodology_version": "1.0.0",
            "captured_at": "2026-10-18T15:01:00Z",
        }
        self.assert_valid(self.envelope("MarketObservation", observation))

    def test_rejects_missing_required_field(self):
        event = {
            "schema_version": "1.0.0",
            "event_id": "evt_example",
        }
        self.assert_invalid(self.envelope("Event", event))

    def test_rejects_unknown_event_type(self):
        event = {
            "schema_version": "1.0.0",
            "event_id": "evt_example",
            "asset_id": "asset:example",
            "event_type": "BULLISH_NEWS",
            "title": "Not a canonical category",
            "summary": "Test record.",
            "captured_at": "2026-10-18T14:05:00Z",
            "recorded_at": "2026-10-18T14:10:00Z",
            "verification_status": "UNVERIFIED",
            "event_status": "UNKNOWN",
            "source_ids": [],
            "evidence_ids": [],
        }
        self.assert_invalid(self.envelope("Event", event))

    def test_rejects_non_utc_timestamp(self):
        source = {
            "source_id": "src_example",
            "source_type": "NEWS_MEDIA",
            "publisher": "Example",
            "url": "https://example.org/news",
            "retrieved_at": "2026-10-18T14:05:00+02:00",
        }
        self.assert_invalid(self.envelope("Source", source))

    def test_rejects_record_type_mismatch(self):
        source = {
            "source_id": "src_example",
            "source_type": "OTHER",
            "publisher": "Example",
            "url": "https://example.org",
            "retrieved_at": "2026-10-18T14:05:00Z",
        }
        self.assert_invalid(self.envelope("Event", source))

    def test_rejects_unknown_observed_price_effect_direction(self):
        event = {
            "schema_version": "1.0.0",
            "event_id": "evt_example",
            "asset_id": "asset:example",
            "event_type": "PROJECT_FUNDAMENTALS",
            "title": "Example",
            "summary": "Test record.",
            "captured_at": "2026-10-18T14:05:00Z",
            "recorded_at": "2026-10-18T14:10:00Z",
            "verification_status": "UNVERIFIED",
            "event_status": "UNKNOWN",
            "source_ids": [],
            "evidence_ids": [],
            "observed_price_effect": {
                "direction": "UP_ONLY",
                "return_pct": 2,
                "window_start": "2026-10-18T14:00:00Z",
                "window_end": "2026-10-18T15:00:00Z",
                "methodology_version": "1.0.0",
            },
        }
        self.assert_invalid(self.envelope("Event", event))


if __name__ == "__main__":
    unittest.main()
