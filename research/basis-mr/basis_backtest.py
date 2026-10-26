#!/usr/bin/env python3
"""BASIS_MR_V1 backtest. Parameters fixed by PARAMS.md (locked, see PARAMS.lock).
Spot–perp basis mean-reversion; hourly sim on Binance public archive data."""
import glob, io, json, zipfile, hashlib
import numpy as np, pandas as pd

D = "data"
LOCK = open("PARAMS.lock").read().split()[0]
assert hashlib.sha256(open("PARAMS.md", "rb").read()).hexdigest() == LOCK, "PARAMS.md changed after lock"

IS = ("2022-01-01", "2024-01-01")
OOS_START = "2024-01-01"
L = 2.0
MM = 0.005
Z_EXIT = 0.5
H_MAX = 168
STOP_BP = 0.0030  # 30 bp
BORROW_APR = 0.08
FEES = {"KRAKEN_RETAIL": (0.0040, 0.0005), "TIER1_CEX": (0.0010, 0.0005)}
SLIP = {"BTCUSDT": 0.0002, "ETHUSDT": 0.0003}
# (z_enter, window_h, both_sides)
VARIANTS = {
    "Z2.0_W24_BOTH": (2.0, 24, True),
    "Z2.0_W72_BOTH": (2.0, 72, True),
    "Z2.5_W24_BOTH": (2.5, 24, True),
    "Z2.5_W72_BOTH": (2.5, 72, True),
    "Z2.0_W24_POS":  (2.0, 24, False),
    "Z2.0_W72_POS":  (2.0, 72, False),
    "Z2.5_W24_POS":  (2.5, 24, False),
    "Z2.5_W72_POS":  (2.5, 72, False),
}

