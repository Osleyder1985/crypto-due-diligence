"""Semantic validation for cross-record references and temporal invariants."""

from datetime import datetime


ID_FIELDS = {
    "Event": "event_id",
    "Source": "source_id",
    "Evidence": "evidence_id",
    "MarketObservation": "observation_id",
}


def _parse_utc(value, location, errors):
    """Parse an ISO-8601 UTC timestamp ending in Z; return None on failure."""
    if not isinstance(value, str) or not value.endswith("Z"):
        errors.append(f"{location}: timestamp must be a UTC ISO-8601 string ending in Z")
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        errors.append(f"{location}: invalid ISO-8601 timestamp")
        return None
    return parsed


def validate_record_collection(envelopes):
    """Return deterministic semantic validation errors for schema-valid envelopes.

    Each item must use the envelope shape:
    {schema_version, record_type, record}. JSON Schema validation remains a
    separate prerequisite and is intentionally not duplicated here.
    """
    errors = []
    records_by_type = {record_type: {} for record_type in ID_FIELDS}
    all_ids = {}

    for index, envelope in enumerate(envelopes):
        location = f"records[{index}]"
        if not isinstance(envelope, dict):
            errors.append(f"{location}: envelope must be an object")
            continue
        record_type = envelope.get("record_type")
        record = envelope.get("record")
        if record_type not in ID_FIELDS or not isinstance(record, dict):
            errors.append(f"{location}: unsupported record_type or record is not an object")
            continue
        id_field = ID_FIELDS[record_type]
        record_id = record.get(id_field)
        if not isinstance(record_id, str) or not record_id:
            errors.append(f"{location}.record.{id_field}: non-empty ID required")
            continue
        if record_id in all_ids:
            errors.append(
                f"{location}.record.{id_field}: duplicate ID {record_id!r} "
                f"(first seen at {all_ids[record_id]})"
            )
        else:
            all_ids[record_id] = f"{location}.record.{id_field}"
        records_by_type[record_type][record_id] = record

    source_ids = set(records_by_type["Source"])
    evidence_ids = set(records_by_type["Evidence"])

    for index, envelope in enumerate(envelopes):
        if not isinstance(envelope, dict):
            continue
        record_type = envelope.get("record_type")
        record = envelope.get("record")
        if record_type not in ID_FIELDS or not isinstance(record, dict):
            continue
        location = f"records[{index}].record"

        if record_type == "Event":
            for field, valid_ids in (("source_ids", source_ids), ("evidence_ids", evidence_ids)):
                values = record.get(field, [])
                if not isinstance(values, list):
                    continue
                for value_index, reference in enumerate(values):
                    if reference not in valid_ids:
                        errors.append(
                            f"{location}.{field}[{value_index}]: reference "
                            f"{reference!r} does not identify an existing "
                            f"{'Source' if field == 'source_ids' else 'Evidence'} record"
                        )
        elif record_type == "Evidence":
            reference = record.get("source_id")
            if reference not in source_ids:
                errors.append(
                    f"{location}.source_id: reference {reference!r} does not identify "
                    "an existing Source record"
                )

        windows = []
        if record_type == "MarketObservation":
            windows.append(("window_start", "window_end", record))
        elif record_type == "Event":
            effect = record.get("observed_price_effect")
            if isinstance(effect, dict):
                windows.append(("window_start", "window_end", effect))

        for start_field, end_field, owner in windows:
            start_value = owner.get(start_field)
            end_value = owner.get(end_field)
            # JSON Schema handles required fields and timestamp format. This
            # semantic layer compares bounds when both values are present.
            if start_value is None or end_value is None:
                continue
            start = _parse_utc(start_value, f"{location}.{start_field}", errors)
            end = _parse_utc(end_value, f"{location}.{end_field}", errors)
            if start is not None and end is not None and start >= end:
                errors.append(
                    f"{location}.{start_field} must be earlier than {end_field}"
                )

    return errors
