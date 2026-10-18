"""Compare persistent direction memory with no-memory and momentum on rolling OOS windows."""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autonomous_research import ResearchError, fetch_candles, utc_date
from prediction_evaluation import EvaluationError, _metrics, walk_forward_evaluate
from prediction_memory import build_examples


def rolling_memory_evaluate(
    candles: list[dict[str, Any]], *, asset_symbol: str, interval: str = "1h",
    lookback: int = 24, horizon: int = 6, min_train: int = 100,
    neighbors: int = 15, fold_size: int = 240, round_trip_fee_bps: float = 20.0,
    source_provider: str = "historical OHLCV",
) -> dict[str, Any]:
    """Paired rolling OOS comparison; each fold's memory ends before its warmup window."""
    if lookback < 6 or horizon < 1 or min_train < 20 or neighbors < 1 or fold_size < 1:
        raise EvaluationError("lookback >=6, horizon >=1, min_train >=20, neighbors >=1 and fold_size >=1 required")
    if not math.isfinite(round_trip_fee_bps) or round_trip_fee_bps < 0:
        raise EvaluationError("round_trip_fee_bps must be finite and non-negative")
    ordered = sorted(candles, key=lambda row: row["timestamp"])
    if len({row["timestamp"] for row in ordered}) != len(ordered):
        raise EvaluationError("duplicate candle timestamps")
    warmup = lookback + min_train + horizon + 1
    first_fold_start = warmup * 2
    if len(ordered) <= first_fold_start:
        raise EvaluationError(
            f"insufficient candles for rolling out-of-sample validation: need more than {first_fold_start}, got {len(ordered)}"
        )

    paired_rows: list[dict[str, Any]] = []
    folds: list[dict[str, Any]] = []
    fold_start = first_fold_start
    while fold_start < len(ordered):
        fold_end = min(len(ordered), fold_start + fold_size)
        segment_start = fold_start - warmup
        segment = ordered[segment_start:fold_end]
        prefix = ordered[:segment_start]
        memory = build_examples(prefix, asset_symbol, interval, source_provider,
                                lookback=lookback, horizon=horizon)
        no_memory = walk_forward_evaluate(
            segment, lookback=lookback, horizon=horizon, min_train=min_train,
            neighbors=neighbors, round_trip_fee_bps=round_trip_fee_bps,
        )
        with_memory = walk_forward_evaluate(
            segment, lookback=lookback, horizon=horizon, min_train=min_train,
            neighbors=neighbors, round_trip_fee_bps=round_trip_fee_bps,
            memory_examples=memory,
        )
        no_map = {row["timestamp"]: row for row in no_memory["predictions"]}
        mem_map = {row["timestamp"]: row for row in with_memory["predictions"]}
        test_timestamps = {row["timestamp"] for row in ordered[fold_start:fold_end]}
        shared = sorted((no_map.keys() & mem_map.keys()) & test_timestamps)
        fold_rows = []
        for timestamp in shared:
            base, mem = no_map[timestamp], mem_map[timestamp]
            if base["actual_direction"] != mem["actual_direction"] or not math.isclose(
                base["forward_return_pct"], mem["forward_return_pct"], rel_tol=1e-10, abs_tol=1e-10
            ):
                raise EvaluationError("paired runs disagree on realized outcome; refusing incomparable evaluation")
            row = {
                "timestamp": timestamp, "target_timestamp": base["target_timestamp"],
                "actual_direction": base["actual_direction"],
                "forward_return_pct": base["forward_return_pct"],
                "round_trip_fee_pct": base["round_trip_fee_pct"],
                "memory_off_prediction": base["knn_prediction"],
                "memory_on_prediction": mem["knn_prediction"],
                "momentum_prediction": base["momentum_prediction"],
                "memory_examples_available": sum(
                    1 for item in memory
                    if item["anchor_timestamp"] < timestamp and item["target_timestamp"] <= timestamp
                ),
            }
            if base["training_max_label_timestamp"] > timestamp or mem["training_max_label_timestamp"] > timestamp:
                raise EvaluationError("temporal leakage guard: training outcome matured after prediction")
            paired_rows.append(row)
            fold_rows.append(row)
        folds.append({
            "fold": len(folds) + 1,
            "test_start": ordered[fold_start]["timestamp"],
            "test_end": ordered[fold_end - 1]["timestamp"],
            "prior_memory_examples": len(memory),
            "paired_prediction_count": len(fold_rows),
        })
        fold_start = fold_end

    if not paired_rows:
        raise EvaluationError("no paired out-of-sample predictions; provide a longer date range")
    metrics = {
        "memory_disabled_knn": _metrics(paired_rows, "memory_off_prediction"),
        "memory_enabled_knn": _metrics(paired_rows, "memory_on_prediction"),
        "momentum_baseline": _metrics(paired_rows, "momentum_prediction"),
    }
    off, on = metrics["memory_disabled_knn"], metrics["memory_enabled_knn"]
    deltas = {
        "directional_accuracy": (
            on["directional_accuracy"] - off["directional_accuracy"]
            if on["directional_accuracy"] is not None and off["directional_accuracy"] is not None else None
        ),
        "balanced_accuracy": (
            on["balanced_accuracy"] - off["balanced_accuracy"]
            if on["balanced_accuracy"] is not None and off["balanced_accuracy"] is not None else None
        ),
        "net_compounded_return_pct": (
            on["net_compounded_return_pct"] - off["net_compounded_return_pct"]
            if on["net_compounded_return_pct"] is not None and off["net_compounded_return_pct"] is not None else None
        ),
    }
    return {
        "evaluation_version": "1.0.0",
        "asset_symbol": asset_symbol.upper(),
        "interval": interval,
        "methodology": "paired rolling walk-forward; memory contains only realized examples from before each fold warmup",
        "configuration": {
            "lookback_candles": lookback, "forward_horizon_candles": horizon,
            "minimum_training_samples": min_train, "neighbors": neighbors,
            "fold_size_candles": fold_size, "warmup_candles": warmup,
            "round_trip_fee_bps": round_trip_fee_bps,
            "first_test_index": first_fold_start,
        },
        "folds": folds,
        "paired_prediction_count": len(paired_rows),
        "metrics": metrics,
        "memory_minus_no_memory": deltas,
        "paired_predictions": paired_rows,
        "limitations": [
            "Historical simulation does not establish future profitability or statistical significance.",
            "Memory examples are generated only from candles before the fold warmup; labels must be mature at prediction time.",
            "Only timestamps shared by both models are scored, making the comparison paired but excluding earlier memory-only predictions.",
            "Round-trip fee is simplified; spread, slippage, market impact, liquidity, taxes and latency are omitted.",
            "Repeated overlapping folds and one asset can overstate robustness; repeat across assets, regimes and untouched periods.",
            "This test compares pattern memory, not causal explanations or calibrated probabilities.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbol")
    parser.add_argument("start_date")
    parser.add_argument("end_date")
    parser.add_argument("--interval", choices=["1m", "5m", "15m", "30m", "1h", "4h", "1d"], default="1h")
    parser.add_argument("--lookback", type=int, default=24)
    parser.add_argument("--horizon", type=int, default=6)
    parser.add_argument("--min-train", type=int, default=100)
    parser.add_argument("--neighbors", type=int, default=15)
    parser.add_argument("--fold-size", type=int, default=240)
    parser.add_argument("--round-trip-fee-bps", type=float, default=20.0)
    parser.add_argument("--output-dir", default="rolling_validations")
    args = parser.parse_args(argv)
    try:
        start, end = utc_date(args.start_date), utc_date(args.end_date, end_exclusive=True)
        market = fetch_candles(args.symbol, start, end, args.interval)
        report = rolling_memory_evaluate(
            market["candles"], asset_symbol=args.symbol, interval=args.interval,
            lookback=args.lookback, horizon=args.horizon, min_train=args.min_train,
            neighbors=args.neighbors, fold_size=args.fold_size,
            round_trip_fee_bps=args.round_trip_fee_bps,
            source_provider=market.get("provider", "Binance public spot API"),
        )
    except (ResearchError, EvaluationError, ValueError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1
    report["market_data"] = {key: value for key, value in market.items() if key != "candles"}
    report["period"] = {"start": args.start_date, "end_inclusive": args.end_date}
    report["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{args.symbol.upper()}_{args.start_date}_{args.end_date}_rolling-memory.json"
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "ok": True, "report": str(output_path), "folds": len(report["folds"]),
        "paired_prediction_count": report["paired_prediction_count"],
        "metrics": report["metrics"], "memory_minus_no_memory": report["memory_minus_no_memory"],
        "warning": "Historical validation only; no guarantee of future performance.",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
