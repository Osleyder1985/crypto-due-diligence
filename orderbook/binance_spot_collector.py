"""Capture Binance Spot depth and trade streams with sequence validation.

Research-only public market-data collector. It stores raw observations as JSONL
and labels all metrics as venue-specific; it never places orders.
"""
import argparse
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json
import logging
from pathlib import Path

from .lifecycle import CVDAccumulator, LevelLifecycleTracker
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import websockets
except ImportError:
    websockets = None

REST_BASE = "https://api.binance.com"
WS_BASE = "wss://stream.binance.com:9443/stream?streams="
USER_AGENT = "crypto-due-diligence-orderbook/0.1"
LOG = logging.getLogger("orderbook")


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _json_request(url, timeout=10):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Binance public market-data request failed: {exc}") from exc


def fetch_depth_snapshot(symbol, limit=1000):
    if limit not in {100, 500, 1000, 5000}:
        raise ValueError("snapshot limit must be one of 100, 500, 1000, 5000")
    payload = _json_request(f"{REST_BASE}/api/v3/depth?symbol={symbol}&limit={limit}")
    if not isinstance(payload.get("lastUpdateId"), int):
        raise RuntimeError("depth snapshot missing integer lastUpdateId")
    return payload


def _levels(raw):
    result = {}
    for row in raw:
        if len(row) < 2:
            continue
        price, quantity = Decimal(str(row[0])), Decimal(str(row[1]))
        if price <= 0 or quantity < 0:
            continue
        if quantity == 0:
            result.pop(price, None)
        else:
            result[price] = quantity
    return result


def apply_depth_event(bids, asks, event):
    """Apply one Binance diff-depth event in place."""
    for side, changes in ((bids, event.get("b", [])), (asks, event.get("a", []))):
        for row in changes:
            price, quantity = Decimal(str(row[0])), Decimal(str(row[1]))
            if quantity == 0:
                side.pop(price, None)
            elif price > 0 and quantity > 0:
                side[price] = quantity


def calculate_metrics(bids, asks, depth_band_pct=Decimal("1"), trade_size_quote=Decimal("1000")):
    """Compute descriptive metrics from a locally reconstructed visible book."""
    if not bids or not asks:
        return {"status": "BOOK_EMPTY"}
    best_bid, best_ask = max(bids), min(asks)
    if best_bid <= 0 or best_ask <= 0 or best_ask < best_bid:
        return {"status": "CROSSED_OR_INVALID_BOOK"}
    mid = (best_bid + best_ask) / Decimal(2)
    spread = best_ask - best_bid
    band = depth_band_pct / Decimal(100)
    bid_levels = [(p, q) for p, q in bids.items() if p >= mid * (1 - band)]
    ask_levels = [(p, q) for p, q in asks.items() if p <= mid * (1 + band)]
    bid_qty = sum((q for _, q in bid_levels), Decimal(0))
    ask_qty = sum((q for _, q in ask_levels), Decimal(0))
    total_qty = bid_qty + ask_qty
    obi = (bid_qty - ask_qty) / total_qty if total_qty else Decimal(0)

    def depth_quote(levels):
        return sum((p * q for p, q in levels), Decimal(0))

    def estimate_slippage(levels, size, side):
        remaining = size
        filled_base = Decimal(0)
        filled_quote = Decimal(0)
        ordered = sorted(levels.items(), key=lambda item: item[0], reverse=(side == "sell"))
        for price, quantity in ordered:
            take_quote = min(remaining, price * quantity)
            if take_quote > 0:
                filled_base += take_quote / price
                filled_quote += take_quote
                remaining -= take_quote
            if remaining <= 0:
                break
        if remaining > 0 or filled_base <= 0:
            return {"fully_filled": False, "unfilled_quote": str(remaining),
                    "slippage_pct": None, "filled_quote": str(filled_quote)}
        average_price = filled_quote / filled_base
        reference = best_ask if side == "buy" else best_bid
        slippage = ((average_price - reference) / reference if side == "buy"
                    else (reference - average_price) / reference) * 100
        return {"fully_filled": True, "unfilled_quote": "0",
                "slippage_pct": str(slippage), "filled_quote": str(filled_quote)}

    return {
        "status": "OK",
        "best_bid": str(best_bid), "best_ask": str(best_ask), "mid_price": str(mid),
        "spread": str(spread), "spread_pct_mid": str(spread / mid * 100),
        "depth_band_pct": str(depth_band_pct),
        "bid_depth_base": str(bid_qty), "ask_depth_base": str(ask_qty),
        "bid_depth_quote": str(depth_quote(bid_levels)),
        "ask_depth_quote": str(depth_quote(ask_levels)),
        "obi_base_quantity": str(obi),
        "slippage_buy_quote": estimate_slippage(asks, trade_size_quote, "buy"),
        "slippage_sell_quote": estimate_slippage(bids, trade_size_quote, "sell"),
        "trade_size_quote": str(trade_size_quote),
        "note": "Visible Binance Spot book only; not total-market liquidity or an investment signal.",
    }


