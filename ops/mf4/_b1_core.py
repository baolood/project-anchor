"""MF4_BRK4H_4R core (frozen 2026-10-07 from eval-backtest/long/morefreq/REPORT.md). SIGNAL ONLY - never places orders.
Same entry as B1: 4h Donchian20 + daily EMA50 filter on Kraken Futures PF_XBTUSD public charts (UTC-aligned).
Stop dist = max(1.0*ATR4h(Wilder14), 0.35%*entry). TP = 4R. No BE/trail.
Size = risk/(sd + 2*0.0004*entry) floored to 0.001 BTC. One virtual position at a time (stop-first on 15m)."""
import json, time, urllib.request

API = 'https://futures.kraken.com/api/charts/v1/trade/PF_XBTUSD/{res}?from={frm}'
SEC = {'15m': 900, '4h': 14400, '1d': 86400}
FEE = 0.0004; ATR_MULT = 1.0; MIN_SD = 0.0035; TP_R = 4.0; LOOKBACK = 20; EMA_N = 50

def fetch(res, frm):
    """Return completed bars [t, o, h, l, c] (t in seconds, bar open) since frm, paging."""
    out = {}; now = time.time(); f = int(frm)
    for _ in range(50):
        req = urllib.request.Request(API.format(res=res, frm=f), headers={'User-Agent': 'eval-watcher/1.0'})
        d = json.load(urllib.request.urlopen(req, timeout=20))
        cs = d.get('candles') or []
        for c in cs:
            t = c['time'] // 1000
            if t + SEC[res] <= now: out[t] = [t, float(c['open']), float(c['high']), float(c['low']), float(c['close'])]
        if not d.get('more_candles') or not cs: break
        f = cs[-1]['time'] // 1000 + SEC[res]
    return [out[k] for k in sorted(out)]

def ema(v, n):
    a = 2/(n+1); e = v[0]; o = []
    for x in v: e = a*x+(1-a)*e; o.append(e)
    return o

def atr(c, n=14):
    tr = [None]+[max(c[i][2]-c[i][3], abs(c[i][2]-c[i-1][4]), abs(c[i][3]-c[i-1][4])) for i in range(1, len(c))]
    out = [None]*len(c); a = None
    for i in range(1, len(c)):
        if i == n: a = sum(tr[1:n+1])/n
        elif i > n: a = (a*(n-1)+tr[i])/n
        out[i] = a
    return out

def size_for(risk, entry, sd): return int(risk/(sd + 2*FEE*entry)*1000)/1000

def signal_at(b4, atr4, bd, ed50, k):
    """Signal at the close of completed 4h bar k (index into b4). Uses last daily bar completed by that time."""
    if k < LOOKBACK or atr4[k] is None: return None
    tclose = b4[k][0] + SEC['4h']
    kd = max((j for j in range(len(bd)) if bd[j][0] + SEC['1d'] <= tclose), default=None)
    if kd is None or kd < EMA_N: return None
    c = b4[k][4]; hh = max(x[2] for x in b4[k-LOOKBACK:k]); ll = min(x[3] for x in b4[k-LOOKBACK:k])
    dc, de = bd[kd][4], ed50[kd]
    info = dict(bar4h_close_utc=tclose, close=c, hh20=hh, ll20=ll, daily_close=dc, daily_ema50=de, atr4h=atr4[k], daily_bar_utc=bd[kd][0])
    if c > hh and dc > de: return dict(side='long', **info)
    if c < ll and dc < de: return dict(side='short', **info)
    return dict(side=None, **info)

def make_trade(sig, entry, risk):
    sd = max(ATR_MULT*sig['atr4h'], MIN_SD*entry); g = 1 if sig['side'] == 'long' else -1
    return dict(side=sig['side'], entry=entry, stop=entry - g*sd, target=entry + g*TP_R*sd, sd=sd,
                size=size_for(risk, entry, sd), risk_usd=risk, signal_4h_close_utc=sig['bar4h_close_utc'])

def scan(b15, b4, bd, start_t, risk=150.0):
    """Replay B1 from start_t (UTC s) to the latest completed bars. Returns (state dict, history list)."""
    atr4 = atr(b4); ed50 = ema([x[4] for x in bd], EMA_N)
    i15 = {b[0]: n for n, b in enumerate(b15)}
    pos = None; hist = []; last_sig = None
    for k in range(len(b4)):
        tclose = b4[k][0] + SEC['4h']
        if tclose < start_t: continue
        # manage open position through this 4h bar's 15m bars (stop-first)
        if pos is not None:
            for t in range(b4[k][0], tclose, 900):
                n = i15.get(t)
                if n is None or t < pos['entry_t']: continue
                _, o, h, l, c = b15[n]; g = 1 if pos['side'] == 'long' else -1
                if (g > 0 and l <= pos['stop']) or (g < 0 and h >= pos['stop']):
                    px = o if (g > 0 and o < pos['stop']) or (g < 0 and o > pos['stop']) else pos['stop']
                    pos.update(exit='stop', exit_px=px, exit_t=t); hist.append(pos); pos = None; break
                if (g > 0 and h >= pos['target']) or (g < 0 and l <= pos['target']):
                    px = o if (g > 0 and o > pos['target']) or (g < 0 and o < pos['target']) else pos['target']
                    pos.update(exit='target', exit_px=px, exit_t=t); hist.append(pos); pos = None; break
        s = signal_at(b4, atr4, bd, ed50, k); last_sig = s
        if pos is None and s and s['side']:
            n = i15.get(tclose)
            entry = b15[n][1] if n is not None else s['close']   # next 15m open; fallback 4h close if not yet available
            pos = make_trade(s, entry, risk); pos['entry_t'] = tclose; pos['entry_is_ref'] = n is None
    return dict(open_position=pos, last_signal=last_sig), hist

def load(days_15m=45):
    now = time.time()
    b15 = fetch('15m', now - days_15m*86400)
    b4 = fetch('4h', now - 400*86400)
    bd = fetch('1d', now - 1200*86400)
    return b15, b4, bd
