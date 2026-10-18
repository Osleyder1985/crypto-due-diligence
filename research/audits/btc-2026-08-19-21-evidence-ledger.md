# BTC event audit: 2026-08-19 to 2026-08-21

Status: **PARTIAL — public-source cross-check; not a completed audit of the 55 feed entries.**  
Causal attribution for all candidates: `NOT_ESTABLISHED`.

## Scope and rules

This note records independently retrievable primary/near-primary sources for the market move and separates (1) event/publication dates, (2) market mechanisms reported by third parties, and (3) causal conclusions. It does not substitute for reviewing the 55 rows in the historical artifact. The artifact's row-level URLs and raw feed timestamp fields must be joined to this ledger before issue #61 can be closed.

- All times are retained with their published timezone; do not convert a date-only source into a fabricated time.
- A publisher timestamp is evidence of article publication, not necessarily the time the underlying event became known to markets.
- ETF flow totals are session-level measurements, typically reported after the session; they must not be treated as intraday triggers without time-resolved flow data.
- Headlines describing the same market move are dependent reporting, not independent causal evidence.
- Return windows are descriptive and cannot establish causality by themselves.

## Reviewed candidate-event ledger

| ID | Candidate / underlying event | Source and time evidence | Classification | Interpretation / caveat | Status |
|---|---|---|---|---|---|
| EVT-001 | U.S. Treasury increases planned liquidity-support buybacks in long-dated nominal coupon securities from a maximum $2bn to at least $4bn per operation | [Official Treasury release](https://home.treasury.gov/news/press-releases/sb0607), dated 2026-08-19. The policy change is stated to take effect 2026-09-09. Exact release time was not verified in this review. | Official announcement; underlying policy implementation is future-dated | Plausible macro/liquidity sentiment catalyst, not proof of BTC-specific causation. The 19 Aug reaction would relate to the announcement/interpretation, not execution of the buybacks on that date. | Source verified; exact event-time alignment unresolved |
| EVT-002 | SEC proposal for tailored exemptions and safe-harbor framework for certain crypto-asset investment contracts | [Official SEC statement](https://www.sec.gov/newsroom/speeches-statements/atkins-statement-regulation-crypto-assets-081826), dated 2026-08-18. Exact intraday timestamp was not verified in this review. | Official regulatory announcement | A potential anticipatory/sentiment factor preceding the 19 Aug move. Need compare the release time with BTC's first abnormal return and other crypto assets before attributing an effect. | Source verified; exact event-time alignment unresolved |
| EVT-003 | BTC breaks higher amid a broad crypto rally and short liquidations; Treasury buybacks cited by market coverage | [CoinDesk report](https://www.coindesk.com/markets/2026/08/19/bitcoin-surges-above-usd68-000-liquidating-usd1-4-billion-shorts-as-treasury-buybacks-boost-risk-appetite), published 2026-08-19 at 12:18 p.m. ET. | Contemporary news report / market commentary | The report describes a mechanism consistent with feedback amplification: short liquidations force repurchases. It is a secondary account of the move, not independent proof of the initiating cause. Liquidation data need a provider, interval, and capture time to reproduce. | Article timestamp verified; mechanism not independently quantified here |
| EVT-004 | Market coverage reports BTC at $69,000 and nearly $1.92bn in 24h crypto liquidations | [The Block report](https://www.theblock.co/news/markets/2026-08-19-bitcoin-69000-ether-jumps-treasury-buybacks-sec-crypto-proposal-fuel-market-rally-412248), published 2026-08-19 at 3:05 p.m. EDT. | Contemporary news report / overlapping report of the same market episode | Likely dependent with EVT-003 because both cover the same rally and cite policy catalysts and liquidations. Do not count this as a second independent causal event. Liquidation estimates may vary by provider and capture time. | Article timestamp verified; event-level dependence to be confirmed against feed rows |
| EVT-005 | U.S. spot BTC ETFs record $517m net inflows on 19 Aug and $606m on 20 Aug | [CoinDesk live coverage](https://www.coindesk.com/tech/2026/08/21/live-updates-bitcoin-ether-etfs-pull-in-usd800-million-as-inflows-surge-for-a-second-day), which reports the session figures in coverage dated 2026-08-21. | Session-level market flow observation reported retrospectively | Supports demand during the rally, but publication of the aggregate figures after the sessions means it cannot be treated as a known trigger at the start of the move. Need original flow dataset, session dates, and as-of availability. | Report located; raw provider data and publication-to-market timing not independently verified |
| EVT-006 | White House crypto-policy/CLARITY Act messaging cited in contemporaneous market coverage | Referenced in [Reuters, 20 Aug](https://www.reuters.com/legal/government/bitcoin-crypto-shares-climb-after-trump-pushes-clarity-act-2026-08-20/) and in EVT-003/EVT-004 coverage. The exact statement time and original transcript/record were not independently verified for this ledger. | Potential competing/concurrent policy catalyst | Must be investigated separately from Treasury and SEC events. Do not bundle all policy headlines into one presumed cause. | Unresolved pending primary-source/time verification |

## Current assessment

1. **Highest-priority candidate:** Treasury's 19 Aug announcement, because contemporaneous reporting explicitly links it to the rally. That linkage is a reported hypothesis, not a causal estimate.
2. **Competing/preceding catalyst:** SEC's 18 Aug proposal, which may have affected sentiment before the observed move.
3. **Potential amplification:** short liquidations, but these can be a consequence and amplifier of the price move as well as a reflection of positioning; a time series is required to establish ordering.
4. **Demand confirmation rather than initiating evidence:** daily ETF inflows. Aggregate session totals are not intraday timestamps.
5. **Unresolved:** other simultaneous macro, policy, positioning, derivatives, and market-wide factors. No counterfactual estimate has been run in this note.

## Required next step to finish issue #61

Join this candidate ledger against all 55 historical-artifact rows. For each row, retain: feed URL; raw timestamp field and value; normalized UTC time; publisher's canonical URL; independently corroborated publication time; event time (if any); original/syndicated/commentary/duplicate/unresolved classification; overlapping reaction-window cluster; competing candidates; timestamp confidence; review rationale.

Then rerun the BTC study and preserve both the prior and new artifacts. The issue remains open until every row is reviewed or explicitly marked unresolved and the report is reproducible. Causal labels must remain `NOT_ESTABLISHED` absent independent identification evidence.
