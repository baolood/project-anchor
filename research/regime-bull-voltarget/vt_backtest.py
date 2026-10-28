#!/usr/bin/env python3
"""REGIME_BULL_VOLTARGET_V1 backtest. Implements PARAMS.md (sha256 in PARAMS.lock). No parameter is tuned.
Engine mechanics are a line-for-line port of regime-bull-v3/paper_track.py::simulate (same brake, band, liquidation, cost conventions);
only the target-exposure formula differs.  `python3 vt_backtest.py --selftest` runs synthetic-data checks only (never touches BTC)."""
import sys, os, json, math, io, glob, zipfile, hashlib
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
START = 10000.0
COST = 0.0015; COST_STRESS = 0.0045            # 10bp fee + 5bp slippage per side; stress = 40bp + 5bp
FUND_DAY = 0.0003                              # assumed perp funding: 0.03% of notional per day, paid by the long
TV = 0.60; CAP = 1.5; VOL_WIN = 60; SMA_WIN = 200; BAND = 0.10; BRAKE_FRAC = 0.80; MM = 0.005
JUDGE = ('2013-01-01', '2017-08-16')           # judged window (PRE)
INFO = ('2018-03-04', '2026-09-30')            # contaminated, information + veto only
NSEEDS = 1000; SEED0 = 20261028

def xnew(vol):  return min(CAP, TV / vol) if vol > 0 else CAP
def xv3(vol):   return 1.5 * min(1.0, 0.40 / vol) if vol > 0 else 1.5     # selftest only

# ---------------------------------------------------------------- engine (notional-based, perp-style line)
def run_lev(c, low, i0, i1, xfun, cost=COST, fund=FUND_DAY, brake_on=True, lev_cap=CAP):
    """Returns dict(eq[], x[] (post-trade exposure), act[], liq, brakes, trades). Row t earns r(t)=c[t]/c[t-1]-1 from the position decided at t-1."""
    n = i1 - i0; E = START; N = 0.0; pk_b = pk_rep = START
    brake = False; seen_off = False; dead = False
    eq = np.zeros(n); x_out = np.zeros(n); act = [''] * n; ddl = np.zeros(n)
    liq = 0; brakes = 0; trades = 0
    for j, t in enumerate(range(i0, i1)):
        r = c[t] / c[t-1] - 1.0; m = low[t] / c[t-1] - 1.0
        sma = c[t-SMA_WIN+1:t+1].mean()
        lr = np.log(c[t-VOL_WIN+1:t+1] / c[t-VOL_WIN:t]); vol = lr.std(ddof=1) * math.sqrt(365)
        regime = c[t] > sma; X = xfun(vol)
        a = ''
        if dead:
            E = 0.0; N = 0.0; a = 'DEAD'; ddl[j] = -1.0
        else:
            x = N / E if N > 0 else 0.0
            if N > 0 and (1 + x * m - MM * x * (1 + m)) <= 0:
                E = 0.0; N = 0.0; dead = True; liq += 1; a = 'LIQUIDATED'; ddl[j] = -1.0
            else:
                E_low = E * (1 + x * m) if N > 0 else E
                ddl[j] = E_low / pk_rep - 1
                trig = None
                if brake_on and N > 0 and not brake and E_low <= BRAKE_FRAC * pk_b:
                    E_cl = E + N * r
                    E_exit = min(BRAKE_FRAC * pk_b, E_cl)
                    N_exit = N * (1 + (E_exit / E - 1) / x)
                    E = E_exit - cost * max(N_exit, 0.0) - N * fund
                    N = 0.0; brake = True; seen_off = False; trig = 'intraday'; a = 'BRAKE intraday'; brakes += 1
                else:
                    E = E + N * r - N * fund; N = N * (1 + r)
                    if E > pk_b: pk_b = E
                    if brake_on and N > 0 and not brake and E <= BRAKE_FRAC * pk_b:
                        E -= cost * N; N = 0.0; brake = True; seen_off = False; trig = 'close'; a = 'BRAKE close'; brakes += 1
                x_cur = N / E if N > 0 else 0.0
                reentered = False
                if brake:
                    if trig != 'close':
                        if not regime: seen_off = True
                        if seen_off and regime:
                            brake = False; pk_b = E; reentered = True
                    if brake and not a: a = 'BRAKE ON'
                if not brake:
                    if not regime: tgt = 0.0
                    elif x_cur == 0.0: tgt = X
                    elif x_cur > lev_cap + 1e-12: tgt = X
                    elif abs(X - x_cur) >= BAND: tgt = X
                    else: tgt = None
                    if tgt is None: a = 'HOLD'
                    else:
                        Ntar = tgt * E; E -= cost * abs(Ntar - N); old = x_cur; N = Ntar
                        if abs(tgt - old) > 1e-12: trades += 1
                        a = 'REENTER' if reentered else ('ENTER' if (old == 0.0 and tgt > 0) else ('EXIT' if (tgt == 0.0 and old > 0) else ('FLAT' if tgt == 0.0 else 'REBAL')))
                if not brake and E > pk_b: pk_b = E
        pk_rep = max(pk_rep, E)
        eq[j] = E; x_out[j] = (N / E) if (N > 0 and E > 0) else 0.0; act[j] = a
    return dict(eq=eq, x=x_out, act=act, liq=liq, brakes=brakes, trades=trades, ddl=ddl)

