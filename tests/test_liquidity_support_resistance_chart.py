import json, tempfile, unittest
from pathlib import Path
from subprocess import run
import sys

class ChartScriptTests(unittest.TestCase):
    def test_chart_generation_with_wide_window(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); inp=root/"book.jsonl"; zones=root/"zones.json"; out=root/"chart.png"
            rec={"mid_price":"100000","price_buckets":[
                {"price_bucket_start":"80000","price_bucket_end_exclusive":"80100","bid_notional_usd":"1000000","ask_notional_usd":"0"},
                {"price_bucket_start":"120000","price_bucket_end_exclusive":"121000","bid_notional_usd":"0","ask_notional_usd":"2000000"}]}
            inp.write_text(json.dumps(rec)+"\\n"+json.dumps(rec)+"\\n")
            zones.write_text(json.dumps({"zones":[{"type":"candidate_support","price_low":"80000","price_high_exclusive":"80100","persistence_pct":100,"max_visible_notional_usd":"1200000"}]}))
            run([sys.executable,"-m","orderbook.liquidity_support_resistance_chart","--input",str(inp),"--zones",str(zones),"--output",str(out),"--range-pct","20"],check=True)
            self.assertTrue(out.exists()); self.assertGreater(out.stat().st_size,10000)

if __name__=="__main__": unittest.main()
