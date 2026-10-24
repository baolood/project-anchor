#!/usr/bin/env python3
"""MF4_BRK4H_4R host forward-stream watcher. SIGNAL/SHADOW ONLY. DEPLOY=NO.

Same stepper as the live host watcher (RESUME fix: state.json stores numbers
as text, and those strings load back as floats). Public Kraken Futures
PF_XBTUSD charts only. 4h Donchian20 + daily EMA50, stop max(1.0xATR4h, 0.35%),
TP 4R, one virtual position, stop-first on 15m, entry ref = 4h close.

No keys, no private endpoints, no orders. Kraken Prop has no API.
MF4_WEBHOOK_ENABLED defaults to 0. The eval guard is read from the manual
snapshot and written into status.json. It does not place an order.
"""
import argparse, datetime as dt, fcntl, hashlib, json, logging, os, sys, time
from decimal import Decimal
from pathlib import Path

try:
    from ops.mf4 import _b1_core as B
    from ops.mf4.eval_guard import evaluate
    from ops.mf4.mf4_webhook import (
        build_payload,
        dispatch,
        event_id_for,
        flush_outbox,
        last_ok_at,
        outbox_count,
        send_test,
        webhook_enabled,
    )
    from ops.mf4.sealed import sealed_reason
except ImportError:  # flat host copy: /opt/anchor-mf4-watcher/bin
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _b1_core as B
    from eval_guard import evaluate
    from mf4_webhook import (
        build_payload,
        dispatch,
        event_id_for,
        flush_outbox,
        last_ok_at,
        outbox_count,
        send_test,
        webhook_enabled,
    )
    from sealed import sealed_reason


def out_dir():
    return os.environ.get('MF4_OUT_DIR', '/var/lib/anchor-mf4-watcher')

def _events_path():
    return os.path.join(out_dir(), 'mf4_forward_events.jsonl')

def _state_path():
    return os.path.join(out_dir(), 'state.json')

def _status_path():
    return os.path.join(out_dir(), 'status.json')

# Kept for verify_chain.py and operators that read the module globals.
OUT = out_dir()
EVENTS = _events_path()
STATE = _state_path()
STATUS = _status_path()

RISK_USD = float(os.environ.get('MF4_RISK_USD', '150'))
SHADOW_EQUITY0 = Decimal(os.environ.get('MF4_SHADOW_EQUITY0', '10000'))
POLL_S = int(os.environ.get('MF4_POLL_S', '30'))
SETTLE_S = 60
REPLAY_DAYS = 120

SCHEMA_VERSION = 'official_ledger_c6_v1'          # same envelope as PR #417 C6 events
STRATEGY_VERSION = 'mf4_brk4h_4r_v1'
STOP_RULE_ID = 'STOP_RULE_MF4_MAX_ATR4H_1X_OR_35BPS_V1'
SIZE_POLICY_ID = 'SIZE_POLICY_MF4_FIXED_RISK_USD_FLOOR_0001_V1'
SAMPLE_CLASS = 'FORWARD_SHADOW_MF4_NON_SCORING'
MARKET = 'PF_XBTUSD'
C6_OFFICIAL_MAX_RISK_PCT = Decimal('0.005')
TZ = dt.timezone(dt.timedelta(hours=8))
log = logging.getLogger('mf4')

EX_ANTE_FIELDS = (
    'trade_id', 'entry_price', 'preset_stop_price', 'equity_at_open', 'risk_amount', 'risk_pct',
    'stop_distance', 'max_risk_amount', 'max_quantity', 'candidate_quantity', 'quantity', 'size_action',
    'stop_rule_id', 'size_policy_id', 'strategy_version', 'schema_version',
)

def iso(t): return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def sh(t): return dt.datetime.fromtimestamp(t, TZ).strftime('%Y-%m-%d %H:%M')
def D(x): return x if isinstance(x, Decimal) else Decimal(str(x))

def _ds(v):
    t = format(v, 'f')
    if '.' in t: t = t.rstrip('0').rstrip('.')
    return '0' if t in ('', '-0') else t

def _js(v):
    if isinstance(v, Decimal): return _ds(v)
    if isinstance(v, float): return _ds(D(v))
    if isinstance(v, dict): return {k: _js(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)): return [_js(x) for x in v]
    return v

def row_hash(ev):  # identical algorithm to PR #417 row_hash
    body = {k: v for k, v in ev.items() if k != 'row_hash'}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()