# ---------------------------------------------------------------- spot-style V2 lines and buy-and-hold
def run_v2(c, i0, i1, target_vol, cost=COST, plain=False):
    n = i1 - i0; E = START; w = 0.0; eq = np.zeros(n); x_out = np.zeros(n); trades = 0
    for j, t in enumerate(range(i0, i1)):
        r = c[t] / c[t-1] - 1.0
        sma = c[t-SMA_WIN+1:t+1].mean()
        lr = np.log(c[t-VOL_WIN+1:t+1] / c[t-VOL_WIN:t]); vol = lr.std(ddof=1) * math.sqrt(365)
        regime = c[t] > sma
        sized = 1.0 if plain else (min(1.0, target_vol / vol) if vol > 0 else 1.0)
        E *= (1 + w * r)
        cur = w * (1 + r) / (1 + w * r) if w > 0 else 0.0
        if not regime: nb = 0.0
        elif cur == 0.0: nb = sized
        elif abs(sized - cur) >= 0.10: nb = sized
        else: nb = cur
        if abs(nb - cur) > 1e-12: trades += 1
        E *= (1 - cost * abs(nb - cur)); w = nb
        eq[j] = E; x_out[j] = w
    return dict(eq=eq, x=x_out, trades=trades)

def run_bh(c, i0, i1, cost=COST):
    n = i1 - i0; E = START; eq = np.zeros(n)
    for j, t in enumerate(range(i0, i1)):
        r = c[t] / c[t-1] - 1.0
        if j == 0: E *= (1 - cost)
        else: E *= (1 + r)
        eq[j] = E
    return dict(eq=eq)

# ---------------------------------------------------------------- metrics
def metrics(eq):
    n = len(eq); e = np.concatenate([[START], eq]); pk = np.maximum.accumulate(e); dd = e / pk - 1
    cagr = (e[-1] / START) ** (365.0 / n) - 1 if e[-1] > 0 else -1.0
    mdd = dd.min(); cal = cagr / max(abs(mdd), 1e-9)
    return dict(days=n, final=float(e[-1]), cagr=float(cagr), max_dd=float(mdd), calmar=float(cal))

def daily_ret(eq): e = np.concatenate([[START], eq]); return e[1:] / e[:-1] - 1