class JsonlWriter:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record):
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


async def collect(symbol="BTCUSDT", output_dir="artifacts/orderbook", snapshot_limit=1000,
                  depth_band_pct=Decimal("1"), trade_size_quote=Decimal("1000"),
                  max_events=None, reconnect_delay=3):
    """Capture public streams; on disconnect or sequence gap, re-sync from a snapshot."""
    if websockets is None:
        raise RuntimeError("install the optional dependency: pip install -r requirements-orderbook.txt")
    symbol = symbol.strip().upper()
    if not symbol.isalnum() or not 5 <= len(symbol) <= 20:
        raise ValueError("symbol must be an alphanumeric Binance Spot pair, e.g. BTCUSDT")
    root = Path(output_dir)
    raw_depth = JsonlWriter(root / f"{symbol.lower()}-depth-events.jsonl")
    raw_trades = JsonlWriter(root / f"{symbol.lower()}-trades.jsonl")
    metrics_out = JsonlWriter(root / f"{symbol.lower()}-book-metrics.jsonl")
    ws_url = WS_BASE + f"{symbol.lower()}@depth@100ms/{symbol.lower()}@trade"
    event_count = 0
    cvd = CVDAccumulator()
    lifecycle = LevelLifecycleTracker()
    lifecycle_out = JsonlWriter(root / f"{symbol.lower()}-level-lifecycle.jsonl")

    while max_events is None or event_count < max_events:
        try:
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20,
                                          close_timeout=5, max_size=2**20) as socket:
                buffer = []
                snapshot = await asyncio.to_thread(fetch_depth_snapshot, symbol, snapshot_limit)
                last_update_id = snapshot["lastUpdateId"]
                snapshot_at = utc_now()
                bids, asks = _levels(snapshot.get("bids", [])), _levels(snapshot.get("asks", []))
                lifecycle.seed(bids, asks, snapshot_at)
                raw_depth.write({
                    "schema_version": "1.0", "record_type": "snapshot", "venue": "binance_spot",
                    "symbol": symbol, "received_at": snapshot_at,
                    "last_update_id": last_update_id, "raw_snapshot": snapshot,
                })
                synchronized = False

                def write_reconstructed_book():
                    if not synchronized:
                        return
                    raw_depth.write({
                        "schema_version": "1.0", "record_type": "reconstructed_book",
                        "venue": "binance_spot", "symbol": symbol, "received_at": utc_now(),
                        "last_update_id": last_update_id,
                        "raw_snapshot": {
                            "lastUpdateId": last_update_id, "limit": snapshot_limit,
                            "bids": [[str(price), str(quantity)] for price, quantity in sorted(bids.items(), reverse=True)],
                            "asks": [[str(price), str(quantity)] for price, quantity in sorted(asks.items())],
                        },
                    })

                async for message in socket:
                    received_at = utc_now()
                    envelope = json.loads(message)
                    stream, event = envelope.get("stream", ""), envelope.get("data", {})
                    if stream.endswith("@trade"):
                        flow = cvd.add_trade(event.get("p", "0"), event.get("q", "0"), bool(event.get("m")))
                        raw_trades.write({
                            "schema_version": "1.0", "venue": "binance_spot", "symbol": symbol,
                            "received_at": received_at, "event_time_ms": event.get("T"),
                            "trade_id": event.get("t"), "price": event.get("p"),
                            "quantity": event.get("q"), "buyer_is_maker": event.get("m"),
                            **flow, "raw_event": event,
                        })
                        event_count += 1
                        if max_events is not None and event_count >= max_events:
                            write_reconstructed_book()
                            return
                        continue
                    if not stream.endswith("@depth@100ms"):
                        continue
                    raw_depth.write({
                        "schema_version": "1.0", "venue": "binance_spot", "symbol": symbol,
                        "received_at": received_at, "event_time_ms": event.get("E"),
                        "first_update_id": event.get("U"), "final_update_id": event.get("u"),
                        "raw_event": event,
                    })
                    event_count += 1
                    if max_events is not None and event_count >= max_events:
                        write_reconstructed_book()
                        return
                    if not synchronized:
                        if event.get("u", 0) <= last_update_id:
                            continue
                        buffer.append(event)
                        first = buffer[0]
                        if first.get("U", 0) <= last_update_id + 1 <= first.get("u", 0):
                            synchronized = True
                        elif first.get("U", 0) > last_update_id + 1:
                            LOG.warning("Initial depth update does not bridge snapshot; reconnecting")
                            break
                        else:
                            continue
                    else:
                        # Binance diff-depth events after the first bridged update must be continuous.
                        if event.get("u", 0) <= last_update_id:
                            continue
                        if event.get("U", 0) > last_update_id + 1:
                            LOG.warning("Depth sequence gap; reconnecting for a new snapshot")
                            break
                        buffer.append(event)
                    while buffer:
                        current = buffer.pop(0)
                        if current.get("u", 0) <= last_update_id:
                            continue
                        if current.get("U", 0) > last_update_id + 1 or current.get("u", 0) < last_update_id + 1:
                            LOG.warning("Depth sequence discontinuity; reconnecting")
                            synchronized = False
                            break
                        apply_depth_event(bids, asks, current)
                        for lifecycle_record in lifecycle.apply_event(current, received_at):
                            lifecycle_out.write({
                                "schema_version": "1.0", "venue": "binance_spot", "symbol": symbol,
                                "first_update_id": current.get("U"), "final_update_id": current.get("u"),
                                **lifecycle_record,
                            })
                        last_update_id = current["u"]
                        metrics_out.write({
                            "schema_version": "1.0", "venue": "binance_spot", "symbol": symbol,
                            "received_at": received_at, "event_time_ms": current.get("E"),
                            "last_update_id": last_update_id,
                            "metrics": calculate_metrics(bids, asks, depth_band_pct, trade_size_quote),
                        })
                    if not synchronized:
                        break
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            LOG.warning("Market-data connection ended (%s); retrying in %ss", exc, reconnect_delay)
        if max_events is None or event_count < max_events:
            await asyncio.sleep(reconnect_delay)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--output-dir", default="artifacts/orderbook")
    parser.add_argument("--snapshot-limit", type=int, choices=[100, 500, 1000, 5000], default=1000)
    parser.add_argument("--depth-band-pct", type=Decimal, default=Decimal("1"))
    parser.add_argument("--trade-size-quote", type=Decimal, default=Decimal("1000"))
    parser.add_argument("--max-events", type=int, default=None, help="stop after N raw depth/trade events")
    parser.add_argument("--reconnect-delay", type=int, default=3)
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()
    if args.depth_band_pct <= 0 or args.trade_size_quote <= 0:
        parser.error("depth band and quote trade size must be positive")
    if args.max_events is not None and args.max_events < 1:
        parser.error("--max-events must be positive")
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(collect(args.symbol, args.output_dir, args.snapshot_limit, args.depth_band_pct,
                        args.trade_size_quote, args.max_events, args.reconnect_delay))


if __name__ == "__main__":
    main()
