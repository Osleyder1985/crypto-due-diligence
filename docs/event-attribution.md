# Event timeline and market-reaction study

## Run

```sh
python event_study.py BTC 2026-07-01 2026-09-21
python event_study.py ETH 2026-01-01 2026-02-01 --interval 1h
```

The date arguments are UTC; both supplied dates are treated as calendar dates, with the end date included by the CLI. The runner fetches Binance Spot `TICKERUSDT` candles, discovers date-scoped RSS/Google News leads using the existing collector, and writes Markdown and JSON under `event_studies/`.

## Interpretation

For each news lead the report measures price return, relative volume, realized volatility (root-sum-square of candle returns), maximum run-up and drawdown over predeclared 1h, 6h and 24h windows. For non-BTC symbols it attempts a BTC comparison. A publication timestamp is only a proxy for when the underlying event occurred; explicit event timestamps are preferred when independently available.


Syndicated and near-identical headlines are grouped with a heuristic token-overlap rule over a 72-hour window. The grouped record retains each source URL and publisher; grouping is for organization only and does not prove independent corroboration. The report uses conservative labels: `observed_reaction` means a descriptive 2% return threshold was crossed in at least one window, while `inconclusive` means it was not crossed or data were insufficient. Neither label attributes a move to a headline. Common alternative explanations are listed as review prompts, not verified findings. Weak or unknown asset matching is explicitly flagged.

## Tests

```sh
python -m unittest tests.test_event_attribution -v
python -m unittest discover -s tests -v
```

Tests use deterministic synthetic candles and do not require internet access.
