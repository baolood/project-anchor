"""EVAL_PASS_PROB_V1 shared code: trade extraction (risk-normalised) + vectorised eval Monte Carlo. Research only; no orders."""
import sys, json, hashlib, random, math
import numpy as np
sys.path.insert(0, '/workspace/eval-watcher/backtests/recent-regime-screen')
import screen as SC
E = SC.E
FEE = 0.0004; MFD = 0.00033
DATA = '/workspace/eval-watcher/backtests/fade-long-line'

def check_lock(d):
    h = hashlib.sha256(open(f'{d}/PARAMS.md', 'rb').read()).hexdigest()
    assert open(f'{d}/PARAMS.lock').read().split()[0] == h, 'PARAMS.md changed after lock'
    return h

_D = None
def load():
    global _D
    if _D is None:
        C = json.load(open(f'{DATA}/perp_15m.json')); H = json.load(open(f'{DATA}/perp_1h.json'))
        _D = SC.prep(E.Data(C, H))
    return _D

def extract(D, strat, start, end, fee=FEE):
    """Free run (no eval lines); one position; risk normalised to 1. Returns list of trade dicts."""
    C = D.C; out = []; pos = None; pend = None; last_exit_t = C[start][0]
    def f_pnl(p, px):
        g = p['g']; return g*(px-p['entry'])*p['size'] - (p['entry']+px)*p['size']*fee
    for i in range(start, end):
        t, o, h, l, c = C[i]
        if pend and not pos:
            sig = pend; entry = o; sd = max(sig['sd'], 0.0035*entry); g = 1 if sig['side'] == 'long' else -1
            if 'tp_dist' in sig:
                tp = entry + g*sig['tp_dist'] if sig['tp_dist'] >= 0.5*sd else None
                if tp is None: pend = None
            else: tp = entry + g*sig.get('tp_R', 1e6)*sd
            if pend:
                pos = dict(g=g, side=sig['side'], entry=entry, t=t, i0=i, size=1.0/(sd+entry*2*fee), sd=sd, stop=entry-g*sd, tp=tp,
                           tmax=sig.get('tmax'), exit_t=sig.get('exit_t'), fund=0.0, mfe=-1e9, mae=1e9, gap=(t-last_exit_t)/3600)
                if hasattr(strat, 'on_entry'): strat.on_entry(sig)
        pend = None
        if pos:
            g = pos['g']
            if t % 14400 == 0 and i > pos['i0']: pos['fund'] += pos['size']*o*MFD/6
            hit = (l <= pos['stop']) if g > 0 else (h >= pos['stop'])
            exitpx = why = None
            if hit:
                exitpx = min(o, pos['stop']) if g > 0 else max(o, pos['stop']); why = 'stop'
                pos['mae'] = min(pos['mae'], f_pnl(pos, exitpx) - pos['fund'])
            else:
                pos['mae'] = min(pos['mae'], f_pnl(pos, l if g > 0 else h) - pos['fund'])
                fav = h if g > 0 else l
                if (g > 0 and h >= pos['tp']) or (g < 0 and l <= pos['tp']):
                    exitpx = max(o, pos['tp']) if g > 0 else min(o, pos['tp']); why = 'TP'; fav = exitpx
                pos['mfe'] = max(pos['mfe'], f_pnl(pos, fav) - pos['fund'])
                if why is None:
                    if pos['tmax'] and i - pos['i0'] + 1 >= pos['tmax']: exitpx = c; why = 'time'
                    elif pos['exit_t'] and t+900 >= pos['exit_t']: exitpx = c; why = 'time'
            if why:
                R = f_pnl(pos, exitpx) - pos['fund']; te = t + 900
                out.append(dict(t=pos['t'], te=te, side=pos['side'], R=R, mfe=max(pos['mfe'], R), mae=min(pos['mae'], R),
                                dur=(te-pos['t'])/3600, gap=pos['gap'], why=why,
                                gross=g*(exitpx-pos['entry'])/pos['entry'], hold_d=(te-pos['t'])/86400))
                pos = None; last_exit_t = te
        if i+1 >= end: break
        if not pos:
            sig = strat.signal(i)
            if sig: pend = sig
    return out

def idx(D, ymd):
    import datetime as dt
    t = int(dt.datetime.strptime(ymd, '%Y-%m-%d').replace(tzinfo=dt.timezone.utc).timestamp()); return D.idx_at(t)

class Rnd:
    """Random direction at strategy decision bars with prob p (same exit template)."""
    def __init__(s, base, p, seed): s.v = base; s.p = p; s.rng = random.Random(seed)
    def signal(s, i):
        if not s.v.decision(i) or s.rng.random() >= s.p: return None
        return s.v.make(i, 'long' if s.rng.random() < 0.5 else 'short')
    def on_entry(s, sig):
        if hasattr(s.v, 'on_entry'): s.v.on_entry(sig)

def match_p(D, strat_factory, start, end, ntr):
    """flat decision bars count from a run of the strategy itself -> p = trades / flat decisions."""
    st = strat_factory(); cnt = SC.Count(st); extract(D, cnt, start, end); return min(1.0, ntr/max(cnt.n, 1))

