import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
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

    def test_http_451_falls_back_to_coinbase_and_normalizes_ohlcv(self):
        calls = []
        def opener(request, timeout=15):
            calls.append(request.full_url)
            if "api.binance.com" in request.full_url:
                from urllib.error import HTTPError
                raise HTTPError(request.full_url, 451, "Unavailable for legal reasons", {}, None)
            # Coinbase schema: [time, low, high, open, close, volume]
            return Response([[1735689600, "90", "110", "100", "105", "12.5"]])
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 2, tzinfo=timezone.utc)
        result = fetch_candles("btc", start, end, "1h", opener=opener)
        self.assertEqual(len(calls), 2)
        self.assertIn("symbol=BTCUSDT", calls[0])
        self.assertIn("products/BTC-USD/candles", calls[1])
        self.assertEqual(result["symbol"], "BTC-USD")
        self.assertIn("Coinbase", result["provider"])
        self.assertEqual(result["candles"][0]["open"], 100)
        self.assertEqual(result["candles"][0]["high"], 110)
        self.assertEqual(result["candles"][0]["low"], 90)
        self.assertEqual(result["candles"][0]["close"], 105)
        self.assertEqual(result["candles"][0]["volume"], 12.5)

    def test_coinbase_fallback_reports_unsupported_interval(self):
        from urllib.error import HTTPError
        def opener(request, timeout=15):
            raise HTTPError(request.full_url, 451, "Unavailable for legal reasons", {}, None)
        with self.assertRaisesRegex(ResearchError, "does not support interval 4h"):
            fetch_candles("btc", datetime(2025, 1, 1, tzinfo=timezone.utc),
                datetime(2025, 1, 2, tzinfo=timezone.utc), "4h", opener=opener)

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
    def test_context_preserves_timestamp_provenance_from_feed_source(self):
        calls = {"count": 0}
        def feed(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] > 1:
                return {"records": []}
            return {"records": [
                {"record_type": "Source", "record": {
                    "source_id": "src1", "source_type": "NEWS_MEDIA", "publisher": "Example",
                    "title": "BTC rises after announcement", "url": "https://example.test/story",
                    "published_at": "2025-01-01T12:00:00Z",
                    "notes": "original_published_value=Wed, 01 Jan 2025 12:00:00 GMT; timestamp_field=pubDate; timestamp_quality=FEED_REPORTED_PUBLICATION; normalized_publication_timestamp=2025-01-01T12:00:00Z"
                }},
                {"record_type": "Evidence", "record": {
                    "evidence_id": "ev1", "verification_status": "UNVERIFIED",
                    "excerpt_or_locator": "BTC announcement"
                }}
            ]}
        result=collect_context("BTC",utc_date("2025-01-01"),utc_date("2025-01-02"),feed_collector=feed)
        self.assertEqual(len(result["entries"]),1)
        entry=result["entries"][0]
        self.assertEqual(entry["publication_timestamp_raw"],"Wed, 01 Jan 2025 12:00:00 GMT")
        self.assertEqual(entry["publication_timestamp_field"],"pubDate")
        self.assertEqual(entry["publication_timestamp_quality"],"FEED_REPORTED_PUBLICATION")
        self.assertEqual(entry["normalized_publication_timestamp"],"2025-01-01T12:00:00Z")

    def test_prediction_memory_accumulates_across_research_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            memory_path=Path(directory)/"prediction-memory.json"
            cases_path=Path(directory)/"cases.json"
            def fetch(symbol,start,end,interval):
                price=100.0; rows=[]
                for i in range(200):
                    change=0.0015*((i%11)-5)/5.0
                    price*=1+change
                    stamp=(start+timedelta(hours=i)).isoformat(timespec="seconds").replace("+00:00","Z")
                    rows.append(candle(stamp,price/(1+change),price,100+i%13))
                return {"provider":"mock","symbol":symbol+"USDT","interval":interval,"retrieved_at":"2025-01-01T00:00:00Z","candles":rows}
            def feed(*args,**kwargs): raise OSError("offline")
            start1=datetime(2025,1,1,tzinfo=timezone.utc); end1=start1+timedelta(hours=200)
            first=run("SOL",start1,end1,output_dir=Path(directory)/"r1",cases_path=cases_path,
                prediction_memory_path=memory_path,market_fetcher=fetch,feed_collector=feed)
            start2=datetime(2025,2,1,tzinfo=timezone.utc); end2=start2+timedelta(hours=200)
            second=run("SOL",start2,end2,output_dir=Path(directory)/"r2",cases_path=cases_path,
                prediction_memory_path=memory_path,market_fetcher=fetch,feed_collector=feed)
            self.assertGreater(first["prediction_memory"]["new_examples_added"],0)
            self.assertGreater(second["prediction_memory"]["prior_eligible_example_count"],0)
            self.assertEqual(second["prediction_signal"]["status"],"EXPERIMENTAL_SIGNAL")
            self.assertLessEqual(second["prediction_signal"]["latest_training_label_timestamp"],second["prediction_signal"]["as_of"])
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
