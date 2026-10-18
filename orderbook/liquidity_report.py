"""Summarize captured order-book JSONL into a transparent liquidity report."""
import argparse
from collections import defaultdict
from decimal import Decimal
import json
from pathlib import Path
import statistics


def read_jsonl(path):
    records = []
    if not Path(path).exists():
        return records
    with Path(path).open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL record") from exc
            if isinstance(value, dict):
                records.append(value)
    return records


def summarize(symbol, lifecycle_records, metric_records, price_bucket=Decimal("100")):
    """Summarize observed price-level events; never infer cancellation intent."""
    if price_bucket <= 0:
        raise ValueError("price_bucket must be positive")
    events_by_side = defaultdict(lambda: {"added": 0, "quantity_changed": 0, "removed": 0})
    completed_lifetimes = defaultdict(list)
    bucket_stats = defaultdict(lambda: {
        "bid_events": 0, "ask_events": 0, "bid_removed_lifetimes_ms": [],
        "ask_removed_lifetimes_ms": [], "bid_quantity_changed": 0, "ask_quantity_changed": 0,
    })
    valid_events = 0
    for event in lifecycle_records:
        side = event.get("side")
        event_type = event.get("event_type")
        if side not in {"bid", "ask"} or event_type not in {"added", "quantity_changed", "removed"}:
            continue
        try:
            price = Decimal(str(event["price"]))
            lifetime = int(event.get("observed_lifetime_ms", 0))
        except (KeyError, ValueError, TypeError):
            continue
        if price <= 0 or lifetime < 0:
            continue
        valid_events += 1
        events_by_side[side][event_type] += 1
        bucket = (price / price_bucket).to_integral_value(rounding="ROUND_FLOOR") * price_bucket
        row = bucket_stats[bucket]
        row[f"{side}_events"] += 1
        if event_type == "quantity_changed":
            row[f"{side}_quantity_changed"] += 1
        if event_type == "removed":
            completed_lifetimes[side].append(lifetime)
            row[f"{side}_removed_lifetimes_ms"].append(lifetime)

    metric_rows = []
    for record in metric_records:
        metrics = record.get("metrics", {})
        if metrics.get("status") == "OK":
            metric_rows.append({
                "received_at": record.get("received_at"),
                "mid_price": metrics.get("mid_price"),
                "spread_pct_mid": metrics.get("spread_pct_mid"),
                "obi_base_quantity": metrics.get("obi_base_quantity"),
                "bid_depth_quote": metrics.get("bid_depth_quote"),
                "ask_depth_quote": metrics.get("ask_depth_quote"),
            })

    def lifetime_summary(values):
        if not values:
            return {"completed_removals": 0, "median_ms": None, "p90_ms": None, "max_ms": None}
        ordered = sorted(values)
        p90_index = max(0, (9 * len(ordered) + 9) // 10 - 1)
        return {
            "completed_removals": len(ordered),
            "median_ms": int(statistics.median(ordered)),
            "p90_ms": ordered[p90_index],
            "max_ms": ordered[-1],
        }

    buckets = []
    for bucket, row in sorted(bucket_stats.items()):
        bid_life, ask_life = row["bid_removed_lifetimes_ms"], row["ask_removed_lifetimes_ms"]
        buckets.append({
            "price_bucket_start": str(bucket),
            "price_bucket_end_exclusive": str(bucket + price_bucket),
            "bid_events": row["bid_events"],
            "ask_events": row["ask_events"],
            "bid_quantity_changed": row["bid_quantity_changed"],
            "ask_quantity_changed": row["ask_quantity_changed"],
            "bid_completed_lifetimes": lifetime_summary(bid_life),
            "ask_completed_lifetimes": lifetime_summary(ask_life),
        })

    return {
        "schema_version": "1.0",
        "symbol": symbol.upper(),
        "scope": "captured Binance Spot visible price-level events only",
        "price_bucket_size": str(price_bucket),
        "lifecycle_event_count_valid": valid_events,
        "lifecycle_events_by_side": dict(events_by_side),
        "completed_visible_lifetime_ms": {
            "bid": lifetime_summary(completed_lifetimes["bid"]),
            "ask": lifetime_summary(completed_lifetimes["ask"]),
        },
        "valid_book_metric_samples": len(metric_rows),
        "latest_book_metrics": metric_rows[-1] if metric_rows else None,
        "price_buckets": buckets,
        "limitations": [
            "A removed visible level is not proof of cancellation, execution, spoofing, or intent.",
            "Lifetime measures continuous observed price-level presence, not individual-order age.",
            "Only captured records are summarized; reconnects, process restarts, and capture gaps limit interpretation.",
            "Descriptive summaries are not investment advice or a validated predictive signal.",
        ],
    }


def render_markdown(report):
    lines = [
        f"# Order-book liquidity report: {report['symbol']}",
        "",
        f"- Scope: {report['scope']}",
        f"- Price bucket size: {report['price_bucket_size']}",
        f"- Valid lifecycle events: {report['lifecycle_event_count_valid']}",
        f"- Valid book metric samples: {report['valid_book_metric_samples']}",
        "",
        "## Completed visible-level lifetimes",
        "",
        "| Side | Completed removals | Median (ms) | P90 (ms) | Maximum (ms) |",
        "|---|---:|---:|---:|---:|",
    ]
    for side in ("bid", "ask"):
        value = report["completed_visible_lifetime_ms"][side]
        lines.append(f"| {side} | {value['completed_removals']} | {value['median_ms'] if value['median_ms'] is not None else 'n/a'} | {value['p90_ms'] if value['p90_ms'] is not None else 'n/a'} | {value['max_ms'] if value['max_ms'] is not None else 'n/a'} |")
    latest = report["latest_book_metrics"]
    lines.extend(["", "## Latest valid book metrics", ""])
    if latest:
        lines.extend([
            f"- Timestamp: {latest.get('received_at') or 'unknown'}",
            f"- Mid price: {latest.get('mid_price') or 'n/a'}",
            f"- Spread (% mid): {latest.get('spread_pct_mid') or 'n/a'}",
            f"- OBI (base quantity): {latest.get('obi_base_quantity') or 'n/a'}",
            f"- Bid depth quote: {latest.get('bid_depth_quote') or 'n/a'}",
            f"- Ask depth quote: {latest.get('ask_depth_quote') or 'n/a'}",
        ])
    else:
        lines.append("No valid book-metric samples were found.")
    lines.extend([
        "",
        "## Price buckets",
        "",
        "| Price range | Bid events | Ask events | Bid median lifetime (ms) | Ask median lifetime (ms) |",
        "|---|---:|---:|---:|---:|",
    ])
    for row in report["price_buckets"]:
        bid = row["bid_completed_lifetimes_ms"]["median_ms"]
        ask = row["ask_completed_lifetimes_ms"]["median_ms"]
        lines.append(f"| [{row['price_bucket_start']}, {row['price_bucket_end_exclusive']}) | {row['bid_events']} | {row['ask_events']} | {bid if bid is not None else 'n/a'} | {ask if ask is not None else 'n/a'} |")
    lines.extend(["", "## Interpretation limits", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--input-dir", default="artifacts/orderbook")
    parser.add_argument("--output-dir", default="artifacts/orderbook")
    parser.add_argument("--price-bucket", type=Decimal, default=Decimal("100"))
    args = parser.parse_args()
    root, output = Path(args.input_dir), Path(args.output_dir)
    symbol = args.symbol.strip().lower()
    report = summarize(
        args.symbol,
        read_jsonl(root / f"{symbol}-level-lifecycle.jsonl"),
        read_jsonl(root / f"{symbol}-book-metrics.jsonl"),
        args.price_bucket,
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{symbol}-liquidity-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / f"{symbol}-liquidity-report.md").write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {symbol}-liquidity-report.json and {symbol}-liquidity-report.md to {output}")


if __name__ == "__main__":
    main()
