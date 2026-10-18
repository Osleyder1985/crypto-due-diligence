"""Tests for semantic evidence collection validation."""

import unittest

from semantic_validation import validate_record_collection


def envelope(record_type, record):
    return {"schema_version": "1.0.0", "record_type": record_type, "record": record}


def source(source_id="src_1"):
    return envelope("Source", {
        "source_id": source_id,
        "source_type": "OFFICIAL_ANNOUNCEMENT",
        "publisher": "Example",
        "url": "https://example.org/source",
        "retrieved_at": "2026-10-18T14:00:00Z",
    })


def evidence(evidence_id="evd_1", source_id="src_1"):
    return envelope("Evidence", {
        "evidence_id": evidence_id,
        "source_id": source_id,
        "claim": "A testable claim.",
        "evidence_role": "SUPPORTS",
        "captured_at": "2026-10-18T14:01:00Z",
        "verification_method": "Compared with the source.",
        "verification_status": "VERIFIED",
    })


def event(source_ids=None, evidence_ids=None, effect=None):
    record = {
        "schema_version": "1.0.0",
        "event_id": "evt_1",
        "asset_id": "asset:example",
        "event_type": "PROJECT_FUNDAMENTALS",
        "title": "Example event",
        "summary": "An example event for tests.",
        "captured_at": "2026-10-18T14:02:00Z",
        "recorded_at": "2026-10-18T14:03:00Z",
        "verification_status": "PARTIALLY_VERIFIED",
        "event_status": "ANNOUNCED",
        "source_ids": ["src_1"] if source_ids is None else source_ids,
        "evidence_ids": ["evd_1"] if evidence_ids is None else evidence_ids,
    }
    if effect is not None:
        record["observed_price_effect"] = effect
    return envelope("Event", record)


def observation(start="2026-10-18T14:00:00Z", end="2026-10-18T15:00:00Z"):
    return envelope("MarketObservation", {
        "observation_id": "obs_1",
        "asset_id": "asset:example",
        "metric": "price_return",
        "value": 1.2,
        "unit": "percent",
        "window_start": start,
        "window_end": end,
        "venue_or_dataset": "example-dataset",
        "methodology_version": "1.0.0",
        "captured_at": "2026-10-18T15:01:00Z",
    })


class EvidenceSemanticValidationTests(unittest.TestCase):
    def test_accepts_valid_cross_record_references(self):
        records = [source(), evidence(), event()]
        self.assertEqual([], validate_record_collection(records))

    def test_rejects_missing_event_source_reference(self):
        errors = validate_record_collection([evidence(), event(source_ids=["src_missing"])])
        self.assertTrue(any("source_ids[0]" in error for error in errors))

    def test_rejects_missing_event_evidence_reference(self):
        errors = validate_record_collection([source(), event(evidence_ids=["evd_missing"])])
        self.assertTrue(any("evidence_ids[0]" in error for error in errors))

    def test_rejects_evidence_with_missing_source(self):
        errors = validate_record_collection([evidence(source_id="src_missing")])
        self.assertTrue(any("source_id" in error and "existing Source" in error for error in errors))

    def test_rejects_duplicate_record_ids(self):
        errors = validate_record_collection([source(), source()])
        self.assertTrue(any("duplicate ID 'src_1'" in error for error in errors))

    def test_accepts_ordered_market_window(self):
        self.assertEqual([], validate_record_collection([observation()]))

    def test_rejects_equal_market_window_bounds(self):
        errors = validate_record_collection([observation(
            start="2026-10-18T14:00:00Z", end="2026-10-18T14:00:00Z"
        )])
        self.assertTrue(any("window_start must be earlier than window_end" in error for error in errors))

    def test_rejects_reversed_market_window_bounds(self):
        errors = validate_record_collection([observation(
            start="2026-10-18T15:00:00Z", end="2026-10-18T14:00:00Z"
        )])
        self.assertTrue(any("window_start must be earlier than window_end" in error for error in errors))

    def test_rejects_reversed_observed_price_effect_window(self):
        effect = {
            "direction": "positive_observed",
            "return_pct": 2.0,
            "window_start": "2026-10-18T15:00:00Z",
            "window_end": "2026-10-18T14:00:00Z",
            "methodology_version": "1.0.0",
        }
        errors = validate_record_collection([event(effect=effect)])
        self.assertTrue(any("window_start must be earlier than window_end" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
