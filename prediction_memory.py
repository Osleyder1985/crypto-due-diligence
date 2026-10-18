"""Persistent, versioned forward-return examples for time-safe direction learning."""
from __future__ import annotations

import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MEMORY_SCHEMA_VERSION = "1.0.0"


class PredictionMemoryError(ValueError):
    """Raised when persisted prediction memory is malformed."""


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").utcoffset().total_seconds() == 0
    except (ValueError, AttributeError):
        return False


def _validate_example(row: Any) -> list[str]:
    if not isinstance(row, dict):
        return ["example must be an object"]
    required = {"example_id","asset_symbol","interval","lookback_candles","horizon_candles",
                "anchor_timestamp","target_timestamp","features","forward_return_pct",
                "outcome_direction","source_provider","created_at"}
    errors = []
    missing = sorted(required - set(row))
    extra = sorted(set(row) - required)
    if missing: errors.append(f"missing fields: {missing}")
    if extra: errors.append(f"unexpected fields: {extra}")
    for key in ("example_id","asset_symbol","interval","outcome_direction","source_provider"):
        if not isinstance(row.get(key), str) or not row[key].strip():
            errors.append(f"{key} must be a non-empty string")
    for key in ("anchor_timestamp","target_timestamp","created_at"):
        if not _valid_timestamp(row.get(key)):
            errors.append(f"{key} must be an ISO 8601 UTC timestamp ending in Z")
    for key in ("lookback_candles","horizon_candles"):
        value = row.get(key)
        if isinstance(value,bool) or not isinstance(value,int) or value <= 0:
            errors.append(f"{key} must be a positive integer")
    features = row.get("features")
    if not isinstance(features,list) or len(features) != 4 or any(
        isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in (features if isinstance(features,list) else [])
    ):
        errors.append("features must be an array of four finite numbers")
    value = row.get("forward_return_pct")
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        errors.append("forward_return_pct must be a finite number")
    if row.get("outcome_direction") not in {"UP","DOWN","FLAT"}:
        errors.append("outcome_direction must be UP, DOWN or FLAT")
    if _valid_timestamp(row.get("anchor_timestamp")) and _valid_timestamp(row.get("target_timestamp")):
        if row["target_timestamp"] <= row["anchor_timestamp"]:
            errors.append("target_timestamp must be after anchor_timestamp")
    return errors


def load_examples(path: str | Path = "data/prediction_memory.json") -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PredictionMemoryError(f"cannot read prediction memory: {exc}") from exc
    if not isinstance(payload,dict) or payload.get("store_schema_version") != MEMORY_SCHEMA_VERSION or not isinstance(payload.get("examples"),list):
        raise PredictionMemoryError("prediction memory must contain store_schema_version 1.0.0 and an examples array")
    seen = set()
    for index,row in enumerate(payload["examples"]):
        errors = _validate_example(row)
        if errors:
            raise PredictionMemoryError(f"examples[{index}]: " + "; ".join(errors))
        if row["example_id"] in seen:
            raise PredictionMemoryError(f"duplicate example_id: {row['example_id']}")
        seen.add(row["example_id"])
    return payload["examples"]


def build_examples(candles: list[dict[str, Any]], asset_symbol: str, interval: str,
                   source_provider: str = "unknown", *, lookback: int = 24,
                   horizon: int = 6) -> list[dict[str, Any]]:
    """Create only examples whose forward return is observable within supplied candles."""
    if lookback < 6 or horizon < 1:
        raise PredictionMemoryError("lookback must be >=6 and horizon >=1")
    ordered = sorted(candles,key=lambda row:row["timestamp"])
    if len({row["timestamp"] for row in ordered}) != len(ordered):
        raise PredictionMemoryError("duplicate candle timestamps")
    if len(ordered) <= lookback + horizon:
        return []
    from prediction_evaluation import _direction, _features
    created = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
    rows=[]
    for i in range(lookback,len(ordered)-horizon):
        features=_features(ordered,i,lookback)
        if features is None: continue
        start=float(ordered[i]["close"]); finish=float(ordered[i+horizon]["close"])
        if not math.isfinite(start) or not math.isfinite(finish) or start<=0 or finish<=0:
            continue
        forward_return=(finish/start-1.0)*100.0
        anchor=ordered[i]["timestamp"]; target=ordered[i+horizon]["timestamp"]
        example_id="|".join([asset_symbol.upper(),interval,str(lookback),str(horizon),anchor])
        row={"example_id":example_id,"asset_symbol":asset_symbol.upper(),"interval":interval,
          "lookback_candles":lookback,"horizon_candles":horizon,"anchor_timestamp":anchor,
          "target_timestamp":target,"features":features,"forward_return_pct":forward_return,
          "outcome_direction":_direction(forward_return),"source_provider":source_provider,"created_at":created}
        errors=_validate_example(row)
        if errors: raise PredictionMemoryError("; ".join(errors))
        rows.append(row)
    return rows


def eligible_examples(examples: list[dict[str, Any]], asset_symbol: str, interval: str,
                      lookback: int, horizon: int, *, as_of: str,
                      before_timestamp: str) -> list[dict[str, Any]]:
    """Select matching-asset examples from before the evaluation window with matured labels."""
    return [row for row in examples
      if row["asset_symbol"] == asset_symbol.upper()
      and row["interval"] == interval
      and row["lookback_candles"] == lookback
      and row["horizon_candles"] == horizon
      and row["anchor_timestamp"] < before_timestamp
      and row["target_timestamp"] <= as_of]


def append_examples(path: str | Path, new_examples: list[dict[str, Any]]) -> dict[str, int]:
    """Append idempotently using atomic replacement; existing IDs are never overwritten."""
    path=Path(path)
    existing=load_examples(path)
    seen={row["example_id"] for row in existing}
    added=[]
    for row in new_examples:
        errors=_validate_example(row)
        if errors: raise PredictionMemoryError("; ".join(errors))
        if row["example_id"] not in seen:
            seen.add(row["example_id"]); added.append(row)
    if not added:
        return {"existing_count":len(existing),"added_count":0,"total_count":len(existing)}
    combined=existing+added
    path.parent.mkdir(parents=True,exist_ok=True)
    payload={"store_schema_version":MEMORY_SCHEMA_VERSION,"examples":combined}
    fd,temp_name=tempfile.mkstemp(prefix=path.name+".",suffix=".tmp",dir=str(path.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as handle:
            json.dump(payload,handle,indent=2,sort_keys=True,ensure_ascii=False)
            handle.write("\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temp_name,path)
    except Exception:
        try: os.unlink(temp_name)
        except OSError: pass
        raise
    return {"existing_count":len(existing),"added_count":len(added),"total_count":len(combined)}
