# BTC historical research artifact audit — 2026-08-19 to 2026-08-21

Tracking issue: #61.

## Scope and provenance

- Artifact: `crypto-research-BTC-2026-07-01-2026-09-21.zip`
- Original audited run: [39170183626](https://github.com/Osleyder1985/crypto-due-diligence/actions/runs/39170183626), commit `3e35b654ea55b1b7ed74ad56919642538331fd59`.
- Original artifact ID: `12152301230`; created 2026-10-18 21:58:56 UTC; 98,175 bytes.
- Follow-up run: [39171383163](https://github.com/Osleyder1985/crypto-due-diligence/actions/runs/39171383163), commit `3b7561fcec8620a2bea9057c6de0422cbe74b7f7`.
- Follow-up artifact ID: `12152272755`; created 2026-10-18 22:15:13 UTC; 93,187 bytes.
- Both ZIPs contain autonomous-research JSON/Markdown and event-study JSON/Markdown. The first artifact predates PR #63's missing-artifact fail-closed check. A successful run alone is not proof of report completeness.

## Findings from the archived JSON

### Dataset and source provenance

- The original run reports `raw_event_count=56` and `deduplicated_event_count=56`; autonomous contextual evidence also contains 56 entries.
- The follow-up run reports `raw_event_count=53` and `deduplicated_event_count=53`. The number of collected entries changed by three between runs; no row-level reconciliation or stable target manifest explains the difference.
- In both runs, exactly **15** entries have feed-reported dates from 2026-08-19 through 2026-08-21. The original run's daily counts are Aug 19: 1, Aug 20: 9, Aug 21: 5. The follow-up run's counts are Aug 19: 3, Aug 20: 7, Aug 21: 5. This does not reconcile with issue #61's 55-entry target, nor does the changing date distribution establish a stable cohort.
- All rows in both archived reports have `publication_timestamp_quality=FEED_REPORTED_PUBLICATION`; all URLs use the `news.google.com` RSS-article wrapper, not a verified publisher-original URL. Direct article timestamps and source-origin verification are not established.
- The original 56 rows are marked `UNIQUE_HEADLINE`; the follow-up contains 53 rows. Headline-level deduplication does not establish that entries represent independent real-world events.
- A `STRONG` ticker match is not independent event verification.

### Event-time and price-reaction limitations

- The event-study rows do not contain independently verified `event_timestamp_utc` values. Analysis anchors are feed timestamp proxies, not confirmed event times.
- Several stories on the same feed date share exactly the same 07:00 UTC anchor and therefore receive identical reaction-window metrics. They are not independent reaction observations.
- In the original run, the reported 24-hour BTC returns are +8.635% for the Aug 19 anchor, +9.321% for the shared Aug 20 anchor, and +1.311% for the shared Aug 21 anchor. These are descriptive market returns from selected hourly candles, not estimates of any article's causal effect.
- The original Aug 20 entries are grouped in overlap cluster `OVERLAP-003` (9 records); Aug 21 entries are grouped in `OVERLAP-004` (5 records). Treat shared windows as dependent evidence, not multiple independent confirmations.
- The event-study status is `COMPLETED`, but the report states that no confounder controls or formal counterfactual are applied.

## Conservative interpretation

The Treasury buyback announcement, SEC crypto-policy developments, political comments about crypto legislation, ETF flows, and derivatives liquidations remain candidate explanations to investigate independently. These artifacts do not establish which event initiated the move. News coverage describing a rally after the fact cannot prove that the news caused the rally, and liquidations may be an amplifier rather than the initiating catalyst.

**Causal attribution for every event remains `NOT_ESTABLISHED`.** Do not train or evaluate a causal model by treating headline rows or overlapping windows as independent causal samples.

## Required next steps

1. Recover the exact 55-row target referenced by issue #61 and reconcile it against both the 56-row and 53-row artifacts. Preserve stable row IDs and explain additions, removals, and date-distribution changes.
2. Resolve Google News wrapper links to publisher-original URLs and preserve both URLs plus redirect-resolution status.
3. Independently corroborate publication timestamps and distinguish publication time from event/effective time. Feed timestamps alone are insufficient.
4. Cluster syndications and semantically related coverage into real-world event clusters, not just exact/near-exact headlines.
5. For each candidate event, record independent evidence, mechanism, prior anticipation, contemporaneous competing events, benchmark behavior, and uncertainty before changing `NOT_ESTABLISHED`.

## Reproducibility note

Both ZIPs were downloaded from their corresponding GitHub Actions artifact endpoints and inspected as four-file archives. Counts above come from the archived JSON reports, not inferred from workflow status.