def zigzag(c):
    """Copied unchanged from regime-bull/rbs_backtest.py (V1/V2/V3 phase definition: 20% zig-zag; bull leg >= +50%, bear leg <= -30%)."""
    piv = []; mode = None; lo = hi = (0, c[0])
    for t in range(len(c)):
        p = c[t]
        if p > hi[1]: hi = (t, p)
        if p < lo[1]: lo = (t, p)
        if mode in (None, 'up') and p <= hi[1] * 0.8:
            if mode is None and lo[0] < hi[0]: piv.append((lo[0], 'T'))
            piv.append((hi[0], 'P')); mode = 'down'; lo = (t, p); hi = (t, p)
        elif mode in (None, 'down') and p >= lo[1] * 1.2:
            if mode is None and hi[0] < lo[0]: piv.append((hi[0], 'P'))
            piv.append((lo[0], 'T')); mode = 'up'; hi = (t, p); lo = (t, p)
    legs = []
    for (a, ka), (b, kb) in zip(piv[:-1], piv[1:]): legs.append((a, b, 'up' if ka == 'T' else 'down'))
    la, lk = piv[-1]
    if lk == 'T': j = la + int(np.argmax(c[la:])); legs.append((la, j, 'up_unfinished'))
    else: j = la + int(np.argmin(c[la:])); legs.append((la, j, 'down_unfinished'))
    out = []
    for a, b, k in legs:
        chg = c[b] / c[a] - 1
        if k.startswith('up') and chg >= 0.50: out.append(dict(kind='bull', start=a, end=b, chg=chg))
        if k.startswith('down') and chg <= -0.30: out.append(dict(kind='bear', start=a, end=b, chg=chg))
    return out

def phase_stats(legs, dates, i0, i1, strat_r, bh_r):
    """Phase days = D0+1..D1 inclusive (clipped to window [i0,i1)); capture = sum ln(1+r_strat)/sum ln(1+r_bh) over bull days."""
    n = i1 - i0; mb = np.zeros(n, bool); per_leg = []
    for L in legs:
        lo = max(L['start'] + 1, i0); hi = min(L['end'], i1 - 1)
        if hi < lo: continue
        m = np.zeros(n, bool); m[lo - i0:hi - i0 + 1] = True
        if L['kind'] == 'bull':
            mb |= m
            per_leg.append(dict(kind='bull', start=str(dates[L['start']])[:10], end=str(dates[L['end']])[:10], days=int(m.sum()),
                                capture=float(np.log1p(strat_r[m]).sum() / np.log1p(bh_r[m]).sum())))
        else:
            per_leg.append(dict(kind='bear', start=str(dates[L['start']])[:10], end=str(dates[L['end']])[:10], days=int(m.sum()),
                                strat_ret=float(np.prod(1 + strat_r[m]) - 1), bh_ret=float(np.prod(1 + bh_r[m]) - 1)))
    cap = float(np.log1p(strat_r[mb]).sum() / np.log1p(bh_r[mb]).sum()) if mb.sum() else None
    return dict(bull_days=int(mb.sum()), bull_capture=cap, legs=per_leg,
                n_bull=sum(1 for L in per_leg if L['kind'] == 'bull'), n_bear=sum(1 for L in per_leg if L['kind'] == 'bear'))

# ---------------------------------------------------------------- random-timing null (circular shift of the exposure series)
def replay(x, r, cost=COST, fund=FUND_DAY):
    """x[j] = exposure after the trade at the close of row j; r[j] = return of day j (earned by x[j-1]; row 0 starts flat)."""
    prev = np.concatenate([[0.0], x[:-1]])
    growth = 1 + prev * (r - fund)
    drift = np.where(prev > 0, prev * (1 + r) / np.where(growth > 0, growth, 1.0), 0.0)
    net = growth * (1 - cost * np.abs(x - drift)) - 1
    net = np.maximum(net, -1.0)
    return START * np.cumprod(1 + net)

def null_calmars(x, r, nseeds=NSEEDS, seed0=SEED0):
    n = len(x); out = []
    for s in range(nseeds):
        rng = np.random.default_rng(seed0 + s); k = int(rng.integers(30, n - 30 + 1))
        out.append(metrics(replay(np.roll(x, k), r))['calmar'])
    return np.array(out)

