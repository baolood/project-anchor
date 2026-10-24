"""EVAL_DIR_FAMILIES_V1: TSMOM_D_V1, FUNDING_CONTRA_V1, HOUR_SEASON_V1. Research only; public data; no orders."""
import sys, json, glob, zipfile, io, csv, math
import numpy as np
sys.path.insert(0, '/workspace/anchor-redesign/eval-pass-prob')
import lib
H0 = lib.check_lock('/workspace/anchor-redesign/eval-dir-families')
D = lib.load(); END = len(D.C)
IS0, IS1 = lib.idx(D, '2022-10-03'), lib.idx(D, '2025-04-01')
S = lib.SC.S

class TSMOM(S):
    def decision(s, i): kd = s.D.Kd[i]; return s.D.isd[i] and kd is not None and kd >= s.kw['L'] + 15
    def rule(s, i):
        kd = s.D.Kd[i]; r = s.D.Bd[kd][4]/s.D.Bd[kd-s.kw['L']][4] - 1
        return 'long' if r > 0 else 'short' if r < 0 else None
    def make(s, i, side): return dict(side=side, sd=2.0*s.D.ATRd[s.D.Kd[i]], tp_R=1e6, tmax=7*96)

# Binance BTCUSDT 8h funding (public archive)
FR = []
for f in sorted(glob.glob('/workspace/anchor-redesign/funding-carry/data/futures_um_monthly_fundingRate_BTCUSDT_*.zip')):
    z = zipfile.ZipFile(f); txt = z.read(z.namelist()[0]).decode()
    for row in csv.DictReader(io.StringIO(txt)): FR.append((int(row['calc_time'])//1000//900*900, float(row['last_funding_rate'])))
FR.sort(); FR_T = {t: k for k, (t, _) in enumerate(FR)}
FR_END = lib.SC.E.Data.idx_at(D, FR[-1][0] + 8*3600)
class FCONTRA(S):
    def decision(s, i):
        k = FR_T.get(D.T[i]); return k is not None and k >= 549 and D.K4h[i] is not None and D.K4h[i] >= 50
    def rule(s, i):
        k = FR_T[D.T[i]]; v = np.mean([FR[m][1] for m in range(k-8, k+1)])
        hist = [np.mean([FR[m][1] for m in range(j-8, j+1)]) for j in range(k-540, k)]
        rk = sum(h < v for h in hist)/540; q = s.kw['q']
        return 'short' if rk >= 1-q else 'long' if rk <= q else None
    def make(s, i, side): return dict(side=side, sd=1.5*D.ATR4h[D.K4h[i]], tp_R=2.0, tmax=72*4)

# hour seasonality estimated on IS only
HT = [x[0] for x in D.H]; HC = D.HC
hr = [[] for _ in range(24)]
for k in range(1, len(D.H)):
    if D.T[IS0] <= HT[k] < D.T[IS1] and HT[k]-HT[k-1] == 3600: hr[(HT[k]//3600) % 24].append(math.log(HC[k]/HC[k-1]))
hm = [np.mean(x) for x in hr]
blk = [sum(hm[(h+j) % 24] for j in range(4)) for h in range(24)]
BEST, WORST = int(np.argmax(blk)), int(np.argmin(blk))
class HSEASON(S):
    def decision(s, i):
        tc = (D.T[i]+900) % 86400; ok = tc == BEST*3600 or (s.kw['ls'] and tc == WORST*3600)
        return ok and D.J[i] is not None and D.J[i] > 50 and D.K4h[i] is not None
    def rule(s, i): return 'long' if (D.T[i]+900) % 86400 == BEST*3600 else 'short'
    def make(s, i, side): return dict(side=side, sd=2.0*D.HATR[D.J[i]], tp_R=1e6, exit_t=D.T[i]+900+4*3600)

FAM = {'TSMOM_D_V1': [('L10', TSMOM, dict(L=10)), ('L30', TSMOM, dict(L=30)), ('L60', TSMOM, dict(L=60))],
       'FUNDING_CONTRA_V1': [('q10', FCONTRA, dict(q=0.10)), ('q05', FCONTRA, dict(q=0.05))],
       'HOUR_SEASON_V1': [('HS_L', HSEASON, dict(ls=False)), ('HS_LS', HSEASON, dict(ls=True))]}
T = json.load(open('/workspace/anchor-redesign/eval-pass-prob/trades.json'))
mf4_ult = lib.mc(T['D1_MF4_RECENT'], 'R_FIX_100')[1095]['pass_']
out = dict(params_sha256=H0, best_block_utc=BEST, worst_block_utc=WORST, hour_means_bp=[x*1e4 for x in hm], mf4_recent_ult_pass=mf4_ult, families={})
for fam, vs in FAM.items():
    oos_end = min(END, FR_END) if fam == 'FUNDING_CONTRA_V1' else END
    rows = {}
    for vn, cls, kw in vs:
        tr = lib.extract(D, cls(D, **kw), IS0, IS1); su = lib.summ(tr)
        wall = 0.0008 + 0.00033*su['mean_hold_d'] if su['n'] else 1
        su['gate_wall_bp'] = wall*1e4; su['gate_pass'] = bool(su['n'] and su['mean_gross_bp'] >= 2*wall*1e4)
        rows[vn] = dict(IS=su); print(fam, vn, 'IS', su, flush=True)
    elig = [v for v in rows if rows[v]['IS']['n'] >= 30]
    sel = max(elig, key=lambda v: rows[v]['IS']['meanR']) if elig else None
    res = dict(variants=rows, selected=sel)
    if sel:
        cls, kw = [(c, k) for n, c, k in vs if n == sel][0]
        tro = lib.extract(D, cls(D, **kw), IS1, oos_end); so = lib.summ(tro); res['OOS'] = so
        p = lib.match_p(D, lambda: cls(D, **kw), IS1, oos_end, so['n'])
        rm = []
        for seed in range(200):
            rt = lib.extract(D, lib.Rnd(cls(D, **kw), p, 5000+seed), IS1, oos_end)
            if rt: rm.append(np.mean([x['R'] for x in rt]))
        res['rand_p95'] = float(np.percentile(rm, 95)); res['rand_mean'] = float(np.mean(rm)); res['rand_p'] = p
        ult = lib.mc(tro, 'R_FIX_100')[1095]['pass_'] if so['n'] else 0.0
        res['oos_ult_pass_100'] = ult
        isr = rows[sel]['IS']
        crit = dict(P1=so['n'] > 0 and so['meanR'] > 0, P2=so['n'] >= 30, P3=so['n'] > 0 and so['meanR'] > res['rand_p95'],
                    P4=isr['meanR'] > 0 and isr['gate_pass'], P5=ult >= mf4_ult + 0.05)
        res['criteria'] = crit; res['verdict'] = 'PASS' if all(crit.values()) else 'FAIL'
        for v in rows:  # transparency: OOS of non-selected variants (not used for selection)
            if v != sel:
                c2, k2 = [(c, k) for n, c, k in vs if n == v][0]; rows[v]['OOS_info_only'] = lib.summ(lib.extract(D, c2(D, **k2), IS1, oos_end))
    else: res['verdict'] = 'FAIL'
    out['families'][fam] = res
    print(fam, 'selected', sel, 'OOS', res.get('OOS'), 'rand p95', res.get('rand_p95'), 'ult', res.get('oos_ult_pass_100'), res.get('criteria'), res['verdict'], flush=True)
json.dump(out, open('results.json', 'w'), indent=1)
