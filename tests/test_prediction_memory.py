import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from prediction_memory import (
    PredictionMemoryError, append_examples, build_examples, eligible_examples, load_examples
)


def make_candles(count=80, start=None):
    start = start or datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows=[]
    price=100.0
    for i in range(count):
        change=0.0015*((i%11)-5)/5.0
        price*=1+change
        timestamp=(start+timedelta(hours=i)).isoformat(timespec="seconds").replace("+00:00","Z")
        rows.append({"timestamp":timestamp,"open":price/(1+change),"high":price*1.002,
                     "low":price*0.998,"close":price,"volume":100.0+i%13})
    return rows


class PredictionMemoryTests(unittest.TestCase):
    def test_build_persist_and_deduplicate_examples(self):
        rows=build_examples(make_candles(), "SOL", "1h", "mock")
        self.assertGreater(len(rows),0)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"memory.json"
            first=append_examples(path,rows)
            second=append_examples(path,rows)
            loaded=load_examples(path)
            self.assertEqual(first["added_count"],len(rows))
            self.assertEqual(second["added_count"],0)
            self.assertEqual(len(loaded),len(rows))
            self.assertTrue(all(x["target_timestamp"]>x["anchor_timestamp"] for x in loaded))

    def test_eligibility_filters_asset_interval_window_and_matured_label(self):
        rows=build_examples(make_candles(80), "SOL", "1h", "mock")
        result=eligible_examples(rows,"SOL","1h",24,6,
            as_of="2025-01-04T00:00:00Z",before_timestamp="2025-01-03T00:00:00Z")
        self.assertTrue(all(x["anchor_timestamp"]<"2025-01-03T00:00:00Z" for x in result))
        self.assertTrue(all(x["target_timestamp"]<="2025-01-04T00:00:00Z" for x in result))
        self.assertEqual(eligible_examples(rows,"ETH","1h",24,6,
            as_of="2025-01-04T00:00:00Z",before_timestamp="2025-01-03T00:00:00Z"),[])

    def test_corrupt_memory_fails_explicitly(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"memory.json"
            path.write_text('{"store_schema_version":"9.9.9","examples":[]}',encoding="utf-8")
            with self.assertRaises(PredictionMemoryError):
                load_examples(path)

    def test_invalid_example_is_rejected(self):
        rows=build_examples(make_candles(), "SOL", "1h", "mock")
        rows[0]["forward_return_pct"]=float("nan")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(PredictionMemoryError):
                append_examples(Path(directory)/"memory.json",rows)


if __name__=="__main__": unittest.main()