# ---------------------------------------------------------------- data
def load_pre():
    d = pd.read_csv(os.path.join(HERE, 'data/bitstamp_btcusd_daily_pre2017-08-17.csv'), parse_dates=['date']).set_index('date')
    return d[['open', 'high', 'low', 'close']].astype(float)
def load_binance():
    frames = []
    for f in sorted(glob.glob(os.path.join(HERE, '../regime-bull/data/BTCUSDT-1d-*.zip'))):
        with zipfile.ZipFile(f) as z: raw = z.read(z.namelist()[0])
        df = pd.read_csv(io.BytesIO(raw), header=None, usecols=[0, 1, 2, 3, 4]); df.columns = ['t', 'open', 'high', 'low', 'close']
        if df['t'].iloc[0] > 1e14: df['t'] = df['t'] // 1000
        frames.append(df)
    d = pd.concat(frames); d['date'] = pd.to_datetime(d['t'], unit='ms').dt.normalize()
    return d.drop_duplicates('date').set_index('date').sort_index().drop(columns='t').astype(float)
def integrity(d):
    full = pd.date_range(d.index[0], d.index[-1])
    return dict(rows=len(d), first=str(d.index[0].date()), last=str(d.index[-1].date()), missing_days=int(len(full.difference(d.index))),
                nonpositive=int((d[['open', 'high', 'low', 'close']] <= 0).sum().sum()), low_gt_close=int((d.low > d.close * 1.0000001).sum()))

# ---------------------------------------------------------------- one window, all lines
def evaluate(d, win, label, null=True):
    dates = d.index; c = d.close.values; low = d.low.values
    i0 = int(np.searchsorted(dates, pd.Timestamp(win[0]))); i1 = int(np.searchsorted(dates, pd.Timestamp(win[1]), side='right'))
    assert i0 >= SMA_WIN - 1, 'need >=200 closes up to and including the first decision (same as V3 simulate: t >= SMA_WIN-1)'
    out = dict(label=label, first_decision=str(dates[i0].date()), last_decision=str(dates[i1-1].date()), days=i1 - i0)
    new = run_lev(c, low, i0, i1, xnew); nb = run_lev(c, low, i0, i1, xnew, brake_on=False)
    new_gross = run_lev(c, low, i0, i1, xnew, cost=0.0, fund=0.0)
    new_st = run_lev(c, low, i0, i1, xnew, cost=COST_STRESS)
    v2b = run_v2(c, i0, i1, 0.40); v2a = run_v2(c, i0, i1, None, plain=True); bh = run_bh(c, i0, i1)
    bh_st = run_bh(c, i0, i1, COST_STRESS); v2b_st = run_v2(c, i0, i1, 0.40, cost=COST_STRESS); v2a_st = run_v2(c, i0, i1, None, cost=COST_STRESS, plain=True)
    L = {'NEW': new, 'NEW_NOBRAKE(info)': nb, 'V2b': v2b, 'V2a': v2a, 'BH': bh}
    out['lines'] = {k: metrics(v['eq']) for k, v in L.items()}
    for k, v in (('NEW', new), ('NEW_NOBRAKE(info)', nb), ('V2b', v2b), ('V2a', v2a)):
        out['lines'][k]['avg_exposure'] = float(v['x'].mean()); out['lines'][k]['trades'] = int(v['trades'])
    out['lines']['NEW']['brakes'] = new['brakes']; out['lines']['NEW']['liquidations'] = new['liq']
    out['lines']['NEW']['max_dd_intraday_low'] = float(min(new['ddl'].min(), out['lines']['NEW']['max_dd']))
    out['lines']['NEW']['max_exposure'] = float(new['x'].max())
    out['lines']['NEW']['fraction_days_at_cap'] = float((new['x'] >= CAP - 1e-6).mean())
    out['gross_cagr'] = metrics(new_gross['eq'])['cagr']
    out['stress45bp'] = {k: metrics(v['eq']) for k, v in (('NEW', new_st), ('V2b', v2b_st), ('V2a', v2a_st), ('BH', bh_st))}
    legs = zigzag(c)
    sr = daily_ret(new['eq']); br = daily_ret(bh['eq'])
    out['phases'] = phase_stats(legs, dates, i0, i1, sr, br)
    if null:
        r = (c[i0:i1] / c[i0-1:i1-1] - 1.0)
        x = new['x']; rep = metrics(replay(x, r))
        nul = null_calmars(x, r)
        out['null'] = dict(n=len(nul), p50=float(np.percentile(nul, 50)), p90=float(np.percentile(nul, 90)), p95=float(np.percentile(nul, 95)),
                           max=float(nul.max()), strat_calmar_engine=out['lines']['NEW']['calmar'], strat_calmar_replay=rep['calmar'],
                           pct_engine=float((nul < out['lines']['NEW']['calmar']).mean() * 100), pct_replay=float((nul < rep['calmar']).mean() * 100),
                           replay_cagr=rep['cagr'], engine_cagr=out['lines']['NEW']['cagr'])
    return out

