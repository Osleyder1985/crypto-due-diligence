"""Plot observed BTC order-book liquidity and candidate zones without implying unobserved coverage."""
import argparse
import json
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
    a = p.parse_args()
    if not 0 < a.range_pct <= 50:
        p.error("--range-pct must be > 0 and <= 50")
    if a.max_zone_labels < 0:
        p.error("--max-zone-labels must be >= 0")

    records = read_records(a.input)
    last = records[-1]
    mid = float(last["mid_price"])
    low, high = mid * (1 - a.range_pct / 100), mid * (1 + a.range_pct / 100)
    accum = {}
    for rec in records:
        for b in rec.get("price_buckets", []):
            lo = float(b["price_bucket_start"])
            hi = float(b.get("price_bucket_end_exclusive", lo + 100))
            if hi <= low or lo >= high:
                continue
            slot = accum.setdefault(lo, {"bid": [], "ask": []})
            slot["bid"].append(float(b.get("bid_notional_usd", 0)))
            slot["ask"].append(float(b.get("ask_notional_usd", 0)))

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

    fig, ax = plt.subplots(figsize=(14, 9), constrained_layout=True)
    if prices:
        ax.barh([x + 50 for x in prices], bids, height=72, label="Buy bids", color="#238b57", alpha=.8)
        ax.barh([x + 50 for x in prices], [-v for v in asks], height=72, label="Sell asks", color="#c94c4c", alpha=.8)
        coverage_low, coverage_high = min(prices), max(prices) + 100
        ax.axhspan(coverage_low, coverage_high, color="#777777", alpha=.045, label="Observed bucket coverage")
        if coverage_low > low:
            ax.axhspan(low, min(coverage_low, high), facecolor="none", edgecolor="#888888", hatch="////", linewidth=0)
        if coverage_high < high:
            ax.axhspan(max(coverage_high, low), high, facecolor="none", edgecolor="#888888", hatch="////", linewidth=0)
        ax.axhline(coverage_low, color="#666666", linestyle=":", linewidth=1)
        ax.axhline(coverage_high, color="#666666", linestyle=":", linewidth=1)
    else:
        coverage_low = coverage_high = None
        ax.text(.5, .5, "No observed order-book buckets in requested price window",
                transform=ax.transAxes, ha="center", va="center", fontsize=12)

    ax.axhline(mid, color="#222222", linestyle="--", linewidth=1.5,
               label="Latest mid-price: " + format(mid, ",.2f"))
    for z, zlo, zhi in zones:
        support = z["type"] == "candidate_support"
        color = "#238b57" if support else "#c94c4c"
        ax.axhspan(zlo, zhi, color=color, alpha=.14, zorder=0)
    # Label only the strongest candidates; keep labels in a compact side panel rather than
    # stamping text over every price level.
    summary = []
    for z, zlo, zhi in labeled:
        kind = "SUP" if z["type"] == "candidate_support" else "RES"
        summary.append(
            f"{kind} {zlo:,.0f}-{zhi:,.0f} | "
            f"{z.get('persistence_pct', 0)}% | "
            f"${float(z.get('max_visible_notional_usd', 0))/1e6:.2f}M"
        )
    if summary:
        ax.text(.99, .985, "TOP CANDIDATE ZONES\n" + "\n".join(summary),
                transform=ax.transAxes, ha="right", va="top", fontsize=8,
                bbox={"facecolor": "white", "alpha": .9, "edgecolor": "#888888", "pad": 5})
    ax.set_ylim(low, high)
    ax.set_xlabel("Average visible notional per $100 bucket (USD): asks left, bids right")
    ax.set_ylabel("BTC/USD price")
    ax.set_title(f"BTC/USD observed order-book liquidity and candidate zones (±{a.range_pct:g}%)")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: "$" + format(abs(v) / 1e6, ".1f") + "M"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: "$" + format(v, ",.0f")))
    ax.grid(True, axis="y", alpha=.25)
    ax.legend(loc="lower left")
    coverage = "No buckets observed"
    if coverage_low is not None:
        coverage = f"Observed bucket span: ${coverage_low:,.0f}–${coverage_high:,.0f}"
    fig.text(.01, .005,
             f"Requested window: ${low:,.0f}–${high:,.0f} | {coverage} | "
             f"{len(prices)} distinct buckets across {len(records)} snapshots. "
             "Hatched areas have no observed buckets; they are not zero liquidity. "
             "Zones are candidates, not confirmed support/resistance.",
             fontsize=8, ha="left")
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print(json.dumps({
        "chart": str(out), "reference_mid_price": mid,
        "window_low": low, "window_high": high,
        "observed_coverage_low": coverage_low, "observed_coverage_high": coverage_high,
        "bucket_count": len(prices), "candidate_zones_in_window": len(zones),
        "candidate_zones_labeled": len(labeled), "bytes": out.stat().st_size
    }, indent=2))


if __name__ == "__main__":
    main()
