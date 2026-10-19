import unittest
from orderbook.nearby_support_resistance import build_nearby_report
def snap(ts, mid, buckets): return {"captured_at":ts,"venue":"kraken_spot","pair_returned":"XXBTZUSD","mid_price":str(mid),"price_buckets":buckets}
def bucket(start,bid="0",ask="0"): return {"price_bucket_start":str(start),"price_bucket_end_exclusive":str(start+100),"bid_notional_usd":bid,"ask_notional_usd":ask}
class NearbyZonesTests(unittest.TestCase):
 def test_near_bid_and_ask_candidates(self):
  r=build_nearby_report([snap("t1",82100,[bucket(82000,bid="300000"),bucket(82200,ask="400000")]),snap("t2",82120,[bucket(82000,bid="350000"),bucket(82200,ask="450000")])],1,100)
  self.assertEqual(r["reference_mid_price"],"82120")
  self.assertEqual({z["type"] for z in r["zones"]},{"candidate_support","candidate_resistance"})
  self.assertTrue(all(z["status"]=="candidate_unconfirmed" for z in r["zones"]))
 def test_filters_far_zones(self):
  r=build_nearby_report([snap("t1",82100,[bucket(80000,bid="500000"),bucket(82000,bid="300000")]),snap("t2",82100,[bucket(82000,bid="300000")])],1,75)
  self.assertEqual(len(r["zones"]),1); self.assertEqual(r["zones"][0]["price_low"],"82000")
 def test_default_proximity_is_20_percent(self):
  r=build_nearby_report([snap("t1",100000,[bucket(85000,bid="300000"),bucket(79000,bid="300000")]),snap("t2",100000,[bucket(85000,bid="300000"),bucket(79000,bid="300000")])])
  self.assertEqual(r["max_distance_pct"],"20")
  self.assertIn("85000", [z["price_low"] for z in r["zones"]])
  self.assertNotIn("79000", [z["price_low"] for z in r["zones"]])
 def test_default_minimum_persistence_is_80_percent(self):
  records=[
   snap("t1",100000,[bucket(99900,bid="300000"),bucket(99800,bid="300000")]),
   snap("t2",100000,[bucket(99900,bid="300000"),bucket(99800,bid="300000")]),
   snap("t3",100000,[bucket(99900,bid="300000"),bucket(99800,bid="300000")]),
   snap("t4",100000,[bucket(99900,bid="300000")]),
   snap("t5",100000,[bucket(99900,bid="300000")]),
  ]
  r=build_nearby_report(records)
  self.assertEqual(r["min_persistence_pct"],"80")
  self.assertIn("99900", [z["price_low"] for z in r["zones"]])
  self.assertNotIn("99800", [z["price_low"] for z in r["zones"]])
 def test_rejects_invalid_price_and_empty_input(self):
  with self.assertRaises(ValueError): build_nearby_report([snap("t",0,[])])
  with self.assertRaises(ValueError): build_nearby_report([])
 def test_rejects_invalid_distance(self):
  with self.assertRaises(ValueError): build_nearby_report([snap("t",82100,[])],0)
if __name__=="__main__": unittest.main()
