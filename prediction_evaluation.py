"""Leakage-aware walk-forward evaluation for an illustrative crypto direction model.

This is an evaluation harness, not a promise of profitability or a trading bot.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autonomous_research import ResearchError, fetch_candles, utc_date

VERSION = "1.0.0"


class EvaluationError(ValueError):
    """Raised when data or evaluation parameters are not adequate."""


def _direction(value: float, deadband: float = 0.0) -> str:
    if value > deadband:
        return "UP"
    if value < -deadband:
        return "DOWN"
    return "FLAT"


def _features(candles: list[dict[str, Any]], index: int, lookback: int) -> list[float] | None:
    """Features at index use only candles with indices <= index."""
    if index < lookback:
        return None
    closes = [float(candles[i]["close"]) for i in range(index - lookback, index + 1)]
    if any(not math.isfinite(x) or x <= 0 for x in closes):
        return None
    returns = []
    for lag in (1, min(6, lookback), lookback):
        returns.append((closes[-1] / closes[-1-lag] - 1.0) * 100.0)
    vols = [float(candles[i]["volume"]) for i in range(index - lookback, index)]
    current_vol = float(candles[index]["volume"])
    mean_vol = sum(vols) / len(vols) if vols else 0.0
    vol_feature = current_vol / mean_vol - 1.0 if mean_vol > 0 else 0.0
    return returns + [vol_feature]


def _standardize(rows: list[list[float]], query: list[float]) -> tuple[list[list[float]], list[float]]:
    dims = len(query)
    means = [sum(row[d] for row in rows) / len(rows) for d in range(dims)]
    scales = []
    for d in range(dims):
        variance = sum((row[d] - means[d]) ** 2 for row in rows) / len(rows)
        scales.append(math.sqrt(variance) or 1.0)
    return [[(v - means[d]) / scales[d] for d, v in enumerate(row)] for row in rows], [
        (v - means[d]) / scales[d] for d, v in enumerate(query)
    ]


def _metrics(predictions: list[dict[str, Any]], key: str) -> dict[str, Any]:
    usable = [row for row in predictions if row[key] in ("UP", "DOWN")]
    if not usable:
        return {"sample_size": 0, "directional_accuracy": None, "balanced_accuracy": None,
                "mean_return_pct": None, "net_compounded_return_pct": None}
    correct = sum(row[key] == row["actual_direction"] for row in usable)
    class_scores = []
    for label in ("UP", "DOWN"):
        actual = [row for row in usable if row["actual_direction"] == label]
        if actual:
            class_scores.append(sum(row[key] == label for row in actual) / len(actual))
    gross_factor = 1.0
    for row in usable:
        sign = 1 if row[key] == "UP" else -1
        net_pct = sign * row["forward_return_pct"] - row["round_trip_fee_pct"]
        gross_factor *= max(0.0, 1.0 + net_pct / 100.0)
    return {"sample_size": len(usable), "directional_accuracy": correct / len(usable),
            "balanced_accuracy": sum(class_scores) / len(class_scores) if class_scores else None,
            "mean_return_pct": sum(row["forward_return_pct"] for row in usable) / len(usable),
            "net_compounded_return_pct": (gross_factor - 1.0) * 100.0,
            "up_samples": sum(row["actual_direction"] == "UP" for row in usable),
            "down_samples": sum(row["actual_direction"] == "DOWN" for row in usable)}


def walk_forward_evaluate(candles: list[dict[str, Any]], *, lookback: int = 24,
                          horizon: int = 6, min_train: int = 100, neighbors: int = 15,
                          round_trip_fee_bps: float = 20.0,
                          memory_examples: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Walk-forward evaluation with only time-mature in-window and prior-memory labels."""
    if lookback < 6 or horizon < 1 or min_train < 20 or neighbors < 1:
        raise EvaluationError("lookback must be >=6, horizon >=1, min_train >=20, neighbors >=1")
    if not math.isfinite(round_trip_fee_bps) or round_trip_fee_bps < 0:
        raise EvaluationError("round_trip_fee_bps must be a finite non-negative number")
    ordered = sorted(candles, key=lambda c: c["timestamp"])
    if len({c["timestamp"] for c in ordered}) != len(ordered):
        raise EvaluationError("duplicate candle timestamps; clean data before evaluation")
    if len(ordered) < lookback + horizon + 2:
        raise EvaluationError(f"insufficient candles for walk-forward targets: need at least {lookback+horizon+2}, got {len(ordered)}")
    memory_examples = memory_examples or []
    if not memory_examples and len(ordered) < lookback + horizon + min_train + 1:
        raise EvaluationError(f"insufficient candles: need at least {lookback+horizon+min_train+1}, got {len(ordered)}")
    closes = [float(c["close"]) for c in ordered]
    if any(not math.isfinite(x) or x <= 0 for x in closes):
        raise EvaluationError("all close prices must be finite and positive")
    fee_pct = round_trip_fee_bps / 100.0
    features = {i: _features(ordered, i, lookback) for i in range(lookback, len(ordered))}
    predictions = []
    start_index = lookback + horizon if memory_examples else lookback + min_train + horizon
    for i in range(start_index, len(ordered) - horizon):
        query = features.get(i)
        if query is None: continue
        train_rows = []
        for j in range(lookback, i - horizon + 1):
            feature = features.get(j)
            if feature is None: continue
            target_return = (closes[j+horizon] / closes[j] - 1.0) * 100.0
            train_rows.append({"features":feature,"anchor":ordered[j]["timestamp"],
              "target":ordered[j+horizon]["timestamp"],"direction":_direction(target_return),"return":target_return})
        for row in memory_examples:
            if row.get("anchor_timestamp", "") < ordered[0]["timestamp"] and row.get("target_timestamp", "") <= ordered[i]["timestamp"]:
                train_rows.append({"features":row["features"],"anchor":row["anchor_timestamp"],
                  "target":row["target_timestamp"],"direction":row["outcome_direction"],"return":row["forward_return_pct"]})
        if len(train_rows) < min_train: continue
        standardized, standardized_query = _standardize([row["features"] for row in train_rows], query)
        distances = []
        for row_index, row in enumerate(train_rows):
            distance = math.sqrt(sum((a-b)**2 for a,b in zip(standardized[row_index], standardized_query)))
            distances.append((distance,row["anchor"],row["direction"],row["return"],row["target"]))
        nearest = sorted(distances, key=lambda row:(row[0],row[1]))[:min(neighbors,len(distances))]
        ups=sum(row[2]=="UP" for row in nearest); downs=sum(row[2]=="DOWN" for row in nearest)
        knn_prediction="UP" if ups>downs else "DOWN" if downs>ups else "FLAT"
        momentum_prediction=_direction(query[2])
        forward_return=(closes[i+horizon]/closes[i]-1.0)*100.0
        predictions.append({"timestamp":ordered[i]["timestamp"],"target_timestamp":ordered[i+horizon]["timestamp"],
          "actual_direction":_direction(forward_return),"forward_return_pct":forward_return,
          "knn_prediction":knn_prediction,"momentum_prediction":momentum_prediction,
          "neighbor_count":len(nearest),"up_vote_fraction":ups/len(nearest),"round_trip_fee_pct":fee_pct,
          "training_max_anchor":max(row["anchor"] for row in train_rows),
          "training_max_label_timestamp":max(row["target"] for row in train_rows)})
    if not predictions:
        raise EvaluationError("no out-of-sample predictions produced; supply more candles or prior matured memory examples")
    for row in predictions:
        if row["training_max_label_timestamp"] > row["timestamp"]:
            raise EvaluationError("internal leakage guard: a training label extends beyond prediction time")
    return {"evaluation_version":VERSION,"methodology":"walk-forward k-nearest neighbors versus fixed lookback momentum",
      "configuration":{"lookback_candles":lookback,"forward_horizon_candles":horizon,"minimum_training_samples":min_train,
        "neighbors":neighbors,"round_trip_fee_bps":round_trip_fee_bps,"feature_names":["return_1","return_6_or_lookback","return_lookback","relative_volume"],
        "prior_memory_example_count":len(memory_examples)},
      "metrics":{"knn":_metrics(predictions,"knn_prediction"),"momentum_baseline":_metrics(predictions,"momentum_prediction")},
      "prediction_count":len(predictions),"predictions":predictions,
      "limitations":["A walk-forward test is historical simulation, not evidence of future profitability.",
        "Training uses only prior memory labels matured before each prediction timestamp.",
        "No hyperparameter tuning or model selection is performed on a separate validation set.",
        "Fee model omits slippage, spread, funding, latency, taxes, liquidity constraints and market impact.",
        "The nearest-neighbor model is experimental; compare against simple baselines and test multiple unseen periods."]}

