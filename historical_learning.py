"""Versioned, auditable memory for reviewed crypto-market research cases.

This module stores reviewed case records and provides descriptive similarity and
outcome summaries. It does not infer causality, predict prices, or retrain a model.
"""
from __future__ import annotations

import json
import math
import os
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

CASE_SCHEMA_VERSION = "1.0.0"
LEARNING_MODULE_VERSION = "1.0.0"

OUTCOME_LABELS = {
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "CONTRADICTED",
    "MULTIPLE_FACTORS",
    "UNKNOWN",
    "INSUFFICIENT_EVIDENCE",
}
REVIEW_STATUSES = {"DRAFT", "REVIEWED"}
VERIFICATION_STATUSES = {"UNVERIFIED", "PARTIALLY_VERIFIED", "VERIFIED"}
MOVEMENT_DIRECTIONS = {"UP", "DOWN", "MIXED", "FLAT", "UNKNOWN"}
ELIGIBLE_OUTCOMES = {
    "SUPPORTED", "PARTIALLY_SUPPORTED", "CONTRADICTED", "MULTIPLE_FACTORS"
}


class CaseValidationError(ValueError):
    """Raised when a historical case violates the versioned record contract."""


def _is_utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0


def validate_case(case: dict[str, Any]) -> list[str]:
    """Return validation errors; an empty list means the case is structurally valid."""
    if not isinstance(case, dict):
        return ["case must be an object"]
    errors = []
    required_strings = (
        "case_id", "asset_id", "event_type", "detected_at",
        "movement_direction", "outcome_label", "review_status",
        "verification_status", "methodology_version",
    )
    for key in required_strings:
        if not isinstance(case.get(key), str) or not case[key].strip():
            errors.append(f"{key} must be a non-empty string")

    if case.get("schema_version") != CASE_SCHEMA_VERSION:
        errors.append(f"schema_version must equal {CASE_SCHEMA_VERSION}")
    if case.get("movement_direction") not in MOVEMENT_DIRECTIONS:
        errors.append(f"movement_direction must be one of {sorted(MOVEMENT_DIRECTIONS)}")
    if case.get("outcome_label") not in OUTCOME_LABELS:
        errors.append(f"outcome_label must be one of {sorted(OUTCOME_LABELS)}")
    if case.get("review_status") not in REVIEW_STATUSES:
        errors.append(f"review_status must be one of {sorted(REVIEW_STATUSES)}")
    if case.get("verification_status") not in VERIFICATION_STATUSES:
        errors.append(f"verification_status must be one of {sorted(VERIFICATION_STATUSES)}")
    if not _is_utc_timestamp(case.get("detected_at")):
        errors.append("detected_at must be an ISO 8601 UTC timestamp ending in Z")

    window = case.get("window_minutes")
    if isinstance(window, bool) or not isinstance(window, int) or window <= 0:
        errors.append("window_minutes must be a positive integer")
    return_pct = case.get("return_pct")
    if return_pct is not None and (
        isinstance(return_pct, bool)
        or not isinstance(return_pct, (int, float))
        or not math.isfinite(return_pct)
    ):
        errors.append("return_pct must be a finite number or null")

    for key in ("candidate_factors", "evidence_ids", "source_case_ids"):
        value = case.get(key, [])
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            errors.append(f"{key} must be an array of non-empty strings")
        elif len(value) != len(set(value)):
            errors.append(f"{key} must not contain duplicates")

    for key in ("reviewer", "reviewed_at"):
        if key in case and case[key] is not None and not isinstance(case[key], str):
            errors.append(f"{key} must be a string or null")
    if case.get("review_status") == "REVIEWED":
        if not case.get("reviewer") or not case.get("reviewed_at"):
            errors.append("reviewed cases require reviewer and reviewed_at")
        elif not _is_utc_timestamp(case["reviewed_at"]):
            errors.append("reviewed_at must be an ISO 8601 UTC timestamp ending in Z")
    return errors


def is_learning_eligible(case: dict[str, Any]) -> bool:
    """Only reviewed, at-least-partially-verified, resolved cases enter summaries."""
    return (
        not validate_case(case)
        and case["review_status"] == "REVIEWED"
        and case["verification_status"] in {"VERIFIED", "PARTIALLY_VERIFIED"}
        and case["outcome_label"] in ELIGIBLE_OUTCOMES
    )


