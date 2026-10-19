"""Collect a maintained Kraken Spot v2 L2 book (up to 1000 levels/side)."""
import argparse
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import zlib

from orderbook.kraken_snapshot_collector import build_report

WS_URL = "wss://ws.kraken.com/v2"


class BookChecksumError(RuntimeError):
    """Raised when the local L2 book fails Kraken's CRC32 checksum."""


def _checksum_component(value):
    """Format a decimal exactly as Kraken specifies for its v2 checksum."""
    text = format(Decimal(str(value)), "f").replace(".", "")
    return text.lstrip("0") or "0"


def calculate_checksum(book):
    """Return the unsigned CRC32 checksum for the top 10 asks then bids."""
    parts = []
    for side, reverse in (("asks", False), ("bids", True)):
        levels = sorted(
            book[side].items(),
            key=lambda row: Decimal(row[0]),
            reverse=reverse,
        )[:10]
        for price, qty in levels:
            parts.append(_checksum_component(price))
            parts.append(_checksum_component(qty))
    payload = "".join(parts).encode("ascii")
    return zlib.crc32(payload) & 0xFFFFFFFF


def apply_book_message(book, message):
    """Apply one Kraken v2 book snapshot/update and validate its checksum."""
    data = message.get("data")
    if not isinstance(data, list) or not data:
        return False
    item = data[0]
    if "bids" not in item and "asks" not in item:
        return False
    is_snapshot = message.get("type") == "snapshot"
    if is_snapshot:
        book["bids"].clear()
        book["asks"].clear()
    for side in ("bids", "asks"):
        for row in item.get(side, []):
            price = str(Decimal(str(row["price"])))
            qty = Decimal(str(row["qty"]))
            if qty <= 0:
                book[side].pop(price, None)
            else:
                book[side][price] = qty
    book["bids"] = dict(sorted(
        book["bids"].items(), key=lambda row: Decimal(row[0]), reverse=True
    )[:1000])
    book["asks"] = dict(sorted(
        book["asks"].items(), key=lambda row: Decimal(row[0])
    )[:1000])
    if "checksum" in item:
        actual = calculate_checksum(book)
        expected = int(item["checksum"])
        if actual != expected:
            raise BookChecksumError(
                f"Kraken book checksum mismatch: expected {expected}, calculated {actual}"
            )
    book["last_update_at"] = item.get("timestamp") or datetime.now(
        timezone.utc
    ).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    book["checksum"] = item.get("checksum")
    return is_snapshot


def snapshot_report(book, pair="BTC/USD", top_n=20):
    bids = [[price, str(qty)] for price, qty in sorted(
        book["bids"].items(), key=lambda row: Decimal(row[0]), reverse=True)]
    asks = [[price, str(qty)] for price, qty in sorted(
        book["asks"].items(), key=lambda row: Decimal(row[0]))]
    if not bids or not asks:
        raise ValueError("WebSocket book has no bids or asks yet")
    report = build_report(pair, pair, {"bids": bids, "asks": asks}, Decimal("100"), top_n)
    report["venue"] = "kraken_spot_ws_v2"
    report["captured_at"] = book.get("last_update_at") or report["captured_at"]
    report["book_depth_requested_per_side"] = 1000
    report["bid_level_count"] = len(bids)
    report["ask_level_count"] = len(asks)
    # These are the actual outer limits of the currently maintained book, not
    # the min/max of buckets that happen to contain notional.
    report["best_bid_price"] = str(max(Decimal(row[0]) for row in bids))
    report["worst_bid_price"] = str(min(Decimal(row[0]) for row in bids))
    report["best_ask_price"] = str(min(Decimal(row[0]) for row in asks))
    report["worst_ask_price"] = str(max(Decimal(row[0]) for row in asks))
    report["book_checksum"] = book.get("checksum")
    report["book_checksum_validated"] = book.get("checksum") is not None
    report["scope"] = "Maintained Kraken Spot WebSocket v2 L2 book; up to 1000 price levels per side, aggregated public liquidity only."
    return report


