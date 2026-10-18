"""Event-study helpers. Temporal coincidence is not causal proof."""
from datetime import datetime, timedelta, timezone
import re
import unicodedata


def parse_utc(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp.astimezone(timezone.utc) if stamp.tzinfo else None


def _candles(rows):
    out = []
    for row in rows or []:
        stamp = parse_utc(row.get("timestamp"))
        try:
            close, high, low, volume = (float(row[k]) for k in ("close", "high", "low", "volume"))
        except (KeyError, TypeError, ValueError):
            continue
        if stamp and close > 0 and high > 0 and low > 0 and volume >= 0:
            out.append({"dt": stamp, "timestamp": stamp.isoformat().replace("+00:00", "Z"),
                        "close": close, "high": high, "low": low, "volume": volume})
    return sorted(out, key=lambda x: x["dt"])


def _reaction(rows, anchor, hours, benchmark):
    start = next((i for i, x in enumerate(rows) if x["dt"] >= anchor), None)
    if start is None:
        return {"status": "OUTSIDE_MARKET_DATA"}
    end = next((i for i, x in enumerate(rows) if x["dt"] >= anchor + timedelta(hours=hours)), None)
    if end is None:
        return {"status": "INSUFFICIENT_FORWARD_COVERAGE"}
    sample = rows[start:end + 1]
    first, last = sample[0], sample[-1]
    ret = (last["close"] / first["close"] - 1) * 100
    baseline = [x["volume"] for x in rows[max(0, start - 24):start]]
    vol = None
    if baseline and sum(baseline) > 0:
        vol = ((sum(x["volume"] for x in sample) / len(sample)) /
               (sum(baseline) / len(baseline)) - 1) * 100
    changes = [(b["close"] / a["close"] - 1) * 100 for a, b in zip(sample, sample[1:])]
    result = {"status": "COMPUTED", "horizon_hours": hours,
              "anchor_candle": first["timestamp"], "end_candle": last["timestamp"],
              "return_pct": round(ret, 6),
              "volume_change_pct_vs_prior_24_candles": round(vol, 6) if vol is not None else None,
              "realized_volatility_pct_rss": round(sum(x*x for x in changes) ** .5, 6),
              "max_runup_pct": round((max(x["high"] for x in sample) / first["close"] - 1) * 100, 6),
              "max_drawdown_pct": round((min(x["low"] for x in sample) / first["close"] - 1) * 100, 6),
              "candle_count": len(sample)}
    if benchmark:
        b0, b1 = benchmark.get(first["timestamp"]), benchmark.get(last["timestamp"])
        if b0 and b1 and b0 > 0:
            result["benchmark_return_pct"] = round((b1 / b0 - 1) * 100, 6)
            result["relative_return_pct"] = round(ret - (b1 / b0 - 1) * 100, 6)
    return result


def _normalized_title(title):
    text = unicodedata.normalize("NFKC", str(title or "")).casefold()
    return " ".join("".join(ch if ch.isalnum() else " " for ch in text).split())


def deduplicate_events(events, similarity_threshold=0.82, max_age_hours=72):
    """Group syndicated headlines without discarding source provenance."""
    if not 0 < similarity_threshold <= 1 or max_age_hours < 0:
        raise ValueError("invalid deduplication threshold or age window")
    groups = []
    ordered = sorted((dict(e) for e in (events or [])),
        key=lambda e: (parse_utc(e.get("published_at")) or datetime.max.replace(tzinfo=timezone.utc),
                       _normalized_title(e.get("title")), str(e.get("url") or "")))
    for event in ordered:
        title, published = _normalized_title(event.get("title")), parse_utc(event.get("published_at"))
        match = None
        if title:
            for group in groups:
                prior = group["title"]
                times = [parse_utc(x.get("published_at")) for x in group["sources"]]
                known = [t for t in times if t]
                within = not published or not known or min(abs((published-t).total_seconds()) for t in known) <= max_age_hours*3600
                a, b = set(title.split()), set(prior.split())
                overlap = len(a & b) / len(a | b) if a and b else 0
                near = len(a) >= 6 and len(b) >= 6 and overlap >= similarity_threshold
                if within and (title == prior or near):
                    match = group
                    break
        if match is None:
            groups.append({"title": title, "representative": event, "sources": [event]})
        else:
            match["sources"].append(event)
    result = []
    for group in groups:
        item = dict(group["representative"])
        item["duplicate_count"] = len(group["sources"])
        item["deduplication"] = "DUPLICATE_GROUP" if len(group["sources"]) > 1 else "UNIQUE_HEADLINE"
        item["duplicate_sources"] = [{"title": x.get("title"), "publisher": x.get("publisher"),
            "url": x.get("url"), "published_at": x.get("published_at"),
            "source_id": x.get("source_id"), "evidence_id": x.get("evidence_id")} for x in group["sources"]]
        result.append(item)
    return result


def analyze_event_reactions(events, candles, benchmark_candles=None, windows_hours=(1, 6, 24)):
    """Measure predeclared post-event windows, preserving timestamp uncertainty."""
    windows = tuple(windows_hours)
    if not windows or any(not isinstance(n, int) or isinstance(n, bool) or n <= 0 for n in windows):
        raise ValueError("windows_hours must contain positive integers")
    market = _candles(candles)
    benchmark = {x["timestamp"]: x["close"] for x in _candles(benchmark_candles)}
    deduplicated = deduplicate_events(events)
    timeline = []
    for event in deduplicated:
        published = parse_utc(event.get("published_at"))
        actual = parse_utc(event.get("event_timestamp"))
        anchor = actual or published
        reactions = ({str(n) + "h": _reaction(market, anchor, n, benchmark) for n in windows}
                     if anchor else {str(n) + "h": {"status": "UNAVAILABLE_TIMESTAMP"} for n in windows})
        match_quality = event.get("match_quality", "UNKNOWN")
        has_observed_reaction = any(x.get("status") == "COMPUTED" and abs(x.get("return_pct", 0)) >= 2 for x in reactions.values())
        timeline.append({
            "title": event.get("title"), "publisher": event.get("publisher"), "url": event.get("url"),
            "match_quality": match_quality,
            "weak_match_warning": ("Ticker appears only outside the headline; verify asset relevance." if match_quality == "WEAK" else
                                   "Asset-match quality was not supplied; verify that the story concerns this asset." if match_quality == "UNKNOWN" else None),
            "duplicate_count": event.get("duplicate_count", 1),
            "deduplication": event.get("deduplication", "UNIQUE_HEADLINE"),
            "duplicate_sources": event.get("duplicate_sources", []),
            "published_at_utc": published.isoformat().replace("+00:00", "Z") if published else None,
            "event_timestamp_utc": actual.isoformat().replace("+00:00", "Z") if actual else None,
            "analysis_anchor_utc": anchor.isoformat().replace("+00:00", "Z") if anchor else None,
            "timestamp_source": "explicit_event_timestamp" if actual else "publication_timestamp_proxy" if published else "unavailable",
            "timestamp_confidence": "MEDIUM" if actual else "LOW" if published else "NONE",
            "asset_topic_tags": event.get("asset_topic_tags", []),
            "verification_status": event.get("verification_status", "UNVERIFIED"),
            "source_id": event.get("source_id"), "evidence_id": event.get("evidence_id"),
            "reactions": reactions,
            "assessment": "observed_reaction" if has_observed_reaction else "inconclusive",
            "assessment_note": ("A descriptive return threshold was crossed; this is not evidence of causation." if has_observed_reaction else
                                "No reaction crossed the descriptive threshold, or available data were insufficient."),
            "alternative_explanations": [
                "Broad-market or BTC movement during the same window",
                "Other contemporaneous news, macroeconomic data, or policy announcements",
                "Liquidity, derivatives positioning, liquidations, or technical market structure",
                "The event may have been anticipated before publication, or the timestamp may be a poor proxy",
                "Coincidence, noisy ticker matching, or incomplete news coverage"]
        })
    # Events whose reaction windows overlap are not independent observations.
    # Keep each headline auditable, but make shared measurement windows explicit.
    for item in timeline:
        anchor = parse_utc(item.get("analysis_anchor_utc"))
        overlaps = {}
        for hours in windows:
            count = 0
            if anchor:
                for other in timeline:
                    if other is item:
                        continue
                    other_anchor = parse_utc(other.get("analysis_anchor_utc"))
                    if other_anchor and abs((other_anchor - anchor).total_seconds()) < hours * 3600:
                        count += 1
            overlaps[f"{hours}h"] = count
        item["overlapping_event_count_by_window"] = overlaps
        item["shared_reaction_window_warning"] = any(value > 0 for value in overlaps.values())
        item["shared_reaction_window_note"] = (
            "One or more other event timestamps fall inside these reaction windows; their returns overlap and must not be counted as independent evidence."
            if item["shared_reaction_window_warning"] else None
        )
    timeline.sort(key=lambda x: x["analysis_anchor_utc"] or "9999")
    return {"methodology_version": "1.1.0", "timezone": "UTC",
            "status": "COMPLETED" if market else "INSUFFICIENT_MARKET_DATA",
            "windows_hours": list(windows), "raw_event_count": len(events or []),
            "deduplicated_event_count": len(timeline), "timeline": timeline,
            "methodology_notes": [
                "Publication timestamp is a proxy unless an event timestamp is explicitly provided.",
                "Window starts at the first candle at or after the timestamp and ends at the first candle at or after the horizon.",
                "Volume comparison uses up to 24 preceding candles.",
                "No confounder controls are applied; reaction metrics are descriptive, not causal attribution.",
                "Alternative explanations are prompts for review, not verified findings.",
                "Never use information published after a prediction cutoff as a prediction feature."]}