def _empty_store() -> dict[str, Any]:
    return {
        "store_schema_version": CASE_SCHEMA_VERSION,
        "learning_module_version": LEARNING_MODULE_VERSION,
        "cases": [],
    }


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    """Load and validate a case store; missing stores are treated as empty."""
    store_path = Path(path)
    if not store_path.exists():
        return []
    with store_path.open(encoding="utf-8") as handle:
        store = json.load(handle)
    if not isinstance(store, dict) or store.get("store_schema_version") != CASE_SCHEMA_VERSION:
        raise CaseValidationError(f"case store schema version must be {CASE_SCHEMA_VERSION}")
    cases = store.get("cases")
    if not isinstance(cases, list):
        raise CaseValidationError("case store must contain a cases array")
    seen = set()
    for index, case in enumerate(cases):
        errors = validate_case(case)
        if errors:
            raise CaseValidationError(f"cases[{index}]: " + "; ".join(errors))
        if case["case_id"] in seen:
            raise CaseValidationError(f"duplicate case_id in store: {case['case_id']}")
        seen.add(case["case_id"])
    return cases


def save_case(path: str | Path, case: dict[str, Any]) -> dict[str, Any]:
    """Validate and append one case using atomic replacement; IDs cannot be overwritten."""
    errors = validate_case(case)
    if errors:
        raise CaseValidationError("; ".join(errors))
    store_path = Path(path)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    cases = load_cases(store_path)
    if any(existing["case_id"] == case["case_id"] for existing in cases):
        raise CaseValidationError(f"case_id already exists: {case['case_id']}")
    cases.append(case)
    payload = _empty_store()
    payload["cases"] = cases
    fd, temp_name = tempfile.mkstemp(prefix=f".{store_path.name}.", suffix=".tmp", dir=str(store_path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
        os.replace(temp_name, store_path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
    return case


def find_similar_cases(
    query: dict[str, Any],
    cases: Iterable[dict[str, Any]],
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Return deterministic, explainable matches based on shared factors and metadata.

    Similarity is a retrieval aid, not a probability that the same cause applies.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")
    query_factors = set(query.get("candidate_factors") or [])
    ranked = []
    for case in cases:
        if case.get("case_id") == query.get("case_id"):
            continue
        shared = sorted(query_factors.intersection(case.get("candidate_factors") or []))
        score = 0
        reasons = []
        if query.get("event_type") and query.get("event_type") == case.get("event_type"):
            score += 3
            reasons.append("same_event_type")
        if query.get("movement_direction") and query.get("movement_direction") == case.get("movement_direction"):
            score += 2
            reasons.append("same_movement_direction")
        if shared:
            score += 2 * len(shared)
            reasons.append("shared_factors")
        if score:
            ranked.append({
                "case_id": case.get("case_id"),
                "similarity_score": score,
                "matching_reasons": reasons,
                "shared_factors": shared,
                "outcome_label": case.get("outcome_label", "UNKNOWN"),
                "learning_eligible": is_learning_eligible(case),
            })
    ranked.sort(key=lambda item: (-item["similarity_score"], item["case_id"] or ""))
    return ranked[:limit]


def summarize_outcomes(cases: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Summarize reviewed outcomes by event type, excluding ineligible cases.

    Counts are descriptive associations only. No causal rates or price forecasts are
    computed; sample size is always exposed.
    """
    eligible = [case for case in cases if is_learning_eligible(case)]
    groups: dict[str, Counter] = defaultdict(Counter)
    for case in eligible:
        groups[case["event_type"]][case["outcome_label"]] += 1
    return {
        "learning_module_version": LEARNING_MODULE_VERSION,
        "eligible_case_count": len(eligible),
        "excluded_case_count": sum(1 for case in cases if not is_learning_eligible(case)),
        "interpretation": (
            "Descriptive counts among reviewed cases only; association does not establish "
            "causation or predict future price movements."
        ),
        "by_event_type": {
            event_type: {
                "sample_size": sum(counts.values()),
                "outcome_counts": dict(sorted(counts.items())),
            }
            for event_type, counts in sorted(groups.items())
        },
    }