async def collect(pair, snapshots, interval_seconds, output_dir, top_n=20):
    import websockets
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    raw_path = root / "kraken-xbtusd-ws-snapshots.jsonl"
    book = {"bids": {}, "asks": {}, "last_update_at": None, "checksum": None}
    ready = asyncio.Event()

    async def reader():
        while True:
            try:
                async with websockets.connect(
                    WS_URL, ping_interval=20, ping_timeout=20,
                    close_timeout=10, max_size=8 * 1024 * 1024
                ) as ws:
                    await ws.send(json.dumps({
                        "method": "subscribe",
                        "params": {"channel": "book", "symbol": [pair], "depth": 1000, "snapshot": True},
                        "req_id": 1,
                    }))
                    async for raw in ws:
                        message = json.loads(raw, parse_float=Decimal)
                        if message.get("channel") == "book" and message.get("type") in ("snapshot", "update"):
                            data = message.get("data") or []
                            if not data or "checksum" not in data[0]:
                                raise BookChecksumError("Kraken book message omitted required checksum")
                            if apply_book_message(book, message):
                                ready.set()
                        elif message.get("method") == "subscribe" and message.get("success") is False:
                            raise RuntimeError("Kraken WebSocket subscription rejected: " + json.dumps(message))
                        elif message.get("success") is False:
                            raise RuntimeError("Kraken WebSocket error: " + json.dumps(message))
                raise ConnectionError("Kraken WebSocket closed; reconnecting")
            except (websockets.ConnectionClosed, OSError, ConnectionError, BookChecksumError) as exc:
                ready.clear()
                book["bids"].clear()
                book["asks"].clear()
                book["last_update_at"] = None
                book["checksum"] = None
                print(json.dumps({
                    "event": "websocket_reconnect",
                    "reason": str(exc),
                    "book_invalidated": True,
                }), flush=True)
                await asyncio.sleep(2)

    task = asyncio.create_task(reader())
    try:
        with raw_path.open("w", encoding="utf-8") as raw_file:
            for i in range(snapshots):
                while not ready.is_set():
                    if task.done():
                        task.result()
                        raise RuntimeError("Kraken WebSocket reader stopped before collection finished")
                    await asyncio.wait_for(ready.wait(), timeout=60)
                if task.done():
                    task.result()
                    raise RuntimeError("Kraken WebSocket reader stopped before collection finished")
                report = snapshot_report(book, pair, top_n)
                record = {
                    "captured_at": report["captured_at"],
                    "venue": report["venue"],
                    "pair_returned": pair,
                    "best_bid": report["best_bid"],
                    "best_ask": report["best_ask"],
                    "mid_price": report["mid_price"],
                    "price_buckets": report["price_buckets"],
                    "top_concentrated_levels_by_notional": report["top_concentrated_levels_by_notional"],
                    "book_depth_requested_per_side": 1000,
                    "bid_level_count": report["bid_level_count"],
                    "ask_level_count": report["ask_level_count"],
                    "best_bid_price": report["best_bid_price"],
                    "worst_bid_price": report["worst_bid_price"],
                    "best_ask_price": report["best_ask_price"],
                    "worst_ask_price": report["worst_ask_price"],
                    "book_checksum": report["book_checksum"],
                    "book_checksum_validated": report["book_checksum_validated"],
                }
                raw_file.write(json.dumps(record) + "\n")
                raw_file.flush()
                print(json.dumps({
                    "sample": i + 1, "total": snapshots, "captured_at": record["captured_at"],
                    "mid_price": record["mid_price"], "bid_levels": record["bid_level_count"],
                    "ask_levels": record["ask_level_count"],
                    "worst_bid_price": record["worst_bid_price"], "worst_ask_price": record["worst_ask_price"],
                    "book_checksum_validated": record["book_checksum_validated"],
                }), flush=True)
                if i + 1 < snapshots:
                    await asyncio.sleep(interval_seconds)
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    return raw_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", default="BTC/USD")
    parser.add_argument("--snapshots", type=int, default=120)
    parser.add_argument("--interval-seconds", type=int, default=5)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--output-dir", default="artifacts/orderbook-ws")
    args = parser.parse_args()
    if not 2 <= args.snapshots <= 10000:
        parser.error("--snapshots must be between 2 and 10000")
    if not 1 <= args.interval_seconds <= 300:
        parser.error("--interval-seconds must be between 1 and 300")
    if args.top_n < 1:
        parser.error("--top-n must be positive")
    print(json.dumps({"output": str(asyncio.run(collect(
        args.pair, args.snapshots, args.interval_seconds, args.output_dir, args.top_n)))}))


if __name__ == "__main__":
    main()