# ---------------------------------------------------------------- verdict (rules exactly as PARAMS.md section "Pass bar")
def judge(ev):
    L = ev['lines']; N = L['NEW']; B = L['BH']; b = L['V2b']; a = L['V2a']; ph = ev['phases']; nu = ev['null']; V = {}
    V['G1_fee_gate'] = 'PASS' if (ev['gross_cagr'] > 0 and N['cagr'] >= 0.5 * ev['gross_cagr']) else 'FAIL'
    V['C0_no_liquidation'] = 'PASS' if N['liquidations'] == 0 else 'FAIL'
    V['C1_survive'] = 'PASS' if (N['max_dd'] >= -0.30 and N['max_dd'] > B['max_dd']) else 'FAIL'
    V['C2_bull_capture'] = 'PASS' if (ph['bull_capture'] is not None and ph['bull_capture'] >= 0.50) else 'FAIL'
    V['C3_vs_buyhold_return_or_calmar'] = 'PASS' if (N['cagr'] >= 0.70 * B['cagr'] or N['calmar'] > B['calmar']) else 'FAIL'
    V['C4_vs_V2'] = 'PASS' if (N['calmar'] > b['calmar'] and N['calmar'] > a['calmar'] and N['cagr'] > b['cagr'] and N['max_dd'] >= b['max_dd'] - 0.05) else 'FAIL'
    lo = min(nu['strat_calmar_engine'], nu['strat_calmar_replay'])
    V['C5_random_timing'] = 'PASS' if lo > nu['p95'] else ('WARN' if lo > nu['p90'] else 'FAIL')
    V['C6_cycle_test'] = 'PASS' if (ph['n_bull'] >= 1 and ph['n_bear'] >= 1) else 'INSUFFICIENT'
    vals = list(V.values())
    if V['G1_fee_gate'] == 'FAIL': overall = 'REJECT (fee gate)'
    elif 'FAIL' in vals: overall = 'FAIL'
    elif 'INSUFFICIENT' in vals: overall = 'INSUFFICIENT'
    elif 'WARN' in vals: overall = 'NOT PASS (conditional)'
    else: overall = 'PASS'
    return V, overall

def veto(info):
    N = info['lines']['NEW']
    flags = []
    if N['liquidations'] > 0: flags.append('liquidation in INFO window')
    if N['max_dd'] < -0.40: flags.append(f"INFO max drawdown {N['max_dd']:.1%} worse than -40%")
    return flags

