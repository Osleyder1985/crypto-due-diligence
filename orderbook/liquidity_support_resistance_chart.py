"""Plot observed liquidity, internal empty buckets, and unobserved depth separately."""
import argparse
import json
import math
import textwrap
from pathlib import Path


def read_records(path):
    raw = Path(path).read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError("input is empty")
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, list) else [obj]
    except json.JSONDecodeError:
        return [json.loads(line) for line in raw.splitlines() if line.strip()]


def _num(record, *keys):
    for key in keys:
        value = record.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    return None


def _merge(intervals):
    merged = []
    for start, end in sorted((a, b) for a, b in intervals if b > a):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, help="JSON snapshot or JSONL repeated snapshots")
    p.add_argument("--zones", required=True, help="JSON report containing candidate zones")
    p.add_argument("--output", required=True)
    p.add_argument("--range-pct", type=float, default=20.0)
    p.add_argument("--max-zone-labels", type=int, default=8)
    p.add_argument("--bucket-size", type=float, default=100.0)
    a = p.parse_args()
    if not 0 < a.range_pct <= 50:
        p.error("--range-pct must be > 0 and <= 50")
    if a.max_zone_labels < 0 or a.bucket_size <= 0:
        p.error("--max-zone-labels must be >= 0 and --bucket-size must be positive")

    records = read_records(a.input)
    last = records[-1]
    mid = float(last["mid_price"])
    low, high = mid * (1 - a.range_pct / 100), mid * (1 + a.range_pct / 100)
    accum = {}
    for rec in records:
        for b in rec.get("price_buckets", []):
            lo = float(b["price_bucket_start"])
            hi = float(b.get("price_bucket_end_exclusive", lo + a.bucket_size))
            if hi <= low or lo >= high:
                continue
            slot = accum.setdefault(lo, {"bid": [], "ask": []})
            slot["bid"].append(float(b.get("bid_notional_usd", 0)))
            slot["ask"].append(float(b.get("ask_notional_usd", 0)))

    prices = sorted(accum)
    bids = [sum(accum[x]["bid"]) / len(accum[x]["bid"]) for x in prices]
    asks = [sum(accum[x]["ask"]) / len(accum[x]["ask"]) for x in prices]

    # Use the actual per-side outer limits saved from each snapshot. Never infer
    # captured depth from the first/last bucket containing nonzero notional.
    bid_ranges, ask_ranges = [], []
    for rec in records:
        best_bid = _num(rec, "best_bid_price", "best_bid")
        worst_bid = _num(rec, "worst_bid_price")
        best_ask = _num(rec, "best_ask_price", "best_ask")
        worst_ask = _num(rec, "worst_ask_price")
        if best_bid is not None and worst_bid is not None:
            bid_ranges.append((max(low, min(best_bid, worst_bid)), min(high, max(best_bid, worst_bid) + a.bucket_size)))
        if best_ask is not None and worst_ask is not None:
            ask_ranges.append((max(low, min(best_ask, worst_ask)), min(high, max(best_ask, worst_ask) + a.bucket_size)))
    # Coverage envelope uses only the latest live book, while bucket history
    # remains averaged over all snapshots. Old artifacts without bounds are
    # deliberately marked as unknown instead of fabricating a depth range.
    latest_bid_best = _num(last, "best_bid_price", "best_bid")
    latest_bid_worst = _num(last, "worst_bid_price")
    latest_ask_best = _num(last, "best_ask_price", "best_ask")
    latest_ask_worst = _num(last, "worst_ask_price")
    bid_interval = None
    ask_interval = None
    if latest_bid_best is not None and latest_bid_worst is not None:
        bid_interval = (max(low, min(latest_bid_best, latest_bid_worst)),
                        min(high, max(latest_bid_best, latest_bid_worst) + a.bucket_size))
    if latest_ask_best is not None and latest_ask_worst is not None:
        ask_interval = (max(low, min(latest_ask_best, latest_ask_worst)),
                        min(high, max(latest_ask_best, latest_ask_worst) + a.bucket_size))

    def coverage_pct(interval):
        if interval is None:
            return None
        return max(0.0, interval[1] - interval[0]) / (high - low) * 100

    bid_coverage = coverage_pct(bid_interval)
    ask_coverage = coverage_pct(ask_interval)

    zones_report = json.loads(Path(a.zones).read_text(encoding="utf-8"))
    zones = []
    for z in zones_report.get("zones", []):
        zlo, zhi = float(z["price_low"]), float(z["price_high_exclusive"])
        if zhi > low and zlo < high:
            zones.append((z, zlo, zhi))
    zones.sort(key=lambda item: float(item[0].get("max_visible_notional_usd", 0)), reverse=True)
    labeled = zones[:a.max_zone_labels]

    fig, ax = plt.subplots(figsize=(14, 9), constrained_layout=False)
    # Reserve dedicated space for the x-axis label and multi-line coverage note;
    # constrained_layout can otherwise let the long note collide with the label.
    if prices:
        ax.barh([x + a.bucket_size / 2 for x in prices], bids, height=a.bucket_size * .72,
                label="Buy bids (observed)", color="#238b57", alpha=.8)
        ax.barh([x + a.bucket_size / 2 for x in prices], [-v for v in asks], height=a.bucket_size * .72,
                label="Sell asks (observed)", color="#c94c4c", alpha=.8)
    else:
        ax.text(.5, .5, "No observed order-book buckets in requested price window",
                transform=ax.transAxes, ha="center", va="center", fontsize=12)

    # Side-specific background: hatched spans outside the actual captured depth
    # are unknown. Missing $100 buckets inside the captured interval are empty
    # observed buckets, not evidence of liquidity beyond the book limits.
    max_bid = max(bids, default=0.0)
    max_ask = max(asks, default=0.0)
    x_extent = max(max_bid, max_ask, 1.0) * 1.18
    ax.set_xlim(-x_extent, x_extent)
    ax.axvline(0, color="#444444", linewidth=.8)
    y_cursor = low
    while y_cursor < high:
        y_end = min(high, y_cursor + a.bucket_size)
        y_mid = (y_cursor + y_end) / 2
        bucket_lo = math.floor(y_cursor / a.bucket_size) * a.bucket_size
        slot = accum.get(bucket_lo)
        # Determine whether this price bucket is inside the latest depth range.
        for side, interval in (("bid", bid_interval), ("ask", ask_interval)):
            x1, x2 = (0, x_extent) if side == "bid" else (-x_extent, 0)
            if interval is None or y_end <= interval[0] or y_cursor >= interval[1]:
                ax.fill_betweenx([y_cursor, y_end], x1, x2, facecolor="none",
                                 edgecolor="#777777", hatch="////", linewidth=0, alpha=.45)
            elif not slot or not slot[side] or sum(slot[side]) <= 0:
                ax.fill_betweenx([y_cursor, y_end], x1, x2, facecolor="none",
                                 edgecolor="#777777", hatch="..", linewidth=0, alpha=.55)
        y_cursor = y_end

    ax.axhline(mid, color="#222222", linestyle="--", linewidth=1.5,
               label="Latest mid-price: " + format(mid, ",.2f"))
    for z, zlo, zhi in zones:
        color = "#238b57" if z["type"] == "candidate_support" else "#c94c4c"
        ax.axhspan(zlo, zhi, color=color, alpha=.14, zorder=0)
    summary = []
    for z, zlo, zhi in labeled:
        kind = "SUP" if z["type"] == "candidate_support" else "RES"
        summary.append(f"{kind} {zlo:,.0f}-{zhi:,.0f} | {z.get('persistence_pct', 0)}% | "
                       f"${float(z.get('max_visible_notional_usd', 0))/1e6:.2f}M")
    if summary:
        ax.text(.99, .985, "TOP CANDIDATE ZONES\n" + "\n".join(summary),
                transform=ax.transAxes, ha="right", va="top", fontsize=8,
                bbox={"facecolor": "white", "alpha": .9, "edgecolor": "#888888", "pad": 5})

    ax.set_ylim(low, high)
    ax.set_xlabel("Average visible notional per price bucket (USD): asks left ← | → bids right")
    ax.set_ylabel("BTC/USD price")
    ax.set_title(f"BTC/USD observed order-book liquidity and candidate zones (±{a.range_pct:g}%)")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: "$" + format(abs(v) / 1e6, ".1f") + "M"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: "$" + format(v, ",.0f")))
    ax.grid(True, axis="y", alpha=.25)
    ax.legend(loc="lower left")

    def fmt(value):
        return "unknown (bounds absent in input)" if value is None else f"{value:.1f}%"
    coverage_text = (
        f"Requested: ${low:,.0f}–${high:,.0f} | latest-book price-span coverage: "
        f"BID {fmt(bid_coverage)}, ASK {fmt(ask_coverage)}. "
        "//// outside captured depth = unknown/not captured; .. inside captured depth = no observed notional in bucket. "
        "Coverage is based on latest book bounds; liquidity bars are bucket averages across snapshots. "
        "Candidate zones are not confirmed support/resistance."
    )
    fig.subplots_adjust(left=0.08, right=0.98, top=0.93, bottom=0.19)
    fig.text(.01, .015, textwrap.fill(coverage_text, width=190), fontsize=8, ha="left", va="bottom")
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print(json.dumps({
        "chart": str(out), "reference_mid_price": mid, "window_low": low, "window_high": high,
        "latest_best_bid": latest_bid_best, "latest_worst_bid": latest_bid_worst,
        "latest_best_ask": latest_ask_best, "latest_worst_ask": latest_ask_worst,
        "bid_coverage_pct": None if bid_coverage is None else round(bid_coverage, 2),
        "ask_coverage_pct": None if ask_coverage is None else round(ask_coverage, 2),
        "bucket_count": len(prices), "candidate_zones_in_window": len(zones),
        "candidate_zones_labeled": len(labeled), "bytes": out.stat().st_size,
        "coverage_semantics": "latest book side-specific outer price limits; hatched outside is unknown, dotted internal empty bucket is no observed notional"
    }, indent=2))


if __name__ == "__main__":
    main()
