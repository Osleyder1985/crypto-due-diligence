"""Deterministic movement detection over caller-supplied OHLCV rows."""
from dataclasses import asdict, dataclass
from statistics import median
from typing import Iterable

METHODOLOGY_VERSION = "1.0.0"


@dataclass(frozen=True)
class DetectionConfig:
    methodology_version: str = METHODOLOGY_VERSION
    return_threshold_pct: float = 5.0
    relative_volume_threshold: float = 2.0
    baseline_windows: int = 5
    require_closed_candles: bool = True

    def validate(self):
        if self.return_threshold_pct <= 0:
            raise ValueError("return_threshold_pct must be positive")
        if self.relative_volume_threshold <= 0:
            raise ValueError("relative_volume_threshold must be positive")
        if self.baseline_windows < 2:
            raise ValueError("baseline_windows must be at least 2")
        if not self.methodology_version:
            raise ValueError("methodology_version is required")


def _validate_rows(rows):
    errors = []
    previous_timestamp = None
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"rows[{index}] must be an object")
            continue
        timestamp = row.get("timestamp")
        if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
            errors.append(f"rows[{index}].timestamp must be UTC ISO-8601 ending in Z")
        elif previous_timestamp is not None and timestamp <= previous_timestamp:
            errors.append(f"rows[{index}].timestamp is duplicated or not strictly increasing")
        if isinstance(timestamp, str):
            previous_timestamp = timestamp
        values = {}
        for field in ("open", "high", "low", "close", "volume"):
            value = row.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                errors.append(f"rows[{index}].{field} must be numeric")
            elif field == "volume" and value < 0:
                errors.append(f"rows[{index}].volume must be non-negative")
            elif field != "volume" and value <= 0:
                errors.append(f"rows[{index}].{field} must be positive")
            else:
                values[field] = float(value)
        if len(values) == 5 and (values["high"] < max(values["open"], values["close"], values["low"]) or values["low"] > min(values["open"], values["close"])):
            errors.append(f"rows[{index}] has inconsistent OHLC bounds")
    return errors


def detect_movements(rows: Iterable[dict], config=None, benchmark_rows=None):
    """Return reproducible alerts and diagnostics; no causal attribution is inferred.

    rows must be ordered closed candles with timestamp/open/high/low/close/volume.
    Relative volume compares current volume with the median of preceding candles.
    A signal fires when absolute one-candle return OR relative volume crosses its
    configured threshold. This deliberately simple baseline is versioned and
    should be calibrated before production use.
    """
    config = config or DetectionConfig()
    config.validate()
    rows = list(rows)
    errors = _validate_rows(rows)
    if errors:
        return {"status": "INVALID_DATA", "methodology_version": config.methodology_version,
                "config": asdict(config), "alerts": [], "errors": errors}
    if len(rows) < config.baseline_windows + 2:
        return {"status": "INSUFFICIENT_COVERAGE", "methodology_version": config.methodology_version,
                "config": asdict(config), "alerts": [],
                "errors": [f"need at least {config.baseline_windows + 2} valid candles"]}

    benchmark_by_timestamp = {}
    if benchmark_rows is not None:
        benchmark_rows = list(benchmark_rows)
        benchmark_errors = _validate_rows(benchmark_rows)
        if benchmark_errors:
            return {"status": "INVALID_DATA", "methodology_version": config.methodology_version,
                    "config": asdict(config), "alerts": [],
                    "errors": [f"benchmark: {error}" for error in benchmark_errors]}
        benchmark_by_timestamp = {row["timestamp"]: row["close"] for row in benchmark_rows}

    alerts = []
    for index in range(config.baseline_windows + 1, len(rows)):
        current = rows[index]
        previous = rows[index - 1]
        baseline = [row["volume"] for row in rows[index - config.baseline_windows:index]]
        baseline_median = median(baseline)
        if baseline_median <= 0:
            continue
        return_pct = (current["close"] / previous["close"] - 1.0) * 100.0
        relative_volume = current["volume"] / baseline_median
        benchmark_return_pct = None
        relative_return_pct = None
        if benchmark_by_timestamp:
            current_benchmark = benchmark_by_timestamp.get(current["timestamp"])
            previous_benchmark = benchmark_by_timestamp.get(previous["timestamp"])
            if current_benchmark and previous_benchmark:
                benchmark_return_pct = (current_benchmark / previous_benchmark - 1.0) * 100.0
                relative_return_pct = return_pct - benchmark_return_pct
        return_triggered = abs(return_pct) >= config.return_threshold_pct
        volume_triggered = relative_volume >= config.relative_volume_threshold and abs(return_pct) > 0
        if return_triggered or volume_triggered:
            triggers = []
            if return_triggered:
                triggers.append("ABSOLUTE_RETURN")
            if volume_triggered:
                triggers.append("RELATIVE_VOLUME")
            alerts.append({
                "timestamp": current["timestamp"],
                "previous_timestamp": previous["timestamp"],
                "return_pct": round(return_pct, 8),
                "relative_volume": round(relative_volume, 8),
                "benchmark_return_pct": None if benchmark_return_pct is None else round(benchmark_return_pct, 8),
                "relative_return_pct": None if relative_return_pct is None else round(relative_return_pct, 8),
                "triggers": triggers,
                "methodology_version": config.methodology_version,
                "config": asdict(config),
            })
    return {"status": "ALERTS" if alerts else "NO_ALERTS",
            "methodology_version": config.methodology_version,
            "config": asdict(config), "alerts": alerts, "errors": []}
