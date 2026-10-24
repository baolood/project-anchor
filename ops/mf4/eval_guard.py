"""Pure eval risk guard. No I/O, no network, no orders. DEPLOY=NO.

Daily line is 97% of the balance at 00:30 UTC (08:30 Asia/Shanghai).
That rule was re-checked on 2026-10-24. Floor is 9,400. Worst case at
the stop includes 0.05% fees per side and 0.1% slippage. A snapshot
older than 24 hours, or a daily reference from before the latest
00:30 UTC reset, is ``unknown`` and never ``ok``.

Sizing (2026-10-24): planned risk is the minimum of $150, equity above
the daily line minus $30, and equity above the floor minus $30. A trade
that may still be open at the next 00:30 UTC is also capped at
3% of balance minus $30. Planned risk under $50 is ``block`` /
``too_close``. The prop size uses 0.04% commission per side and is
floored to 0.001 BTC. Every skip is logged with its reason.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from typing import Any, Mapping


FEE_RATE = Decimal("0.0005")
SLIPPAGE = Decimal("0.001")
DAILY_FACTOR = Decimal("0.97")
DEFAULT_FLOOR = Decimal("9400")
DEFAULT_TARGET = Decimal("11000")
WARN_FRACTION = Decimal("0.5")
STALE_SECONDS = 24 * 60 * 60
_MONEY = Decimal("0.01")
_SIZE = Decimal("0.00000001")
VERDICTS = ("ok", "warn", "block", "unknown")
# Prop commission per side. Distinct from FEE_RATE, which stays the
# worst-case cushion on an open position (0.05% plus 0.1% slippage).
PROP_FEE = Decimal("0.0004")
RISK_CAP = Decimal("150")
RISK_MIN = Decimal("50")
BUFFER = Decimal("30")
OVERNIGHT_FACTOR = Decimal("0.03")
SIZE_LOT = Decimal("0.001")
_LOG = logging.getLogger("ops.mf4.eval_guard")


def latest_daily_reset(now: datetime) -> datetime:
    """Most recent 00:30 UTC at or before ``now`` (08:30 Asia/Shanghai)."""
    moment = _as_utc(now)
    candidate = moment.replace(hour=0, minute=30, second=0, microsecond=0)
    if moment < candidate:
        candidate -= timedelta(days=1)
    return candidate


def planned_risk_usd(
    equity: Decimal,
    daily_line: Decimal,
    floor: Decimal,
    balance: Decimal | None,
    may_cross_reset: bool,
) -> Decimal:
    """Dollars of risk for one new trade under the 2026-10-24 rule."""
    risk = min(RISK_CAP, equity - daily_line - BUFFER, equity - floor - BUFFER)
    if may_cross_reset and balance is not None:
        risk = min(risk, OVERNIGHT_FACTOR * balance - BUFFER)
    return risk


def btc_size(planned: Decimal, entry: Decimal | None, stop: Decimal | None) -> Decimal | None:
    """``planned / (|entry-stop| + 2*0.0004*entry)``, floored to 0.001 BTC."""
    if entry is None or stop is None or entry <= 0:
        return None
    if planned <= 0:
        return Decimal("0.000")
    denom = abs(entry - stop) + (Decimal(2) * PROP_FEE * entry)
    if denom <= 0:
        return Decimal("0.000")
    return (planned / denom).quantize(SIZE_LOT, rounding=ROUND_FLOOR)


def account_status(equity: Decimal, daily_line: Decimal, floor: Decimal, target: Decimal) -> str:
    """``breached``, ``passed``, ``locked``, or ``running``.

    ``locked`` means a new trade at the $50 minimum no longer fits above
    the static floor. It is not a breach.
    """
    if equity < floor or equity < daily_line:
        return "breached"
    if equity >= target:
        return "passed"
    if equity - floor - BUFFER < RISK_MIN:
        return "locked"
    return "running"


def evaluate(
    account: Mapping[str, Any] | None,
    mark: Decimal | float | str | None,
    *,
    now: datetime,
    risk_usd: Decimal | float | str | None = None,
    stop_dist: Decimal | float | str | None = None,
    entry: Decimal | float | str | None = None,
    stop: Decimal | float | str | None = None,
    may_cross_reset: bool = False,
) -> dict[str, Any]:
    """Return the guard view for one manual account snapshot.

    ``account`` is the ``eval_account.json`` object. ``mark`` is the public
    PF mark. Missing or stale inputs yield ``verdict="unknown"``.
    ``may_cross_reset`` defaults off. Set it when the trade may still be
    open at the next 00:30 UTC.
    """
    moment = _as_utc(now)
    quote_entry = entry
    quote_stop = stop
    if not isinstance(account, Mapping):
        return _unknown("account_missing", moment, None)
    balance = _decimal(account.get("balance"))
    daily_ref = _decimal(account.get("daily_ref_balance"))
    if balance is None or daily_ref is None:
        return _unknown("account_incomplete", moment, account)
    snapshot_at = _parse_time(account.get("snapshot_at"))
    daily_ref_at = _parse_time(account.get("daily_ref_at"))
    age = None if snapshot_at is None else (moment - snapshot_at).total_seconds()
    if snapshot_at is None or age is None or age > STALE_SECONDS or age < -300:
        return _unknown("snapshot_stale", moment, account, age_s=age)
    reset = latest_daily_reset(moment)
    if daily_ref_at is None or daily_ref_at < reset:
        return _unknown("daily_ref_before_reset", moment, account, age_s=age)

    floor = _decimal(account.get("floor"))
    if floor is None:
        floor = DEFAULT_FLOOR
    target = _decimal(account.get("target"))
    if target is None:
        target = DEFAULT_TARGET
    position = account.get("position")
    if position is None:
        side = None
        size = Decimal("0")
        pos_entry = None
        sl = None
        tp = None
    elif isinstance(position, Mapping):
        side = position.get("side")
        size = _decimal(position.get("size")) or Decimal("0")
        pos_entry = _decimal(position.get("entry"))
        sl = _decimal(position.get("sl"))
        tp = _decimal(position.get("tp"))
    else:
        return _unknown("position_rejected", moment, account, age_s=age)

    mark_dec = _decimal(mark)
    if side in {"long", "short"} and (mark_dec is None or pos_entry is None or size <= 0):
        return _unknown("mark_missing", moment, account, age_s=age)

    unreal = Decimal("0")
    fees_est = Decimal("0")
    if side == "long" and mark_dec is not None and pos_entry is not None:
        unreal = size * (mark_dec - pos_entry)
        fees_est = FEE_RATE * size * (pos_entry + mark_dec)
    elif side == "short" and mark_dec is not None and pos_entry is not None:
        unreal = size * (pos_entry - mark_dec)
        fees_est = FEE_RATE * size * (pos_entry + mark_dec)
    est = balance + unreal - fees_est
    daily_line = daily_ref * DAILY_FACTOR
    worst = _worst_case(side, size, pos_entry, sl)
    worst_equity = balance + worst
    headroom_daily = est - daily_line
    headroom_floor = est - floor
    distance = _decimal(stop_dist)
    if distance is None and pos_entry is not None and sl is not None:
        distance = abs(pos_entry - sl)
    max_size = _max_size(headroom_daily, distance, _decimal(risk_usd))
    entry_px = _decimal(quote_entry) if quote_entry is not None else pos_entry
    stop_px = _decimal(quote_stop) if quote_stop is not None else sl
    cross_reset = may_cross_reset is True
    planned_dec = planned_risk_usd(est, daily_line, floor, balance, cross_reset)
    planned_size = btc_size(planned_dec, entry_px, stop_px)
    status = account_status(est, daily_line, floor, target)

    breach = (
        est < daily_line
        or est < floor
        or worst_equity < daily_line
        or worst_equity < floor
    )
    daily_budget = daily_ref - daily_line
    floor_budget = daily_ref - floor
    thin = False
    if daily_budget > 0 and headroom_daily < WARN_FRACTION * daily_budget:
        thin = True
    if floor_budget > 0 and headroom_floor < WARN_FRACTION * floor_budget:
        thin = True
    if breach:
        verdict = "block"
        reason = "worst_case_breaches_line"
    elif planned_dec < RISK_MIN:
        verdict = "block"
        reason = "too_close"
    elif thin:
        verdict = "warn"
        reason = "headroom_below_half"
    else:
        verdict = "ok"
        reason = "within_lines"
    planned = _money(planned_dec)
    if verdict == "block":
        _log_skip(reason, planned)
    return {
        "est_equity": _money(est),
        "daily_line": _money(daily_line),
        "floor": _money(floor),
        "target": _money(target),
        "headroom_daily": _money(headroom_daily),
        "headroom_floor": _money(headroom_floor),
        "worst_case_at_sl": _money(worst),
        "max_size_for_signal": None if max_size is None else _size(max_size),
        "planned_risk": planned,
        "size": None if planned_size is None else float(planned_size),
        "account_status": status,
        "may_cross_reset": cross_reset,
        "verdict": verdict,
        "reason": reason,
        "snapshot_age_s": int(age),
    }


def _worst_case(side: Any, size: Decimal, entry: Decimal | None, sl: Decimal | None) -> Decimal:
    if side not in {"long", "short"} or entry is None or sl is None or size <= 0:
        return Decimal("0")
    if side == "long":
        move = size * (sl - entry)
    else:
        move = size * (entry - sl)
    fees = FEE_RATE * size * (entry + sl)
    slip = SLIPPAGE * abs(sl) * size
    return move - fees - slip


def _max_size(headroom_daily: Decimal, stop_dist: Decimal | None, risk_usd: Decimal | None) -> Decimal | None:
    if stop_dist is None or stop_dist <= 0:
        return None
    room = WARN_FRACTION * headroom_daily
    if room <= 0:
        return Decimal("0")
    budget = room if risk_usd is None else min(risk_usd, room)
    if budget <= 0:
        return Decimal("0")
    return budget / stop_dist


def _log_skip(reason: str, planned: float | None) -> None:
    shown = "none" if planned is None else f"{planned:.2f}"
    _LOG.info("eval_guard skip reason=%s planned_risk=%s", reason, shown)


def _unknown(
    reason: str,
    now: datetime,
    account: Mapping[str, Any] | None,
    age_s: float | None = None,
) -> dict[str, Any]:
    floor = DEFAULT_FLOOR
    target = DEFAULT_TARGET
    daily_line = None
    if isinstance(account, Mapping):
        parsed_floor = _decimal(account.get("floor"))
        parsed_target = _decimal(account.get("target"))
        daily_ref = _decimal(account.get("daily_ref_balance"))
        if parsed_floor is not None:
            floor = parsed_floor
        if parsed_target is not None:
            target = parsed_target
        if daily_ref is not None:
            daily_line = _money(daily_ref * DAILY_FACTOR)
    age = None if age_s is None else int(age_s)
    _log_skip(reason, None)
    return {
        "est_equity": None,
        "daily_line": daily_line,
        "floor": _money(floor),
        "target": _money(target),
        "headroom_daily": None,
        "headroom_floor": None,
        "worst_case_at_sl": None,
        "max_size_for_signal": None,
        "planned_risk": None,
        "size": None,
        "account_status": "unknown",
        "may_cross_reset": False,
        "verdict": "unknown",
        "reason": reason,
        "snapshot_age_s": age,
    }


def _money(value: Decimal) -> float:
    return float(value.quantize(_MONEY, rounding=ROUND_HALF_UP))


def _size(value: Decimal) -> float:
    return float(value.quantize(_SIZE, rounding=ROUND_HALF_UP))


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float, str)):
        try:
            number = Decimal(str(value).strip())
        except Exception:
            return None
        if not number.is_finite():
            return None
        return number
    return None


def _as_utc(now: datetime) -> datetime:
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