def append_event(ev):
    """Append under an exclusive lock; chain prev_hash -> row_hash. Shared with verify_chain.py."""
    os.makedirs(out_dir(), exist_ok=True)
    path = _events_path()
    with open(path, 'a+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0); prev, seq = 'GENESIS', 0
        for line in f:
            if line.strip():
                seq += 1; prev = json.loads(line)['row_hash']
        ev = _js(dict(ev))
        ev.update(schema_version=SCHEMA_VERSION, strategy_version=STRATEGY_VERSION, market=MARKET,
                  sample_class=SAMPLE_CLASS, deploy='HOST_SHADOW', live_trading='NO-GO', execution='signal_only',
                  ledger_event_id='mf4-%06d' % (seq + 1), recorded_at_utc=iso(time.time()), prev_hash=prev)
        ev['row_hash'] = row_hash(ev)
        f.seek(0, 2); f.write(json.dumps(ev, sort_keys=True, separators=(',', ':')) + '\n'); f.flush(); os.fsync(f.fileno())
        fcntl.flock(f, fcntl.LOCK_UN)
    log.info('EVENT %s %s', ev['event_type'], json.dumps({k: ev.get(k) for k in ('side', 'signal_side', 'close', 'hh20', 'll20', 'entry_price', 'preset_stop_price', 'exit_price') if ev.get(k) is not None}))
    return ev

def write_json(path, obj):
    tmp = path + '.tmp'
    with open(tmp, 'w') as f: json.dump(_js(obj), f, indent=1, sort_keys=True)
    os.replace(tmp, path)

def sig_fields(s):
    return {k: s[k] for k in ('close', 'hh20', 'll20', 'daily_close', 'daily_ema50', 'atr4h')} | \
           {'bar4h_close_utc': iso(s['bar4h_close_utc']), 'daily_bar_open_utc': iso(s['daily_bar_utc'])}


def _num(d):
    """RESUME fix 2026-10-24: write_json stores floats as strings; turn numeric strings back into floats."""
    if not isinstance(d, dict): return d
    out = {}
    for k, v in d.items():
        if isinstance(v, str) and k not in ('side', 'trade_id'):
            try: v = float(v)
            except ValueError: pass
        out[k] = v
    return out


def _pos_public(pos):
    """Status view. Trading state keeps stop/target; the MCP reader asks for sl/tp."""
    if not isinstance(pos, dict):
        return None
    view = dict(pos)
    if 'sl' not in view and 'stop' in view:
        view['sl'] = view['stop']
    if 'tp' not in view and 'target' in view:
        view['tp'] = view['target']
    return view


def _compare(directory):
    path = os.path.join(directory, 'compare.jsonl')
    consecutive = 0
    last_diff = None
    blob = b''
    if os.path.isfile(path):
        try:
            with open(path, 'rb') as handle:
                blob = handle.read()
        except OSError:
            blob = b''
    if len(blob) > 64 * 1024:
        blob = blob[-64 * 1024:]
    for line in blob.decode('utf-8', errors='replace').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        if row.get('match') is True:
            consecutive += 1
        else:
            consecutive = 0
            if isinstance(row.get('at'), str):
                last_diff = row['at']
    return {'consecutive_matches': consecutive, 'last_diff_at': last_diff}


class Watcher:
    def __init__(self):
        self.b15 = {}; self.b4 = {}; self.bd = {}
        self.pos = None; self.proc = None; self.last = None; self.equity = SHADOW_EQUITY0; self.err = None
        self.last_signal = None; self.reason = 'no_signal'
        self.now = None
        self.poster = None
        self.sleeper = None

    def _merge(self, d, rows):
        for r in rows: d[r[0]] = r

    def _now(self):
        moment = self.now or dt.datetime.now(dt.timezone.utc)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=dt.timezone.utc)
        return moment.astimezone(dt.timezone.utc)

    def resume_from(self, st):
        """Load state.json. Numeric strings become floats so round() and stops work after a restart."""
        self.pos = _num(st.get('pos')); self.proc = st['proc']; self.last = _num(st.get('last')); self.equity = D(st.get('equity', SHADOW_EQUITY0))
        sig = st.get('last_signal')
        self.last_signal = _num(sig) if isinstance(sig, dict) else None
        reason = st.get('reason')
        if isinstance(reason, str) and reason:
            self.reason = reason

    def start(self):
        now = time.time()
        b15, b4, bd = B.load(REPLAY_DAYS + 10)
        self._merge(self.b15, b15); self._merge(self.b4, b4); self._merge(self.bd, bd)
        st = None
        state_path = _state_path()
        if os.path.exists(state_path):
            with open(state_path) as handle:
                st = json.load(handle)
        if st and st.get('proc'):
            self.resume_from(st)
            mode = 'RESUME'
        else:
            s, hist = B.scan(b15, b4, bd, now - REPLAY_DAYS*86400, RISK_USD)
            self.pos = s['open_position']; self.last = s['last_signal']; self.proc = b15[-1][0]
            mode = 'REPLAY_INIT'; st = {'replayed_closed_trades': len(hist)}
        append_event({'event_type': 'SERVICE_START', 'reason_code': mode, 'risk_usd': RISK_USD,
                      'bars': [len(b15), len(b4), len(bd)], 'virtual_position': json.dumps(self.pos, default=str),
                      'last_4h': (sig_fields(self.last) | {'signal_side': self.last['side'] or 'NONE'}) if self.last else None,
                      'proc_15m_open_utc': iso(self.proc), 'core_sha256': hashlib.sha256(open(B.__file__, 'rb').read()).hexdigest()})
        self.save()

    def save(self):
        write_json(_state_path(), {'proc': self.proc, 'pos': self.pos, 'last': self.last, 'equity': self.equity,
                                   'last_signal': self.last_signal, 'reason': self.reason})

    def refresh(self, now):
        self._merge(self.b15, B.fetch('15m', min(now - 2*86400, self.proc - 900)))
        if max(self.b4) + 2*B.SEC['4h'] <= now: self._merge(self.b4, B.fetch('4h', now - 5*86400))
        if max(self.bd) + 2*B.SEC['1d'] <= now: self._merge(self.bd, B.fetch('1d', now - 10*86400))
        for d, keep in ((self.b15, 15000), (self.b4, 3000), (self.bd, 1500)):
            for k in sorted(d)[:max(0, len(d) - keep)]: del d[k]

    def tick(self):
        now = time.time()
        if now < self.proc + 2*B.SEC['15m'] + SETTLE_S: return
        self.refresh(now)
        for t in sorted(k for k in self.b15 if k > self.proc and k + B.SEC['15m'] + SETTLE_S <= now):
            self.step(t, catchup=(now - (t + B.SEC['15m']) > 1800))
            self.proc = t; self.save()

    def ex_ante(self, p):
        entry, sd, q = D(p['entry']), D(p['sd']), D(p['size'])
        risk_amount = sd*q + 2*D(B.FEE)*entry*q
        return {'trade_id': p['trade_id'], 'entry_price': entry, 'preset_stop_price': D(p['stop']),
                'equity_at_open': D(p['equity_at_open']), 'risk_amount': risk_amount,
                'risk_pct': risk_amount / D(p['equity_at_open']), 'stop_distance': sd,
                'max_risk_amount': D(RISK_USD), 'max_quantity': q, 'candidate_quantity': q, 'quantity': q,
                'size_action': 'UNCHANGED', 'stop_rule_id': STOP_RULE_ID, 'size_policy_id': SIZE_POLICY_ID,
                'strategy_version': STRATEGY_VERSION, 'schema_version': SCHEMA_VERSION,
                'target_price': D(p['target']), 'target_rule': 'TP_4R'}

    def _remember_signal(self, kind, side, price, when_t):
        self.last_signal = {'type': kind, 'side': side, 'price': price, 'at_sh': sh(when_t)}

    def _guard(self, mark):
        path = os.path.join(out_dir(), 'eval_account.json')
        if not os.path.isfile(path):
            return None
        try:
            with open(path) as handle:
                account = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(account, dict):
            return None
        position = account.get('position')
        open_hold = self.pos is not None or (
            isinstance(position, dict) and position.get('side') in ('long', 'short')
        )
        try:
            return evaluate(
                account,
                mark,
                now=self._now(),
                risk_usd=os.environ.get('MF4_RISK_USD', str(RISK_USD)),
                may_cross_reset=open_hold,
            )
        except Exception:
            return None

    def _flush_webhook(self):
        if not webhook_enabled():
            return
        try:
            flush_outbox(Path(out_dir()), poster=self.poster, sleeper=self.sleeper)
        except Exception:
            log.warning('webhook flush failed')

    def _emit_webhook(self, kind, side, price, when_t, reason):
        """Post only when MF4_WEBHOOK_ENABLED=1. A network error cannot stall the step."""
        if not webhook_enabled():
            return
        try:
            guard = self._guard(price)
            payload = build_payload(
                signal=kind,
                price=price,
                when=self._now(),
                reason=reason,
                event_id=event_id_for(kind, str(side), iso(when_t)),
                guard=guard,
                test=False,
            )
            dispatch(
                Path(out_dir()),
                payload,
                poster=self.poster,
                sleeper=self.sleeper,
                asynchronous=True,
            )
        except Exception:
            log.warning('webhook hook failed')

    def step(self, t, catchup=False):
        self._flush_webhook()
        _, o, h, l, c = self.b15[t]
        if self.pos is not None and self.pos.get('trade_id'):
            p = self.pos; g = 1 if p['side'] == 'long' else -1; ex = None
            if (g > 0 and l <= p['stop']) or (g < 0 and h >= p['stop']):
                ex = ('HARD_STOP_EXIT', 'HARD_STOP_TOUCHED', o if g*(o - p['stop']) < 0 else p['stop'])
            elif (g > 0 and h >= p['target']) or (g < 0 and l <= p['target']):
                ex = ('FLAT_EXIT', 'TARGET_4R_TOUCHED', o if g*(o - p['target']) > 0 else p['target'])
            if ex:
                xp = D(ex[2]); q = D(p['size']); entry = D(p['entry'])
                gross = g*(xp - entry)*q; fees = D(B.FEE)*(entry + xp)*q; net = gross - fees
                self.equity += net
                append_event({'event_type': ex[0], 'reason_code': ex[1], 'side': p['side'].upper(),
                              'position_before': p['side'].upper(), 'position_after': 'FLAT',
                              'bar15_open_utc': iso(t), 'fill_time_utc': iso(t), 'exit_price': xp, 'effective_price': xp,
                              'gross_pnl': gross, 'fee_paid': fees, 'NET_PNL_EX_FUNDING': net, 'R': g*(xp - entry)/D(p['sd']),
                              'funding_pnl': None, 'FUNDING_DATA_STATUS': 'MISSING', 'NET_PNL_STATUS': 'EX_FUNDING',
                              'net_liquidation_equity': self.equity, 'catchup': catchup, **self.ex_ante(p)})
                self.pos = None
                self.reason = ex[1]
                self._remember_signal('EXIT', p['side'], float(xp), t)
                self._emit_webhook('EXIT', p['side'], float(xp), t, ex[1])
            # position from replay (no trade_id) is managed silently like the box replay
        elif self.pos is not None:
            p = self.pos; g = 1 if p['side'] == 'long' else -1
            if (g > 0 and (l <= p['stop'] or h >= p['target'])) or (g < 0 and (h >= p['stop'] or l <= p['target'])):
                self.pos = None
        tclose = t + B.SEC['15m']
        if tclose % B.SEC['4h'] != 0: return
        b4 = [self.b4[k] for k in sorted(self.b4) if k + B.SEC['4h'] <= tclose]
        bd = [self.bd[k] for k in sorted(self.bd)]
        if not b4 or b4[-1][0] + B.SEC['4h'] != tclose:
            append_event({'event_type': 'SIGNAL_4H_SKIPPED', 'reason_code': 'BAR4H_NOT_AVAILABLE', 'bar4h_close_utc': iso(tclose)})
            self.reason = 'BAR4H_NOT_AVAILABLE'
            return
        s = B.signal_at(b4, B.atr(b4), bd, B.ema([x[4] for x in bd], B.EMA_N), len(b4) - 1)
        self.last = s
        if not s: return
        opened = bool(s['side'] and self.pos is None)
        self.reason = ('MF4_' + s['side'].upper()) if s['side'] else 'NO_SIGNAL'
        append_event({'event_type': 'SIGNAL_4H', 'reason_code': self.reason,
                      'signal_side': (s['side'] or 'NONE').upper(), 'signal_available_at': iso(tclose),
                      'position_before': (self.pos['side'].upper() if self.pos else 'FLAT'), 'opens_trade': opened,
                      'catchup': catchup, **sig_fields(s)})
        if opened:
            p = B.make_trade(s, s['close'], RISK_USD); p['entry_t'] = tclose; p['entry_is_ref'] = True
            p['equity_at_open'] = str(self.equity); p['trade_id'] = 'tr_mf4_%s' % iso(tclose)
            self.pos = p
            append_event({'event_type': 'OPEN', 'reason_code': 'MF4_OPEN_SHADOW', 'side': p['side'].upper(),
                          'signal_choice': p['side'].upper(), 'position_before': 'FLAT', 'position_after': p['side'].upper(),
                          'reference_price': D(s['close']), 'effective_price': D(p['entry']), 'fill_time_utc': iso(tclose),
                          'signal_available_at': iso(tclose), 'fill_status': 'SHADOW_REF_4H_CLOSE',
                          'c6_official_cap_check': 'EXCEEDS_0.005' if self.ex_ante(p)['risk_pct'] > C6_OFFICIAL_MAX_RISK_PCT else 'WITHIN_0.005',
                          'catchup': catchup, **self.ex_ante(p)})
            self._remember_signal('OPEN', p['side'], float(p['entry']), tclose)
            self._emit_webhook('OPEN', p['side'], float(p['entry']), tclose, 'MF4_OPEN_SHADOW')

    def _last_price(self):
        bar = self.b15.get(self.proc) if self.proc is not None else None
        if not bar:
            return None
        return bar[4]

    def status(self):
        s = self.last or {}
        mark = self._last_price()
        moment = self._now()
        guard = self._guard(mark)
        guard_view = None
        if isinstance(guard, dict):
            guard_view = {key: guard.get(key) for key in (
                'est_equity', 'daily_line', 'floor', 'target', 'headroom_daily', 'headroom_floor',
                'worst_case_at_sl', 'max_size_for_signal', 'planned_risk', 'size', 'account_status',
                'verdict', 'reason',
            )}
        payload = {
            'updated_utc': iso(moment.timestamp()), 'updated_sh': sh(moment.timestamp()),
            'state': 'flat' if self.pos is None else self.pos['side'], 'pos': _pos_public(self.pos),
            'last_4h_close_sh': sh(s['bar4h_close_utc']) if s else None,
            'last_4h_close': {
                'at_sh': sh(s['bar4h_close_utc']) if s else None,
                'close': s.get('close') if s else None,
            },
            'last_signal': self.last_signal,
            'long_trigger_gt': round(s['hh20'], 1) if s else None,
            'short_trigger_lt': round(s['ll20'], 1) if s else None,
            'trend': (None if not s else ('up(long only)' if s['daily_close'] > s['daily_ema50'] else 'down(short only)')),
            'futures_last_15m_sh': sh(self.proc) if self.proc else None,
            'price': {'last': mark, 'at': iso(moment.timestamp())},
            'shadow_equity': self.equity,
            'webhook': {
                'enabled': webhook_enabled(),
                'last_ok_at_sh': last_ok_at(Path(out_dir())),
                'outbox_n': outbox_count(Path(out_dir())),
            },
            'compare': _compare(out_dir()),
            'guard': guard_view,
            'reason': self.reason,
            'err': self.err,
        }
        write_json(_status_path(), payload)
        with open(_status_path()) as handle:
            return json.load(handle)


