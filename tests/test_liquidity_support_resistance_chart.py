import json, tempfile, unittest
from pathlib import Path
from orderbook.liquidity_support_resistance_chart import read_records

class ChartInputTests(unittest.TestCase):
    def test_reads_jsonl_snapshots(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"snapshots.jsonl"
            a={"mid_price":"100000","price_buckets":[]}
            b={"mid_price":"101000","price_buckets":[]}
            path.write_text(json.dumps(a)+"\n"+json.dumps(b)+"\n",encoding="utf-8")
            records=read_records(path)
            self.assertEqual(len(records),2)
            self.assertEqual(records[-1]["mid_price"],"101000")

if __name__=="__main__": unittest.main()
