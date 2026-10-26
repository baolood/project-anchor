#!/usr/bin/env python3
"""MULTICOIN_TREND_V1 backtest. Refuses to run if PARAMS.md hash != PARAMS.lock."""
import hashlib, zipfile, glob, io, json, os, sys
import numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
lock = open(f"{H}/PARAMS.lock").read().split()[0]
if hashlib.sha256(open(f"{H}/PARAMS.md","rb").read()).hexdigest() != lock: sys.exit("PARAMS.md changed vs lock")
COINS = "BTC ETH XRP ADA DOGE LTC LINK SOL DOT AVAX".split()
def ts(x):
    x = np.asarray(x, dtype="int64"); x = np.where(x > 10**14, x // 1000, x)
    return pd.to_datetime(x, unit="ms", utc=True)
def read_zips(pat):
    out = []
    for f in sorted(glob.glob(pat)):
        with zipfile.ZipFile(f) as z:
            raw = z.read(z.namelist()[0]).decode()
        df = pd.read_csv(io.StringIO(raw), header=None)
        if not str(df.iloc[0,0]).lstrip("-").isdigit(): df = df.iloc[1:]
        out.append(df)
    return pd.concat(out) if out else None
O, C, F = {}, {}, {}
for c in COINS:
    k = read_zips(f"{H}/data/{c}USDT-1d-*.zip")
    d = ts(k[0].astype("int64")).normalize()
    s = pd.DataFrame({"o": k[1].astype(float).values, "c": k[4].astype(float).values}, index=d)
    s = s[~s.index.duplicated()].sort_index()
    O[c], C[c] = s["o"], s["c"]
    fr = read_zips(f"{H}/data/{c}USDT-fundingRate-*.zip")
    if fr is not None:
        f = pd.Series(fr[2].astype(float).values, index=ts(fr[0].astype("int64")).normalize())
        F[c] = f.groupby(level=0).sum()
O = pd.DataFrame(O); C = pd.DataFrame(C)
Fd = pd.DataFrame(F).reindex(C.index)  # daily summed funding rate; NaN = missing
ret1 = C.pct_change(fill_method=None)
vol60 = ret1.rolling(60).std() * np.sqrt(365)
nbars = C.notna().cumsum()
mondays = [d for d in C.index if d.weekday() == 0 and d >= pd.Timestamp("2020-01-01", tz="UTC")]
TV, CAP, GROSS, FILT, FEE = 0.20, 0.25, 1.0, 0.05, 0.0010
def weights(L, mode):
    sma = C.rolling(L).mean(); rL = C / C.shift(L) - 1
    W = {}; prev = pd.Series(0.0, index=COINS)
    for m in mondays:
        sd = m - pd.Timedelta(days=1)  # Sunday close
        if sd not in C.index: W[m] = prev.copy(); continue
        cl, sm, rr, v = C.loc[sd], sma.loc[sd], rL.loc[sd], vol60.loc[sd]
        elig = (nbars.loc[sd] >= 120) & cl.notna() & sm.notna() & v.notna() & (v > 0)
        sig = pd.Series(0.0, index=COINS)
        sig[elig & (cl > sm) & (rr > 0)] = 1.0
        if mode == "LONG_SHORT": sig[elig & (cl < sm) & (rr < 0)] = -1.0
        tgt = pd.Series(0.0, index=COINS)
        act = sig[sig != 0].index
        if len(act):
            raw = sig[act] / v[act]
            win = ret1.loc[:sd, act].tail(60).fillna(0)
            cov = win.cov().values * 365
            pv = float(np.sqrt(max(raw.values @ cov @ raw.values, 1e-12)))
            w = raw * (TV / pv)
            w = w.clip(-CAP, CAP)
            g = w.abs().sum()
            if g > GROSS: w = w * GROSS / g
            tgt[act] = w
        new = prev.copy()
        ch = (tgt - prev).abs() >= FILT
        new[ch] = tgt[ch]
        # a coin leaving the eligible/active set to exactly 0 with |w|<FILT also stays (filter applies uniformly)
        W[m] = new; prev = new
    return pd.DataFrame(W).T
def simulate(W, fee=FEE, signs=None):
    idx = W.index; rows = []
    prevw = pd.Series(0.0, index=COINS)
    for i, m in enumerate(idx[:-1]):
        n = idx[i+1]
        w = W.loc[m] if signs is None else W.loc[m] * signs[i]
        r = (O.loc[n] / O.loc[m] - 1).fillna(0) if (m in O.index and n in O.index) else pd.Series(0.0, index=COINS)
        tc = (w - prevw).abs() * fee
        days = Fd.loc[m:n - pd.Timedelta(days=1)]
        fsum = days.sum(min_count=1)
        miss = days.isna().sum()
        fund = w * fsum.fillna(0) + np.where(w > 0, w * miss * 0.0003, 0.0)  # long pays 0.01%/8h when missing
        gross = w * r
        rows.append({"t": n, "gross": gross.sum(), "tc": tc.sum(), "fund": float(np.sum(fund)),
                     **{f"n_{c}": gross[c] - tc[c] - fund[c] for c in COINS}})
        prevw = w
    df = pd.DataFrame(rows).set_index("t"); df["net"] = df.gross - df.tc - df.fund
    return df
def stats(df):
    yrs = len(df) / 52.0
    eq = (1 + df.net).cumprod()
    ann = eq.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 else np.nan
    sh = df.net.mean() / df.net.std() * np.sqrt(52) if df.net.std() > 0 else 0
    dd = (eq / eq.cummax() - 1).min()
    cost = df.tc.sum() + df.fund.sum()
    return {"weeks": len(df), "ann_net": ann, "sharpe_net": sh, "maxdd": dd,
            "ann_gross_simple": df.gross.sum() / yrs, "ann_cost_simple": cost / yrs,
            "gross_over_cost": df.gross.sum() / cost if cost > 0 else np.inf,
            "fees_total": df.tc.sum(), "funding_total": df.fund.sum()}
IS0, IS1 = pd.Timestamp("2020-01-01", tz="UTC"), pd.Timestamp("2023-12-31", tz="UTC")
OS0, OS1 = pd.Timestamp("2024-01-01", tz="UTC"), pd.Timestamp("2026-09-30", tz="UTC")
res = {"variants": {}}
allW = {}
for L in (50, 100):
    for mode in ("LONG_FLAT", "LONG_SHORT"):
        vid = f"L{L}_{mode}"; W = weights(L, mode); allW[vid] = W
        Wis = W.loc[IS0:IS1 + pd.Timedelta(days=7)]
        res["variants"][vid] = {"IS": stats(simulate(Wis).loc[IS0:IS1])}
sel = max(res["variants"], key=lambda k: res["variants"][k]["IS"]["sharpe_net"])
res["selected"] = sel; isst = res["variants"][sel]["IS"]
gate = isst["ann_gross_simple"] >= 2 * isst["ann_cost_simple"]
res["gate"] = {"ann_gross": isst["ann_gross_simple"], "ann_cost": isst["ann_cost_simple"], "pass": bool(gate)}
if not gate:
    res["verdict"] = "REJECT_AT_GATE"
else:
    W = allW[sel].loc[OS0 - pd.Timedelta(days=7):OS1 + pd.Timedelta(days=7)]
    W = W.loc[W.index >= W.index[W.index <= OS0][-1]] if (W.index <= OS0).any() else W
    oos = simulate(W).loc[OS0:OS1]; st = stats(oos); res["OOS"] = st
    rng = np.random.default_rng(20261026); nW = len(W) - 1; sims = []
    for _ in range(1000):
        sg = rng.choice([-1.0, 1.0], size=(nW, len(COINS)))
        sims.append(stats(simulate(W, signs=[pd.Series(s, index=COINS) for s in sg]).loc[OS0:OS1])["sharpe_net"])
    p95 = float(np.percentile(sims, 95)); res["random_p95_sharpe"] = p95
    seg = {y: float(oos.net[(oos.index >= pd.Timestamp(f"{y}-01-01", tz="UTC")) & (oos.index < pd.Timestamp(f"{y+1}-01-01", tz="UTC"))].sum()) for y in (2024, 2025, 2026)}
    contrib = {c: float(oos[f"n_{c}"].sum()) for c in COINS}; top = max(contrib, key=contrib.get)
    stress = stats(simulate(W, fee=0.0045).loc[OS0:OS1])
    P = {"P1_ann_net>=8%": st["ann_net"] >= 0.08, "P2_sharpe>=0.7": st["sharpe_net"] >= 0.7,
         "P3_sharpe>random_p95": st["sharpe_net"] > p95, "P4_maxdd<=25%": st["maxdd"] >= -0.25,
         "P5_gross/cost>=2": st["gross_over_cost"] >= 2, "P6_2of3_segments>0": sum(v > 0 for v in seg.values()) >= 2,
         "P7_ex_top_coin>0": oos.net.sum() - contrib[top] > 0}
    res.update({"segments_net_sum": seg, "coin_net_contrib": contrib, "top_coin": top,
                "stress_spot_40bp_info_only": stress, "criteria": {k: bool(v) for k, v in P.items()},
                "verdict": "PASS" if all(P.values()) else "FAIL"})
json.dump(res, open(f"{H}/results.json", "w"), indent=1, default=float)
print(json.dumps(res, indent=1, default=float))
