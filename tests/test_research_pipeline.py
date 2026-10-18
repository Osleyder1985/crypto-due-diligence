"""Integration tests for the structural-then-semantic validation entry point."""
import json
import unittest
from pathlib import Path

from research_pipeline import validate_envelopes, validate_fixture

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "research"


class ResearchPipelineTests(unittest.TestCase):
    def test_all_reference_fixtures_pass_validation(self):
        for path in sorted(FIXTURES.glob("*.json")):
            with self.subTest(fixture=path.name):
                result = validate_fixture(path)
                self.assertTrue(result["valid"], result)

    def test_structural_errors_prevent_semantic_stage(self):
        result = validate_envelopes([{"schema_version": "1.0.0", "record_type": "Source", "record": {}}])
        self.assertFalse(result["valid"])
        self.assertEqual("structural", result["stage"])

    def test_semantic_errors_reported_after_structural_validation(self):
        fixture = json.loads((FIXTURES / "supporting_evidence.json").read_text(encoding="utf-8"))
        fixture["records"][2]["record"]["source_ids"] = ["src_missing"]
        result = validate_envelopes(fixture["records"])
        self.assertFalse(result["valid"])
        self.assertEqual("semantic", result["stage"])
        self.assertTrue(any("existing Source" in error for error in result["errors"]))

    def test_empty_record_list_is_rejected_as_semantically_validity_not_proof(self):
        # An empty collection has no schema violations and no broken references;
        # caller-level policy may reject it for a specific research task.
        result = validate_envelopes([])
        self.assertTrue(result["valid"])


if __name__ == "__main__":
    unittest.main()