def predict_next(candles: list[dict[str, Any]], *, lookback: int = 24,
                 horizon: int = 6, min_train: int = 100, neighbors: int = 15,
                 memory_examples: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Estimate direction using labels mature by the as-of timestamp, including prior runs."""
    if lookback < 6 or horizon < 1 or min_train < 20 or neighbors < 1:
        raise EvaluationError("lookback must be >=6, horizon >=1, min_train >=20, neighbors >=1")
    ordered=sorted(candles,key=lambda c:c["timestamp"])
    if len({c["timestamp"] for c in ordered}) != len(ordered):
        raise EvaluationError("duplicate candle timestamps; clean data before prediction")
    closes=[float(c["close"]) for c in ordered]
    if any(not math.isfinite(x) or x<=0 for x in closes):
        raise EvaluationError("all close prices must be finite and positive")
    anchor=len(ordered)-1
    query=_features(ordered,anchor,lookback)
    if query is None: raise EvaluationError("not enough candles to calculate current features")
    as_of=ordered[anchor]["timestamp"]
    train_rows=[]
    for j in range(lookback,anchor-horizon+1):
        feature=_features(ordered,j,lookback)
        if feature is None: continue
        forward_return=(closes[j+horizon]/closes[j]-1.0)*100.0
        train_rows.append({"features":feature,"anchor":ordered[j]["timestamp"],
          "target":ordered[j+horizon]["timestamp"],"direction":_direction(forward_return),"return":forward_return})
    memory_examples=memory_examples or []
    for row in memory_examples:
        if row.get("anchor_timestamp","") < ordered[0]["timestamp"] and row.get("target_timestamp","") <= as_of:
            train_rows.append({"features":row["features"],"anchor":row["anchor_timestamp"],
              "target":row["target_timestamp"],"direction":row["outcome_direction"],"return":row["forward_return_pct"]})
    if len(train_rows)<min_train:
        raise EvaluationError(f"insufficient matured training samples: need {min_train}, got {len(train_rows)}")
    standardized,standardized_query=_standardize([row["features"] for row in train_rows],query)
    distances=[]
    for row_index,row in enumerate(train_rows):
        distance=math.sqrt(sum((a-b)**2 for a,b in zip(standardized[row_index],standardized_query)))
        distances.append((distance,row["anchor"],row["direction"],row["return"],row["target"]))
    nearest=sorted(distances,key=lambda row:(row[0],row[1]))[:min(neighbors,len(distances))]
    ups=sum(row[2]=="UP" for row in nearest); downs=sum(row[2]=="DOWN" for row in nearest); flats=sum(row[2]=="FLAT" for row in nearest)
    signal="UP" if ups>downs else "DOWN" if downs>ups else "INCONCLUSIVE"
    latest_anchor=max(row["anchor"] for row in train_rows)
    latest_label=max(row["target"] for row in train_rows)
    if latest_label>as_of: raise EvaluationError("internal leakage guard: training label extends beyond as-of time")
    return {"status":"EXPERIMENTAL_SIGNAL","as_of":as_of,"target_horizon_candles":horizon,
      "lookback_candles":lookback,"signal":signal,"neighbor_count":len(nearest),
      "neighbor_votes":{"UP":ups,"DOWN":downs,"FLAT":flats},"neighbor_vote_share":max(ups,downs)/len(nearest),
      "matured_training_sample_count":len(train_rows),"prior_memory_example_count":len(memory_examples),
      "latest_training_anchor":latest_anchor,"latest_training_label_timestamp":latest_label,
      "limitations":["Neighbor vote share is not a calibrated probability or a guarantee.",
        "This experimental signal uses price/volume patterns, not a verified causal explanation.",
        "The current candle must be complete; live/incomplete candles can change features."]}

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbol")
    parser.add_argument("start_date")
    parser.add_argument("end_date")
    parser.add_argument("--interval", choices=["1m","5m","15m","30m","1h","4h","1d"], default="1h")
    parser.add_argument("--lookback", type=int, default=24)
    parser.add_argument("--horizon", type=int, default=6)
    parser.add_argument("--min-train", type=int, default=100)
    parser.add_argument("--neighbors", type=int, default=15)
    parser.add_argument("--round-trip-fee-bps", type=float, default=20.0)
    parser.add_argument("--output-dir", default="prediction_evaluations")
    args = parser.parse_args(argv)
    try:
        start, end = utc_date(args.start_date), utc_date(args.end_date, end_exclusive=True)
        market = fetch_candles(args.symbol, start, end, args.interval)
        report = walk_forward_evaluate(market["candles"], lookback=args.lookback, horizon=args.horizon,
            min_train=args.min_train, neighbors=args.neighbors, round_trip_fee_bps=args.round_trip_fee_bps)
    except (ResearchError, EvaluationError, ValueError, OSError) as exc:
        print(json.dumps({"ok":False,"error":str(exc)}, indent=2), file=sys.stderr)
        return 1
    report["asset_symbol"] = args.symbol.upper()
    report["market_data"] = {k:v for k,v in market.items() if k != "candles"}
    report["period"] = {"start":args.start_date,"end_inclusive":args.end_date}
    report["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{args.symbol.upper()}_{args.start_date}_{args.end_date}_evaluation.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps({"ok":True,"report":str(path),"prediction_count":report["prediction_count"],
      "knn":report["metrics"]["knn"],"momentum_baseline":report["metrics"]["momentum_baseline"],
      "warning":"Historical evaluation is not a guarantee of future results."}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
