"""Transparent hypothesis assessment with an explicit inconclusive outcome."""
from collections import Counter

EVALUATOR_VERSION = "1.0.0"
VERIFIED_STATES = {"VERIFIED", "PARTIALLY_VERIFIED"}
VALID_ROLES = {"SUPPORTS", "CONTRADICTS", "CONTEXTUALIZES", "REFUTES"}


def evaluate_hypotheses(hypotheses, envelopes, market_context=None, min_relevant_evidence=2):
    """Assess evidentiary balance, not causal probability.

    Each hypothesis is a dict with hypothesis_id, statement, supporting_evidence_ids,
    contradicting_evidence_ids, and optional contextual_evidence_ids. A result is
    INCONCLUSIVE when evidence is sparse, mixed, unverified, or references are missing.
    """
    if min_relevant_evidence < 1:
        raise ValueError("min_relevant_evidence must be at least 1")
    evidence_by_id = {}
    for envelope in envelopes:
        if isinstance(envelope, dict) and envelope.get("record_type") == "Evidence":
            record = envelope.get("record", {})
            if isinstance(record, dict) and isinstance(record.get("evidence_id"), str):
                evidence_by_id[record["evidence_id"]] = record

    results = []
    for hypothesis in hypotheses:
        hid = hypothesis.get("hypothesis_id", "hypothesis_unknown")
        support_ids = hypothesis.get("supporting_evidence_ids", [])
        against_ids = hypothesis.get("contradicting_evidence_ids", [])
        context_ids = hypothesis.get("contextual_evidence_ids", [])
        missing_ids = sorted(set(support_ids + against_ids + context_ids) - set(evidence_by_id))
        support = [evidence_by_id[eid] for eid in support_ids if eid in evidence_by_id]
        against = [evidence_by_id[eid] for eid in against_ids if eid in evidence_by_id]
        context = [evidence_by_id[eid] for eid in context_ids if eid in evidence_by_id]
        eligible_support = [e for e in support if e.get("verification_status") in VERIFIED_STATES]
        eligible_against = [e for e in against if e.get("verification_status") in VERIFIED_STATES]
        eligible_support = [e for e in eligible_support if e.get("evidence_role") in {"SUPPORTS", "CONTEXTUALIZES"}]
        eligible_against = [e for e in eligible_against if e.get("evidence_role") in {"CONTRADICTS", "REFUTES"}]
        counts = Counter(e.get("verification_status", "UNKNOWN") for e in support + against + context)
        total_relevant = len(eligible_support) + len(eligible_against)
        if total_relevant < min_relevant_evidence:
            outcome = "INCONCLUSIVE"
            reason = "insufficient independently verified relevant evidence"
        elif len(eligible_support) == len(eligible_against):
            outcome = "INCONCLUSIVE"
            reason = "verified evidence is balanced or does not discriminate between alternatives"
        elif len(eligible_support) > len(eligible_against):
            outcome = "EVIDENCE_FAVORS"
            reason = "the mapped verified evidence favors the hypothesis; this is not proof of causality"
        else:
            outcome = "EVIDENCE_AGAINST"
            reason = "the mapped verified evidence weighs against the hypothesis"
        results.append({
            "hypothesis_id": hid, "statement": hypothesis.get("statement", ""),
            "outcome": outcome, "reason": reason,
            "supporting_evidence_ids": support_ids,
            "contradicting_evidence_ids": against_ids,
            "contextual_evidence_ids": context_ids,
            "missing_evidence_ids": missing_ids,
            "verification_state_counts": dict(sorted(counts.items())),
            "market_context": market_context or {},
            "evaluator_version": EVALUATOR_VERSION,
            "causal_probability": None,
        })
    return {"evaluator_version": EVALUATOR_VERSION, "results": results,
            "limitations": [
                "Outcomes summarize mapped evidence and are not probabilities.",
                "Source independence, selection bias and evidence quality require analyst review.",
                "Temporal association alone does not establish causation.",
            ]}
