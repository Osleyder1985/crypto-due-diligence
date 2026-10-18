import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from historical_learning import (
    CaseValidationError,
    find_similar_cases,
    is_learning_eligible,
    load_cases,
    save_case,
    summarize_outcomes,
    validate_case,
)


def make_case(case_id="case-1", **overrides):
    case = {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "asset_id": "asset:example",
        "asset_symbol": "EX",
        "event_type": "EXCHANGE_MARKET_ACCESS",
        "detected_at": "2025-01-01T12:00:00Z",
        "window_minutes": 60,
        "movement_direction": "UP",
        "return_pct": 12.5,
        "candidate_factors": ["exchange_listing", "high_volume"],
        "evidence_ids": ["evidence-1"],
        "source_case_ids": [],
        "outcome_label": "SUPPORTED",
        "review_status": "REVIEWED",
        "verification_status": "VERIFIED",
        "reviewer": "analyst",
        "reviewed_at": "2025-01-02T12:00:00Z",
        "methodology_version": "1.0.0",
        "notes": None,
    }
    case.update(overrides)
    return case


class HistoricalLearningTests(unittest.TestCase):
    def test_valid_case_and_learning_eligibility(self):
        case = make_case()
        self.assertEqual(validate_case(case), [])
        self.assertTrue(is_learning_eligible(case))

    def test_executable_json_schema_accepts_valid_case_and_rejects_extra_fields(self):
        schema_path = Path(__file__).resolve().parents[1] / "schemas" / "historical-case.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        self.assertEqual(list(validator.iter_errors(make_case())), [])
        invalid = make_case(unexpected_field="must be rejected")
        self.assertTrue(list(validator.iter_errors(invalid)))

    def test_unreviewed_or_insufficient_cases_are_excluded(self):
        draft = make_case(review_status="DRAFT", reviewer=None, reviewed_at=None)
        insufficient = make_case("case-2", outcome_label="INSUFFICIENT_EVIDENCE")
        unverified = make_case("case-3", verification_status="UNVERIFIED")
        self.assertFalse(is_learning_eligible(draft))
        self.assertFalse(is_learning_eligible(insufficient))
        self.assertFalse(is_learning_eligible(unverified))

    def test_invalid_case_rejected(self):
        case = make_case(detected_at="not-a-time", window_minutes=0)
        self.assertTrue(validate_case(case))
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(CaseValidationError):
                save_case(Path(directory) / "cases.json", case)

    def test_persistence_and_duplicate_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            save_case(path, make_case())
            self.assertEqual(load_cases(path)[0]["case_id"], "case-1")
            with self.assertRaises(CaseValidationError):
                save_case(path, make_case())
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["store_schema_version"], "1.0.0")

    def test_similarity_is_explainable_and_deterministic(self):
        query = make_case("new-case")
        similar = make_case("prior-case")
        unrelated = make_case("unrelated", event_type="SECURITY_INCIDENT",
                              movement_direction="DOWN", candidate_factors=["exploit"])
        results = find_similar_cases(query, [unrelated, similar], limit=5)
        self.assertEqual(results[0]["case_id"], "prior-case")
        self.assertIn("shared_factors", results[0]["matching_reasons"])
        self.assertEqual(len(results), 1)

    def test_summary_excludes_unresolved_cases_and_reports_sample_size(self):
        cases = [
            make_case(),
            make_case("case-2", outcome_label="CONTRADICTED"),
            make_case("case-3", outcome_label="UNKNOWN"),
            make_case("case-4", review_status="DRAFT", reviewer=None, reviewed_at=None),
        ]
        summary = summarize_outcomes(cases)
        self.assertEqual(summary["eligible_case_count"], 2)
        self.assertEqual(summary["excluded_case_count"], 2)
        group = summary["by_event_type"]["EXCHANGE_MARKET_ACCESS"]
        self.assertEqual(group["sample_size"], 2)
        self.assertEqual(group["outcome_counts"]["SUPPORTED"], 1)
        self.assertIn("does not establish", summary["interpretation"])


if __name__ == "__main__":
    unittest.main()
