"""Capture a one-shot public Kraken Spot XBT/USD order-book snapshot."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.kraken.com/0/public/Depth"
USER_AGENT = "crypto-due-diligence-orderbook/0.2"


def fetch_book(pair="XBTUSD", count=500, timeout=15):
    if not 1 <= count <= 500:
        raise ValueError("count must be between 1 and 500")
    url = BASE_URL + "?" + urlencode({"pair": pair, "count": count})
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Kraken public depth request failed: {exc}") from exc
    if payload.get("error"):
        raise RuntimeError("Kraken API error: " + "; ".join(payload["error"]))
    result = payload.get("result")
    if not isinstance(result, dict) or not result:
        raise RuntimeError("Kraken depth response has no result book")
    key = next(iter(result))
    book = result[key]
    if not book.get("bids") or not book.get("asks"):
        raise RuntimeError("Kraken depth response is missing bids or asks")
    return key, book


def _parse_levels(rows, side):
    levels = []
    for row in rows:
        if not isinstance(row, list) or len(row) < 2:
            continue
        price, quantity = Decimal(str(row[0])), Decimal(str(row[1]))
        if price <= 0 or quantity <= 0:
            continue
        levels.append({
            "side": side, "price": str(price), "quantity_btc": str(quantity),
            "notional_usd": str(price * quantity),
            "distance_from_mid_pct": None,
        })
    return levels


def build_report(pair, book_key, book, bucket_size=Decimal("100"), top_n=20):
    if bucket_size <= 0:
        raise ValueError("bucket_size must be positive")
    bids = _parse_levels(book["bids"], "bid")
    asks = _parse_levels(book["asks"], "ask")
    if not bids or not asks:
        raise ValueError("book must contain valid bid and ask levels")
    best_bid = max(Decimal(x["price"]) for x in bids)
    best_ask = min(Decimal(x["price"]) for x in asks)
    if best_ask < best_bid:
        raise ValueError("crossed or invalid order book")
    mid = (best_bid + best_ask) / Decimal(2)
    for level in bids + asks:
        level["distance_from_mid_pct"] = str(
            (abs(Decimal(level["price"]) - mid) / mid) * Decimal(100)
        )
    ranked = sorted(bids + asks, key=lambda x: Decimal(x["notional_usd"]), reverse=True)
    buckets = defaultdict(lambda: {"bid_notional_usd": Decimal(0), "ask_notional_usd": Decimal(0),
                                   "bid_levels": 0, "ask_levels": 0})
    for level in bids + asks:
        price = Decimal(level["price"])
        start = (price / bucket_size).to_integral_value(rounding=ROUND_FLOOR) * bucket_size
        bucket = buckets[start]
        bucket[level["side"] + "_notional_usd"] += Decimal(level["notional_usd"])
        bucket[level["side"] + "_levels"] += 1
    bucket_rows = [{
        "price_bucket_start": str(start), "price_bucket_end_exclusive": str(start + bucket_size),
        "bid_notional_usd": str(values["bid_notional_usd"]),
        "ask_notional_usd": str(values["ask_notional_usd"]),
        "bid_levels": values["bid_levels"], "ask_levels": values["ask_levels"],
    } for start, values in sorted(buckets.items())]
    return {
        "schema_version": "1.0",
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "venue": "kraken_spot", "pair_requested": pair, "pair_returned": book_key,
        "scope": "Single Kraken Spot public aggregated order-book snapshot; not total-market liquidity.",
        "best_bid": str(best_bid), "best_ask": str(best_ask), "mid_price": str(mid),
        "spread": str(best_ask - best_bid),
        "spread_pct_mid": str((best_ask - best_bid) / mid * Decimal(100)),
        "bid_level_count": len(bids), "ask_level_count": len(asks),
        "bid_depth_usd": str(sum((Decimal(x["notional_usd"]) for x in bids), Decimal(0))),
        "ask_depth_usd": str(sum((Decimal(x["notional_usd"]) for x in asks), Decimal(0))),
        "top_concentrated_levels_by_notional": ranked[:top_n],
        "price_buckets": bucket_rows,
        "limitations": [
            "This is one snapshot from Kraken Spot XBT/USD, not Binance BTC/USDT or the combined global market.",
            "Displayed levels can change or be cancelled; visible liquidity is not guaranteed execution liquidity.",
            "The aggregated public book does not identify individual owners or their intent.",
            "A single snapshot cannot establish persistence, order lifecycle, causal impact, or a predictive signal.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", default="XBTUSD")
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--output-dir", default="artifacts/orderbook")
    parser.add_argument("--price-bucket", type=Decimal, default=Decimal("100"))
    parser.add_argument("--top-n", type=int, default=20)
    args = parser.parse_args()
    if args.top_n < 1:
        parser.error("--top-n must be positive")
    key, book = fetch_book(args.pair, args.count)
    report = build_report(args.pair, key, book, args.price_bucket, args.top_n)
    root = Path(args.output_dir)
    root.mkdir(parents=True, exist_ok=True)
    stem = args.pair.lower().replace("/", "-")
    (root / f"{stem}-kraken-book.json").write_text(json.dumps({
        "captured_at": report["captured_at"], "venue": report["venue"],
        "pair_returned": key, "raw_book": book,
    }, indent=2) + "\n", encoding="utf-8")
    (root / f"{stem}-kraken-liquidity-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        f"# Kraken Spot order-book concentration: {args.pair}", "",
        f"- Captured at: {report['captured_at']}",
        f"- Best bid / ask: {report['best_bid']} / {report['best_ask']}",
        f"- Mid price: {report['mid_price']}",
        f"- Spread: {report['spread']} ({report['spread_pct_mid']}% of mid)",
        f"- Visible bid depth: ${report['bid_depth_usd']}",
        f"- Visible ask depth: ${report['ask_depth_usd']}", "",
        "## Largest visible levels by notional", "",
        "| Side | Price | BTC quantity | Notional USD | Distance from mid (%) |",
        "|---|---:|---:|---:|---:|",
    ]
    for level in report["top_concentrated_levels_by_notional"]:
        lines.append(f"| {level['side']} | {level['price']} | {level['quantity_btc']} | {level['notional_usd']} | {level['distance_from_mid_pct']} |")
    lines.extend(["", "## Aggregated price buckets", "",
                  "| Price range | Bid notional USD | Ask notional USD | Bid levels | Ask levels |",
                  "|---|---:|---:|---:|---:|"])
    for row in report["price_buckets"]:
        lines.append(f"| [{row['price_bucket_start']}, {row['price_bucket_end_exclusive']}) | {row['bid_notional_usd']} | {row['ask_notional_usd']} | {row['bid_levels']} | {row['ask_levels']} |")
    lines.extend(["", "## Limitations", ""] + [f"- {item}" for item in report["limitations"]])
    (root / f"{stem}-kraken-liquidity-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "venue": report["venue"], "pair": report["pair_returned"],
        "bid_levels": report["bid_level_count"], "ask_levels": report["ask_level_count"],
        "best_bid": report["best_bid"], "best_ask": report["best_ask"],
        "report": str(root / f"{stem}-kraken-liquidity-report.json"),
    }, indent=2))


if __name__ == "__main__":
    main()