# ---------------- Monte Carlo ----------------
START = 9954.28; TARGET = 11000.0; FLOOR = 9400.0; BUF = 30.0
HOR = [30, 60, 90, 180, 365, 1095]

def risk_rule(name, eq):
    if name.startswith('R_FIX_') or name.startswith('R_FREQ2_'):
        return np.full_like(eq, float(name.split('_')[-1])), float(name.split('_')[-1]), False
    if name == 'R_FLOORFRAC': return np.clip(0.25*(eq-FLOOR), 50, 300), 50.0, True
    if name == 'R_SNAP': return np.clip((TARGET-eq)/3.6, 50, 300), 50.0, True
    if name == 'R_DAILYSHRINK150': return np.full_like(eq, 150.0), 50.0, True
    raise ValueError(name)

def mc(trades, rule, n=20000, seed=7, start_eq=START, max_days=1095):
    rng = np.random.default_rng(seed)
    R = np.array([x['R'] for x in trades]); MF = np.array([x['mfe'] for x in trades]); MA = np.array([x['mae'] for x in trades])
    DU = np.array([x['dur'] for x in trades]); GP = np.array([x['gap'] for x in trades])
    if rule.startswith('R_FREQ2_'): GP = GP/2
    eq = np.full(n, start_eq); t = rng.uniform(0, 24, n)  # hours since an 00:30 UTC reset
    bal_reset = eq.copy(); day = np.floor(t/24)
    st = np.zeros(n, int); tres = np.full(n, np.inf); ntr = np.zeros(n, int); H = max_days*24
    for step in range(200000):
        run = (st == 0) & (t < H)
        if not run.any(): break
        j = rng.integers(0, len(R), n)
        te = t + GP[j]
        nd = np.floor(te/24); newday = run & (nd > day)
        bal_reset = np.where(newday, eq, bal_reset); day = np.where(run, np.maximum(day, nd), day)
        dfl = np.maximum(FLOOR, 0.97*bal_reset)
        risk, rmin, shrink = risk_rule(rule, eq)
        stat_room = eq - FLOOR - BUF; day_room = eq - dfl - BUF
        if shrink:
            risk = np.minimum(risk, stat_room)
            lock = run & (stat_room < rmin)
            risk = np.minimum(risk, day_room); skip = run & ~lock & (risk < rmin)
        else:
            lock = run & (stat_room < rmin); skip = run & ~lock & (day_room < risk)
        st[lock] = 3; tres[lock] = np.minimum(tres[lock], te[lock])
        # skipped: wait to next reset
        nxt = (np.floor(te/24)+1)*24
        t = np.where(skip, nxt, t); bal_reset = np.where(skip, eq, bal_reset); day = np.where(skip, np.floor(nxt/24), day)
        go = run & ~lock & ~skip & (te < H)
        t = np.where(run & ~lock & ~skip & (te >= H), te, t)
        if not go.any(): continue
        tx = te + DU[j]; spans = np.floor(tx/24) > np.floor(te/24)
        feff = np.where(spans, np.maximum(dfl, np.maximum(FLOOR, 0.97*eq)), dfl)
        brk = go & (eq + MA[j]*risk <= feff)
        ps = go & ~brk & (eq + MF[j]*risk >= TARGET)
        st[brk] = 2; tres[brk] = te[brk] + DU[j][brk]/2
        st[ps] = 1; tres[ps] = te[ps] + DU[j][ps]/2
        ok = go & ~brk & ~ps
        bal_reset = np.where(ok & spans, eq, bal_reset)  # reset during trade uses balance at entry (excl. unrealized)
        eq = np.where(ok, eq + R[j]*risk, eq); t = np.where(ok, tx, t); day = np.where(ok, np.floor(tx/24), day)
        ntr += go
    res = {}
    for hd in HOR:
        hh = hd*24
        res[hd] = dict(pass_=float(np.mean((st == 1) & (tres <= hh))), fail=float(np.mean((st == 2) & (tres <= hh))),
                       locked=float(np.mean((st == 3) & (tres <= hh))))
        res[hd]['running'] = 1 - res[hd]['pass_'] - res[hd]['fail'] - res[hd]['locked']
    resolved = st > 0
    res['med_days_resolved'] = float(np.median(tres[resolved])/24) if resolved.any() else None
    res['med_days_pass'] = float(np.median(tres[st == 1])/24) if (st == 1).any() else None
    res['mean_trades'] = float(ntr.mean())
    return res

def summ(tr):
    if not tr: return dict(n=0)
    R = np.array([x['R'] for x in tr]); g = np.array([x['gross'] for x in tr])
    return dict(n=len(tr), meanR=float(R.mean()), win=float((R > 0).mean()), sumR=float(R.sum()),
                mean_gross_bp=float(g.mean()*1e4), mean_hold_d=float(np.mean([x['hold_d'] for x in tr])),
                fee_R=None)
