# BTC historical research artifact audit — 2026-08-19 to 2026-08-21

## Scope and provenance

- Artifact: `crypto-research-BTC-2026-07-01-2026-09-21.zip`
- GitHub Actions run: [39170183626](https://github.com/Osleyder1985/crypto-due-diligence/actions/runs/39170183626), commit `3e35b654ea55b1b7ed74ad56919642538331fd59`.
- Artifact ID: `12152301230`; created 2026-10-18 21:58:56 UTC; 98,175 bytes; expires 2026-11-17.
- Contents: autonomous-research JSON/Markdown and event-study JSON/Markdown.
- The artifact predates PR #63's missing-artifact fail-closed check. Its successful run alone is not proof of report completeness.

## Findings from the actual JSON

### Dataset and source provenance

- Standalone event study reports `raw_event_count=56` and `deduplicated_event_count=56`; autonomous contextual evidence also contains 56 entries.
- Only **15** of those entries have feed-reported dates from 2026-08-19 through 2026-08-21. This does not match the 55 records described in issue #61, so the artifact's search result set is not demonstrably the same dataset as that issue's 55-entry audit target.
- All 56 entries have `publication_timestamp_quality=FEED_REPORTED_PUBLICATION`, `publication_timestamp_field=pubDate`, and `verification_status=UNVERIFIED`.
- All 56 URLs use the `news.google.com` RSS-article wrapper, not a verified publisher-original URL. Publisher labels exist as feed metadata, but source-origin verification and direct article timestamps are not established.
- All 56 records are marked `UNIQUE_HEADLINE`; headline-level deduplication did not merge any entries. This does not establish that they represent 56 independent real-world events.
- All 56 have `match_quality=STRONG`, but ticker matching is not independent event verification.

### Event-time and price-reaction limitations

- The event-study rows have no independently verified `event_timestamp_utc`. The analysis anchors are feed timestamp proxies, not confirmed event times.
- Several stories on the same feed date share exactly the same 07:00 UTC anchor and therefore receive identical reaction-window metrics. They are not independent reaction observations.
- For the Aug 19 anchor, the reported 24-hour BTC return is +8.635%; for the shared Aug 20 anchor, +9.321%; for the shared Aug 21 anchor, +1.311%. These are descriptive market returns from the selected hourly candles, not estimates of the causal effect of any individual article.
- The Aug 20 entries are grouped in overlap cluster `OVERLAP-003` (9 records); Aug 21 entries are grouped in `OVERLAP-004` (5 records). Treat each shared window as dependent evidence, not multiple independent confirmations.
- The report's event-study status is `COMPLETED`, but the report itself states that no confounder controls or formal counterfactual are applied.

## Conservative interpretation

The Treasury buyback announcement, SEC crypto-policy developments, political comments about crypto legislation, ETF flows, and derivatives liquidations remain candidate explanations to investigate independently. This artifact does not establish which event initiated the move. News coverage that describes a rally after the fact cannot prove that the news caused the rally, and liquidations may be an amplifier rather than the initiating catalyst.

**Causal attribution for every event remains `NOT_ESTABLISHED`.** Do not train or evaluate a causal model by treating the 56 headline rows, or overlapping windows, as 56 independent causal samples.

## Required next steps

1. Reconcile issue #61's 55-entry target with this artifact's 56-entry full-period feed set and identify the exact 55 target rows.
2. Resolve Google News wrapper links to publisher-original URLs and preserve both URLs plus redirect resolution status.
3. Independently corroborate publication timestamps and distinguish publication time from event/effective time. The current feed timestamp alone is insufficient.
4. Cluster syndications and semantically related coverage into real-world event clusters, not just exact/near-exact headlines.
5. For each candidate event, record independent evidence, mechanism, prior anticipation, contemporaneous competing events, benchmark behavior, and uncertainty before changing `NOT_ESTABLISHED`.

## Reproducibility note

The ZIP was recovered directly through the GitHub Actions artifact API and inspected as a four-file archive. The counts and metrics above are from the archived JSON reports, not inferred from the workflow's green status.
