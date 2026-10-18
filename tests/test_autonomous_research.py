import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from autonomous_research import ResearchError, analyze, collect_context, fetch_candles, utc_date, run

def candle(ts, op, close, vol=10):
    return {"timestamp":ts,"open":op,"high":max(op,close),"low":min(op,close),"close":close,"volume":vol}

class Response:
    status=200
    def __init__(self,payload): self.payload=json.dumps(payload).encode()
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self): return self.payload

class AutonomousResearchTests(unittest.TestCase):
    def test_end_date_is_inclusive_utc(self):
        start=utc_date("2025-01-01"); end=utc_date("2025-01-01",True)
        self.assertEqual(start.tzinfo,timezone.utc)
        self.assertEqual((end-start).total_seconds(),86400)

    def test_analysis_and_benchmark(self):
        rows=[candle("2025-01-01T00:00:00Z",100,105),candle("2025-01-01T01:00:00Z",105,110)]
        btc=[candle("2025-01-01T00:00:00Z",100,102),candle("2025-01-01T01:00:00Z",102,104)]
        result=analyze(rows,btc)
        self.assertAlmostEqual(result["return_pct"],10)
        self.assertAlmostEqual(result["btc_return_pct"],4)
        self.assertAlmostEqual(result["relative_return_pct"],6)
        self.assertEqual(result["direction"],"UP")

    def test_fetch_parses_public_candles(self):
        payload=[[1735689600000,"100","110","90","105","12.5",0,0,0,0,0,0]]
        def opener(request,timeout=15):
            self.assertIn("symbol=SOLUSDT",request.full_url)
            return Response(payload)
        result=fetch_candles("sol",datetime(2025,1,1,tzinfo=timezone.utc),datetime(2025,1,2,tzinfo=timezone.utc),opener=opener)
        self.assertEqual(result["symbol"],"SOLUSDT")
        self.assertEqual(result["candles"][0]["close"],105)

    def test_provider_error_is_explicit(self):
        def opener(request,timeout=15): return Response({"code":-1121,"msg":"Invalid symbol."})
        with self.assertRaises(ResearchError):
            fetch_candles("bad",datetime(2025,1,1,tzinfo=timezone.utc),datetime(2025,1,2,tzinfo=timezone.utc),opener=opener)

    def test_context_search_is_scoped_to_ticker_and_requested_dates(self):
        urls=[]
        def feed(url,*args,**kwargs):
            urls.append(url)
            return {"records":[]}
        result=collect_context("SOL",utc_date("2025-01-01"),utc_date("2025-01-08"),feed_collector=feed)
        news=[url for url in urls if "news.google.com/rss/search" in url]
        self.assertEqual(len(news),1)
        query=parse_qs(urlparse(news[0]).query)["q"][0]
        self.assertIn('"SOL" crypto',query)
        self.assertIn("after:2025-01-01",query)
        self.assertIn("before:2025-01-08",query)
        self.assertEqual(result["entries"],[])
    def test_end_to_end_writes_report_and_unreviewed_case(self):
        start=datetime(2025,1,1,tzinfo=timezone.utc); end=datetime(2025,1,2,tzinfo=timezone.utc)
        market={"provider":"mock","symbol":"SOLUSDT","interval":"1h","retrieved_at":"2025-01-02T00:00:00Z",
          "candles":[candle("2025-01-01T00:00:00Z",100,101),candle("2025-01-01T01:00:00Z",101,110)]}
        def fetch(symbol,s,e,interval):
            if symbol=="BTC": raise ResearchError("benchmark offline")
            return market
        def feed(*args,**kwargs): raise OSError("offline")
        with tempfile.TemporaryDirectory() as directory:
            report=run("SOL",start,end,output_dir=Path(directory)/"reports",cases_path=Path(directory)/"cases.json",
                market_fetcher=fetch,feed_collector=feed)
            self.assertTrue(Path(report["output_markdown"]).exists())
            self.assertTrue(Path(report["output_json"]).exists())
            self.assertEqual(report["historical_case"]["review_status"],"DRAFT")
            self.assertEqual(report["historical_case"]["verification_status"],"UNVERIFIED")
            self.assertEqual(report["prediction_signal"]["status"],"INSUFFICIENT_DATA")
            self.assertEqual(report["prediction_evaluation"]["status"],"INSUFFICIENT_DATA")
            store=json.loads((Path(directory)/"cases.json").read_text())
            self.assertEqual(len(store["cases"]),1)
            self.assertIn("does not prove causes",report["markdown"])

if __name__=="__main__": unittest.main()
