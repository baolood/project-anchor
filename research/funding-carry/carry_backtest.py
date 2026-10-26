#!/usr/bin/env python3
"""FUNDING_CARRY_V1 backtest. Parameters are fixed by PARAMS.md (locked, see PARAMS.lock).
Delta-neutral: long spot + short USDT perp, equal qty. Hourly simulation on Binance public archive data."""
import glob, io, json, zipfile, hashlib, sys
import numpy as np, pandas as pd

D = "data"
LOCK = open("PARAMS.lock").read().split()[0]
assert hashlib.sha256(open("PARAMS.md", "rb").read()).hexdigest() == LOCK, "PARAMS.md changed after lock"

IS = ("2022-01-01", "2024-01-01")
OOS_START = "2024-01-01"
L = 2.0; MM = 0.005; REB_LO, REB_HI = 0.30, 0.70
FEES = {"KRAKEN_RETAIL": (0.0040, 0.0005), "TIER1_CEX": (0.0010, 0.0005)}
SLIP = {"BTCUSDT": 0.0002, "ETHUSDT": 0.0003}
VARIANTS = {"V0_ALWAYS": None, "V1_T0.005%": 0.00005, "V1_T0.010%": 0.00010, "V1_T0.020%": 0.00020}

def _ts(x):
    x = np.asarray(x, dtype="int64"); x = np.where(x > 1e14, x // 1000, x)  # us -> ms
    return pd.to_datetime(x, unit="ms", utc=True)

def load_klines(kind, sym):
    fr = []
    for f in sorted(glob.glob(f"{D}/{kind}_*_klines_{sym}_1h_*.zip")):
        raw = zipfile.ZipFile(f).read(zipfile.ZipFile(f).namelist()[0]).decode()
        df = pd.read_csv(io.StringIO(raw), header=None)
        if str(df.iloc[0, 0]).startswith("open"): df = df.iloc[1:]
        df = df.iloc[:, :5].astype(float); df.columns = ["t", "o", "h", "l", "c"]
        fr.append(df)
    df = pd.concat(fr); df.index = _ts(df.t.astype("int64")); df = df[~df.index.duplicated()].sort_index()
    return df[["o", "h", "l", "c"]]

def load_funding(sym):
    fr = []
    for f in sorted(glob.glob(f"{D}/futures_um_monthly_fundingRate_{sym}_*.zip")):
        fr.append(pd.read_csv(io.BytesIO(zipfile.ZipFile(f).read(zipfile.ZipFile(f).namelist()[0]))))
    df = pd.concat(fr); idx = _ts(df.calc_time.values).floor("h")
    s = pd.Series(df.last_funding_rate.values.astype(float), index=idx)
    return s[~s.index.duplicated()].sort_index()

def simulate(sym, sp, pp, fund, start, end, fee_name, thr):
    fs, fp = FEES[fee_name]; sl = SLIP[sym]
    idx = sp.index[(sp.index >= start) & (sp.index < end)].intersection(pp.index)
    idx = idx[idx <= fund.index[-1] + pd.Timedelta(hours=8)]
    S_c, F_c, F_o, F_h = sp.c.reindex(idx).values, pp.c.reindex(idx).values, pp.o.reindex(idx).values, pp.h.reindex(idx).values
    fset = fund.reindex(idx)  # rate printed at bar open time t
    hist = []  # funding prints known so far
    cash, q, Fref, marg = 1.0, 0.0, 0.0, 0.0
    fund_in = fund_out = cost = 0.0; trades = reb = liq = 0; minratio = 9.0
    eq = np.empty(len(idx)); inpos = np.zeros(len(idx), bool)
    def open_pos(E, S, F):
        nonlocal q, Fref, marg, cost
        qq = E / (S * (1 + sl + fs) + F / L + F * (fp + sl))
        c = qq * S * (sl + fs) + qq * F * (fp + sl); cost += c
        q, Fref, marg = qq, F, qq * F / L
        return E - qq * S * (1 + sl + fs) - marg - qq * F * (fp + sl)  # leftover cash ~0
    def close_pos(S, F):
        nonlocal q, Fref, marg, cost
        c = q * S * (sl + fs) + q * F * (fp + sl); cost += c
        v = q * S + marg + q * (Fref - F) - c
        q = Fref = marg = 0.0
        return v
    for i, t in enumerate(idx):
        S, F = S_c[i], F_c[i]
        r = fset.iloc[i]
        if not np.isnan(r):
            if q > 0:  # funding at t on position held at t, mark ~ perp open of bar t
                amt = r * q * F_o[i]; marg += amt
                if amt >= 0: fund_in += amt
                else: fund_out += -amt
            hist.append(r)
        if q > 0:  # liquidation check on bar high
            e_hi = marg + q * (Fref - F_h[i])
            minratio = min(minratio, e_hi / (q * F_h[i]))
            if e_hi <= MM * q * F_h[i]:
                liq += 1; c = q * S * (sl + fs); cost += c
                cash += q * S - c; q = Fref = marg = 0.0  # perp margin lost, spot sold
        # decisions at bar close using prints with time <= t
        want = True if thr is None else None
        if thr is not None and len(hist) >= 3:
            m = float(np.mean(hist[-3:]))
            want = (m > thr) if q == 0 else (m >= 0)
        if want is None: want = q > 0
        if q == 0 and want and (thr is not None or trades == 0 and liq == 0):
            cash = open_pos(cash, S, F); trades += 1
        elif q > 0 and not want:
            cash += close_pos(S, F); trades += 1
        elif q > 0:
            ratio = (marg + q * (Fref - F)) / (q * F)
            if ratio < REB_LO or ratio > REB_HI:
                E = q * S + marg + q * (Fref - F)
                qn = E / (S + F / L); dq = abs(q - qn)
                c = dq * S * (sl + fs) + dq * F * (fp + sl); cost += c; E -= c
                qn = E / (S + F / L); q, Fref, marg = qn, F, qn * F / L; reb += 1
        eq[i] = cash + q * S + marg + q * (Fref - F); inpos[i] = q > 0
    # mark-to-market at end without forcing exit cost (also report exit-cost-adjusted)
    if q > 0: final_exit = eq[-1] - (q * S * (sl + fs) + q * F * (fp + sl))
    else: final_exit = eq[-1]
    e = pd.Series(eq, index=idx)
    yrs = (idx[-1] - idx[0]).total_seconds() / (365.25 * 86400)
    ann = final_exit ** (1 / yrs) - 1
    dd = float((e / e.cummax() - 1).min())
    mon = e.resample("ME").last(); mon = pd.concat([pd.Series([1.0], index=[idx[0]]), mon]).pct_change().dropna()
    yr = e.resample("YE").last(); yr = pd.concat([pd.Series([1.0], index=[idx[0]]), yr]).pct_change().dropna()
    basis = final_exit - 1 - (fund_in - fund_out) + cost  # residual = basis/price P&L
    return dict(start=str(idx[0]), end=str(idx[-1]), years=round(yrs, 3), final=final_exit, ann_return=ann,
                max_dd=dd, worst_month=float(mon.min()), worst_month_at=str(mon.idxmin())[:7],
                funding_received=fund_in, funding_paid=fund_out, fees_slippage=cost, basis_residual=basis,
                funding_to_cost=(fund_in - fund_out) / cost if cost else None,
                trades=trades, rebalances=reb, liquidations=liq, min_margin_ratio=minratio if minratio < 9 else None,
                time_in_market=float(inpos.mean()),
                yearly={str(k.year): float(v) for k, v in yr.items()},
                monthly={str(k)[:7]: float(v) for k, v in mon.items()})

def main():
    out = {"params_sha256": LOCK, "runs": {}}
    for sym in ["BTCUSDT", "ETHUSDT"]:
        sp, pp, fd = load_klines("spot", sym), load_klines("futures_um", sym), load_funding(sym)
        end = str((fd.index[-1] + pd.Timedelta(hours=8)).date())
        out.setdefault("data_end", {})[sym] = str(fd.index[-1])
        # raw funding stats
        out.setdefault("funding_stats", {})[sym] = {str(y): {"mean_apr": float(g.mean() * 3 * 365), "neg_share": float((g < 0).mean())}
                                                    for y, g in fd.groupby(fd.index.year)}
        for fee in FEES:
            for vn, thr in VARIANTS.items():
                for per, (a, b) in {"IS": IS, "OOS": (OOS_START, "2100-01-01"), "FULL": ("2022-01-01", "2100-01-01")}.items():
                    out["runs"][f"{sym}|{fee}|{vn}|{per}"] = simulate(sym, sp, pp, fd, pd.Timestamp(a, tz="UTC"), pd.Timestamp(min(b, end), tz="UTC") if b < end else pd.Timestamp("2100-01-01", tz="UTC"), fee, thr)
                    print(sym, fee, vn, per, {k: round(v, 4) if isinstance(v, float) else v for k, v in out["runs"][f"{sym}|{fee}|{vn}|{per}"].items() if k not in ("monthly", "yearly")}, flush=True)
    # selection on IS (BTC, KRAKEN_RETAIL)
    cand = {vn: out["runs"][f"BTCUSDT|KRAKEN_RETAIL|{vn}|IS"]["ann_return"] for vn in VARIANTS}
    sel = max(cand, key=cand.get); o = out["runs"][f"BTCUSDT|KRAKEN_RETAIL|{sel}|OOS"]; i_ = out["runs"][f"BTCUSDT|KRAKEN_RETAIL|{sel}|IS"]
    yrs_ok = {y: o["yearly"].get(y, -1) > 0 for y in ("2024", "2025", "2026")}
    crit = {"P1_ann>=8%": o["ann_return"] >= 0.08, "P2_maxDD<=5%": o["max_dd"] >= -0.05, "P3_worst_month>=-2%": o["worst_month"] >= -0.02,
            "P4_no_liquidation": o["liquidations"] == 0 and i_["liquidations"] == 0,
            "P5_funding>=3x_costs": (o["funding_to_cost"] or 0) >= 3, "P6_each_year_positive": all(yrs_ok.values()), "P7_IS_positive": i_["ann_return"] > 0}
    out["selection"] = {"is_ann_by_variant": cand, "selected": sel, "criteria": crit, "yearly_ok": yrs_ok, "PASS": all(crit.values())}
    # Kraken cross-check
    try:
        k = json.load(open(f"{D}/k_btc.json"))["rates"]; ks = pd.Series([r["relativeFundingRate"] for r in k], index=pd.to_datetime([r["timestamp"] for r in k]))
        fd = load_funding("BTCUSDT"); win = fd[fd.index >= ks.index[0]]
        out["kraken_crosscheck"] = {"kraken_PF_XBTUSD_window": [str(ks.index[0]), str(ks.index[-1])], "kraken_mean_apr": float(ks.mean() * 24 * 365),
                                    "kraken_neg_share": float((ks < 0).mean()), "binance_same_window_mean_apr": float(win.mean() * 3 * 365),
                                    "kraken_monthly_apr": {str(p): float(g.mean() * 24 * 365) for p, g in ks.groupby(ks.index.strftime("%Y-%m"))}}
    except Exception as e: out["kraken_crosscheck"] = {"error": str(e)}
    json.dump(out, open("results.json", "w"), indent=1, default=float)
    print(json.dumps(out["selection"], indent=1, default=str)); print(json.dumps({k: v for k, v in out["kraken_crosscheck"].items() if k != "kraken_monthly_apr"}, indent=1))
if __name__ == "__main__": main()
