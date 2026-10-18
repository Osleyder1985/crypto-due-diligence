"""Research a crypto ticker over a UTC date range; preserve provenance and uncertainty."""
import argparse
import json
import re
import sys
import urllib.parse
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from uuid import uuid4

from evidence_collector import collect_feed, CollectionError
from historical_learning import load_cases, save_case, find_similar_cases, summarize_outcomes

FEEDS = [
    {"name": "Cointelegraph", "url": "https://cointelegraph.com/rss"},
    {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/"},
    {"name": "CryptoSlate", "url": "https://cryptoslate.com/feed/"},
]
INTERVALS = {"1m":60000,"5m":300000,"15m":900000,"30m":1800000,"1h":3600000,
             "4h":14400000,"1d":86400000}

class ResearchError(RuntimeError):
    pass

def utc_date(value, end_exclusive=False):
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("dates must use YYYY-MM-DD")
    if end_exclusive:
        parsed += timedelta(days=1)
    return datetime.combine(parsed, time.min, tzinfo=timezone.utc)

def fetch_candles(symbol, start, end, interval="1h", opener=urlopen):
    symbol = symbol.upper().strip()
    if not re.fullmatch(r"[A-Z0-9]{2,20}", symbol):
        raise ResearchError("ticker must contain 2-20 letters or digits")
    if interval not in INTERVALS or start >= end:
        raise ResearchError("invalid interval or date range")
    start_ms, end_ms = int(start.timestamp()*1000), int(end.timestamp()*1000)-1
    candles = []
    cursor = start_ms
    pages = 0
    while cursor <= end_ms:
        if pages >= 100:
            raise ResearchError("candle retrieval exceeded 100 pages; shorten the date range or use a larger interval")
        url = "https://api.binance.com/api/v3/klines?" + urllib.parse.urlencode({
            "symbol":symbol+"USDT","interval":interval,"startTime":cursor,"endTime":end_ms,"limit":1000})
        request = Request(url, headers={"User-Agent":"CryptoDueDiligence/1.0","Accept":"application/json"})
        try:
            with opener(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            raise ResearchError(f"market data request failed: {exc}") from exc
        pages += 1
        if not isinstance(payload, list):
            reason = payload.get("msg", "provider returned an invalid response") if isinstance(payload, dict) else "invalid response"
            raise ResearchError(reason)
        if not payload:
            break
        for row in payload:
            if not isinstance(row, list) or len(row) < 6:
                raise ResearchError("provider returned malformed candle data")
            stamp = int(row[0])
            if start_ms <= stamp < int(end.timestamp()*1000):
                candles.append({"timestamp":datetime.fromtimestamp(stamp/1000,timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),
                    "open":float(row[1]),"high":float(row[2]),"low":float(row[3]),"close":float(row[4]),"volume":float(row[5])})
        last_stamp = int(payload[-1][0])
        if last_stamp >= end_ms or len(payload) < 1000:
            break
        if last_stamp + 1 <= cursor:
            raise ResearchError("market-data pagination did not advance")
        cursor = last_stamp + 1
    if not candles:
        raise ResearchError(f"no {symbol}USDT candles for requested period")
    return {"provider":"Binance public spot API","symbol":symbol+"USDT","interval":interval,
            "retrieved_at":datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),"candles":candles}

def analyze(candles, benchmark=None):
    candles = sorted(candles, key=lambda x:x["timestamp"])
    first,last = candles[0],candles[-1]
    if first["open"] <= 0:
        raise ResearchError("first open price must be positive")
    change = (last["close"]/first["open"]-1)*100
    highs=[x["high"] for x in candles]; lows=[x["low"] for x in candles]
    deltas=[]
    for a,b in zip(candles,candles[1:]):
        dt1=datetime.fromisoformat(a["timestamp"].replace("Z","+00:00"))
        dt2=datetime.fromisoformat(b["timestamp"].replace("Z","+00:00"))
        deltas.append(int((dt2-dt1).total_seconds()*1000))
    expected=min((x for x in deltas if x>0),default=None)
    gaps=sum(x>expected*1.5 for x in deltas) if expected else 0
    result={"candle_count":len(candles),"first_candle":first["timestamp"],"last_candle":last["timestamp"],
      "start_price":first["open"],"end_price":last["close"],"return_pct":change,
      "direction":"UP" if change>0 else "DOWN" if change<0 else "FLAT","high":max(highs),"low":min(lows),
      "total_volume_base_asset":sum(x["volume"] for x in candles),"observed_gap_count":gaps,
      "data_quality_notes":[f"{gaps} interval gap(s) detected"] if gaps else []}
    if benchmark:
        bytime={x["timestamp"]:x for x in benchmark}
        matches=[(x,bytime[x["timestamp"]]) for x in candles if x["timestamp"] in bytime]
        if len(matches)>=2 and matches[0][1]["open"]>0:
            br=(matches[-1][1]["close"]/matches[0][1]["open"]-1)*100
            result["btc_return_pct"]=br
            result["relative_return_pct"]=change-br
    return result

def collect_context(symbol,start,end,feed_collector=collect_feed):
    entries=[]; errors=[]
    for i,feed in enumerate(FEEDS):
        try:
            capture=feed_collector(feed["url"],feed["name"],f"src_{i}_{uuid4().hex[:8]}",f"ev_{i}_{uuid4().hex[:8]}")
            records=capture.get("records",[])
            for j in range(0,len(records)-1,2):
                source,evidence=records[j],records[j+1]
                if source.get("record_type")!="Source" or evidence.get("record_type")!="Evidence": continue
                s,e=source["record"],evidence["record"]; published=s.get("published_at")
                try: when=datetime.fromisoformat(published.replace("Z","+00:00")) if published else None
                except ValueError: when=None
                text=(s.get("title") or "")+" "+(e.get("excerpt_or_locator") or "")
                if when and start<=when<end and re.search(rf"(?<![A-Z0-9]){re.escape(symbol)}(?![A-Z0-9])",text.upper()):
                    entries.append({"title":s.get("title"),"url":s.get("url"),"publisher":s.get("publisher"),
                      "published_at":published,"excerpt":(e.get("excerpt_or_locator") or "")[:1000],
                      "verification_status":e.get("verification_status","UNVERIFIED"),
                      "source_id":s.get("source_id"),"evidence_id":e.get("evidence_id")})
        except (CollectionError,OSError,ValueError,KeyError,TypeError) as exc:
            errors.append({"feed":feed["name"],"error":str(exc)})
    return {"entries":entries,"feed_errors":errors,"interpretation":"Feed matches are leads, not proof of causation."}

def run(symbol,start,end,interval="1h",output_dir="research_runs",cases_path="data/historical_cases.json",
        market_fetcher=fetch_candles,feed_collector=collect_feed):
    symbol=symbol.upper().strip()
    market=market_fetcher(symbol,start,end,interval)
    candles=market["candles"]
    benchmark=None; benchmark_error=None
    if symbol!="BTC":
        try: benchmark=market_fetcher("BTC",start,end,interval)["candles"]
        except ResearchError as exc: benchmark_error=str(exc)
    stats=analyze(candles,benchmark)
    if benchmark_error: stats["data_quality_notes"].append("BTC benchmark unavailable: "+benchmark_error)
    context=collect_context(symbol,start,end,feed_collector)
    existing=load_cases(cases_path)
    factors=[]
    if abs(stats["return_pct"])>=5: factors.append("large_period_return")
    if stats["observed_gap_count"]: factors.append("market_data_gaps")
    if context["entries"]: factors.append("ticker_mentioned_in_feed")
    case={"schema_version":"1.0.0","case_id":"case-"+uuid4().hex,"asset_id":"binance:spot:"+symbol+"USDT",
      "asset_symbol":symbol,"event_type":"PRICE_MOVEMENT_RESEARCH","detected_at":candles[-1]["timestamp"],
      "window_minutes":max(1,int((end-start).total_seconds()//60)),"movement_direction":stats["direction"],
      "return_pct":stats["return_pct"],"candidate_factors":factors,
      "evidence_ids":sorted({x["evidence_id"] for x in context["entries"] if x.get("evidence_id")}),
      "source_case_ids":[],"outcome_label":"UNKNOWN","review_status":"DRAFT","verification_status":"UNVERIFIED",
      "reviewer":None,"reviewed_at":None,"methodology_version":"1.0.0",
      "notes":"Automated draft; review required before inclusion in learning summaries."}
    precedents=find_similar_cases(case,existing,limit=10)
    save_case(cases_path,case)
    # Prediction is optional: short periods still produce the market/evidence report.
    try:
        from prediction_evaluation import predict_next, walk_forward_evaluate
        prediction_signal = predict_next(candles, lookback=24, horizon=6, min_train=100, neighbors=15)
    except (ImportError, ValueError, KeyError, TypeError) as exc:
        prediction_signal = {"status":"INSUFFICIENT_DATA", "reason":str(exc)}
    try:
        from prediction_evaluation import walk_forward_evaluate
        evaluation_full = walk_forward_evaluate(candles, lookback=24, horizon=6, min_train=100, neighbors=15)
        prediction_evaluation = {"status":"COMPLETED", "prediction_count":evaluation_full["prediction_count"],
            "configuration":evaluation_full["configuration"], "metrics":evaluation_full["metrics"],
            "methodology":evaluation_full["methodology"]}
    except (ImportError, ValueError, KeyError, TypeError) as exc:
        prediction_evaluation = {"status":"INSUFFICIENT_DATA", "reason":str(exc)}
    report={"report_version":"1.1.0","run_id":"run-"+uuid4().hex,"asset_symbol":symbol,
      "period":{"start":start.isoformat().replace("+00:00","Z"),"end_inclusive":(end-timedelta(milliseconds=1)).isoformat().replace("+00:00","Z")},
      "generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),
      "market_data":{k:v for k,v in market.items() if k!="candles"},"market_analysis":stats,"contextual_evidence":context,
      "historical_summary":summarize_outcomes(existing),"similar_cases":precedents,"historical_case":case,
      "prediction_signal":prediction_signal,"prediction_evaluation":prediction_evaluation,
      "limitations":["RSS coverage is incomplete; only literal ticker matches are collected.",
       "Collected evidence remains unverified; timing does not establish causality.",
       "Draft cases are excluded from learning summaries until reviewed and verified.",
       "The experimental direction signal is not a calibrated probability or guarantee.",
       "Prediction metrics on this requested period do not guarantee future performance."]}

    lines=[f"# Research report: {symbol}","","## Period",report["period"]["start"]+" — "+report["period"]["end_inclusive"],
      "","## Observed movement",f"- Direction: {stats['direction']}",f"- Return: {stats['return_pct']:.4f}%",
      f"- First open / last close: {stats['start_price']} / {stats['end_price']}",f"- High / low: {stats['high']} / {stats['low']}",
      f"- Candles: {stats['candle_count']}; volume: {stats['total_volume_base_asset']}",f"- Gap count: {stats['observed_gap_count']}"]
    if "btc_return_pct" in stats: lines += [f"- BTC return: {stats['btc_return_pct']:.4f}%",f"- Relative return: {stats['relative_return_pct']:.4f}%"]
    lines += ["","## Evidence leads",""]
    if context["entries"]:
        for item in context["entries"]: lines.append(f"- {item['title']} — {item['publisher']} — {item['published_at']} — {item['url']} — UNVERIFIED")
    else: lines.append("No matching feed entries found. This does not establish that no catalyst existed.")
    lines += ["","## Historical precedents",f"Eligible reviewed cases in memory: {report['historical_summary']['eligible_case_count']}."]
    lines += [f"- {x['case_id']}: score {x['similarity_score']}, label {x['outcome_label']}" for x in precedents]
    lines += ["","## Interpretation","The report describes price/volume behavior and collects contextual leads. It does not prove causes or predict future direction. Human review and verified outcomes are required before a case contributes to learning.",""]
    report["markdown"]="\n".join(lines)
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    stem=f"{symbol}_{start.date()}_{(end-timedelta(days=1)).date()}"
    jp,mp=out/(stem+".json"),out/(stem+".md")
    jp.write_text(json.dumps({k:v for k,v in report.items() if k!="markdown"},indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    mp.write_text(report["markdown"],encoding="utf-8")
    report["output_json"],report["output_markdown"]=str(jp),str(mp)
    return report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("symbol"); p.add_argument("start_date"); p.add_argument("end_date")
    p.add_argument("--interval",choices=sorted(INTERVALS),default="1h")
    p.add_argument("--output-dir",default="research_runs"); p.add_argument("--cases-path",default="data/historical_cases.json")
    a=p.parse_args(argv)
    try:
        result=run(a.symbol,utc_date(a.start_date),utc_date(a.end_date,True),a.interval,a.output_dir,a.cases_path)
    except (ResearchError,CollectionError,ValueError,OSError) as exc:
        print(json.dumps({"ok":False,"error":str(exc)},indent=2),file=sys.stderr); return 1
    print(json.dumps({"ok":True,"symbol":result["asset_symbol"],"return_pct":result["market_analysis"]["return_pct"],
      "direction":result["market_analysis"]["direction"],"matching_evidence":len(result["contextual_evidence"]["entries"]),
      "report":result["output_markdown"],"case_id":result["historical_case"]["case_id"],
      "warning":"No causal attribution or price forecast is produced."},indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
