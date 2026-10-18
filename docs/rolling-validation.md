# Rolling validation of persistent prediction memory

This evaluation compares the direction model with persistent memory enabled and disabled, plus a momentum baseline, on paired out-of-sample timestamps.

Run: `python rolling_validation.py SOL 2024-01-01 2025-01-01`

The final date is inclusive and dates are UTC. The runner fetches Binance Spot candles for `TICKERUSDT` and writes JSON under `rolling_validations/`. Each fold builds memory only from candles before its warmup segment and rejects training labels that mature after prediction time. Only timestamps predicted by both model variants are scored.

A positive memory-minus-no-memory delta favors memory for that metric in this historical sample; a negative delta disfavors it. One asset or period cannot establish an edge. Fees are simplified; spread, slippage, liquidity, latency, market impact and taxes are omitted. This is historical simulation, not a guarantee, causal explanation, calibrated probability, or financial advice.
