"""Pass-probability Monte Carlo. DEPLOY=NO. No orders.

Stdlib port of ``mc`` in ``research/eval-pass-prob/lib.py``. Each step
follows that research step: draw a stored trade, roll the 00:30 UTC
balance, size with the 2026-10-24 cap-150 rule, then lock, skip, pass,
breach, or continue. The seed is fixed. A running account finishes in
well under a second.

When the trade log is empty the book is a zero-edge 4R baseline: one
win in five, gross +4R or -1R, and 0.09R of costs on every trade.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence


FLOOR = 9400.0
TARGET = 11000.0
BUFFER = 30.0
RISK_CAP = 150.0
RISK_MIN = 50.0
COST_R = 0.09
SEED = 7
PATHS = 20000
HORIZONS = (30, 60, 90)
NO_LIMIT_DAYS = 1095
# (R, mfe, mae, duration hours, gap hours)
_WIN = (4.0 - COST_R, 4.0 - COST_R, -0.15, 24.0, 96.0)
_LOSS = (-1.0 - COST_R, 0.02, -1.0 - COST_R, 8.0, 96.0)
BASELINE: tuple[tuple[float, float, float, float, float], ...] = (
    _WIN,
    _LOSS,
    _LOSS,
    _LOSS,
    _LOSS,
)


def baseline_mean_r() -> float:
    """Mean R of the zero-edge 4R book. Costs take it to about -0.09R."""
    return sum(row[0] for row in BASELINE) / len(BASELINE)


def hours_since_daily_reset(now: datetime) -> float:
    """Hours since the latest 00:30 UTC reset, in ``[0, 24]``."""
    moment = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    moment = moment.astimezone(timezone.utc)
    candidate = moment.replace(hour=0, minute=30, second=0, microsecond=0)
    if moment < candidate:
        candidate -= timedelta(days=1)
    hours = (moment - candidate).total_seconds() / 3600.0
    if hours < 0.0:
        return 0.0
    if hours > 24.0:
        return 24.0
    return hours


def pass_probability(
    *,
    equity: float,
    reset_balance: float,
    status: str,
    outcomes: Sequence[Mapping[str, Any]] | None = None,
    hours_since_reset: float = 0.0,
    floor: float = FLOOR,
    target: float = TARGET,
    seed: int = SEED,
    paths: int = PATHS,
) -> dict[str, Any]:
    """Return pass / breach / locked / running at 30, 60, 90 days and no-limit."""
    book, source, cost_r = book_from_outcomes(outcomes)
    if status == "breached":
        return _terminal("breach", source=source, cost_r=cost_r)
    if status == "locked":
        return _terminal("locked", source=source, cost_r=cost_r)
    if status == "passed":
        return _terminal("pass", source=source, cost_r=cost_r)
    if status != "running":
        return {"available": False, "reason": "equity_unknown"}
    raw = simulate(
        book,
        equity=float(equity),
        reset_balance=float(reset_balance),
        hours_since_reset=float(hours_since_reset),
        floor=float(floor),
        target=float(target),
        paths=paths,
        seed=seed,
    )
    body: dict[str, Any] = {
        "available": True,
        "model": "mc",
        "source": source,
        "seed": seed,
        "paths": paths,
        "rule": "cap150",
        "trades": len(book),
        "cost_r": None if cost_r is None else round(cost_r, 4),
        "median_days": None if raw["median_days"] is None else round(raw["median_days"], 1),
    }
    for label, days in (("d30", 30), ("d60", 60), ("d90", 90), ("nolimit", NO_LIMIT_DAYS)):
        body[label] = _probs(raw["horizons"][days])
    return body


def book_from_outcomes(
    rows: Sequence[Mapping[str, Any]] | None,
) -> tuple[list[tuple[float, float, float, float, float]], str, float | None]:
    """Stored trades when any row is usable, otherwise the 0.09R baseline."""
    parsed: list[tuple[float, float, float, float, float]] = []
    costs: list[float] = []
    for row in rows or ():
        if not isinstance(row, Mapping):
            continue
        item = _row_trade(row)
        if item is None:
            continue
        parsed.append(item[0])
        if item[1] is not None:
            costs.append(item[1])
    if not parsed:
        return list(BASELINE), "zero_edge_4r", COST_R
    cost = sum(costs) / len(costs) if costs else None
    return parsed, "stored", cost


def simulate(
    trades: Sequence[tuple[float, float, float, float, float]],
    *,
    equity: float,
    reset_balance: float,
    hours_since_reset: float,
    floor: float = FLOOR,
    target: float = TARGET,
    paths: int = PATHS,
    seed: int = SEED,
    max_days: int = NO_LIMIT_DAYS,
) -> dict[str, Any]:
    """Run ``paths`` accounts from one equity and one last-reset balance."""
    book = [
        (float(item[0]), float(item[1]), float(item[2]), float(item[3]), float(item[4]))
        for item in trades
    ]
    if not book:
        raise ValueError("empty_book")
    count = int(paths)
    if count < 1:
        raise ValueError("paths")
    rng = random.Random(seed)
    width = len(book)
    eq = [float(equity)] * count
    clock = [float(hours_since_reset)] * count
    balance = [float(reset_balance)] * count
    day = [int(float(hours_since_reset) // 24.0)] * count
    state = [0] * count
    resolved_at: list[float | None] = [None] * count
    horizon = float(max_days) * 24.0
    steps = 0
    alive = count
    while alive and steps < 100000:
        steps += 1
        alive = 0
        for i in range(count):
            if state[i]:
                continue
            now_h = clock[i]
            if now_h >= horizon:
                continue
            alive += 1
            realized, favourable, adverse, duration, gap = book[rng.randrange(width)]
            if gap < 0.25:
                gap = 0.25
            if duration < 0.0:
                duration = 0.0
            entry_h = now_h + gap
            next_day = int(entry_h // 24.0)
            reset_balance_i = balance[i]
            equity_i = eq[i]
            day_i = day[i]
            if next_day > day_i:
                reset_balance_i = equity_i
                day_i = next_day
            daily_floor = 0.97 * reset_balance_i
            if daily_floor < floor:
                daily_floor = floor
            static_room = equity_i - floor - BUFFER
            daily_room = equity_i - daily_floor - BUFFER
            risk = RISK_CAP
            if static_room < risk:
                risk = static_room
            if daily_room < risk:
                risk = daily_room
            if int((entry_h + duration) // 24.0) > int(entry_h // 24.0):
                overnight = 0.03 * equity_i - BUFFER
                if overnight < risk:
                    risk = overnight
            if static_room < RISK_MIN:
                state[i] = 3
                resolved_at[i] = entry_h
                continue
            if risk < RISK_MIN:
                nxt = (int(entry_h // 24.0) + 1) * 24.0
                clock[i] = nxt
                balance[i] = equity_i
                day[i] = int(nxt // 24.0)
                continue
            if entry_h >= horizon:
                clock[i] = entry_h
                balance[i] = reset_balance_i
                day[i] = day_i
                continue
            exit_h = entry_h + duration
            breach_line = daily_floor
            spans_reset = int(exit_h // 24.0) > int(entry_h // 24.0)
            if spans_reset:
                new_line = 0.97 * equity_i
                if new_line < floor:
                    new_line = floor
                if new_line > breach_line:
                    breach_line = new_line
            if equity_i + adverse * risk <= breach_line:
                state[i] = 2
                resolved_at[i] = entry_h + duration * 0.5
                continue
            if equity_i + favourable * risk >= target:
                state[i] = 1
                resolved_at[i] = entry_h + duration * 0.5
                continue
            if spans_reset:
                reset_balance_i = equity_i
            eq[i] = equity_i + realized * risk
            clock[i] = exit_h
            balance[i] = reset_balance_i
            day[i] = int(exit_h // 24.0)
    return _aggregate(state, resolved_at, count, steps)


def _row_trade(
    row: Mapping[str, Any],
) -> tuple[tuple[float, float, float, float, float], float | None] | None:
    realized = _num(row.get("realized_r"))
    if realized is None:
        realized = _num(row.get("R"))
    if realized is None:
        return None
    favourable = _num(row.get("mfe"))
    adverse = _num(row.get("mae"))
    if favourable is None:
        favourable = realized
    if adverse is None:
        adverse = realized
    if favourable < realized:
        favourable = realized
    if adverse > realized:
        adverse = realized
    duration = _num(row.get("duration_h"))
    if duration is None:
        duration = _num(row.get("dur"))
    if duration is None or duration < 0.0:
        duration = 8.0
    gap = _num(row.get("gap_h"))
    if gap is None:
        gap = _num(row.get("gap"))
    if gap is None or gap <= 0.0:
        gap = 96.0
    cost = None
    risk = _trade_risk_usd(row.get("size"), row.get("entry"), row.get("stop"))
    fee = _num(row.get("commission"))
    carry = _num(row.get("funding"))
    if risk is not None and risk > 0 and fee is not None and carry is not None:
        cost = (fee + carry) / risk
    return (realized, favourable, adverse, duration, gap), cost


def _aggregate(
    state: list[int],
    resolved_at: list[float | None],
    count: int,
    steps: int,
) -> dict[str, Any]:
    samples = [moment / 24.0 for moment in resolved_at if moment is not None]
    samples.sort()
    median = samples[len(samples) // 2] if samples else None
    horizons: dict[int, tuple[float, float, float, float]] = {}
    for days in (*HORIZONS, NO_LIMIT_DAYS):
        horizons[days] = _at_horizon(state, resolved_at, count, days * 24.0)
    return {"steps": steps, "horizons": horizons, "median_days": median}


def _at_horizon(
    state: list[int],
    resolved_at: list[float | None],
    count: int,
    limit: float,
) -> tuple[float, float, float, float]:
    passed = breach = locked = 0
    for outcome, moment in zip(state, resolved_at):
        if moment is None or moment > limit or outcome == 0:
            continue
        if outcome == 1:
            passed += 1
        elif outcome == 2:
            breach += 1
        elif outcome == 3:
            locked += 1
    pass_p = passed / count
    breach_p = breach / count
    locked_p = locked / count
    return pass_p, breach_p, locked_p, 1.0 - pass_p - breach_p - locked_p


def _probs(values: tuple[float, float, float, float]) -> dict[str, float]:
    passed, breach, locked, running = values
    return {
        "pass": round(passed, 4),
        "breach": round(breach, 4),
        "locked": round(locked, 4),
        "running": round(running, 4),
    }


def _terminal(kind: str, *, source: str, cost_r: float | None) -> dict[str, Any]:
    row = {"pass": 0.0, "breach": 0.0, "locked": 0.0, "running": 0.0}
    row[kind] = 1.0
    return {
        "available": True,
        "model": "terminal",
        "source": source,
        "seed": SEED,
        "paths": 0,
        "rule": "cap150",
        "trades": 0,
        "cost_r": None if cost_r is None else round(cost_r, 4),
        "d30": dict(row),
        "d60": dict(row),
        "d90": dict(row),
        "nolimit": dict(row),
        "median_days": 0.0,
    }


def _trade_risk_usd(size: Any, entry: Any, stop: Any) -> float | None:
    """Same denominator as ``eval_outcomes.trade_risk_usd`` (0.04% per side)."""
    size_f = _num(size)
    entry_f = _num(entry)
    stop_f = _num(stop)
    if size_f is None or entry_f is None or stop_f is None:
        return None
    if size_f <= 0 or entry_f <= 0:
        return None
    return size_f * (abs(entry_f - stop_f) + 2.0 * 0.0004 * entry_f)


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float, str)):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if number != number or number in {float("inf"), float("-inf")}:
            return None
        return number
    return None