def main():
    pre = load_pre(); bn = load_binance()
    out = dict(integrity=dict(pre=integrity(pre), binance=integrity(bn)))
    for k, v in out['integrity'].items():
        if v['missing_days'] or v['nonpositive'] or v['low_gt_close']: print('INTEGRITY FAILURE', k, v); json.dump(out, open(os.path.join(HERE, 'results.json'), 'w'), indent=1); sys.exit(2)
    ev = evaluate(pre, JUDGE, 'PRE 2013-01-01..2017-08-16 (JUDGED)')
    V, overall = judge(ev)
    info = evaluate(bn, INFO, 'INFO Binance 2018-03-04..2026-09-30 (contaminated, veto only)', null=True)
    flags = veto(info)
    final = overall if not (overall == 'PASS' and flags) else 'PASS_PRE_BUT_VETOED (not promoted): ' + '; '.join(flags)
    out.update(judged=ev, criteria=V, overall_pre=overall, info=info, veto_flags=flags, final=final,
               hashes=dict(script=hashlib.sha256(open(__file__, 'rb').read()).hexdigest()))
    json.dump(out, open(os.path.join(HERE, 'results.json'), 'w'), indent=1, default=float)
    print(json.dumps(dict(criteria=V, overall_pre=overall, veto=flags, final=final, lines=ev['lines'], phases={k: v for k, v in ev['phases'].items() if k != 'legs'}, null=ev['null']), indent=1, default=float))

# ---------------------------------------------------------------- synthetic self-test (no BTC data)
def selftest():
    sys.path.insert(0, os.path.join(HERE, '../regime-bull-v3'))
    import paper_track as pt
    rng = np.random.default_rng(7); n = 1500
    # regime-switching synthetic price path (not BTC)
    mu = np.where((np.arange(n) // 250) % 2 == 0, 0.0015, -0.0020); sd = np.where((np.arange(n) // 125) % 2 == 0, 0.02, 0.045)
    ret = rng.normal(mu, sd); c = 100 * np.exp(np.cumsum(ret)); low = c * (1 - np.abs(rng.normal(0, 0.012, n)))
    low = np.minimum(low, np.minimum(c, np.roll(c, 1)))
    dates = [(pd.Timestamp('2020-01-01') + pd.Timedelta(days=i)).strftime('%Y-%m-%d') for i in range(n)]
    fund = [FUND_DAY] * n; i0 = 250; i1 = n
    ref = pt.simulate(dates, c.tolist(), low.tolist(), fund, i0, i1)
    mine = run_lev(c, low, i0, i1, xv3, lev_cap=1.5)
    d1 = np.max(np.abs(mine['eq'] - np.array([r['eq_v3'] for r in ref])) / np.array([r['eq_v3'] for r in ref]))
    v2 = run_v2(c, i0, i1, 0.40); d2 = np.max(np.abs(v2['eq'] - np.array([r['eq_b1'] for r in ref])) / np.array([r['eq_b1'] for r in ref]))
    bh = run_bh(c, i0, i1); d3 = np.max(np.abs(bh['eq'] - np.array([r['eq_bh'] for r in ref])) / np.array([r['eq_bh'] for r in ref]))
    print('selftest: max rel diff vs V3 engine  lev-line %.2e  V2b %.2e  BH %.2e   brakes=%d liq=%d' % (d1, d2, d3, mine['brakes'], mine['liq']))
    assert d1 < 1e-9 and d2 < 1e-9 and d3 < 1e-9
    nw = run_lev(c, low, i0, i1, xnew)
    assert nw["x"].max() <= CAP * (1 + 0.003) and (nw['x'] >= 0).all() and (nw['eq'] > 0).all()
    rep = metrics(replay(nw['x'], c[i0:i1] / c[i0-1:i1-1] - 1.0)); eng = metrics(nw['eq'])
    print('selftest: new-line engine cagr %.4f replay cagr %.4f (replay ignores brake gap fills; should be close)' % (eng['cagr'], rep['cagr']))
    nul = null_calmars(nw['x'], c[i0:i1] / c[i0-1:i1-1] - 1.0, nseeds=50)
    assert len(nul) == 50 and np.isfinite(nul).all()
    legs = zigzag(c); print('selftest: zigzag legs', len(legs)); print('SELFTEST OK')

if __name__ == '__main__':
    if '--selftest' in sys.argv: selftest()
    else: main()
