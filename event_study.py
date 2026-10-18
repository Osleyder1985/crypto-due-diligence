"""Build an event timeline and descriptive price-reaction report for a crypto period."""
import argparse
import json
from pathlib import Path

from autonomous_research import ResearchError, collect_context, fetch_candles, utc_date
from event_attribution import analyze_event_reactions


def run_event_study(symbol, start, end, interval="1h", output_dir="event_studies"):
    symbol = symbol.upper().strip()
    market = fetch_candles(symbol, start, end, interval)
    benchmark = None
    benchmark_note = None
    if symbol != "BTC":
        try:
            benchmark = fetch_candles("BTC", start, end, interval)["candles"]
        except ResearchError as exc:
            benchmark_note = str(exc)
    context = collect_context(symbol, start, end)
    study = analyze_event_reactions(context["entries"], market["candles"], benchmark)
    report = {
        "report_version": "1.0.0", "asset_symbol": symbol,
        "period": {"start": start.isoformat().replace("+00:00", "Z"),
                   "end_exclusive": end.isoformat().replace("+00:00", "Z")},
        "market_data": {key: value for key, value in market.items() if key != "candles"},
        "event_discovery": {"entry_count": len(context["entries"]),
                            "feed_errors": context["feed_errors"],
                            "interpretation": context["interpretation"]},
        "benchmark_status": "AVAILABLE" if benchmark is not None or symbol == "BTC" else "UNAVAILABLE",
        "benchmark_note": benchmark_note,
        "event_study": study,
        "limitations": [
            "RSS search is incomplete and ticker matches may be false positives.",
            "Publication timestamps may differ from the actual event time.",
            "A post-publication price reaction does not demonstrate that a news item caused it.",
            "No formal counterfactual or confounder controls are applied.",
            "News discovered after the period or prediction cutoff must not be used as a contemporaneous driver or prediction feature."
        ]
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = f"{symbol}_{start.date()}_{(end.date()).isoformat()}_event-study"
    json_path = out / (stem + ".json")
    md_path = out / (stem + ".md")
    lines = [f"# Event study: {symbol}", "",
             f"Period (UTC): {report['period']['start']} to {report['period']['end_exclusive']} (end exclusive)", "",
             "## Method", "Reaction windows are measured from the first candle at or after the timestamp, for 1h, 6h and 24h. Publication time is only a proxy when an explicit event timestamp is absent.", "",
             "## Event timeline", ""]
    if not study["timeline"]:
        lines.append("No matching timestamped news leads were found. This does not prove that no relevant event occurred.")
    for item in study["timeline"]:
        lines += [f"### {item.get('title') or '(untitled event)'}",
                  f"- Publisher: {item.get('publisher') or 'unknown'}",
                  f"- Published UTC: {item.get('published_at_utc') or 'unavailable'}",
                  f"- Timestamp basis/confidence: {item['timestamp_source']} / {item['timestamp_confidence']}",
                  f"- Source timestamp metadata: {item.get('publication_timestamp_quality', 'LEGACY_OR_UNKNOWN')} (field: {item.get('publication_timestamp_field') or 'unknown'}; raw: {item.get('publication_timestamp_raw') or 'unavailable'})",
                  f"- Temporal overlap cluster: {item.get('overlap_cluster_id') or 'none'} (size: {item.get('overlap_cluster_size', 0)}; not an economic-event classification)",
                  f"- Source: {item.get('url') or 'unavailable'}",
                  f"- Assessment: {item['assessment']} — {item['assessment_note']}"]
        if item.get("shared_reaction_window_warning"):
            counts = ", ".join(f"{window}: {count} other event(s)" for window, count in item["overlapping_event_count_by_window"].items() if count)
            lines.append(f"- OVERLAPPING WINDOWS: {counts}. {item['shared_reaction_window_note']}")
        for window, metric in item["reactions"].items():
            if metric["status"] == "COMPUTED":
                lines.append(f"- {window}: return {metric['return_pct']:.4f}%; volume change {metric['volume_change_pct_vs_prior_24_candles']}; realized volatility RSS {metric['realized_volatility_pct_rss']}; run-up {metric['max_runup_pct']}%; drawdown {metric['max_drawdown_pct']}%")
            else:
                lines.append(f"- {window}: {metric['status']}")
        lines.append("")
    lines += ["## Limitations", *[f"- {item}" for item in report["limitations"]], ""]
    report["markdown"] = "\n".join(lines)
    json_path.write_text(json.dumps({k: v for k, v in report.items() if k != "markdown"},
                                    indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(report["markdown"], encoding="utf-8")
    return {"report_json": str(json_path), "report_markdown": str(md_path),
            "event_count": len(study["timeline"]), "study": study}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbol")
    parser.add_argument("start_date")
    parser.add_argument("end_date")
    parser.add_argument("--interval", choices=["1m", "5m", "15m", "30m", "1h", "4h", "1d"], default="1h")
    parser.add_argument("--output-dir", default="event_studies")
    args = parser.parse_args(argv)
    try:
        result = run_event_study(args.symbol, utc_date(args.start_date),
                                 utc_date(args.end_date, end_exclusive=True),
                                 args.interval, args.output_dir)
    except (ResearchError, ValueError, OSError) as exc:
        parser.exit(1, f"event study failed: {exc}\n")
    print(json.dumps({key: value for key, value in result.items() if key != "study"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
