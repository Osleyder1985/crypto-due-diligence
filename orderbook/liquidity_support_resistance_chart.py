"""Plot observed Kraken liquidity using the actual captured book range, not a fixed percentage."""
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



def _captured_bounds(records):
    """Return the union of actual BID/ASK bounds across all captured snapshots."""
    bid_ranges = []
    ask_ranges = []
    for record in records:
        bid_best = _num(record, "best_bid_price", "best_bid")
        bid_worst = _num(record, "worst_bid_price")
        ask_best = _num(record, "best_ask_price", "best_ask")
        ask_worst = _num(record, "worst_ask_price")
        if None in (bid_best, bid_worst, ask_best, ask_worst):
            raise ValueError("every snapshot must include best and worst price bounds for both BID and ASK")
        bid_ranges.append((min(bid_best, bid_worst), max(bid_best, bid_worst)))
        ask_ranges.append((min(ask_best, ask_worst), max(ask_best, ask_worst)))
    bid_low = min(bounds[0] for bounds in bid_ranges)
    bid_high = max(bounds[1] for bounds in bid_ranges)
    ask_low = min(bounds[0] for bounds in ask_ranges)
    ask_high = max(bounds[1] for bounds in ask_ranges)
    low = min(bid_low, ask_low)
    high = max(bid_high, ask_high)
    if not high > low:
        raise ValueError("captured price range is empty or invalid")
    return bid_low, bid_high, ask_low, ask_high, low, high


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
    p.add_argument("--max-zone-labels", type=int, default=8)
    p.add_argument("--bucket-size", type=float, default=100.0)
    a = p.parse_args()
    if a.max_zone_labels < 0 or a.bucket_size <= 0:
        p.error("--max-zone-labels must be >= 0 and --bucket-size must be positive")

    records = read_records(a.input)
    last = records[-1]
    mid = float(last["mid_price"])
    latest_best_bid = _num(last, "best_bid_price", "best_bid")
    latest_worst_bid = _num(last, "worst_bid_price")
    latest_best_ask = _num(last, "best_ask_price", "best_ask")
    latest_worst_ask = _num(last, "worst_ask_price")

    # Use the union of actual captured bounds across every snapshot, never a fixed percentage.
    bid_low, bid_high, ask_low, ask_high, low, high = _captured_bounds(records)

    accum = {}
    observed_by_side = {"bid": set(), "ask": set()}
    # Bucket samples are averaged independently; no artificial price range is added.
    for rec in records:
        for b in rec.get("price_buckets", []):
            lo = float(b["price_bucket_start"])
            hi = float(b.get("price_bucket_end_exclusive", lo + a.bucket_size))
            if hi <= low or lo >= high:
                continue
            slot = accum.setdefault(lo, {"bid": [], "ask": []})
            for side, key in (("bid", "bid_notional_usd"), ("ask", "ask_notional_usd")):
                value = float(b.get(key, 0))
                slot[side].append(value)
                if value > 0:
                    observed_by_side[side].add(lo)

    prices = sorted(accum)
    bids = [sum(accum[x]["bid"]) / len(accum[x]["bid"]) for x in prices]
    asks = [sum(accum[x]["ask"]) / len(accum[x]["ask"]) for x in prices]
    zones_report = json.loads(Path(a.zones).read_text(encoding="utf-8"))
    zones = []
    for z in zones_report.get("zones", []):
        zlo, zhi = float(z["price_low"]), float(z["price_high_exclusive"])
        if zhi > low and zlo < high:
            zones.append((z, zlo, zhi))
    zones.sort(key=lambda item: float(item[0].get("max_visible_notional_usd", 0)), reverse=True)
    labeled = zones[:a.max_zone_labels]

    fig, ax = plt.subplots(figsize=(14, 9))
    if prices:
        ax.barh([x + a.bucket_size / 2 for x in prices], bids, height=a.bucket_size * .72,
                label="Buy bids (observed)", color="#238b57", alpha=.8)
        ax.barh([x + a.bucket_size / 2 for x in prices], [-v for v in asks], height=a.bucket_size * .72,
                label="Sell asks (observed)", color="#c94c4c", alpha=.8)
    else:
        ax.text(.5, .5, "No observed order-book buckets in captured price range",
                transform=ax.transAxes, ha="center", va="center", fontsize=12)

    max_notional = max(max(bids, default=0), max(asks, default=0), 1.0)
    x_extent = max_notional * 1.18
    ax.set_xlim(-x_extent, x_extent)
    ax.axvline(0, color="#444444", linewidth=.8)

    # A missing/zero bucket inside a side's captured bounds is not evidence of depth
    # outside the book. Hatching is only used outside each side's actual price bounds.
    y = low
    while y < high:
        y2 = min(high, y + a.bucket_size)
        bucket = math.floor(y / a.bucket_size) * a.bucket_size
        slot = accum.get(bucket)
        for side, interval in (("bid", (bid_low, bid_high)), ("ask", (ask_low, ask_high))):
            x1, x2 = (0, x_extent) if side == "bid" else (-x_extent, 0)
            if y2 <= interval[0] or y >= interval[1]:
                ax.fill_betweenx([y, y2], x1, x2, facecolor="none",
                                 edgecolor="#777777", hatch="////", linewidth=0, alpha=.45)
            elif not slot or not slot[side] or sum(slot[side]) <= 0:
                ax.fill_betweenx([y, y2], x1, x2, facecolor="none",
                                 edgecolor="#777777", hatch="..", linewidth=0, alpha=.55)
        y = y2

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

    def pct(span):
        return max(0.0, span[1] - span[0]) / (high - low) * 100
    bid_coverage, ask_coverage = pct((bid_low, bid_high)), pct((ask_low, ask_high))
    ax.set_ylim(low, high)
    ax.set_xlabel("Average visible notional per price bucket (USD): asks left ← | → bids right")
    ax.set_ylabel("BTC/USD price")
    ax.set_title("BTC/USD observed order-book liquidity and candidate zones (automatic captured range)")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: "$" + format(abs(v) / 1e6, ".1f") + "M"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: "$" + format(v, ",.0f")))
    ax.grid(True, axis="y", alpha=.25)
    ax.legend(loc="lower left")
    note = (f"Captured range: ${low:,.2f}–${high:,.2f} | latest mid-price: ${mid:,.2f} | "
            f"BID span coverage: {bid_coverage:.1f}% | ASK span coverage: {ask_coverage:.1f}%. "
            "//// outside that side's captured bounds = not captured; .. inside captured bounds = no observed notional. "
            "Coverage describes price span, not liquidity density. Bars average observed bucket values across snapshots. "
            "Candidate zones are not confirmed support/resistance.")
    fig.subplots_adjust(left=.08, right=.98, top=.93, bottom=.19)
    fig.text(.01, .015, textwrap.fill(note, width=190), fontsize=8, ha="left", va="bottom")
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print(json.dumps({
        "chart": str(out), "reference_mid_price": mid, "window_low": low, "window_high": high,
        "latest_best_bid": latest_best_bid, "latest_worst_bid": latest_worst_bid,
        "latest_best_ask": latest_best_ask, "latest_worst_ask": latest_worst_ask,
        "bid_coverage_pct": round(bid_coverage, 2), "ask_coverage_pct": round(ask_coverage, 2),
        "bucket_count": len(prices), "candidate_zones_in_window": len(zones),
        "candidate_zones_labeled": len(labeled), "bytes": out.stat().st_size,
        "coverage_semantics": "union of captured snapshot bounds; hatched outside side bounds, dotted internal buckets with no observed notional"
    }, indent=2))


if __name__ == "__main__":
    main()
