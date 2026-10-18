# Order Book & Liquidity Intelligence (research)

## Scope

First collector: Binance Spot, initially `BTCUSDT`. It subscribes to the public diff-depth stream at up to 100 ms and public trade stream, fetches a REST depth snapshot, applies update-ID continuity checks, and writes newline-delimited JSON (JSONL). No API key or trading permission is required. It does not place, amend, or cancel orders.

## Run

Use Python 3.11+ and install the optional dependency:

```sh
python -m pip install -r requirements-orderbook.txt
python -m unittest discover -s tests -v
python -m orderbook.binance_spot_collector --symbol BTCUSDT --output-dir artifacts/orderbook
```

A bounded capture for a smoke test is possible with `--max-events 100`; it still needs live network access to Binance. Outputs are append-only:
- `<symbol>-depth-events.jsonl`: raw depth diffs with receipt time and exchange event/update IDs.
- `<symbol>-trades.jsonl`: raw public trades, buyer-maker flag, and inferred aggressor side.
- `<symbol>-book-metrics.jsonl`: descriptive metrics emitted only from locally reconstructed depth after synchronization.\n- `<symbol>-level-lifecycle.jsonl`: observed additions, quantity changes and removals of visible price levels, with first-observed time and elapsed visible lifetime.\n\nThe depth JSONL starts each synchronization session with the raw REST snapshot (`record_type: snapshot`) before subsequent diff events, preserving the baseline needed to replay that session.

## Sequence and integrity

A REST snapshot and a WebSocket diff stream are separate observations. Correct reconstruction requires buffering events around the snapshot and verifying that the first applied update bridges `lastUpdateId + 1`; subsequent updates must remain continuous. On a discontinuity, reconnect and rebuild from a new snapshot rather than silently continuing. Raw messages are retained so derived metrics can be independently audited.

## Metrics

- best bid / best ask, mid price, absolute and mid-relative spread;
- visible bid and ask quantity and quote-notional depth inside a configurable mid-price band;
- base-quantity order-book imbalance (OBI);
- estimated quote-size market-buy / market-sell slippage from currently visible levels, with incomplete fills explicitly marked;
- public trade prints with the buyer-maker flag and cumulative buy/sell volume delta (CVD) in base and quote units. The inferred aggressor side is based on Binance’s public buyer-maker flag.\n- price-level lifecycle events that measure how long a price level remains continuously visible and record quantity changes/removals.

Slippage is a static-book estimate and excludes fees, latency, market impact, hidden liquidity, other venues and changes while an order executes. OBI is quantity-based and depends on the selected band; quote-notional imbalance can be added separately if justified.

## Interpretation guardrails

- Results describe **visible Binance Spot liquidity at capture time**, not the entire crypto market.
- Displayed orders may be cancelled, replenished, spoofed, or moved; a wall is not proof of manipulation, durable support, or resistance.
- Public trades are executions; the buyer-maker flag permits a conventional aggressor-side inference, not knowledge of participant identity or intent.
- This collector alone cannot conclude that an asset is a good investment or generate a buy/sell instruction.
- Preserve UTC receipt time and venue event time separately. Do not backfill historical order-book state from OHLCV candles.
- Any predictive claim must be tested with point-in-time data, chronological out-of-sample / walk-forward evaluation, realistic fees and slippage, and comparisons against simple baselines. Avoid look-ahead leakage and survivorship bias.

## Known first-iteration constraints

- The collector is designed for a continuously running process; disconnects can leave gaps in time coverage, which must be detected from logs and raw timestamps.
- The current metric file stores metrics after each successfully applied depth update, so output volume may be high. Lifecycle records are emitted only when a tracked level is added, changed or removed.\n- Lifecycle age is the continuous time a price level has been observed by this process, not the age of an individual order. It resets after collector restart/re-synchronization; gaps must not be interpreted as continuous persistence. CVD also resets at process start.
- Cross-exchange aggregation, derivatives open interest/funding/liquidations, and alerting are intentionally not claimed as implemented. Level removal means displayed quantity at that price fell to zero in the observed book; it does not prove why it disappeared or that an order was cancelled rather than executed/replaced.
- Live exchange smoke testing and CI execution must be checked before treating the collector as validated.
