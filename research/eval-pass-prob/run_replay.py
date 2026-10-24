"""Model B: historical replay of the actual trade sequence from weekly starts (Mon 00:30 UTC). Same accounting as MC."""
import json, lib, numpy as np, datetime as dt
lib.check_lock('.')
T = json.load(open('trades.json'))
RULES = ['R_FIX_50','R_FIX_100','R_FIX_150','R_FIX_200','R_FIX_250','R_FLOORFRAC','R_SNAP','R_DAILYSHRINK150']
def one(tr, t0, rule):
    eq = lib.START; bal = eq; RES = 1800  # 00:30 UTC offset seconds
    day = lambda ts: (ts - RES)//86400
    cur = t0; d = day(cur); k = 0
    while k < len(tr) and tr[k]['t'] < t0: k += 1
    while k < len(tr):
        x = tr[k]; te = x['t']
        if day(te) > d: bal = eq; d = day(te)
        dfl = max(lib.FLOOR, 0.97*bal)
        r, rmin, shrink = lib.risk_rule(rule, np.array([eq])); r = float(r[0])
        stat = eq - lib.FLOOR - lib.BUF; dr = eq - dfl - lib.BUF
        if shrink:
            r = min(r, stat)
            if stat < rmin: return 'locked', te
            r = min(r, dr)
            if r < rmin: k += 1; continue
        else:
            if stat < rmin: return 'locked', te
            if dr < r: k += 1; continue
        spans = day(x['te']) > day(te)
        feff = max(dfl, lib.FLOOR, 0.97*eq) if spans else dfl
        if eq + x['mae']*r <= feff: return 'fail', x['te']
        if eq + x['mfe']*r >= lib.TARGET: return 'pass', x['te']
        if spans: bal = eq
        eq += x['R']*r; d = day(x['te']); k += 1
    return 'running', None
out = {}
for dname, s0 in (('D1_MF4_RECENT', '2024-09-30'), ('D2_MF4_FULL', '2022-10-03')):
    tr = T[dname]; last = tr[-1]['te']
    t0 = int(dt.datetime.strptime(s0, '%Y-%m-%d').replace(tzinfo=dt.timezone.utc).timestamp()) + 1800
    starts = list(range(t0, last, 7*86400))
    for rule in RULES:
        rows = [one(tr, s, rule) + (s,) for s in starts]
        def frac(st, hd):
            return np.mean([r[0] == st and (r[1] - r[2]) <= hd*86400 for r in rows])
        res = {str(hd): {st: float(frac(st, hd)) for st in ('pass', 'fail', 'locked')} for hd in (60, 180)}
        res['end'] = {st: float(np.mean([r[0] == st for r in rows])) for st in ('pass', 'fail', 'locked', 'running')}
        res['n_starts'] = len(rows); out[f'{dname}|{rule}'] = res
        print(f"{dname:15s} {rule:17s} n={len(rows)} 60d P/F/L {res['60']['pass']*100:5.1f}/{res['60']['fail']*100:4.1f}/{res['60']['locked']*100:5.1f}  180d P {res['180']['pass']*100:5.1f}  end P/F/L/run {res['end']['pass']*100:5.1f}/{res['end']['fail']*100:4.1f}/{res['end']['locked']*100:5.1f}/{res['end']['running']*100:5.1f}")
json.dump(out, open('replay_results.json', 'w'), indent=1)