def main(argv=None):
    parser = argparse.ArgumentParser(description='MF4 public PF_XBTUSD watcher. DEPLOY=NO. No orders.')
    parser.add_argument('--send-test', action='store_true')
    parser.add_argument('--once', action='store_true', help='One public poll, then exit')
    parser.add_argument('--loop', action='store_true', help='Poll until the process is stopped')
    parser.add_argument('--out-dir', default=None)
    args = parser.parse_args(argv)
    if args.out_dir:
        os.environ['MF4_OUT_DIR'] = args.out_dir
    directory = out_dir()
    if sealed_reason(Path(directory)) is not None:
        print('MF4_WATCHER=REFUSED', file=sys.stderr)
        return 2
    if args.send_test:
        code = send_test(Path(directory), env=os.environ)
        print('DEPLOY=NO')
        return code
    return _serve(once=bool(args.once) and not args.loop)


def _serve(once=False):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', stream=sys.stdout)
    w = Watcher()
    while True:
        try:
            w.start(); break
        except Exception as e:
            log.warning('init error %r; retry 60s', e)
            if once:
                return 1
            time.sleep(60)
    if once:
        try:
            w.tick(); w.err = None
        except Exception as e:
            w.err = repr(e)[:200]; log.warning('tick error %s', w.err)
        try:
            w.status()
        except Exception as e:
            log.warning('status error %r', e)
        print('MF4_WATCHER=ONCE')
        print('DEPLOY=NO')
        return 0
    while True:
        try:
            w.tick(); w.err = None
        except Exception as e:
            w.err = repr(e)[:200]; log.warning('tick error %s', w.err)
        try:
            w.status()
        except Exception as e:
            log.warning('status error %r', e)
        time.sleep(POLL_S)


if __name__ == '__main__':
    raise SystemExit(main())