def _ts(x):
    x = np.asarray(x, dtype="int64")
    x = np.where(x > 1e14, x // 1000, x)
    return pd.to_datetime(x, unit="ms", utc=True)

def load_klines(kind, sym):
    fr = []
    for f in sorted(glob.glob(f"{D}/{kind}_*_klines_{sym}_1h_*.zip")):
        raw = zipfile.ZipFile(f).read(zipfile.ZipFile(f).namelist()[0]).decode()
        df = pd.read_csv(io.StringIO(raw), header=None)
        if str(df.iloc[0, 0]).startswith("open"):
            df = df.iloc[1:]
        df = df.iloc[:, :5].astype(float)
        df.columns = ["t", "o", "h", "l", "c"]
        fr.append(df)
    df = pd.concat(fr)
    df.index = _ts(df.t.astype("int64"))
    df = df[~df.index.duplicated()].sort_index()
    return df[["o", "h", "l", "c"]]

def load_funding(sym):
    fr = []
    for f in sorted(glob.glob(f"{D}/futures_um_monthly_fundingRate_{sym}_*.zip")):
        fr.append(pd.read_csv(io.BytesIO(zipfile.ZipFile(f).read(zipfile.ZipFile(f).namelist()[0]))))
    df = pd.concat(fr)
    idx = _ts(df.calc_time.values).floor("h")
    s = pd.Series(df.last_funding_rate.values.astype(float), index=idx)
    return s[~s.index.duplicated()].sort_index()

def simulate(sym, sp, pp, fund, start, end, fee_name, z_enter, W, both):
    fs, fp = FEES[fee_name]
    sl = SLIP[sym]
    borrow_h = BORROW_APR / (365.25 * 24)

    # Align on intersection; need room for next-bar fill
    idx = sp.index.intersection(pp.index)
    idx = idx[(idx >= start) & (idx < end)]
    if len(idx) < W + 5:
        return dict(error="too_short", ann_return=-1.0, max_dd=-1.0, worst_month=-1.0,
                    liquidations=99, trades=0, fees_slippage=0.0, borrow_cost=0.0,
                    funding_net=0.0, basis_pnl=0.0, costs_coverage=0.0, final=1.0,
                    years=0.0, time_in_market=0.0, yearly={}, monthly={},
                    min_margin_ratio=None, start=None, end=None)

    S_c = sp.c.reindex(idx).values
    S_h = sp.h.reindex(idx).values
    S_l = sp.l.reindex(idx).values
    F_c = pp.c.reindex(idx).values
    F_h = pp.h.reindex(idx).values
    F_l = pp.l.reindex(idx).values
    F_o = pp.o.reindex(idx).values
    basis = (F_c - S_c) / S_c
    # z at bar t using only data <= t (rolling on basis series)
    bser = pd.Series(basis, index=idx)
    roll_m = bser.rolling(W, min_periods=W).mean()
    roll_s = bser.rolling(W, min_periods=W).std(ddof=0)
    z = ((bser - roll_m) / roll_s.replace(0, np.nan)).values
    fset = fund.reindex(idx)  # funding printed at bar open

    cash = 1.0
    # side: 0 flat, +1 LONG_BASIS (long spot short perp), -1 SHORT_BASIS
    side = 0
    q = 0.0          # coin qty
    Fref = 0.0       # perp entry ref for unrealized
    Sref = 0.0       # spot entry ref (for short spot MTM)
    marg_p = 0.0     # perp margin
    marg_s = 0.0     # spot margin (SHORT_BASIS only; long spot is fully paid)
    entry_basis = 0.0
    entry_i = -1
    pending = None   # ("enter"|"exit", side_wanted) decided at t, fill at t+1

    fund_in = fund_out = cost = borrow = 0.0
    basis_pnl = 0.0  # realized basis/price residual tracked via equity path
    trades = liq = 0
    minratio = 9.0
    n = len(idx)
    eq = np.empty(n)
    inpos = np.zeros(n, bool)

    def equity_now(Si, Fi):
        if side == 0:
            return cash
        if side == 1:  # long spot, short perp
            return cash + q * Si + marg_p + q * (Fref - Fi)
        # side == -1: short spot, long perp
        # short spot MTM: marg_s + q*(Sref - Si); long perp: marg_p + q*(Fi - Fref)
        return cash + marg_s + q * (Sref - Si) + marg_p + q * (Fi - Fref)

    def open_long_basis(E, S, F):
        """Long spot + short perp. Capital: spot notional + perp/L."""
        nonlocal q, Fref, Sref, marg_p, marg_s, cost, side
        # qq * S*(1+sl+fs) + qq*F/L + qq*F*(fp+sl) = E  (approx; leftover cash kept)
        denom = S * (1 + sl + fs) + F / L + F * (fp + sl)
        qq = E / denom
        c = qq * S * (sl + fs) + qq * F * (fp + sl)
        cost += c
        spot_spend = qq * S * (1 + sl + fs)
        marg_p = qq * F / L
        cash_left = E - spot_spend - marg_p - qq * F * (fp + sl)
        q, Fref, Sref, marg_s, side = qq, F, S, 0.0, 1
        return cash_left

    def open_short_basis(E, S, F):
        """Short spot + long perp. Both at L=2."""
        nonlocal q, Fref, Sref, marg_p, marg_s, cost, side
        # marg_s = qq*S/L, marg_p = qq*F/L, plus fees on both
        denom = S / L + F / L + S * (sl + fs) + F * (fp + sl)
        qq = E / denom
        c = qq * S * (sl + fs) + qq * F * (fp + sl)
        cost += c
        marg_s = qq * S / L
        marg_p = qq * F / L
        cash_left = E - marg_s - marg_p - c
        q, Fref, Sref, side = qq, F, S, -1
        return cash_left

    def close_pos(S, F):
        nonlocal q, Fref, Sref, marg_p, marg_s, cost, side, cash, basis_pnl
        c = q * S * (sl + fs) + q * F * (fp + sl)
        cost += c
        if side == 1:
            # sell spot, cover short perp
            v = q * S + marg_p + q * (Fref - F) - c
            # basis component approx: entry basis realization
            basis_pnl += q * ((Fref - Sref) - (F - S))
        else:
            # cover short spot (buy), sell long perp
            v = marg_s + q * (Sref - S) + marg_p + q * (F - Fref) - c
            basis_pnl += q * ((Sref - Fref) - (S - F))  # reverse basis capture
        q = Fref = Sref = marg_p = marg_s = 0.0
        side = 0
        return v

    for i in range(n):
        S, F = S_c[i], F_c[i]
        # 1) Accrue funding on open position at funding print (bar open)
        r = fset.iloc[i]
        if not np.isnan(r) and side != 0:
            # short perp receives +r * notional when r>0; long perp pays
            notional_o = q * F_o[i]
            if side == 1:  # short perp
                amt = r * notional_o
                marg_p += amt
            else:  # long perp
                amt = -r * notional_o
                marg_p += amt
            if amt >= 0:
                fund_in += amt
            else:
                fund_out += -amt

        # 2) Borrow cost on short spot (hourly)
        if side == -1 and q > 0:
            b = borrow_h * q * S
            marg_s -= b
            borrow += b

        # 3) Liquidation checks on bar extremes
        if side == 1 and q > 0:
            # short perp hurt by HIGH; long spot hurt by LOW (but long spot unlevered — no liq on spot)
            e_hi = marg_p + q * (Fref - F_h[i])
            minratio = min(minratio, e_hi / (q * F_h[i] + 1e-12))
            if e_hi <= MM * q * F_h[i]:
                liq += 1
                # lose perp margin; sell spot
                c = q * S * (sl + fs)
                cost += c
                cash += q * S - c
                q = Fref = Sref = marg_p = marg_s = 0.0
                side = 0
                pending = None
        elif side == -1 and q > 0:
            # long perp hurt by LOW; short spot hurt by HIGH
            e_p = marg_p + q * (F_l[i] - Fref)
            e_s = marg_s + q * (Sref - S_h[i])
            minratio = min(minratio, e_p / (q * F_l[i] + 1e-12), e_s / (q * S_h[i] + 1e-12))
            if e_p <= MM * q * F_l[i] or e_s <= MM * q * S_h[i]:
                liq += 1
                # both margins lost conceptually; force flat with remaining
                c = q * S * (sl + fs) + q * F * (fp + sl)
                cost += c
                # residual: if spot short liquidated, marg_s~0; perp similarly
                cash += max(0.0, e_p) + max(0.0, e_s) - c
                # clamp
                if cash < 0:
                    cash = 0.0
                q = Fref = Sref = marg_p = marg_s = 0.0
                side = 0
                pending = None

        # 4) Execute pending decision from previous bar (fill at this bar close)
        if pending is not None and side == 0 and pending[0] == "enter":
            want = pending[1]
            E = cash
            if want == 1:
                cash = open_long_basis(E, S, F)
            else:
                cash = open_short_basis(E, S, F)
            entry_basis = (F - S) / S
            entry_i = i
            trades += 1
            pending = None
        elif pending is not None and side != 0 and pending[0] == "exit":
            cash += close_pos(S, F)
            trades += 1
            pending = None
            entry_i = -1

        # 5) Decide at this bar close using z[i]; schedule fill for next bar
        zi = z[i]
        if pending is None:
            if side == 0:
                if not np.isnan(zi) and i + 1 < n:
                    if zi >= z_enter:
                        pending = ("enter", 1)
                    elif both and zi <= -z_enter:
                        pending = ("enter", -1)
            else:
                held = i - entry_i
                cur_b = basis[i]
                adverse = False
                if side == 1 and cur_b > entry_basis + STOP_BP:
                    adverse = True
                if side == -1 and cur_b < entry_basis - STOP_BP:
                    adverse = True
                revert = False
                if not np.isnan(zi):
                    if abs(zi) <= Z_EXIT:
                        revert = True
                    # crossed 0 toward mean from entry side
                    if side == 1 and cur_b <= 0:
                        revert = True
                    if side == -1 and cur_b >= 0:
                        revert = True
                if (revert or adverse or held >= H_MAX) and i + 1 < n:
                    pending = ("exit", 0)

        eq[i] = equity_now(S, F)
        inpos[i] = side != 0

    # Force mark exit cost at end if still open
    final_mtm = eq[-1]
    if side != 0:
        S, F = S_c[-1], F_c[-1]
        # hypothetical close cost
        c = q * S * (sl + fs) + q * F * (fp + sl)
        final_exit = final_mtm - c
        # also realize remaining basis into basis_pnl for reporting
        if side == 1:
            basis_pnl += q * ((Fref - Sref) - (F - S))
        else:
            basis_pnl += q * ((Sref - Fref) - (S - F))
    else:
        final_exit = final_mtm

    e = pd.Series(eq, index=idx)
    yrs = max((idx[-1] - idx[0]).total_seconds() / (365.25 * 86400), 1e-9)
    ann = final_exit ** (1 / yrs) - 1 if final_exit > 0 else -1.0
    dd = float((e / e.cummax() - 1).min()) if len(e) else 0.0
    mon = e.resample("ME").last()
    mon = pd.concat([pd.Series([1.0], index=[idx[0]]), mon]).pct_change().dropna()
    yr = e.resample("YE").last()
    yr = pd.concat([pd.Series([1.0], index=[idx[0]]), yr]).pct_change().dropna()
    costs_total = cost + borrow
    edge = basis_pnl + (fund_in - fund_out)
    cov = (edge / costs_total) if costs_total > 1e-12 else None
    return dict(
        start=str(idx[0]), end=str(idx[-1]), years=round(yrs, 3),
        final=float(final_exit), ann_return=float(ann), max_dd=float(dd),
        worst_month=float(mon.min()) if len(mon) else 0.0,
        worst_month_at=str(mon.idxmin())[:7] if len(mon) else None,
        funding_received=float(fund_in), funding_paid=float(fund_out),
        funding_net=float(fund_in - fund_out),
        fees_slippage=float(cost), borrow_cost=float(borrow),
        basis_pnl=float(basis_pnl), costs_coverage=float(cov) if cov is not None else None,
        trades=int(trades), liquidations=int(liq),
        min_margin_ratio=float(minratio) if minratio < 9 else None,
        time_in_market=float(inpos.mean()),
        yearly={str(k.year): float(v) for k, v in yr.items()},
        monthly={str(k)[:7]: float(v) for k, v in mon.items()},
    )

def main():
    out = {"params_sha256": LOCK, "strategy": "BASIS_MR_V1", "runs": {}}
    for sym in ["BTCUSDT", "ETHUSDT"]:
        sp, pp, fd = load_klines("spot", sym), load_klines("futures_um", sym), load_funding(sym)
        end = str(min(sp.index[-1], pp.index[-1]).date() + pd.Timedelta(days=1))[:10]
        out.setdefault("data_end", {})[sym] = str(min(sp.index[-1], pp.index[-1]))
        # basis stats
        j = sp.c.align(pp.c, join="inner")
        b = (j[1] - j[0]) / j[0]
        out.setdefault("basis_stats_bp", {})[sym] = {
            str(y): {
                "mean": float(g.mean() * 1e4),
                "std": float(g.std() * 1e4),
                "p01": float(g.quantile(0.01) * 1e4),
                "p99": float(g.quantile(0.99) * 1e4),
            }
            for y, g in b.groupby(b.index.year)
        }
        for fee in FEES:
            for vn, (ze, W, both) in VARIANTS.items():
                for per, (a, b_) in {
                    "IS": IS,
                    "OOS": (OOS_START, "2100-01-01"),
                    "FULL": ("2022-01-01", "2100-01-01"),
                }.items():
                    end_ts = pd.Timestamp(min(b_, end), tz="UTC") if b_ < end else pd.Timestamp(end, tz="UTC")
                    key = f"{sym}|{fee}|{vn}|{per}"
                    out["runs"][key] = simulate(
                        sym, sp, pp, fd,
                        pd.Timestamp(a, tz="UTC"), end_ts,
                        fee, ze, W, both,
                    )
                    r = out["runs"][key]
                    brief = {k: (round(v, 4) if isinstance(v, float) else v)
                             for k, v in r.items() if k not in ("monthly", "yearly")}
                    print(key, brief, flush=True)

    # Selection on IS BTC KRAKEN_RETAIL
    cand = {}
    for vn in VARIANTS:
        r = out["runs"][f"BTCUSDT|KRAKEN_RETAIL|{vn}|IS"]
        cand[vn] = (r["ann_return"], r["max_dd"])  # higher ann, then higher (less neg) dd
    sel = max(cand.keys(), key=lambda v: (cand[v][0], cand[v][1]))
    o = out["runs"][f"BTCUSDT|KRAKEN_RETAIL|{sel}|OOS"]
    i_ = out["runs"][f"BTCUSDT|KRAKEN_RETAIL|{sel}|IS"]
    yrs_ok = {y: o["yearly"].get(y, -1) > 0 for y in ("2024", "2025", "2026")}
    cov = o.get("costs_coverage") or 0
    crit = {
        "P1_ann>=8%": o["ann_return"] >= 0.08,
        "P2_maxDD<=8%": o["max_dd"] >= -0.08,
        "P3_worst_month>=-3%": o["worst_month"] >= -0.03,
        "P4_no_liquidation": o["liquidations"] == 0 and i_["liquidations"] == 0,
        "P5_edge>=2x_costs": cov >= 2.0,
        "P6_each_year_positive": all(yrs_ok.values()),
        "P7_IS_positive": i_["ann_return"] > 0,
    }
    out["selection"] = {
        "is_ann_by_variant": {k: cand[k][0] for k in cand},
        "is_dd_by_variant": {k: cand[k][1] for k in cand},
        "selected": sel,
        "criteria": crit,
        "yearly_ok": yrs_ok,
        "PASS": all(crit.values()),
        "oos_summary": {
            "ann_return": o["ann_return"],
            "max_dd": o["max_dd"],
            "worst_month": o["worst_month"],
            "trades": o["trades"],
            "fees_slippage": o["fees_slippage"],
            "borrow_cost": o["borrow_cost"],
            "basis_pnl": o["basis_pnl"],
            "funding_net": o["funding_net"],
            "costs_coverage": o["costs_coverage"],
            "time_in_market": o["time_in_market"],
            "yearly": o["yearly"],
        },
    }
    json.dump(out, open("results.json", "w"), indent=1, default=float)
    print("SELECTION", json.dumps(out["selection"], indent=1, default=str))

if __name__ == "__main__":
    main()
