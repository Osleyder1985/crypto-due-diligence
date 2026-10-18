"""Event-study helpers. Temporal coincidence is not causal proof."""
from datetime import datetime, timedelta, timezone


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


def analyze_event_reactions(events, candles, benchmark_candles=None, windows_hours=(1, 6, 24)):
    """Measure predeclared post-event windows, preserving timestamp uncertainty."""
    windows = tuple(windows_hours)
    if not windows or any(not isinstance(n, int) or isinstance(n, bool) or n <= 0 for n in windows):
        raise ValueError("windows_hours must contain positive integers")
    market = _candles(candles)
    benchmark = {x["timestamp"]: x["close"] for x in _candles(benchmark_candles)}
    timeline = []
    for event in events or []:
        published = parse_utc(event.get("published_at"))
        actual = parse_utc(event.get("event_timestamp"))
        anchor = actual or published
        reactions = ({str(n) + "h": _reaction(market, anchor, n, benchmark) for n in windows}
                     if anchor else {str(n) + "h": {"status": "UNAVAILABLE_TIMESTAMP"} for n in windows})
        timeline.append({
            "title": event.get("title"), "publisher": event.get("publisher"), "url": event.get("url"),
            "published_at_utc": published.isoformat().replace("+00:00", "Z") if published else None,
            "event_timestamp_utc": actual.isoformat().replace("+00:00", "Z") if actual else None,
            "analysis_anchor_utc": anchor.isoformat().replace("+00:00", "Z") if anchor else None,
            "timestamp_source": "explicit_event_timestamp" if actual else "publication_timestamp_proxy" if published else "unavailable",
            "timestamp_confidence": "MEDIUM" if actual else "LOW" if published else "NONE",
            "asset_topic_tags": event.get("asset_topic_tags", []),
            "verification_status": event.get("verification_status", "UNVERIFIED"),
            "source_id": event.get("source_id"), "evidence_id": event.get("evidence_id"),
            "reactions": reactions,
            "assessment": "plausible_hypothesis" if any(x.get("status") == "COMPUTED" and abs(x.get("return_pct", 0)) >= 2 for x in reactions.values()) else "inconclusive",
            "assessment_note": "A price reaction after publication does not prove that the event caused it."
        })
    timeline.sort(key=lambda x: x["analysis_anchor_utc"] or "9999")
    return {"methodology_version": "1.0.0", "timezone": "UTC",
            "status": "COMPLETED" if market else "INSUFFICIENT_MARKET_DATA",
            "windows_hours": list(windows), "timeline": timeline,
            "methodology_notes": [
                "Publication timestamp is a proxy unless an event timestamp is explicitly provided.",
                "Window starts at the first candle at or after the timestamp and ends at the first candle at or after the horizon.",
                "Volume comparison uses up to 24 preceding candles.",
                "No confounder controls are applied; reaction metrics are descriptive, not causal attribution.",
                "Never use information published after a prediction cutoff as a prediction feature."]}
