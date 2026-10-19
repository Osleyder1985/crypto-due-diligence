"""Compare near-contemporaneous Kraken REST depth-500 and WebSocket depth-1000 captures."""
import argparse
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import statistics


def _read_jsonl(path):
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    if not rows:
        raise ValueError(f"no snapshots found in {path}")
    return rows


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _dec(row, *keys):
    for key in keys:
        value = row.get(key)
        if value is not None:
            return Decimal(str(value))
    raise ValueError(f"snapshot missing all expected fields: {keys}")


def summarize(rows, venue, requested_depth):
    times = [_time(row["captured_at"]) for row in rows]
    bid_counts = [int(row.get("bid_level_count", requested_depth)) for row in rows]
    ask_counts = [int(row.get("ask_level_count", requested_depth)) for row in rows]
    bid_outer = [_dec(row, "worst_bid_price") for row in rows]
    ask_outer = [_dec(row, "worst_ask_price") for row in rows]
    mids = [_dec(row, "mid_price") for row in rows]
    checksummed = sum(bool(row.get("book_checksum_validated")) for row in rows)
    return {
        "venue": venue,
        "requested_levels_per_side": requested_depth,
        "snapshot_count": len(rows),
        "first_snapshot_at": min(times).isoformat(),
        "last_snapshot_at": max(times).isoformat(),
        "window_seconds": round((max(times) - min(times)).total_seconds(), 3),
        "bid_level_count_min": min(bid_counts),
        "bid_level_count_median": statistics.median(bid_counts),
        "bid_level_count_max": max(bid_counts),
        "ask_level_count_min": min(ask_counts),
        "ask_level_count_median": statistics.median(ask_counts),
        "ask_level_count_max": max(ask_counts),
        "worst_bid_price_min": str(min(bid_outer)),
        "worst_bid_price_median": str(statistics.median(bid_outer)),
        "worst_bid_price_max": str(max(bid_outer)),
        "worst_ask_price_min": str(min(ask_outer)),
        "worst_ask_price_median": str(statistics.median(ask_outer)),
        "worst_ask_price_max": str(max(ask_outer)),
        "mid_price_min": str(min(mids)),
        "mid_price_median": str(statistics.median(mids)),
        "mid_price_max": str(max(mids)),
        "checksum_validated_snapshots": checksummed,
    }


def compare(rest_path, ws_path, output_dir):
    rest_rows, ws_rows = _read_jsonl(rest_path), _read_jsonl(ws_path)
    rest = summarize(rest_rows, "kraken_spot_rest", 500)
    ws = summarize(ws_rows, "kraken_spot_ws_v2", 1000)
    rest_start, rest_end = _time(rest["first_snapshot_at"]), _time(rest["last_snapshot_at"])
    ws_start, ws_end = _time(ws["first_snapshot_at"]), _time(ws["last_snapshot_at"])
    overlap_start, overlap_end = max(rest_start, ws_start), min(rest_end, ws_end)
    overlap = max(0.0, (overlap_end - overlap_start).total_seconds())
    report = {
        "schema_version": "1.0",
        "comparison_method": "Two live Kraken XBT/USD captures started concurrently. REST samples are requested at depth 500 per side every 15 seconds; WebSocket v2 maintains up to 1000 price levels per side and is sampled every 5 seconds. This is a comparison of observed snapshots, not proof that REST and WebSocket snapshots are identical or that either contains all market liquidity.",
        "pair": "XBT/USD",
        "rest": rest,
        "websocket": ws,
        "temporal_overlap_seconds": round(overlap, 3),
        "temporal_windows_overlap": overlap > 0,
        "ws_vs_rest_median_level_count": {
            "bid_delta": ws["bid_level_count_median"] - rest["bid_level_count_median"],
            "ask_delta": ws["ask_level_count_median"] - rest["ask_level_count_median"],
        },
        "interpretation_limits": [
            "Depth is the number of price levels returned or maintained, not a completeness guarantee for all market liquidity.",
            "The REST endpoint is a one-shot snapshot sampled periodically; WebSocket is a maintained book with incremental updates and checksum validation.",
            "Differences in outer price limits reflect the observed books and market movement as well as depth; they must not be interpreted as a direct quality score.",
            "A positive temporal overlap makes the windows comparable in time, but does not make each individual sample simultaneous.",
        ],
    }
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    (root / "kraken-ws-rest-depth-comparison.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Kraken REST 500 vs WebSocket v2 1000 depth comparison",
        "",
        f"- Pair: {report['pair']}",
        f"- Temporal overlap: {report['temporal_overlap_seconds']} seconds",
        f"- Windows overlap: {'yes' if report['temporal_windows_overlap'] else 'no'}",
        "",
        "| Metric | REST depth 500 | WebSocket v2 depth 1000 |",
        "|---|---:|---:|",
        f"| Samples | {rest['snapshot_count']} | {ws['snapshot_count']} |",
        f"| Capture window (s) | {rest['window_seconds']} | {ws['window_seconds']} |",
        f"| Median BID levels | {rest['bid_level_count_median']} | {ws['bid_level_count_median']} |",
        f"| Median ASK levels | {rest['ask_level_count_median']} | {ws['ask_level_count_median']} |",
        f"| Median worst BID price | {rest['worst_bid_price_median']} | {ws['worst_bid_price_median']} |",
        f"| Median worst ASK price | {rest['worst_ask_price_median']} | {ws['worst_ask_price_median']} |",
        f"| Median mid price | {rest['mid_price_median']} | {ws['mid_price_median']} |",
        f"| Checksum-validated WS samples | n/a | {ws['checksum_validated_snapshots']}/{ws['snapshot_count']} |",
        "",
        "## Interpretation limits",
        "",
    ] + [f"- {item}" for item in report["interpretation_limits"]]
    (root / "kraken-ws-rest-depth-comparison.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    if not report["temporal_windows_overlap"]:
        raise RuntimeError("REST and WebSocket capture windows did not overlap; comparison is not temporally comparable")
    if ws["checksum_validated_snapshots"] != ws["snapshot_count"]:
        raise RuntimeError("some WebSocket samples were not checksum validated")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rest", required=True)
    parser.add_argument("--websocket", required=True)
    parser.add_argument("--output-dir", default="artifacts/orderbook-comparison")
    args = parser.parse_args()
    report = compare(args.rest, args.websocket, args.output_dir)
    print(json.dumps({
        "comparison_json": str(Path(args.output_dir) / "kraken-ws-rest-depth-comparison.json"),
        "temporal_overlap_seconds": report["temporal_overlap_seconds"],
        "rest_samples": report["rest"]["snapshot_count"],
        "websocket_samples": report["websocket"]["snapshot_count"],
        "checksum_validated_ws_samples": report["websocket"]["checksum_validated_snapshots"],
    }, indent=2))


if __name__ == "__main__":
    main()
