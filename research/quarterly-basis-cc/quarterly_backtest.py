#!/usr/bin/env python3
"""QUARTERLY_BASIS_CC_V1 — locked by PARAMS.md / PARAMS.lock."""
from __future__ import annotations
import csv, hashlib, io, json, math, os, sys, urllib.request, zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
LOCK = open("PARAMS.lock").read().split()[0]
assert hashlib.sha256(open("PARAMS.md", "rb").read()).hexdigest() == LOCK, "PARAMS.md changed after lock"

DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

IS = (pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2024-01-01", tz="UTC"))
OOS_START = pd.Timestamp("2024-01-01", tz="UTC")
L, MM = 2.0, 0.005
REB_LO, REB_HI = 0.30, 0.70
FEES = {"KRAKEN_RETAIL": (0.0040, 0.0005), "TIER1_CEX": (0.0010, 0.0005)}
SLIP = 0.0002
EXIT_BP, D_EXIT, STOP_BP = 0.0, 2, 80.0
VARIANTS = [
    {"id": "M130_D90", "min_bp": 130.0, "d_entry_max": 90},
    {"id": "M150_D90", "min_bp": 150.0, "d_entry_max": 90},
    {"id": "M200_D90", "min_bp": 200.0, "d_entry_max": 90},
    {"id": "M130_D60", "min_bp": 130.0, "d_entry_max": 60},
    {"id": "M150_D60", "min_bp": 150.0, "d_entry_max": 60},
    {"id": "M200_D60", "min_bp": 200.0, "d_entry_max": 60},
]

# Contracts with expiry in window (Binance UM dated)
SYMBOLS = [
    "BTCUSDT_220325","BTCUSDT_220624","BTCUSDT_220930","BTCUSDT_221230",
    "BTCUSDT_230331","BTCUSDT_230630","BTCUSDT_230929","BTCUSDT_231229",
    "BTCUSDT_240329","BTCUSDT_240628","BTCUSDT_240927","BTCUSDT_241227",
    "BTCUSDT_250328","BTCUSDT_250627","BTCUSDT_250926","BTCUSDT_251226",
    "BTCUSDT_260327","BTCUSDT_260626","BTCUSDT_260925",
]

def expiry_of(sym: str) -> pd.Timestamp:
    d = sym.split("_")[1]
    return pd.Timestamp(datetime(2000+int(d[0:2]), int(d[2:4]), int(d[4:6]), 8, 0, tzinfo=timezone.utc))

def _norm_ts_ms(x: int) -> int:
    if x > 1e14:  # us
        x //= 1000
    return int(x)

def download_zip(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 100:
        return True
    try:
        with urllib.request.urlopen(url, timeout=90) as r:
            dest.write_bytes(r.read())
        return True
    except Exception as e:
        if dest.exists():
            dest.unlink()
        return False

def ensure_spot_months(years_months):
    for y, m in years_months:
        path = DATA / f"spot_monthly_klines_BTCUSDT_1h_BTCUSDT-1h-{y}-{m:02d}.zip"
        url = f"https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-{y}-{m:02d}.zip"
        ok = download_zip(url, path)
        if not ok:
            print(f"WARN missing spot {y}-{m:02d}", flush=True)

def ensure_fut_months(sym, years_months):
    for y, m in years_months:
        path = DATA / f"um_monthly_klines_{sym}_1h_{sym}-1h-{y}-{m:02d}.zip"
        url = f"https://data.binance.vision/data/futures/um/monthly/klines/{sym}/1h/{sym}-1h-{y}-{m:02d}.zip"
        ok = download_zip(url, path)
        if not ok:
            print(f"WARN missing {sym} {y}-{m:02d}", flush=True)

def read_klines_zip(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as zf:
        raw = zf.read(zf.namelist()[0]).decode()
    rows = []
    for row in csv.reader(io.StringIO(raw)):
        if not row or str(row[0]).startswith("open"):
            continue
        t = _norm_ts_ms(int(float(row[0])))
        rows.append((t, float(row[1]), float(row[2]), float(row[3]), float(row[4])))
    df = pd.DataFrame(rows, columns=["t", "o", "h", "l", "c"])
    df.index = pd.to_datetime(df.t, unit="ms", utc=True)
    return df[~df.index.duplicated()].sort_index()[["o", "h", "l", "c"]]

def load_spot() -> pd.DataFrame:
    frames = []
    for p in sorted(DATA.glob("spot_monthly_klines_BTCUSDT_1h_*.zip")):
        frames.append(read_klines_zip(p))
    if not frames:
        raise SystemExit("no spot data")
    df = pd.concat(frames)
    return df[~df.index.duplicated()].sort_index()

def load_fut(sym: str) -> pd.DataFrame:
    frames = []
    for p in sorted(DATA.glob(f"um_monthly_klines_{sym}_1h_*.zip")):
        frames.append(read_klines_zip(p))
    if not frames:
        return pd.DataFrame(columns=["o", "h", "l", "c"])
    df = pd.concat(frames)
    return df[~df.index.duplicated()].sort_index()

def months_covering(start: pd.Timestamp, end: pd.Timestamp):
    cur = pd.Timestamp(year=start.year, month=start.month, day=1, tz="UTC")
    out = []
    while cur <= end:
        out.append((cur.year, cur.month))
        cur = (cur + pd.offsets.MonthBegin(1))
    return out

def fetch_all():
    print("Fetching archive zips…", flush=True)
    # spot 2021-12 → 2026-10
    ym = months_covering(pd.Timestamp("2021-12-01", tz="UTC"), pd.Timestamp("2026-10-01", tz="UTC"))
    ensure_spot_months(ym)
    for sym in SYMBOLS:
        exp = expiry_of(sym)
        start = exp - pd.Timedelta(days=120)
        ensure_fut_months(sym, months_covering(start, exp))
    print("Fetch done.", flush=True)


@dataclass
class Trade:
    sym: str
    entry_time: str
    exit_time: str
    entry_basis_bp: float
    exit_basis_bp: float
    gross_basis: float
    costs: float
    net: float
    reason: str


def simulate(spot: pd.DataFrame, futs: dict, start, end, fee_name: str, min_bp: float, d_entry_max: int):
    fs, ff = FEES[fee_name]
    sl = SLIP
    # Build unified hourly index from spot in [start, end)
    idx = spot.index[(spot.index >= start) & (spot.index < end)]
    cash = 1.0
    q = 0.0
    Fref = 0.0
    marg = 0.0
    cur_sym = None
    entry_basis = None
    used_syms = set()
    pending = None  # ("enter"|"exit", sym, reason) decided at t, execute at t+1
    cost_tot = 0.0
    basis_gross = 0.0
    trades: list[Trade] = []
    liq = 0
    reb = 0
    minratio = 9.0
    eq = []
    eq_idx = []
    open_meta = None

    def open_pos(E, S, F):
        nonlocal q, Fref, marg, cost_tot
        qq = E / (S * (1 + sl + fs) + F / L + F * (ff + sl))
        c = qq * S * (sl + fs) + qq * F * (ff + sl)
        cost_tot += c
        leftover = E - qq * S * (1 + sl + fs) - qq * F / L - qq * F * (ff + sl)
        q, Fref, marg = qq, F, qq * F / L
        return leftover

    def close_pos(S, F):
        nonlocal q, Fref, marg, cost_tot, basis_gross
        c = q * S * (sl + fs) + q * F * (ff + sl)
        cost_tot += c
        # basis P&L approx: short fut (Fref-F)*q + spot (S_exit - S_entry)*q but we track via equity
        # Record gross basis contribution as entry_basis * notional_spot proxy
        v = q * S + marg + q * (Fref - F) - c
        q = Fref = marg = 0.0
        return v

    spot_c = spot["c"]
    spot_re = spot.reindex(idx)

    for i, t in enumerate(idx):
        S = float(spot_re.at[t, "c"])
        # Determine active contract prices if in position or for signal
        F = None
        F_h = None
        days_left = None
        sym_for_signal = None

        if q > 0 and cur_sym:
            fut = futs[cur_sym]
            if t not in fut.index:
                # missing bar: mark with last
                if len(fut.loc[:t]) == 0:
                    eq.append(cash); eq_idx.append(t); continue
                row = fut.loc[:t].iloc[-1]
                F, F_h = float(row["c"]), float(row["h"])
            else:
                F = float(fut.at[t, "c"]); F_h = float(fut.at[t, "h"])
            days_left = (expiry_of(cur_sym) - t).total_seconds() / 86400.0

        # Liquidation check
        if q > 0 and F is not None:
            e_hi = marg + q * (Fref - F_h)
            notional = q * F_h
            if notional > 0:
                minratio = min(minratio, e_hi / notional)
                if e_hi <= MM * notional:
                    liq += 1
                    c = q * S * (sl + fs); cost_tot += c
                    cash += q * S - c
                    if open_meta:
                        trades.append(Trade(cur_sym, open_meta["t"], str(t), open_meta["basis"],
                                            (F - S) / S * 1e4 if S else 0, 0.0, cost_tot - open_meta["cost_at_entry"],
                                            cash - open_meta["eq_before"], "LIQUIDATION"))
                    q = Fref = marg = 0.0; cur_sym = None; entry_basis = None; open_meta = None
                    pending = None

        # Execute pending from prior bar (no look-ahead)
        if pending and q == 0 and pending[0] == "enter":
            _, psym, _ = pending
            fut = futs[psym]
            if t in fut.index:
                Fexec = float(fut.at[t, "c"])
                beq = cash
                basis_e = (Fexec - S) / S * 1e4
                cash = open_pos(cash, S, Fexec)
                cur_sym = psym; entry_basis = basis_e; used_syms.add(psym)
                open_meta = {"t": str(t), "basis": basis_e, "cost_at_entry": cost_tot, "eq_before": beq, "S": S, "F": Fexec}
                # gross expected ≈ basis_e/1e4 * spot notional ≈ basis captured if converges
            pending = None
        elif pending and q > 0 and pending[0] == "exit":
            reason = pending[2]
            fut = futs[cur_sym]
            Fexec = float(fut.at[t, "c"]) if t in fut.index else float(fut.loc[:t].iloc[-1]["c"])
            beq = cash + q * S + marg + q * (Fref - Fexec)
            # gross basis: value change attributable to convergence vs entry
            S0, F0 = open_meta["S"], open_meta["F"]
            # PnL spot + short fut before costs already in beq path; isolate basis:
            # entry: long S0 short F0; exit long S short F → (S-S0) - (F-F0) per coin = (F0-S0) - (F-S)
            gross_b = q * ((F0 - S0) - (Fexec - S))
            basis_gross += gross_b
            costs_trade = (cost_tot - open_meta["cost_at_entry"])  # will add exit costs in close
            cash = close_pos(S, Fexec)
            costs_trade = cost_tot - open_meta["cost_at_entry"]
            net = cash - open_meta["eq_before"]
            trades.append(Trade(cur_sym, open_meta["t"], str(t), open_meta["basis"],
                                (Fexec - S) / S * 1e4, gross_b, costs_trade, net, reason))
            cur_sym = None; entry_basis = None; open_meta = None; pending = None

        # Mark
        if q > 0 and cur_sym:
            fut = futs[cur_sym]
            if t in fut.index:
                Fm = float(fut.at[t, "c"])
            else:
                Fm = float(fut.loc[:t].iloc[-1]["c"]) if len(fut.loc[:t]) else Fref
            equity = cash + q * S + marg + q * (Fref - Fm)
            # rebalance
            ratio = (marg + q * (Fref - Fm)) / (q * Fm) if q * Fm else 1
            if ratio < REB_LO or ratio > REB_HI:
                E = q * S + marg + q * (Fref - Fm)
                dq_est = abs(q - E / (S + Fm / L))
                c = dq_est * S * (sl + fs) + dq_est * Fm * (ff + sl)
                cost_tot += c; E -= c
                qn = E / (S + Fm / L)
                q, Fref, marg = qn, Fm, qn * Fm / L
                reb += 1
                equity = cash + q * S + marg  # cash~0 leftover ignored
        else:
            equity = cash

        eq.append(equity); eq_idx.append(t)

        # Decisions at close → pending for next bar
        if pending:
            continue
        if q > 0 and cur_sym:
            days_left = (expiry_of(cur_sym) - t).total_seconds() / 86400.0
            fut = futs[cur_sym]
            Fm = float(fut.at[t, "c"]) if t in fut.index else float(fut.loc[:t].iloc[-1]["c"])
            basis_now = (Fm - S) / S * 1e4
            reason = None
            if days_left <= D_EXIT:
                reason = "EXPIRY_NEAR"
            elif basis_now <= EXIT_BP:
                reason = "BASIS_FLAT"
            elif entry_basis is not None and basis_now >= entry_basis + STOP_BP:
                reason = "STOP_WIDEN"
            if reason:
                pending = ("exit", cur_sym, reason)
        elif q == 0:
            # find any contract in entry window with basis >= min_bp, not used
            best = None
            for sym in SYMBOLS:
                if sym in used_syms:
                    continue
                exp = expiry_of(sym)
                dl = (exp - t).total_seconds() / 86400.0
                if not (D_EXIT < dl <= d_entry_max):
                    continue
                fut = futs.get(sym)
                if fut is None or t not in fut.index:
                    continue
                Fm = float(fut.at[t, "c"])
                bp = (Fm - S) / S * 1e4
                if bp >= min_bp:
                    # prefer largest basis
                    if best is None or bp > best[1]:
                        best = (sym, bp)
            if best:
                pending = ("enter", best[0], "SIGNAL")

    e = pd.Series(eq, index=pd.DatetimeIndex(eq_idx, tz="UTC"))
    e = e[~e.index.duplicated(keep="last")].sort_index()
    if len(e) < 2:
        return None
    # force flat at end for fair exit-cost equity
    final = float(e.iloc[-1])
    yrs = max((e.index[-1] - e.index[0]).total_seconds() / (365.25 * 86400), 1e-9)
    ann = (final ** (1 / yrs) - 1) * 100 if final > 0 else -100.0
    # max DD
    peak = e.cummax()
    dd = ((peak - e) / peak).max() * 100
    # monthly
    m = e.resample("ME").last().pct_change().dropna() * 100
    worst_m = float(m.min()) if len(m) else 0.0
    by_year = {}
    for y, g in e.groupby(e.index.year):
        if len(g) < 2:
            continue
        by_year[int(y)] = float(g.iloc[-1] / g.iloc[0] - 1) * 100
    closed = [t for t in trades if t.reason != "LIQUIDATION" or True]
    n_closed = len(trades)
    sum_gross = sum(t.gross_basis for t in trades)
    sum_costs = sum(t.costs for t in trades) if trades else cost_tot
    # costs may double-count across trades if cost_tot shared; prefer per-trade costs sum
    if sum_costs <= 0:
        sum_costs = cost_tot
    edge_x = (sum_gross / sum_costs) if sum_costs > 0 else 0.0
    return {
        "ann_pct": ann,
        "final_eq": final,
        "max_dd_pct": -float(dd),
        "worst_month_pct": worst_m,
        "liq": liq,
        "reb": reb,
        "n_trades": n_closed,
        "basis_gross": sum_gross,
        "costs": sum_costs,
        "edge_x": edge_x,
        "min_margin_ratio": minratio,
        "by_year": by_year,
        "trades": [t.__dict__ for t in trades],
        "yrs": yrs,
    }


def main():
    fetch_all()
    spot = load_spot()
    futs = {sym: load_fut(sym) for sym in SYMBOLS}
    futs = {k: v for k, v in futs.items() if len(v) > 100}
    print("contracts loaded:", list(futs.keys()), flush=True)

    results = {"variants": {}, "selected": None, "criteria": {}, "fee_gate": {
        "cost_rt_bp": 65, "min_bp_floor": 130, "probe": "../_fee_gate_probe/quarterly_basis_probe.json"
    }}

    # Run all variants IS + OOS under KRAKEN, and OOS TIER1 for selected later
    is_scores = []
    for v in VARIANTS:
        for fee in ["KRAKEN_RETAIL"]:
            r_is = simulate(spot, futs, IS[0], IS[1], fee, v["min_bp"], v["d_entry_max"])
            r_oos = simulate(spot, futs, OOS_START, pd.Timestamp("2026-10-01", tz="UTC"), fee, v["min_bp"], v["d_entry_max"])
            key = f"{v['id']}|{fee}"
            results["variants"][key] = {"IS": r_is, "OOS": r_oos, **v}
            if r_is:
                is_scores.append((v["id"], r_is["ann_pct"], r_is["max_dd_pct"], v))
            print(f"{v['id']} IS ann={r_is and r_is['ann_pct']:.2f} n={r_is and r_is['n_trades']} | "
                  f"OOS ann={r_oos and r_oos['ann_pct']:.2f} n={r_oos and r_oos['n_trades']}", flush=True)

    # select
    is_scores.sort(key=lambda x: (-x[1], x[2]))  # high ann, then better (less neg) dd — max_dd stored negative
    if not is_scores:
        print("No IS results"); sys.exit(1)
    # max_dd_pct is negative number like -5; "lower IS max DD" means less drawdown → higher (closer to 0)
    selected_id, _, _, selected_v = is_scores[0]
    results["selected"] = selected_id
    sel = results["variants"][f"{selected_id}|KRAKEN_RETAIL"]
    # secondary tier1 OOS
    r_t1 = simulate(spot, futs, OOS_START, pd.Timestamp("2026-10-01", tz="UTC"), "TIER1_CEX",
                    selected_v["min_bp"], selected_v["d_entry_max"])
    results["variants"][f"{selected_id}|TIER1_CEX"] = {"IS": None, "OOS": r_t1, **selected_v}

    oos = sel["OOS"]; isr = sel["IS"]
    def ok(c): return "PASS" if c else "FAIL"
    crit = {}
    crit["P1"] = {"rule": "OOS ann >= 8%", "value": oos["ann_pct"] if oos else None,
                  "result": ok(oos and oos["ann_pct"] >= 8.0)}
    crit["P2"] = {"rule": "OOS maxDD <= 8%", "value": oos["max_dd_pct"] if oos else None,
                  "result": ok(oos and abs(oos["max_dd_pct"]) <= 8.0)}
    crit["P3"] = {"rule": "OOS worst month >= -3%", "value": oos["worst_month_pct"] if oos else None,
                  "result": ok(oos and oos["worst_month_pct"] >= -3.0)}
    crit["P4"] = {"rule": "zero liq IS+OOS", "value": (isr["liq"] if isr else None, oos["liq"] if oos else None),
                  "result": ok(isr and oos and isr["liq"] == 0 and oos["liq"] == 0)}
    crit["P5"] = {"rule": "edge >= 2x costs", "value": oos["edge_x"] if oos else None,
                  "result": ok(oos and oos["edge_x"] >= 2.0)}
    # P6: years with >=1 closed trade must be >0
    year_fail = False
    year_vals = {}
    if oos:
        # map trades to years
        ty = {}
        for t in oos["trades"]:
            y = int(t["exit_time"][:4])
            ty.setdefault(y, 0)
            ty[y] += t["net"]
        for y, net in ty.items():
            # approximate year return from trade nets on starting 1.0 is imperfect; use by_year if trades
            year_vals[y] = oos["by_year"].get(y)
            if year_vals[y] is not None and year_vals[y] <= 0:
                year_fail = True
        if not ty:
            year_fail = False  # N/A years — per PARAMS, zero-trade years don't fail; but P8 may fail
    crit["P6"] = {"rule": "years with trades >0", "value": year_vals,
                  "result": ok(oos and not year_fail and (len(year_vals) > 0 or oos["n_trades"] == 0))}
    # Re-read P6: "years with zero trades are N/A and do not fail". If we have trades in a year and return <=0 → fail.
    # If no trades at all, P6 passes vacuously but P8 fails.
    if oos and oos["n_trades"] == 0:
        crit["P6"]["result"] = "PASS"
        crit["P6"]["note"] = "no OOS trades; N/A years"
    crit["P7"] = {"rule": "IS net positive", "value": isr["ann_pct"] if isr else None,
                  "result": ok(isr and isr["final_eq"] > 1.0)}
    crit["P8"] = {"rule": "OOS closed trades >= 3", "value": oos["n_trades"] if oos else None,
                  "result": ok(oos and oos["n_trades"] >= 3)}
    results["criteria"] = crit
    results["overall"] = "PASS" if all(c["result"] == "PASS" for c in crit.values()) else "FAIL"

    out = ROOT / "results.json"
    out.write_text(json.dumps(results, indent=2, default=str))
    print("OVERALL", results["overall"], "selected", selected_id)
    print(json.dumps(crit, indent=2, default=str))
    return results

if __name__ == "__main__":
    main()
