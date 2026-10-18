import math
import unittest
from datetime import datetime, timedelta, timezone

from prediction_evaluation import EvaluationError, predict_next, walk_forward_evaluate


def candles(count=260):
    rows=[]
    price=100.0
    start=datetime(2025,1,1,tzinfo=timezone.utc)
    for i in range(count):
        # Deterministic, nonstationary signal with both positive and negative returns.
        ret=0.0015*math.sin(i/5.0)+0.0008*math.cos(i/13.0)
        price*=1+ret
        ts=(start+timedelta(hours=i)).isoformat(timespec="seconds").replace("+00:00","Z")
        rows.append({"timestamp":ts,"open":price/(1+ret),"high":price*1.002,
                     "low":price*0.998,"close":price,"volume":100+20*math.sin(i/7.0)+i%9})
    return rows


class PredictionEvaluationTests(unittest.TestCase):
    def test_walk_forward_produces_metrics_and_prequential_predictions(self):
        result=walk_forward_evaluate(candles(),lookback=12,horizon=3,min_train=40,neighbors=5)
        self.assertGreater(result["prediction_count"],0)
        self.assertEqual(result["metrics"]["knn"]["sample_size"],result["prediction_count"])
        self.assertIsNotNone(result["metrics"]["momentum_baseline"]["directional_accuracy"])
        for row in result["predictions"]:
            self.assertLessEqual(row["training_max_label_timestamp"],row["timestamp"])
            self.assertLess(row["timestamp"],row["target_timestamp"])
            self.assertEqual(row["neighbor_count"],5)

    def test_future_mutation_does_not_change_earlier_prediction(self):
        original=candles()
        changed=candles()
        anchor=80
        for i in range(anchor+1,len(changed)):
            changed[i]["close"]*=1.5
            changed[i]["open"]*=1.5
            changed[i]["high"]*=1.5
            changed[i]["low"]*=1.5
        kwargs=dict(lookback=12,horizon=3,min_train=40,neighbors=5)
        a=walk_forward_evaluate(original,**kwargs)
        b=walk_forward_evaluate(changed,**kwargs)
        row_a=next(x for x in a["predictions"] if x["timestamp"]==original[anchor]["timestamp"])
        row_b=next(x for x in b["predictions"] if x["timestamp"]==original[anchor]["timestamp"])
        self.assertEqual(row_a["knn_prediction"],row_b["knn_prediction"])
        self.assertEqual(row_a["momentum_prediction"],row_b["momentum_prediction"])

    def test_next_signal_uses_only_matured_labels(self):
        rows=candles(260)
        result=predict_next(rows,lookback=12,horizon=3,min_train=40,neighbors=5)
        self.assertEqual(result["status"],"EXPERIMENTAL_SIGNAL")
        self.assertLessEqual(result["latest_training_label_timestamp"],result["as_of"])
        self.assertIn(result["signal"],("UP","DOWN","INCONCLUSIVE"))
        self.assertEqual(sum(result["neighbor_votes"].values()),5)

    def test_next_signal_requires_matured_training_samples(self):
        with self.assertRaises(EvaluationError):
            predict_next(candles(54),lookback=12,horizon=3,min_train=40,neighbors=5)
    def test_insufficient_data_fails(self):
        with self.assertRaises(EvaluationError):
            walk_forward_evaluate(candles(55),lookback=12,horizon=3,min_train=40)

    def test_duplicate_timestamps_fail(self):
        rows=candles()
        rows[10]["timestamp"]=rows[9]["timestamp"]
        with self.assertRaises(EvaluationError):
            walk_forward_evaluate(rows,lookback=12,horizon=3,min_train=40)

    def test_invalid_fee_fails(self):
        with self.assertRaises(EvaluationError):
            walk_forward_evaluate(candles(),lookback=12,horizon=3,min_train=40,round_trip_fee_bps=-1)


if __name__=="__main__":
    unittest.main()
