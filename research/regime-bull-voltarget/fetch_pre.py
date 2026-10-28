"""Fetch Bitstamp BTCUSD daily OHLC 2011-09-13 .. 2017-08-16 (the pre-Binance window). Public API, no keys. Data only."""
import requests, pandas as pd, time
H={"User-Agent":"Mozilla/5.0"}
rows=[]; start=1315872000   # 2011-09-13 00:00 UTC
END=1502928000              # 2017-08-17 00:00 UTC (exclusive)
while start<END:
    r=requests.get("https://www.bitstamp.net/api/v2/ohlc/btcusd/",params={"step":86400,"limit":1000,"start":start},headers=H,timeout=30).json()
    o=r["data"]["ohlc"]
    if not o: break
    rows+=o; last=int(o[-1]["timestamp"])
    if len(o)<1000: break
    start=last+86400; time.sleep(0.3)
b=pd.DataFrame(rows).drop_duplicates("timestamp")
b["timestamp"]=b.timestamp.astype(int); b=b[b.timestamp<END].sort_values("timestamp")
b["date"]=pd.to_datetime(b.timestamp,unit="s").dt.strftime("%Y-%m-%d")
b[["date","open","high","low","close","volume"]].to_csv("data/bitstamp_btcusd_daily_pre2017-08-17.csv",index=False)
print(b.date.min(),b.date.max(),len(b))
