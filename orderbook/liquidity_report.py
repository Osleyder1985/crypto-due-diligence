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


def summarize_snapshot_liquidity(depth_records, price_bucket=Decimal("100"), top_n=10):
    """Rank visible price concentrations from the latest captured REST snapshot."""
    if price_bucket <= 0:
        raise ValueError("price_bucket must be positive")
    snapshots = [row for row in depth_records if row.get("record_type") in {"snapshot", "reconstructed_book"} and isinstance(row.get("raw_snapshot"), dict)]
    if not snapshots:
        return {"snapshot_at": None, "source_record_type": None, "mid_price": None, "bids": [], "asks": [], "price_buckets": []}
    snapshot = snapshots[-1]
    raw = snapshot["raw_snapshot"]
    bids = [(Decimal(str(p)), Decimal(str(q))) for p, q in raw.get("bids", []) if Decimal(str(p)) > 0 and Decimal(str(q)) > 0]
    asks = [(Decimal(str(p)), Decimal(str(q))) for p, q in raw.get("asks", []) if Decimal(str(p)) > 0 and Decimal(str(q)) > 0]
    if not bids or not asks:
        return {"snapshot_at": snapshot.get("received_at"), "source_record_type": snapshot.get("record_type"), "mid_price": None, "bids": [], "asks": [], "price_buckets": []}
    best_bid, best_ask = max(p for p, _ in bids), min(p for p, _ in asks)
    mid = (best_bid + best_ask) / Decimal(2)
    grouped = {side: defaultdict(lambda: {"base_quantity": Decimal(0), "quote_notional": Decimal(0), "levels": 0}) for side in ("bid", "ask")}
    ranked = {"bid": [], "ask": []}
    for side, levels in (("bid", bids), ("ask", asks)):
        for price, quantity in levels:
            notional = price * quantity
            bucket = (price / price_bucket).to_integral_value(rounding="ROUND_FLOOR") * price_bucket
            grouped[side][bucket]["base_quantity"] += quantity
            grouped[side][bucket]["quote_notional"] += notional
            grouped[side][bucket]["levels"] += 1
            distance = (mid - price) / mid * 100 if side == "bid" else (price - mid) / mid * 100
            ranked[side].append({"price": str(price), "base_quantity": str(quantity), "quote_notional": str(notional), "distance_from_mid_pct": str(distance)})
    buckets = []
    for bucket in sorted(set(grouped["bid"]) | set(grouped["ask"])):
        item = {"price_bucket_start": str(bucket), "price_bucket_end_exclusive": str(bucket + price_bucket)}
        for side in ("bid", "ask"):
            value = grouped[side].get(bucket, {})
            item[f"{side}_base_quantity"] = str(value.get("base_quantity", Decimal(0)))
            item[f"{side}_quote_notional"] = str(value.get("quote_notional", Decimal(0)))
            item[f"{side}_level_count"] = value.get("levels", 0)
        buckets.append(item)
    return {"snapshot_at": snapshot.get("received_at"), "source_record_type": snapshot.get("record_type"), "mid_price": str(mid), "best_bid": str(best_bid), "best_ask": str(best_ask), "snapshot_limit": raw.get("limit"),
            "bids": sorted(ranked["bid"], key=lambda x: Decimal(x["quote_notional"]), reverse=True)[:top_n],
            "asks": sorted(ranked["ask"], key=lambda x: Decimal(x["quote_notional"]), reverse=True)[:top_n],
            "price_buckets": sorted(buckets, key=lambda x: Decimal(x["bid_quote_notional"]) + Decimal(x["ask_quote_notional"]), reverse=True)}
def summarize(symbol, lifecycle_records, metric_records, price_bucket=Decimal("100"), depth_records=None):
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

    snapshot_liquidity = summarize_snapshot_liquidity(depth_records or [], price_bucket)

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
        "snapshot_liquidity_map": snapshot_liquidity,
        "limitations": [
            "A removed visible level is not proof of cancellation, execution, spoofing, or intent.",
            "Lifetime measures continuous observed price-level presence, not individual-order age.",
            "The concentration map uses the latest persisted reconstructed book when available; otherwise it falls back to the initial REST snapshot.",
            "Snapshot depth is limited by the REST request limit; levels outside captured depth are not included.",
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
    snapshot_map = report.get("snapshot_liquidity_map", {})
    lines.extend(["", "## Snapshot price concentrations", "", "Visible levels from the latest persisted book state, ranked by quote notional; falls back to the initial REST snapshot if capture ended before synchronization.", ""])
    if snapshot_map.get("mid_price") is not None:
        lines.extend([f"- Snapshot time: {snapshot_map.get('snapshot_at') or 'unknown'}", f"- Snapshot mid price: {snapshot_map['mid_price']}", "", "| Side | Price | BTC quantity | Quote notional | Distance from mid (%) |", "|---|---:|---:|---:|---:|"])
        for side in ("bids", "asks"):
            for row in snapshot_map.get(side, []):
                lines.append(f"| {side[:-1].upper()} | {row['price']} | {row['base_quantity']} | {row['quote_notional']} | {row['distance_from_mid_pct']} |")
        lines.extend(["", "### Aggregated price buckets", "", "| Price range | Bid notional | Ask notional | Bid levels | Ask levels |", "|---|---:|---:|---:|---:|"])
        for row in snapshot_map.get("price_buckets", []):
            lines.append(f"| [{row['price_bucket_start']}, {row['price_bucket_end_exclusive']}) | {row['bid_quote_notional']} | {row['ask_quote_notional']} | {row['bid_level_count']} | {row['ask_level_count']} |")
    else:
        lines.append("No valid REST snapshot with both bids and asks was available.")
    lines.extend([
        "",
        "## Price buckets",
        "",
        "| Price range | Bid events | Ask events | Bid median lifetime (ms) | Ask median lifetime (ms) |",
        "|---|---:|---:|---:|---:|",
    ])
    for row in report["price_buckets"]:
        bid = row["bid_completed_lifetimes"]["median_ms"]
        ask = row["ask_completed_lifetimes"]["median_ms"]
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
        read_jsonl(root / f"{symbol}-depth-events.jsonl"),
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{symbol}-liquidity-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / f"{symbol}-liquidity-report.md").write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {symbol}-liquidity-report.json and {symbol}-liquidity-report.md to {output}")


if __name__ == "__main__":
    main()
