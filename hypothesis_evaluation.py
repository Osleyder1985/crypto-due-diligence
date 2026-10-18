"""Transparent hypothesis assessment with an explicit inconclusive outcome."""
from collections import Counter

EVALUATOR_VERSION = "1.0.0"
VERIFIED_STATES = {"VERIFIED", "PARTIALLY_VERIFIED"}


def evaluate_hypotheses(hypotheses, envelopes, market_context=None, min_relevant_evidence=2):
    """Assess mapped evidence and expose alternatives/context for analyst comparison.

    Each hypothesis accepts supporting_evidence_ids, contradicting_evidence_ids,
    contextual_evidence_ids, and alternative_explanations. Run each competing
    explanation as a separate hypothesis to compare its evidentiary outcome.
    Market context is preserved as structured input, not silently converted into
    causal evidence or a probability.
    """
    if min_relevant_evidence < 1:
        raise ValueError("min_relevant_evidence must be at least 1")
    market_context = market_context or {}
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
        referenced_ids = support_ids + against_ids + context_ids
        missing_ids = sorted(set(referenced_ids) - set(evidence_by_id))
        support = [evidence_by_id[eid] for eid in support_ids if eid in evidence_by_id]
        against = [evidence_by_id[eid] for eid in against_ids if eid in evidence_by_id]
        context = [evidence_by_id[eid] for eid in context_ids if eid in evidence_by_id]
        eligible_support = [
            e for e in support
            if e.get("verification_status") in VERIFIED_STATES
            and e.get("evidence_role") in {"SUPPORTS", "CONTEXTUALIZES"}
        ]
        eligible_against = [
            e for e in against
            if e.get("verification_status") in VERIFIED_STATES
            and e.get("evidence_role") in {"CONTRADICTS", "REFUTES"}
        ]
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
            "hypothesis_id": hid,
            "statement": hypothesis.get("statement", ""),
            "outcome": outcome,
            "reason": reason,
            "supporting_evidence_ids": support_ids,
            "contradicting_evidence_ids": against_ids,
            "contextual_evidence_ids": context_ids,
            "missing_evidence_ids": missing_ids,
            "alternative_explanations": hypothesis.get("alternative_explanations", []),
            "verification_state_counts": dict(sorted(counts.items())),
            "contextual_evidence_count": len(context),
            "market_context": market_context,
            "market_context_review_required": bool(market_context),
            "evaluator_version": EVALUATOR_VERSION,
            "causal_probability": None,
        })
    return {
        "evaluator_version": EVALUATOR_VERSION,
        "results": results,
        "limitations": [
            "Outcomes summarize mapped evidence and are not probabilities.",
            "Run competing explanations as separate hypotheses; alternative_explanations is a review checklist, not an automatic test.",
            "Market context is retained for review and is not automatically treated as causal evidence.",
            "Source independence, selection bias and evidence quality require analyst review.",
            "Temporal association alone does not establish causation.",
        ],
    }
