#!/usr/bin/env python3
"""MF4 host watcher. Public PF_XBTUSD only. DEPLOY=NO. Webhook default off.

Kraken Prop has no API. This process never places an order and never calls
a private Kraken endpoint. It reads the public ticker and public 4h candles,
runs ``_b1_core.decide``, writes ``status.json``, and optionally posts a
signal webhook.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

try:
    from ops.mf4 import _b1_core
    from ops.mf4.eval_guard import evaluate
    from ops.mf4.mf4_webhook import (
        build_payload,
        dispatch,
        event_id_for,
        flush_outbox,
        last_ok_at,
        outbox_count,
        send_test,
        shanghai_stamp,
        webhook_enabled,
    )
    from ops.mf4.sealed import sealed_reason
except ImportError:  # host copy runs as a script from its own directory
    import _b1_core
    from eval_guard import evaluate
    from mf4_webhook import (
        build_payload,
        dispatch,
        event_id_for,
        flush_outbox,
        last_ok_at,
        outbox_count,
        send_test,
        shanghai_stamp,
        webhook_enabled,
    )
    from sealed import sealed_reason


SYMBOL = "PF_XBTUSD"
TICKER_URL = "https://futures.kraken.com/derivatives/api/v3/tickers/PF_XBTUSD"
CANDLE_URL = "https://futures.kraken.com/api/charts/v1/trade/PF_XBTUSD/4h"
USER_AGENT = "anchor-mf4-watcher/1.0 (public research; no auth)"
STATUS_NAME = "status.json"
STATE_NAME = "watcher_state.json"
ACCOUNT_NAME = "eval_account.json"
COMPARE_NAME = "compare.jsonl"
DEFAULT_OUT = Path("/var/lib/anchor-mf4-watcher")
SHADOW_START = 10000.0


def process_once(
    *,
    out_dir: Path,
    candles: Sequence[Mapping[str, Any]],
    mark: float | None,
    mark_at: datetime,
    env: Mapping[str, str] | None = None,
    poster: Callable[..., Any] | None = None,
    sleeper: Callable[[float], None] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Advance one closed-bar step and write status.json.

    Webhook delivery is scheduled on a background thread only when
    ``MF4_WEBHOOK_ENABLED=1``. Failures are swallowed.
    """
    moment = now or mark_at
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    refusal = sealed_reason(out_dir)
    if refusal is not None:
        raise ValueError(refusal)
    selected = dict(os.environ if env is None else env)
    if webhook_enabled(selected):
        try:
            flush_outbox(out_dir, env=selected, poster=poster, sleeper=sleeper)
        except Exception:
            pass
    state = _load_state(out_dir)
    decision = _b1_core.decide(candles, state.get("position"))
    signal = decision.get("signal")
    _apply_signal(state, signal, moment)
    account = _read_json(out_dir / ACCOUNT_NAME)
    guard = None
    if isinstance(account, dict):
        guard = evaluate(account, mark, now=moment, risk_usd=selected.get("MF4_RISK_USD"))
    status = _status(decision, state, mark, mark_at, guard, out_dir, selected)
    _atomic_json(out_dir / STATUS_NAME, status)
    _save_state(out_dir, state)
    if isinstance(signal, dict) and signal.get("type") in {"OPEN", "EXIT"}:
        _emit(out_dir, signal, decision, guard, moment, selected, poster, sleeper)
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MF4 public host watcher")
    parser.add_argument("--send-test", action="store_true")
    parser.add_argument("--once", action="store_true", help="One public poll, then exit")
    parser.add_argument("--loop", action="store_true", help="Poll the public ticker until the process is stopped")
    parser.add_argument("--out-dir", default=os.environ.get("MF4_OUT_DIR", str(DEFAULT_OUT)))
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir)
    if sealed_reason(out_dir) is not None:
        print("MF4_WATCHER=REFUSED", file=sys.stderr)
        return 2
    if args.send_test:
        return send_test(out_dir, env=os.environ)
    if args.loop:
        return _loop(out_dir)
    if args.once:
        ticker = _fetch_json(TICKER_URL)
        candles_payload = _fetch_json(CANDLE_URL)
        mark = mark_from_ticker(ticker or {})
        candles = candles_from_payload(candles_payload or {})
        if mark is None or not candles:
            print("MF4_WATCHER=PUBLIC_DATA_MISSING", file=sys.stderr)
            return 1
        process_once(
            out_dir=out_dir,
            candles=candles,
            mark=float(mark),
            mark_at=datetime.now(timezone.utc),
            env=os.environ,
        )
        print("MF4_WATCHER=ONCE")
        print("DEPLOY=NO")
        return 0
    print("MF4_WATCHER=REFUSED", file=sys.stderr)
    print("FAIL_REASON=loop_not_started_from_repo_entrypoint", file=sys.stderr)
    return 2


