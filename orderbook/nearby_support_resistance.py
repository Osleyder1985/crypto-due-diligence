"""Rank nearby candidate support/resistance zones from Kraken persistence snapshots."""
import argparse, json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

def build_nearby_report(records, max_distance_pct=Decimal("20"), min_persistence_pct=Decimal("80"), large_concentration_threshold_usd=Decimal("1000000")):
    if not records: raise ValueError("at least one snapshot record is required")
    max_distance_pct, min_persistence_pct = Decimal(str(max_distance_pct)), Decimal(str(min_persistence_pct))
    large_concentration_threshold_usd = Decimal(str(large_concentration_threshold_usd))
    if not 0 < max_distance_pct <= 50: raise ValueError("max distance percentage must be > 0 and <= 50")
    if not 0 <= min_persistence_pct <= 100: raise ValueError("minimum persistence must be between 0 and 100")
    if large_concentration_threshold_usd <= Decimal("250000"): raise ValueError("large concentration threshold must exceed the 250000 USD reference threshold")
    latest = records[-1]
    price = Decimal(str(latest.get("mid_price") or "0"))
    if price <= 0: raise ValueError("latest snapshot has no valid positive mid_price")
    stats, total = {}, len(records)
    for record in records:
        sample_price = Decimal(str(record.get("mid_price") or "0"))
        if sample_price <= 0: continue
        for b in record.get("price_buckets", []):
            lo = Decimal(str(b["price_bucket_start"]))
            hi = Decimal(str(b.get("price_bucket_end_exclusive", lo + Decimal("100"))))
            center = (lo + hi) / 2
            for side in ("bid", "ask"):
                notional = Decimal(str(b.get(f"{side}_notional_usd", "0")))
                if notional <= 0 or (side == "bid" and center >= sample_price) or (side == "ask" and center <= sample_price): continue
                key = (side, str(lo), str(hi))
                s = stats.setdefault(key, {"side":side,"lo":str(lo),"hi":str(hi),"center":str(center),"present":0,"hits":0,"large_hits":0,"sum":Decimal(0),"max":Decimal(0)})
                s["present"] += 1; s["sum"] += notional; s["max"] = max(s["max"], notional)
                if notional >= Decimal("250000"): s["hits"] += 1
                if notional >= large_concentration_threshold_usd: s["large_hits"] += 1
    zones = []
    for s in stats.values():
        distance = abs(Decimal(s["center"]) - price) / price * 100
        persistence = Decimal(s["hits"]) / total * 100
        large_persistence = Decimal(s["large_hits"]) / total * 100
        if distance > max_distance_pct or persistence < min_persistence_pct: continue
        distance_score = max(Decimal(0), Decimal(1) - distance / max_distance_pct)
        score = persistence / 100 * Decimal(".6") + min(Decimal(1), s["max"] / Decimal("1000000")) * Decimal(".25") + distance_score * Decimal(".15")
        zones.append({"type":"candidate_support" if s["side"]=="bid" else "candidate_resistance","side":s["side"],"price_low":s["lo"],"price_high_exclusive":s["hi"],"price_center":s["center"],"distance_from_latest_mid_pct":round(float(distance),4),"observations_present":s["present"],"snapshot_count":total,"persistence_pct":round(float(persistence),2),"large_concentration_persistence_pct":round(float(large_persistence),2),"liquidity_classification":"persistent_large_concentration" if large_persistence >= min_persistence_pct else "significant_liquidity","large_concentration_threshold_usd":str(large_concentration_threshold_usd),"max_visible_notional_usd":str(s["max"]),"average_notional_when_present_usd":str((s["sum"]/s["present"]).quantize(Decimal(".01"))),"descriptive_score_0_100":round(float(score*100),2),"status":"candidate_unconfirmed","evidence":["Aggregated visible book liquidity; orders may be cancelled or moved.","Persistence alone does not confirm price reaction."]})
    zones.sort(key=lambda z:(z["descriptive_score_0_100"],-z["distance_from_latest_mid_pct"],float(z["max_visible_notional_usd"])),reverse=True)
    return {"schema_version":"1.0","generated_at":datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z"),"venue":latest.get("venue","kraken_spot"),"pair":latest.get("pair_returned","unknown"),"reference_price_type":"latest_snapshot_mid_price","reference_mid_price":str(price),"reference_timestamp":latest.get("captured_at"),"snapshot_count":total,"max_distance_pct":str(max_distance_pct),"min_persistence_pct":str(min_persistence_pct),"notional_threshold_usd":"250000","large_concentration_threshold_usd":str(large_concentration_threshold_usd),"zone_aggregation":"Aggregated USD notional per $100 price bucket and side per snapshot; no per-order-count threshold.","zones":zones,"interpretation":"Zones are relative to the latest sampled mid-price. Scores are descriptive rankings, not probabilities or trading signals.","limitations":["Reference is the latest sampled mid-price, not a guaranteed real-time quote.","Persistence does not prove the same orders stayed open between samples.","Reaction confirmation needs separate OHLC/trade analysis and out-of-sample evaluation.","Only public Kraken Spot liquidity is covered; not total-market liquidity."]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",default="artifacts/orderbook-persistence/kraken-xbtusd-snapshots.jsonl")
    p.add_argument("--output-dir",default="artifacts/orderbook-persistence")
    p.add_argument("--max-distance-pct",type=Decimal,default=Decimal("20"))
    p.add_argument("--min-persistence-pct",type=Decimal,default=Decimal("80"))
    p.add_argument("--large-concentration-threshold-usd",type=Decimal,default=Decimal("1000000"))
    a=p.parse_args()
    records=[json.loads(x) for x in Path(a.input).read_text(encoding="utf-8").splitlines() if x.strip()]
    r=build_nearby_report(records,a.max_distance_pct,a.min_persistence_pct,a.large_concentration_threshold_usd); root=Path(a.output_dir); root.mkdir(parents=True,exist_ok=True)
    (root/"kraken-nearby-support-resistance.json").write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
    lines=["# Kraken BTC: nearby candidate support and resistance","",f"- Pair: {r['pair']}",f"- Latest sampled mid-price: USD {Decimal(r['reference_mid_price']):,.2f}",f"- Reference timestamp: {r['reference_timestamp']}",f"- Snapshots: {r['snapshot_count']}",f"- Nearby window: ±{r['max_distance_pct']}%",f"- Minimum persistence: {r['min_persistence_pct']}%","- Significant-liquidity reference: $250,000 aggregated per $100 bucket and side","- Large-concentration threshold: ${Decimal(r['large_concentration_threshold_usd']):,.0f} aggregated per $100 bucket and side","","These are unconfirmed candidates based on visible book liquidity.","","| Type | Price range | Distance | Persistence at $250k | Persistence at $1m | Classification | Max visible notional USD | Score / 100 |","|---|---:|---:|---:|---:|---|---:|---:|"]
    for z in r["zones"]: lines.append(f"| {z['type']} | [{z['price_low']}, {z['price_high_exclusive']}) | {z['distance_from_latest_mid_pct']:.4f}% | {z['persistence_pct']:.2f}% | {z['large_concentration_persistence_pct']:.2f}% | {z['liquidity_classification']} | {Decimal(z['max_visible_notional_usd']):,.0f} | {z['descriptive_score_0_100']:.2f} |")
    if not r["zones"]: lines.append("| No qualifying zones | — | — | — | — | — |")
    lines += ["","## Interpretation","",r["interpretation"],"","## Limitations",""]+[f"- {x}" for x in r["limitations"]]
    (root/"kraken-nearby-support-resistance.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"reference_mid_price":r["reference_mid_price"],"zone_count":len(r["zones"])},indent=2))
if __name__=="__main__": main()
