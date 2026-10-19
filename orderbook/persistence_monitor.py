"""Repeated public Kraken Spot snapshots and summarize persistent liquidity zones."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import time

from orderbook.kraken_snapshot_collector import build_report, fetch_book


def summarize_snapshots(reports, min_notional_usd=Decimal("250000")):
    """Rank $100 price buckets by how consistently visible liquidity is present."""
    if not reports:
        raise ValueError("at least one report is required")
    threshold = Decimal(str(min_notional_usd))
    if threshold < 0:
        raise ValueError("minimum notional cannot be negative")

    bucket_stats = {}
    level_stats = {}
    for report in reports:
        seen_buckets = set()
        for bucket in report["price_buckets"]:
            start = Decimal(bucket["price_bucket_start"])
            for side in ("bid", "ask"):
                notional = Decimal(bucket[f"{side}_notional_usd"])
                if notional <= 0:
                    continue
                key = (side, str(start))
                stats = bucket_stats.setdefault(key, {
                    "side": side, "bucket_start": str(start),
                    "bucket_end_exclusive": str(Decimal(bucket.get("price_bucket_end_exclusive", str(start + Decimal("100"))))),
                    "observations_present": 0, "observations_above_threshold": 0,
                    "notional_sum_usd": Decimal(0), "notional_max_usd": Decimal(0),
                })
                stats["observations_present"] += 1
                stats["notional_sum_usd"] += notional
                stats["notional_max_usd"] = max(stats["notional_max_usd"], notional)
                if notional >= threshold:
                    stats["observations_above_threshold"] += 1
                    seen_buckets.add(key)

        for level in report["top_concentrated_levels_by_notional"]:
            side = level["side"]
            price = str(Decimal(level["price"]))
            notional = Decimal(level["notional_usd"])
            key = (side, price)
            stats = level_stats.setdefault(key, {
                "side": side, "price": price, "observations_seen_in_top_n": 0,
                "notional_sum_usd": Decimal(0), "notional_max_usd": Decimal(0),
            })
            stats["observations_seen_in_top_n"] += 1
            stats["notional_sum_usd"] += notional
            stats["notional_max_usd"] = max(stats["notional_max_usd"], notional)

    n = len(reports)
    buckets = []
    for stats in bucket_stats.values():
        buckets.append({
            **stats,
            "persistence_pct": round(100 * stats["observations_above_threshold"] / n, 2),
            "average_notional_usd_when_present": str(
                stats["notional_sum_usd"] / stats["observations_present"]
            ),
            "notional_max_usd": str(stats["notional_max_usd"]),
            "notional_sum_usd": str(stats["notional_sum_usd"]),
        })
    buckets.sort(key=lambda x: (
        x["persistence_pct"], Decimal(x["notional_max_usd"])
    ), reverse=True)

    levels = []
    for stats in level_stats.values():
        levels.append({
            **stats,
            "persistence_pct_of_top_n": round(100 * stats["observations_seen_in_top_n"] / n, 2),
            "average_notional_usd_when_seen": str(
                stats["notional_sum_usd"] / stats["observations_seen_in_top_n"]
            ),
            "notional_max_usd": str(stats["notional_max_usd"]),
            "notional_sum_usd": str(stats["notional_sum_usd"]),
        })
    levels.sort(key=lambda x: (
        x["observations_seen_in_top_n"], Decimal(x["notional_max_usd"])
    ), reverse=True)

    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "venue": "kraken_spot",
        "pair": reports[0].get("pair_returned", "unknown"),
        "snapshot_count": n,
        "first_snapshot_at": reports[0]["captured_at"],
        "last_snapshot_at": reports[-1]["captured_at"],
        "min_bucket_notional_usd": str(threshold),
        "method": "A $100 price bucket is above threshold when its aggregated side notional meets the threshold in a snapshot. Persistence is the fraction of all snapshots meeting that condition. Exact price levels are tracked only when present in the report's top-N list.",
        "persistent_buckets": buckets,
        "repeated_top_levels": levels[:50],
        "limitations": [
            "This is persistence across sampled snapshots, not proof that the same orders remained continuously open between samples.",
            "Buckets aggregate all levels in each $100 interval; a persistent bucket does not imply one persistent order.",
            "Exact-price levels may change price or quantity and are only tracked when included in top-N.",
            "One venue only; this is not total-market liquidity and does not identify owners or intent.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", default="XBTUSD")
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--snapshots", type=int, default=20)
    parser.add_argument("--interval-seconds", type=int, default=30)
    parser.add_argument("--price-bucket", type=Decimal, default=Decimal("100"))
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--min-bucket-notional-usd", type=Decimal, default=Decimal("250000"))
    parser.add_argument("--output-dir", default="artifacts/orderbook-persistence")
    args = parser.parse_args()
    if not 2 <= args.snapshots <= 100:
        parser.error("--snapshots must be between 2 and 100")
    if not 5 <= args.interval_seconds <= 300:
        parser.error("--interval-seconds must be between 5 and 300")
    if args.top_n < 1:
        parser.error("--top-n must be positive")
    if args.price_bucket != Decimal("100"):
        parser.error("persistence buckets currently require --price-bucket 100")
    if args.min_bucket_notional_usd < 0:
        parser.error("--min-bucket-notional-usd cannot be negative")

    root = Path(args.output_dir)
    root.mkdir(parents=True, exist_ok=True)
    reports = []
    raw_path = root / "kraken-xbtusd-snapshots.jsonl"
    with raw_path.open("w", encoding="utf-8") as raw_file:
        for i in range(args.snapshots):
            key, book = fetch_book(args.pair, args.count)
            report = build_report(args.pair, key, book, args.price_bucket, args.top_n)
            reports.append(report)
            raw_file.write(json.dumps({
                "captured_at": report["captured_at"],
                "venue": report["venue"],
                "pair_returned": key,
                "best_bid": report["best_bid"],
                "best_ask": report["best_ask"],
                "best_bid_price": report["best_bid"],
                "worst_bid_price": str(min(Decimal(row[0]) for row in book["bids"])),
                "best_ask_price": report["best_ask"],
                "worst_ask_price": str(max(Decimal(row[0]) for row in book["asks"])),
                "mid_price": report["mid_price"],
                "price_buckets": report["price_buckets"],
                "top_concentrated_levels_by_notional": report["top_concentrated_levels_by_notional"],
            }) + "\n")
            raw_file.flush()
            print(json.dumps({
                "sample": i + 1, "total": args.snapshots,
                "captured_at": report["captured_at"], "mid_price": report["mid_price"],
            }), flush=True)
            if i + 1 < args.snapshots:
                time.sleep(args.interval_seconds)

    summary = summarize_snapshots(reports, args.min_bucket_notional_usd)
    (root / "kraken-liquidity-persistence.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Kraken Spot liquidity persistence",
        "",
        f"- Pair: {summary['pair']}",
        f"- Snapshots: {summary['snapshot_count']}",
        f"- Window: {summary['first_snapshot_at']} to {summary['last_snapshot_at']}",
        f"- Threshold: ${summary['min_bucket_notional_usd']} per $100 bucket and side",
        "",
        "## Most persistent $100 price buckets",
        "",
        "| Side | Price range | Snapshots above threshold | Persistence | Max notional |",
        "|---|---:|---:|---:|---:|",
    ]
    for item in summary["persistent_buckets"][:30]:
        lines.append(
            f"| {item['side']} | [{item['bucket_start']}, {item['bucket_end_exclusive']}) | "
            f"{item['observations_above_threshold']}/{summary['snapshot_count']} | "
            f"{item['persistence_pct']:.2f}% | ${Decimal(item['notional_max_usd']):,.0f} |"
        )
    lines.extend(["", "## Repeated exact-price levels in top-N", "",
                  "| Side | Price | Seen in top-N | Persistence | Max notional |",
                  "|---|---:|---:|---:|---:|"])
    for item in summary["repeated_top_levels"][:30]:
        lines.append(
            f"| {item['side']} | {item['price']} | {item['observations_seen_in_top_n']}/{summary['snapshot_count']} | "
            f"{item['persistence_pct_of_top_n']:.2f}% | ${Decimal(item['notional_max_usd']):,.0f} |"
        )
    lines.extend(["", "## Limitations", ""] + [f"- {item}" for item in summary["limitations"]])
    (root / "kraken-liquidity-persistence.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "snapshot_count": summary["snapshot_count"],
        "first_snapshot_at": summary["first_snapshot_at"],
        "last_snapshot_at": summary["last_snapshot_at"],
        "persistent_bucket_count": len(summary["persistent_buckets"]),
        "report": str(root / "kraken-liquidity-persistence.json"),
    }, indent=2))


if __name__ == "__main__":
    main()