def mark_from_ticker(payload: Mapping[str, Any]) -> str | None:
    ticker = payload.get("ticker")
    if isinstance(ticker, dict) and ticker.get("markPrice") not in {None, ""}:
        return str(ticker.get("markPrice"))
    tickers = payload.get("tickers")
    if isinstance(tickers, list):
        for item in tickers:
            if isinstance(item, dict) and item.get("symbol") in {None, SYMBOL}:
                if item.get("markPrice") not in {None, ""}:
                    return str(item.get("markPrice"))
    return None


def candles_from_payload(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("candles")
    if not isinstance(rows, list):
        return []
    candles: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            candles.append(
                {
                    "time": _candle_time(row.get("time")),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                }
            )
        except (TypeError, ValueError, KeyError):
            continue
    return candles


def _emit(
    out_dir: Path,
    signal: Mapping[str, Any],
    decision: Mapping[str, Any],
    guard: Mapping[str, Any] | None,
    moment: datetime,
    env: Mapping[str, str],
    poster: Callable[..., Any] | None,
    sleeper: Callable[[float], None] | None,
) -> None:
    if not webhook_enabled(env):
        return
    candle_time = str(decision.get("bar_time") or "")
    payload = build_payload(
        signal=str(signal.get("type")),
        price=signal.get("price"),
        when=moment,
        reason=str(signal.get("reason") or ""),
        event_id=event_id_for(str(signal.get("type")), str(signal.get("side")), candle_time),
        guard=guard,
        test=False,
    )
    try:
        dispatch(
            out_dir,
            payload,
            env=env,
            poster=poster,
            sleeper=sleeper,
            asynchronous=True,
        )
    except Exception:
        return


def _status(
    decision: Mapping[str, Any],
    state: Mapping[str, Any],
    mark: float | None,
    mark_at: datetime,
    guard: Mapping[str, Any] | None,
    out_dir: Path,
    env: Mapping[str, str],
) -> dict[str, Any]:
    last_signal = state.get("last_signal")
    compare = _compare(out_dir)
    age_basis = mark_at if mark_at.tzinfo is not None else mark_at.replace(tzinfo=timezone.utc)
    return {
        "state": decision.get("state") or "FLAT",
        "pos": state.get("position"),
        "trend": decision.get("trend"),
        "long_trigger_gt": decision.get("long_trigger_gt"),
        "short_trigger_lt": decision.get("short_trigger_lt"),
        "last_4h_close": {
            "at_sh": None if decision.get("bar_time") is None else _as_shanghai(decision.get("bar_time"), age_basis),
            "close": decision.get("close"),
        },
        "last_signal": last_signal,
        "price": {"last": mark, "at": age_basis.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
        "shadow_equity": state.get("shadow_equity"),
        "webhook": {
            "enabled": webhook_enabled(env),
            "last_ok_at_sh": last_ok_at(out_dir),
            "outbox_n": outbox_count(out_dir),
        },
        "compare": compare,
        "guard": None if guard is None else {key: guard.get(key) for key in (
            "est_equity",
            "daily_line",
            "floor",
            "target",
            "headroom_daily",
            "headroom_floor",
            "worst_case_at_sl",
            "max_size_for_signal",
            "verdict",
        )},
        "reason": decision.get("reason") or "no_signal",
    }


def _loop(out_dir: Path) -> int:
    import time

    poll = 30.0
    raw = os.environ.get("MF4_POLL_SECONDS", "").strip()
    if raw:
        try:
            poll = max(5.0, float(raw))
        except ValueError:
            poll = 30.0
    while True:
        try:
            ticker = _fetch_json(TICKER_URL)
            candles_payload = _fetch_json(CANDLE_URL)
            mark = mark_from_ticker(ticker or {})
            candles = candles_from_payload(candles_payload or {})
            if mark is not None and candles:
                process_once(
                    out_dir=out_dir,
                    candles=candles,
                    mark=float(mark),
                    mark_at=datetime.now(timezone.utc),
                    env=os.environ,
                )
        except Exception:
            print("MF4_WATCHER=PUBLIC_POLL_FAILED", file=sys.stderr)
        time.sleep(poll)


def _apply_signal(state: dict[str, Any], signal: Mapping[str, Any] | None, moment: datetime) -> None:
    if not isinstance(signal, dict):
        return
    state["last_signal"] = {
        "type": signal.get("type"),
        "side": signal.get("side"),
        "price": signal.get("price"),
        "at_sh": shanghai_stamp(moment),
    }
    if signal.get("type") == "OPEN":
        state["position"] = {
            "side": signal.get("side"),
            "size": None,
            "entry": signal.get("price"),
            "sl": signal.get("sl"),
            "tp": signal.get("tp"),
        }
    elif signal.get("type") == "EXIT":
        position = state.get("position") if isinstance(state.get("position"), dict) else None
        if position and position.get("entry") is not None and signal.get("price") is not None:
            entry = float(position["entry"])
            price = float(signal["price"])
            direction = 1.0 if position.get("side") == "long" else -1.0
            state["shadow_equity"] = float(state.get("shadow_equity") or SHADOW_START) + direction * (price - entry)
        state["position"] = None


def _compare(out_dir: Path) -> dict[str, Any]:
    path = out_dir / COMPARE_NAME
    consecutive = 0
    last_diff = None
    if path.is_file():
        try:
            blob = path.read_bytes()
        except OSError:
            blob = b""
        if len(blob) > 64 * 1024:
            blob = blob[-64 * 1024 :]
        for line in blob.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            if row.get("match") is True:
                consecutive += 1
            else:
                consecutive = 0
                if isinstance(row.get("at"), str):
                    last_diff = row["at"]
    return {"consecutive_matches": consecutive, "last_diff_at": last_diff}


def _as_shanghai(value: Any, fallback: datetime) -> str | None:
    if isinstance(value, str) and value.strip():
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return shanghai_stamp(parsed)
        return value
    return shanghai_stamp(fallback)


def _candle_time(value: Any) -> str:
    if isinstance(value, (int, float)) and value > 10_000_000_000:
        moment = datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc)
        return moment.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, (int, float)):
        moment = datetime.fromtimestamp(float(value), tz=timezone.utc)
        return moment.strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(value)


def _load_state(out_dir: Path) -> dict[str, Any]:
    payload = _read_json(out_dir / STATE_NAME)
    if not isinstance(payload, dict):
        payload = {}
    payload.setdefault("position", None)
    payload.setdefault("shadow_equity", SHADOW_START)
    payload.setdefault("last_signal", None)
    return payload


def _save_state(out_dir: Path, state: Mapping[str, Any]) -> None:
    _atomic_json(out_dir / STATE_NAME, dict(state))


def _read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")
    try:
        os.chmod(temporary, 0o640)
    except OSError:
        pass
    os.replace(temporary, path)
    try:
        os.chmod(path, 0o640)
    except OSError:
        pass


def _fetch_json(url: str) -> dict[str, Any] | None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read(1_000_000).decode("utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


if __name__ == "__main__":
    raise SystemExit(main())
