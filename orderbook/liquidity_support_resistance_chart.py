"""Plot BTC price and order-book liquidity profile over a configurable broad price window."""
import argparse, json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

def read_records(path):
    raw=Path(path).read_text(encoding="utf-8").strip()
    if not raw: raise ValueError("input is empty")
    try:
        obj=json.loads(raw)
        return obj if isinstance(obj,list) else [obj]
    except json.JSONDecodeError:
        return [json.loads(line) for line in raw.splitlines() if line.strip()]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",required=True,help="JSON snapshot or JSONL repeated snapshots")
    p.add_argument("--zones",required=True,help="JSON report containing candidate zones")
    p.add_argument("--output",required=True)
    p.add_argument("--range-pct",type=float,default=20.0)
    a=p.parse_args()
    if not 0<a.range_pct<=50: p.error("--range-pct must be > 0 and <= 50")
    records=read_records(a.input); last=records[-1]
    mid=float(last["mid_price"]); low=mid*(1-a.range_pct/100); high=mid*(1+a.range_pct/100)
    accum={}
    for rec in records:
        for b in rec.get("price_buckets",[]):
            lo=float(b["price_bucket_start"]); hi=float(b.get("price_bucket_end_exclusive",lo+100))
            if hi<low or lo>high: continue
            slot=accum.setdefault(lo,{"bid":[],"ask":[]})
            slot["bid"].append(float(b.get("bid_notional_usd",0))); slot["ask"].append(float(b.get("ask_notional_usd",0)))
    prices=sorted(accum)
    bids=[sum(accum[x]["bid"])/len(accum[x]["bid"]) for x in prices]
    asks=[sum(accum[x]["ask"])/len(accum[x]["ask"]) for x in prices]
    zones_report=json.loads(Path(a.zones).read_text(encoding="utf-8"))
    fig,ax=plt.subplots(figsize=(15,9),constrained_layout=True)
    ax.barh([x+50 for x in prices],bids,height=75,label="Buy orders (bids)",color="#238b57",alpha=.8)
    ax.barh([x+50 for x in prices],[-v for v in asks],height=75,label="Sell orders (asks)",color="#c94c4c",alpha=.8)
    ax.axhline(mid,color="#222222",linestyle="--",linewidth=1.5,label="Latest mid-price: "+format(mid,",.2f"))
    visible=[]
    for z in zones_report.get("zones",[]):
        lo=float(z["price_low"]); hi=float(z["price_high_exclusive"])
        if hi<low or lo>high: continue
        support=z["type"]=="candidate_support"; color="#238b57" if support else "#c94c4c"
        ax.axhspan(lo,hi,color=color,alpha=.2)
        label=("SUPPORT " if support else "RESISTANCE ")+format(lo,",.0f")+"-"+format(hi,",.0f")+" | persistence "+str(z["persistence_pct"])+"% | max $"+format(float(z["max_visible_notional_usd"]),",.0f")
        ax.text(.99,(lo+hi)/2,label,transform=ax.get_yaxis_transform(),ha="right",va="center",fontsize=8,bbox={"facecolor":"white","alpha":.8,"edgecolor":color,"pad":2})
        visible.append(z)
    ax.set_ylim(low,high); ax.set_xlabel("Average visible notional per $100 bucket (USD): asks left, bids right"); ax.set_ylabel("BTC/USD price")
    ax.set_title("BTC/USD order-book liquidity and candidate support/resistance (±"+str(a.range_pct)+"%)")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v,_:"$"+format(abs(v)/1e6,".1f")+"M"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_:"$"+format(v,",.0f")))
    ax.grid(True,axis="y",alpha=.25); ax.legend(loc="upper left")
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); fig.savefig(out,dpi=160); plt.close(fig)
    print(json.dumps({"chart":str(out),"reference_mid_price":mid,"window_low":low,"window_high":high,"bucket_count":len(prices),"candidate_zones_in_window":len(visible),"bytes":out.stat().st_size},indent=2))

if __name__=="__main__": main()
