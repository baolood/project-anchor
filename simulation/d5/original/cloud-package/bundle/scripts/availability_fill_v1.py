#!/usr/bin/env python3
"""Availability fill rule v1 -- minimal, isolated engine.

Rule version: FILL_RULE_AVAILABILITY_T3_STRICT_OPEN_V1

Model assumptions (all UNVERIFIED):
  * SLIPPAGE_PER_SIDE / COMMISSION_PER_SIDE / NOTIONAL_POSITION_AMOUNT / ASSUMED_STARTING_EQUITY.
  * Every simulated fill price is a MODEL ASSUMPTION, not evidence of tradability.

Evidence ordering (binding):
  * A signal becomes available at the *published* instant (T3) of the round that produced it.
    T3 is producer-side publication evidence; it does NOT mean a downstream consumer received it.
  * A round artifact must never contain a timestamp taken after its own write, and never claim
    that its own instructions were registered; those live in later, separate records.
  * Backlogged bars and previously pending instructions are processed strictly in time order
    BEFORE this round's new instructions are registered, so a new signal can never erase a fill
    that should already have happened.
  * `simulated_entry_at` belongs to the OPENING leg of one specific instruction only. A pure
    EXIT instruction can never fill an entry time.

Run with:  python3 -m unittest tests/test_availability_fill_v1.py -v
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

FILL_RULE_VERSION = "FILL_RULE_AVAILABILITY_T3_STRICT_OPEN_V1"
RESOLUTION_SECONDS = 14400  # 4h bars

# --- ALL model assumptions below are UNVERIFIED -----------------------------
SLIPPAGE_PER_SIDE = 0.0002          # 2 bps per side
COMMISSION_PER_SIDE = 0.0004        # 4 bps per side, charged on every leg
NOTIONAL_POSITION_AMOUNT = 1000.0   # notional position amount (NOT "principal")
ASSUMED_STARTING_EQUITY = 5000.0    # unverified assumed starting equity
STOP_PCT = 0.01
TARGET_PCT = 0.015

# --- instruction / report statuses ------------------------------------------
STATUS_PENDING = "PENDING"
STATUS_FILLED = "FILLED"
STATUS_CONFLICT_SAME_T3 = "CONFLICT_SAME_T3"
STATUS_UNKNOWN_NO_T3_EVIDENCE = "UNKNOWN_NO_T3_EVIDENCE"
STATUS_NOT_APPLICABLE_EXIT = "NOT_APPLICABLE_EXIT"
STATUS_NO_ACTIVE_INSTRUCTION = "NO_ACTIVE_INSTRUCTION"

KIND_ENTER = "ENTER"
KIND_EXIT = "EXIT"

LABEL_BOTH_LEVELS = "ADVERSE_FIRST_ASSUMED"
LABEL_GAP_STOP = "exit_gap_through_stop"
LABEL_GAP_TARGET = "exit_gap_through_target"

# Exit reasons
EXIT_TARGET = "TARGET"
EXIT_STOP = "STOP"
EXIT_GAP_STOP = "GAP_STOP"
EXIT_GAP_TARGET = "GAP_TARGET"
EXIT_SIGNAL = "SIGNAL"


def pair_key(strategy: str, symbol: str) -> str:
    return f"{strategy}|{symbol}"


def _digest(*parts: Any) -> str:
    raw = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def make_instruction_id(pair: str, kind: str, side: int, signal_bar_close_at: str | None,
                        round_id: str) -> str:
    """Deterministic id, generated BEFORE publication (so artifact A can carry it)."""
    return _digest("instruction", pair, kind, side, signal_bar_close_at, round_id)


def _seconds(iso: str) -> float:
    from datetime import datetime, timezone
    value = iso.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def new_state() -> dict:
    return {
        "version": FILL_RULE_VERSION,
        "cursor_seconds": {},            # pair -> last processed bar OPEN (seconds)
        "pending": {},                   # pair -> list of instructions
        "position": {},                  # pair -> open position or None
        "trades": {},                    # pair -> list of closed trades
        "last_observed_signal": {},      # pair -> int | None (last OBSERVED state)
        "applied_rounds": {},            # round_id -> advance_id (idempotence)
        "log": [],                       # audit trail (replaced / dropped / conflict / ...)
    }


def load_state(path: Path) -> dict:
    if not Path(path).is_file():
        return new_state()
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_state(path: Path, state: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# --- per-pair accessors -----------------------------------------------------

def _cursor(state: Mapping[str, Any], pair: str) -> float | None:
    return state["cursor_seconds"].get(pair)


def _pending(state: Mapping[str, Any], pair: str) -> list:
    return state["pending"].setdefault(pair, [])


def _position(state: Mapping[str, Any], pair: str):
    return state["position"].get(pair)


def _trades(state: Mapping[str, Any], pair: str) -> list:
    return state["trades"].setdefault(pair, [])


# --- planning (BEFORE publication; artifact A content) ----------------------

def plan_round(state: Mapping[str, Any], *, round_id: str,
               current_signals: Mapping[str, int | None],
               signal_bar_close_at: Mapping[str, str | None]) -> dict:
    """Decide, per pair, whether THIS round produces a new instruction.

    Detection is on the observed signal STATE, including non-zero -> zero (which the
    legacy `new_signal` flag misses). The first observation of an already-present
    direction is not a new entry: there is no adjacent prior bar yet. The action
    itself is re-derived from the actual position at execution time, so no position
    lookup happens here.

    Produces correlation ids only. No T3, no registration status: both are recorded
    later, in separate records written after the artifacts.
    """
    plan: dict[str, dict] = {}
    for pair, signal in current_signals.items():
        if signal is None:
            continue
        previous = state["last_observed_signal"].get(pair)
        if signal == previous:
            continue
        # Research backtest enters only when adjacent bars change direction.
        # A missing previous observation is not that prior bar, so startup must
        # not open on an already-present direction (None -> -1 or None -> 1).
        # None -> 0 stays a no-op as well.
        if previous is None:
            continue
        if signal == 0:
            kind, side = KIND_EXIT, 0
        else:
            kind, side = KIND_ENTER, (1 if signal > 0 else -1)
        plan[pair] = {
            "instruction_id": make_instruction_id(
                pair, kind, side, signal_bar_close_at.get(pair), round_id
            ),
            "kind": kind,
            "side": side,
            "signal_bar_close_at": signal_bar_close_at.get(pair),
        }
    return plan


def register_round(state: dict, plan: Mapping[str, Mapping[str, Any]],
                   current_signals: Mapping[str, int | None], *, t3: str | None,
                   round_id: str) -> list[dict]:
    """Register this round's planned instructions AFTER the backlog was processed.

    Latest-wins: any instruction still pending for that pair is replaced (and logged).
    The observed signal state is updated for EVERY pair we have a signal for - whether
    or not an instruction was produced - so a later transition is never missed.
    """
    for pair, signal in current_signals.items():
        if signal is not None:
            state["last_observed_signal"][pair] = signal

    registered: list[dict] = []
    for pair, planned in plan.items():
        replaced = _pending(state, pair)
        for old in replaced:
            old["status"] = "REPLACED"
            state["log"].append({
                "event": "instruction_replaced",
                "pair": pair,
                "replaced_instruction": old["instruction_id"],
                "replaced_by": planned["instruction_id"],
                "round_id": round_id,
            })
        instruction = {
            "instruction_id": planned["instruction_id"],
            "kind": planned["kind"],
            "side": planned["side"],
            "signal_bar_close_at": planned["signal_bar_close_at"],
            "t3": t3,
            "registered_round_id": round_id,
            "status": STATUS_PENDING if t3 else STATUS_UNKNOWN_NO_T3_EVIDENCE,
        }
        state["pending"][pair] = [instruction]
        registered.append(instruction)
    return registered


# --- advance (backlog: bars strictly after each pair's cursor) --------------

def compute_advance_id(state: Mapping[str, Any], series_by_pair: Mapping[str, Sequence[Mapping]],
                       round_id: str) -> str:
    parts: list[Any] = ["advance", round_id]
    for pair in sorted(series_by_pair):
        cursor = _cursor(state, pair)
        newest = max((bar["time"] for bar in series_by_pair[pair]), default=None)
        parts += [pair, cursor, newest]
    return _digest(*parts)


def _select_pending(pending: Sequence[Mapping[str, Any]], bar_open: float) -> tuple[Any, str | None]:
    """Latest instruction with T3 strictly earlier than the bar open.

    Equal T3 values give no reliable ordering evidence -> do not execute; report a conflict.
    """
    eligible = [i for i in pending
                if i.get("t3") and _seconds(i["t3"]) < bar_open
                and i.get("status") == STATUS_PENDING]
    if not eligible:
        return None, None
    best_t3 = max(_seconds(i["t3"]) for i in eligible)
    best = [i for i in eligible if _seconds(i["t3"]) == best_t3]
    if len(best) > 1:
        return None, STATUS_CONFLICT_SAME_T3
    return best[0], None


def _leg_fee() -> float:
    return NOTIONAL_POSITION_AMOUNT * COMMISSION_PER_SIDE


def _open_position(state: dict, pair: str, *, side: int, bar: Mapping[str, Any],
                   instruction_id: str, events: list) -> None:
    price = bar["open"] * (1 + SLIPPAGE_PER_SIDE * side)
    state["position"][pair] = {
        "side": side,
        "entry_time": _iso(bar["time"]),
        "entry_price": price,
        "stop": price * (1 - STOP_PCT) if side > 0 else price * (1 + STOP_PCT),
        "target": price * (1 + TARGET_PCT) if side > 0 else price * (1 - TARGET_PCT),
        "instruction_id": instruction_id,
        "fees": _leg_fee(),
    }
    events.append({"event": "open_leg", "pair": pair, "instruction_id": instruction_id,
                   "time": _iso(bar["time"]), "price": price, "side": side})


def _close_position(state: dict, pair: str, *, bar_open_price: float, time_iso: str,
                    reason: str, labels: Sequence[str], events: list,
                    instruction_id: str | None = None) -> None:
    """Close the open position.

    `instruction_id` is the instruction that CAUSED this leg (a flip's closing leg shares
    the flip instruction's id). A resting stop/target fill is caused by no instruction and
    passes None.
    """
    position = _position(state, pair)
    if position is None:
        return
    side = position["side"]
    exit_price = bar_open_price * (1 - SLIPPAGE_PER_SIDE * side)
    fees = position["fees"] + _leg_fee()
    gross = (exit_price - position["entry_price"]) / position["entry_price"] * side
    trade = {
        "entry_instruction_id": position["instruction_id"],
        "exit_instruction_id": instruction_id,
        "side": side,
        "entry_time": position["entry_time"],
        "entry_price": position["entry_price"],
        "exit_time": time_iso,
        "exit_price": exit_price,
        "exit_reason": reason,
        "labels": sorted(set(labels)),
        "fees": fees,
        "pnl": gross * NOTIONAL_POSITION_AMOUNT - fees,
    }
    _trades(state, pair).append(trade)
    state["position"][pair] = None
    events.append({"event": "close_leg", "pair": pair, "instruction_id": instruction_id,
                   "time": time_iso, "price": exit_price, "reason": reason,
                   "labels": trade["labels"], "pnl": trade["pnl"]})


def _iso(seconds: float) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


def _process_bar_open(state: dict, pair: str, bar: Mapping[str, Any], events: list) -> None:
    position = _position(state, pair)
    bar_open = bar["open"]
    if position is not None:
        side = position["side"]
        if side > 0 and bar_open <= position["stop"]:
            _close_position(state, pair, bar_open_price=bar_open, time_iso=_iso(bar["time"]),
                            reason=EXIT_GAP_STOP, labels=[LABEL_GAP_STOP], events=events)
        elif side < 0 and bar_open >= position["stop"]:
            _close_position(state, pair, bar_open_price=bar_open, time_iso=_iso(bar["time"]),
                            reason=EXIT_GAP_STOP, labels=[LABEL_GAP_STOP], events=events)
        elif side > 0 and bar_open >= position["target"]:
            _close_position(state, pair, bar_open_price=bar_open, time_iso=_iso(bar["time"]),
                            reason=EXIT_GAP_TARGET, labels=[LABEL_GAP_TARGET], events=events)
        elif side < 0 and bar_open <= position["target"]:
            _close_position(state, pair, bar_open_price=bar_open, time_iso=_iso(bar["time"]),
                            reason=EXIT_GAP_TARGET, labels=[LABEL_GAP_TARGET], events=events)

    instruction, conflict = _select_pending(_pending(state, pair), bar["time"])
    if conflict:
        for item in _pending(state, pair):
            if item.get("status") == STATUS_PENDING and item.get("t3") \
                    and _seconds(item["t3"]) < bar["time"]:
                item["status"] = STATUS_CONFLICT_SAME_T3
        state["log"].append({"event": "instruction_conflict_same_t3", "pair": pair,
                             "bar_open": _iso(bar["time"])})
        events.append({"event": "instruction_conflict_same_t3", "pair": pair,
                       "time": _iso(bar["time"])})
        return
    if instruction is None:
        return

    instruction["status"] = "EXECUTED"
    state["pending"][pair] = [i for i in _pending(state, pair) if i is not instruction]
    target_side = instruction["side"] if instruction["kind"] == KIND_ENTER else 0
    current = _position(state, pair)

    if target_side == 0:
        if current is None:
            state["log"].append({"event": "instruction_dropped_no_position", "pair": pair,
                                 "instruction_id": instruction["instruction_id"]})
            events.append({"event": "dropped_no_position", "pair": pair,
                           "instruction_id": instruction["instruction_id"],
                           "time": _iso(bar["time"])})
        else:
            _close_position(state, pair, bar_open_price=bar["open"], time_iso=_iso(bar["time"]),
                            reason=EXIT_SIGNAL, labels=[], events=events,
                            instruction_id=instruction["instruction_id"])
        return

    if current is None:
        _open_position(state, pair, side=target_side, bar=bar,
                       instruction_id=instruction["instruction_id"], events=events)
        return
    if current["side"] == target_side:
        state["log"].append({"event": "instruction_dropped_position_open", "pair": pair,
                             "instruction_id": instruction["instruction_id"]})
        events.append({"event": "dropped_position_open", "pair": pair,
                       "instruction_id": instruction["instruction_id"],
                       "time": _iso(bar["time"])})
        return
    # flip: ONE instruction, TWO fill legs sharing this instruction's id/T3
    _close_position(state, pair, bar_open_price=bar["open"], time_iso=_iso(bar["time"]),
                    reason=EXIT_SIGNAL, labels=[], events=events,
                    instruction_id=instruction["instruction_id"])
    _open_position(state, pair, side=target_side, bar=bar,
                   instruction_id=instruction["instruction_id"], events=events)


def _process_bar_close(state: dict, pair: str, bar: Mapping[str, Any], events: list) -> None:
    position = _position(state, pair)
    if position is None:
        return
    side = position["side"]
    stop_hit = bar["low"] <= position["stop"] if side > 0 else bar["high"] >= position["stop"]
    target_hit = bar["high"] >= position["target"] if side > 0 else bar["low"] <= position["target"]
    labels: list[str] = []
    reason = None
    if stop_hit and target_hit:
        labels.append(LABEL_BOTH_LEVELS)      # conservative assumption, not evidence
        reason = EXIT_STOP                    # adverse-first
    elif stop_hit:
        reason = EXIT_STOP
    elif target_hit:
        reason = EXIT_TARGET
    if reason is None:
        return
    level = position["stop"] if reason == EXIT_STOP else position["target"]
    _close_position(state, pair, bar_open_price=level, time_iso=_iso(bar["time"]),
                    reason=reason, labels=labels, events=events)


def apply_advance(state: dict, series_by_pair: Mapping[str, Sequence[Mapping[str, Any]]], *,
                  round_id: str) -> tuple[list[dict], bool]:
    """Process backlogged bars in time order. Returns (events, applied?).

    Idempotent per round: a rerun after a failed report write (state already saved) does
    NOT re-apply fills or fees. Bars left unprocessed stay behind the cursor and are picked
    up by the next round's advance.
    """
    advance_id = compute_advance_id(state, series_by_pair, round_id)
    if round_id in state["applied_rounds"]:
        return [], False
    events: list[dict] = []
    for pair, series in series_by_pair.items():
        cursor = _cursor(state, pair)
        for bar in sorted(series, key=lambda item: item["time"]):
            if cursor is not None and bar["time"] <= cursor:
                continue
            _process_bar_open(state, pair, bar, events)
            _process_bar_close(state, pair, bar, events)
            state["cursor_seconds"][pair] = bar["time"]
    state["applied_rounds"][round_id] = advance_id
    return events, True


# --- reporting --------------------------------------------------------------

def _pending_conflict(pending: Sequence[Mapping[str, Any]]) -> bool:
    active = [i for i in pending if i.get("status") == STATUS_PENDING]
    if len(active) < 2:
        return False
    stamps = [i.get("t3") for i in active]
    return len(set(stamps)) < len(stamps)


def instruction_view(state: Mapping[str, Any], pair: str) -> dict:
    """`simulated_entry_at` belongs to the OPENING leg of the current instruction only."""
    pending = _pending(state, pair)
    active = [i for i in pending if i.get("status") == STATUS_PENDING]
    conflicted = [i for i in pending if i.get("status") == STATUS_CONFLICT_SAME_T3]
    if conflicted or _pending_conflict(pending):
        return {"instruction_id": (active[0]["instruction_id"] if active else None),
                "simulated_entry_at": None,
                "simulated_entry_time_status": STATUS_CONFLICT_SAME_T3}
    if active:
        instruction = active[0]
        if not instruction.get("t3"):
            status = STATUS_UNKNOWN_NO_T3_EVIDENCE
        elif instruction["kind"] == KIND_EXIT:
            status = STATUS_NOT_APPLICABLE_EXIT
        else:
            status = STATUS_PENDING
        return {"instruction_id": instruction["instruction_id"],
                "simulated_entry_at": None, "simulated_entry_time_status": status}
    position = _position(state, pair)
    if position is not None:
        return {"instruction_id": position["instruction_id"],
                "simulated_entry_at": position["entry_time"],
                "simulated_entry_time_status": STATUS_FILLED}
    return {"instruction_id": None, "simulated_entry_at": None,
            "simulated_entry_time_status": STATUS_NO_ACTIVE_INSTRUCTION}


def metrics(state: Mapping[str, Any], pair: str) -> dict:
    trades = _trades(state, pair)
    equity = ASSUMED_STARTING_EQUITY
    peak = equity
    worst = 0.0
    wins = 0
    gross_win = 0.0
    gross_loss = 0.0
    for trade in trades:
        equity += trade["pnl"]
        peak = max(peak, equity)
        if peak > 0:
            worst = max(worst, (peak - equity) / peak * 100.0)
        if trade["pnl"] > 0:
            wins += 1
            gross_win += trade["pnl"]
        elif trade["pnl"] < 0:
            gross_loss += -trade["pnl"]
    net = sum(t["pnl"] for t in trades)
    return {
        "fill_rule_version": FILL_RULE_VERSION,
        "trades": len(trades),
        "net_pnl": net,
        "win_rate_pct": (wins / len(trades) * 100.0) if trades else None,
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else None,
        "max_drawdown_pct": worst,
        "assumed_starting_equity": ASSUMED_STARTING_EQUITY,
        "notional_position_amount": NOTIONAL_POSITION_AMOUNT,
        "slippage_per_side": SLIPPAGE_PER_SIDE,
        "commission_per_side": COMMISSION_PER_SIDE,
        "model_assumptions_unverified": True,
    }


# --- minimal round driver ---------------------------------------------------

def build_artifact_a(plan: Mapping[str, Mapping[str, Any]], *, round_id: str) -> dict:
    """Artifact-A content: signal-driven correlation ids ONLY.

    Deliberately carries NO T3 (that instant is only obtained after A is written) and NO
    registration status (registration happens after the backlog, in a later record).
    """
    return {
        "fill_rule_version": FILL_RULE_VERSION,
        "round_id": round_id,
        "planned_instructions": {
            pair: {
                "instruction_id": item["instruction_id"],
                "kind": item["kind"],
                "side": item["side"],
                "signal_bar_close_at": item["signal_bar_close_at"],
            }
            for pair, item in sorted(plan.items())
        },
    }


def build_artifact_b(state: Mapping[str, Any], *, round_id: str, source_round_t3: str | None,
                     events: Sequence[Mapping], applied: bool,
                     registered: Sequence[Mapping]) -> dict:
    """Engine report.

    Carries `source_round_t3` (the A round's publication instant: prior knowledge) but
    NEVER its own post-write publication instant - that belongs in the caller's later record.
    """
    pairs = sorted(state["last_observed_signal"])
    return {
        "fill_rule_version": FILL_RULE_VERSION,
        "round_id": round_id,
        "source_round_t3": source_round_t3,
        "advance_applied": applied,
        "events": [dict(event) for event in events],
        "registered_instructions": [
            {"instruction_id": i["instruction_id"], "kind": i["kind"], "side": i["side"],
             "t3": i["t3"], "status": i["status"]}
            for i in registered
        ],
        "views": {pair: instruction_view(state, pair) for pair in pairs},
        "metrics_v1": {pair: metrics(state, pair) for pair in pairs},
        "model_assumptions_unverified": True,
    }


def execute_round(state: dict, *, round_id: str, t3: str | None,
                  series_by_pair: Mapping[str, Sequence[Mapping[str, Any]]],
                  current_signals: Mapping[str, int | None],
                  signal_bar_close_at: Mapping[str, str | None],
                  state_path: Path | None = None, report_writer=None) -> dict:
    """Minimal round driver, in the binding order.

    1. plan            -> artifact-A content (correlation ids only)
    2. advance         -> backlogged bars handled with the OLD pending instructions
    3. register        -> THIS round's instructions (never before the backlog)
    4. save state      -> persisted BEFORE the report write
    5. write report B  -> a failure here is retryable: the rerun does not re-apply fills
    """
    plan = plan_round(state, round_id=round_id, current_signals=current_signals,
                      signal_bar_close_at=signal_bar_close_at)
    artifact_a = build_artifact_a(plan, round_id=round_id)
    events, applied = apply_advance(state, series_by_pair, round_id=round_id)
    registered = register_round(state, plan, current_signals, t3=t3, round_id=round_id)
    if state_path is not None:
        save_state(Path(state_path), state)
    report = build_artifact_b(state, round_id=round_id, source_round_t3=t3, events=events,
                              applied=applied, registered=registered)
    if report_writer is not None:
        report_writer(report)
    return {"artifact_a": artifact_a, "report": report}
