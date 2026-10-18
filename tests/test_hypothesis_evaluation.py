"""Tests for transparent hypothesis assessment."""
import unittest

from hypothesis_evaluation import evaluate_hypotheses


def evidence(eid, role, status="VERIFIED"):
    return {"schema_version": "1.0.0", "record_type": "Evidence", "record": {
        "evidence_id": eid, "source_id": "src_fixture", "claim": f"claim {eid}",
        "evidence_role": role, "captured_at": "2026-01-01T00:00:00Z",
        "verification_method": "test fixture", "verification_status": status,
    }}


class HypothesisEvaluationTests(unittest.TestCase):
    def test_evidence_favors_when_multiple_verified_items_support(self):
        records = [evidence("evd_s1", "SUPPORTS"), evidence("evd_s2", "SUPPORTS")]
        result = evaluate_hypotheses([{"hypothesis_id": "h1", "statement": "hypothesis",
            "supporting_evidence_ids": ["evd_s1", "evd_s2"]}], records)
        self.assertEqual("EVIDENCE_FAVORS", result["results"][0]["outcome"])
        self.assertIsNone(result["results"][0]["causal_probability"])

    def test_contradiction_outweighs_support(self):
        records = [evidence("evd_s1", "SUPPORTS"), evidence("evd_c1", "REFUTES"), evidence("evd_c2", "CONTRADICTS")]
        result = evaluate_hypotheses([{"hypothesis_id": "h1", "supporting_evidence_ids": ["evd_s1"],
            "contradicting_evidence_ids": ["evd_c1", "evd_c2"]}], records)
        self.assertEqual("EVIDENCE_AGAINST", result["results"][0]["outcome"])

    def test_insufficient_or_unverified_evidence_is_inconclusive(self):
        records = [evidence("evd_u1", "SUPPORTS", "UNVERIFIED")]
        result = evaluate_hypotheses([{"hypothesis_id": "h1", "supporting_evidence_ids": ["evd_u1"]}], records)
        self.assertEqual("INCONCLUSIVE", result["results"][0]["outcome"])

    def test_balanced_evidence_is_inconclusive(self):
        records = [evidence("evd_s1", "SUPPORTS"), evidence("evd_c1", "REFUTES")]
        result = evaluate_hypotheses([{"hypothesis_id": "h1", "supporting_evidence_ids": ["evd_s1"],
            "contradicting_evidence_ids": ["evd_c1"]}], records)
        self.assertEqual("INCONCLUSIVE", result["results"][0]["outcome"])

    def test_missing_evidence_reference_is_reported(self):
        result = evaluate_hypotheses([{"hypothesis_id": "h1", "supporting_evidence_ids": ["evd_missing"]}], [])
        self.assertEqual(["evd_missing"], result["results"][0]["missing_evidence_ids"])
        self.assertEqual("INCONCLUSIVE", result["results"][0]["outcome"])


if __name__ == "__main__":
    unittest.main()
