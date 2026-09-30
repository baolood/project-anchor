"""Gate A protective risk boundary for Official-shaped Fake-Fill.

DEPLOY = NO. Live trading is NO-GO.

Order for every open candidate:
1. Build the fill price from the signal reference and the frozen slippage schedule.
2. Set preset_stop_price from the frozen adverse-bps rule. Side and entry only.
3. Measure stop_distance from that entry to that stop.
4. max_risk_amount = equity_at_open * 0.5%.
5. Solve the maximum quantity from stop_distance, expected fees, and simulated slippage.
6. If the candidate is larger, shrink the quantity. If no positive quantity fits, reject.
The stop is never moved farther from entry to make a size fit.

Version constants are the contract. This module does not load a prior ledger series.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Optional


DEPLOY = "NO"
LIVE_TRADING = "NO-GO"

STRATEGY_VERSION = "affl_v2_c6_protective_v1"
SCHEMA_VERSION = "official_ledger_c6_v1"
MODEL_VERSION = STRATEGY_VERSION
DATA_VERSION = "c6_boundary_v1"
STOP_RULE_ID = "STOP_RULE_C6_FIXED_ADVERSE_BPS_V1"
SIZE_POLICY_ID = "SIZE_POLICY_C6_SHRINK_TO_MAX_ELSE_REJECT_V1"

# Round schedule constants for this schema. They are not fitted outputs.
FIXED_ADVERSE_STOP_BPS = Decimal("100")
FEE_BPS = Decimal("5")
SLIPPAGE_BPS = Decimal("2")
MAX_RISK_PCT = Decimal("0.005")
QTY_QUANTUM = Decimal("0.00000001")
BPS = Decimal(1) / Decimal(10000)

FEE_RATE = FEE_BPS * BPS
SLIPPAGE_RATE = SLIPPAGE_BPS * BPS
STOP_RATE = FIXED_ADVERSE_STOP_BPS * BPS

MARKET = "PF_XBTUSD"
SAMPLE_CLASS = "FORWARD_LIVE_SHADOW"
FUNDING_DATA_STATUS = "MISSING"
NET_PNL_STATUS = "EX_FUNDING"
GENESIS_HASH = "GENESIS"
EXECUTION_FAKE_FILL = "fake_fill"

SIZE_ACTION_UNCHANGED = "UNCHANGED"
SIZE_ACTION_SHRINK = "SHRINK"

EX_ANTE_FIELDS = (
    "trade_id",
    "entry_price",
    "preset_stop_price",
    "equity_at_open",
    "risk_amount",
    "risk_pct",
    "stop_distance",
    "max_risk_amount",
    "max_quantity",
    "candidate_quantity",
    "quantity",
    "size_action",
    "stop_rule_id",
    "size_policy_id",
    "strategy_version",
    "schema_version",
)


class ProtectiveBoundaryError(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _require_execution(execution: str) -> None:
    if execution != EXECUTION_FAKE_FILL:
        raise ProtectiveBoundaryError("LIVE_TRADING_NO_GO")


def D(value) -> Decimal:
    if isinstance(value, float):
        raise TypeError("float is forbidden; pass Decimal or str")
    if isinstance(value, Decimal):
        return value
    return Decimal(value)


def floor_qty(amount: Decimal) -> Decimal:
    if amount <= 0:
        return Decimal(0)
    return amount.quantize(QTY_QUANTUM, rounding=ROUND_DOWN)


def adverse_fill_price(order_side: str, reference_price: Decimal) -> Decimal:
    """Buy fills above the reference. Sell fills below it."""
    reference_price = D(reference_price)
    if order_side == "LONG":
        return reference_price * (Decimal(1) + SLIPPAGE_RATE)
    if order_side == "SHORT":
        return reference_price * (Decimal(1) - SLIPPAGE_RATE)
    raise ProtectiveBoundaryError("C6_INVALID_SIDE")


def frozen_stop_price(side: str, entry_price: Decimal) -> Decimal:
    """Preset stop from the frozen adverse-bps rule.

    Arguments are the position side and the entry fill only.
    """
    entry_price = D(entry_price)
    if entry_price <= 0:
        raise ProtectiveBoundaryError("C6_INVALID_ENTRY")
    if side == "LONG":
        return entry_price * (Decimal(1) - STOP_RATE)
    if side == "SHORT":
        return entry_price * (Decimal(1) + STOP_RATE)
    raise ProtectiveBoundaryError("C6_INVALID_SIDE")


def price_stop_distance(entry_price: Decimal, preset_stop_price: Decimal) -> Decimal:
    return abs(D(entry_price) - D(preset_stop_price))


def risk_per_unit(
    entry_price: Decimal,
    preset_stop_price: Decimal,
    reference_price: Decimal,
) -> Decimal:
    """Ex-ante loss of one unit from entry to the preset stop, plus fees and sim slip."""
    entry_price = D(entry_price)
    preset_stop_price = D(preset_stop_price)
    reference_price = D(reference_price)
    stop_distance = price_stop_distance(entry_price, preset_stop_price)
    entry_slip = abs(entry_price - reference_price)
    exit_slip = abs(preset_stop_price) * SLIPPAGE_RATE
    fees = (abs(entry_price) + abs(preset_stop_price)) * FEE_RATE
    return stop_distance + entry_slip + exit_slip + fees


def max_allowed_quantity(
    entry_price: Decimal,
    preset_stop_price: Decimal,
    reference_price: Decimal,
    equity_at_open: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    """Return (max_quantity, max_risk_amount, per_unit).

    max_quantity is rounded down to the quantum so risk_pct stays at or under 0.5%.
    """
    equity_at_open = D(equity_at_open)
    if equity_at_open <= 0:
        return Decimal(0), Decimal(0), risk_per_unit(entry_price, preset_stop_price, reference_price)
    per_unit = risk_per_unit(entry_price, preset_stop_price, reference_price)
    max_risk_amount = equity_at_open * MAX_RISK_PCT
    if per_unit <= 0:
        return Decimal(0), max_risk_amount, per_unit
    max_quantity = floor_qty(max_risk_amount / per_unit)
    guard = 0
    while max_quantity > 0 and (per_unit * max_quantity) > max_risk_amount:
        max_quantity -= QTY_QUANTUM
        guard += 1
        if max_quantity < 0 or guard > 8:
            return Decimal(0), max_risk_amount, per_unit
    return max_quantity, max_risk_amount, per_unit


def _decimal_str(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in ("", "-0"):
        return "0"
    return text


def _jsonable(value):
    if isinstance(value, Decimal):
        return _decimal_str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError("unsupported ledger value %s" % type(value).__name__)


def row_hash(event: dict) -> str:
    body = {key: _jsonable(val) for key, val in event.items() if key != "row_hash"}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass
class OpenLeg:
    trade_id: str
    side: str
    quantity: Decimal
    entry_price: Decimal
    reference_price: Decimal
    preset_stop_price: Decimal
    protective_stop_price: Decimal
    equity_at_open: Decimal
    risk_amount: Decimal
    risk_pct: Decimal
    stop_distance: Decimal
    max_risk_amount: Decimal
    max_quantity: Decimal
    candidate_quantity: Decimal
    size_action: str
    entry_fee: Decimal
    entry_ledger_event_id: str

    def ex_ante(self) -> dict:
        return {
            "trade_id": self.trade_id,
            "entry_price": self.entry_price,
            "preset_stop_price": self.preset_stop_price,
            "equity_at_open": self.equity_at_open,
            "risk_amount": self.risk_amount,
            "risk_pct": self.risk_pct,
            "stop_distance": self.stop_distance,
            "max_risk_amount": self.max_risk_amount,
            "max_quantity": self.max_quantity,
            "candidate_quantity": self.candidate_quantity,
            "quantity": self.quantity,
            "size_action": self.size_action,
            "stop_rule_id": STOP_RULE_ID,
            "size_policy_id": SIZE_POLICY_ID,
            "strategy_version": STRATEGY_VERSION,
            "schema_version": SCHEMA_VERSION,
        }


class ProtectiveRiskBook:
    """In-memory Fake-Fill book. Append-only Official-shaped events. No order routing."""

    def __init__(self, starting_equity, *, execution: str = EXECUTION_FAKE_FILL):
        _require_execution(execution)
        starting_equity = D(starting_equity)
        if starting_equity < 0:
            raise ProtectiveBoundaryError("C6_INVALID_EQUITY")
        self.execution = execution
        self.cash = starting_equity
        self.realized_pnl_cum = Decimal(0)
        self.position: Optional[OpenLeg] = None
        self._events: list[dict] = []
        self._seq = 0
        self._prev_hash = GENESIS_HASH

    @property
    def events(self) -> list[dict]:
        return deepcopy(self._events)

    def to_jsonl(self) -> str:
        lines = []
        for event in self._events:
            lines.append(json.dumps(_jsonable(event), sort_keys=True, separators=(",", ":")))
        if not lines:
            return ""
        return "\n".join(lines) + "\n"

    def net_liquidation(self, mark: Decimal) -> Decimal:
        if self.position is None:
            return self.cash
        mark = D(mark)
        direction = Decimal(1) if self.position.side == "LONG" else Decimal(-1)
        unrealized = (mark - self.position.entry_price) * self.position.quantity * direction
        return self.cash + unrealized

    def on_signal(
        self,
        choice: str,
        reference_price,
        candidate_quantity,
        *,
        observation_id: str,
        at: str,
        execution: str = EXECUTION_FAKE_FILL,
    ) -> list[dict]:
        _require_execution(execution)
        if choice not in ("LONG", "SHORT", "FLAT"):
            raise ProtectiveBoundaryError("C6_INVALID_SIDE")
        reference = D(reference_price)
        candidate = D(candidate_quantity)

        if self.position is None:
            if choice == "FLAT":
                return []
            return [self._open_leg(choice, reference, candidate, observation_id, at, "OPEN")]

        if choice == self.position.side:
            return []

        if choice == "FLAT":
            return [self._close_leg(
                exit_price=adverse_fill_price(_sell_buy(self.position.side), reference),
                event_type="FLAT_EXIT",
                reason_code="FLAT_SIGNAL",
                observation_id=observation_id,
                at=at,
                signal_choice="FLAT",
                reference_price=reference,
            )]

        events = [self._close_leg(
            exit_price=adverse_fill_price(_sell_buy(self.position.side), reference),
            event_type="REVERSE_EXIT",
            reason_code="REVERSE_SIGNAL",
            observation_id=observation_id,
            at=at,
            signal_choice=choice,
            reference_price=reference,
        )]
        events.append(self._open_leg(choice, reference, candidate, observation_id, at, "REVERSE_ENTRY"))
        return events

    def on_mark(self, price, *, observation_id: str, at: str) -> Optional[dict]:
        if self.position is None:
            return None
        mark = D(price)
        if mark <= 0:
            raise ProtectiveBoundaryError("C6_INVALID_MARK")
        trigger = self.position.protective_stop_price
        if self.position.side == "LONG" and mark > trigger:
            return None
        if self.position.side == "SHORT" and mark < trigger:
            return None
        slipped = adverse_fill_price(_sell_buy(self.position.side), trigger)
        if self.position.side == "LONG":
            exit_price = mark if mark < slipped else slipped
        else:
            exit_price = mark if mark > slipped else slipped
        return self._close_leg(
            exit_price=exit_price,
            event_type="HARD_STOP_EXIT",
            reason_code="HARD_STOP_TOUCHED",
            observation_id=observation_id,
            at=at,
            signal_choice=self.position.side,
            reference_price=trigger,
        )

    def propose_stop_update(self, new_stop, *, observation_id: str, at: str) -> Optional[dict]:
        if self.position is None:
            raise ProtectiveBoundaryError("C6_NO_POSITION")
        proposed = D(new_stop)
        current = self.position.protective_stop_price
        entry = self.position.entry_price
        if proposed == current:
            return None
        if not _is_tighter(self.position.side, entry, current, proposed):
            return self._append(self._shell(
                event_type="STOP_UPDATE_REJECTED",
                reason_code="STOP_WIDEN_FORBIDDEN",
                observation_id=observation_id,
                at=at,
                fill_status=None,
                extra={
                    "proposed_stop_price": proposed,
                    "protective_stop_price": current,
                    **self.position.ex_ante(),
                },
            ))
        self.position.protective_stop_price = proposed
        return self._append(self._shell(
            event_type="STOP_TIGHTEN",
            reason_code="STOP_TIGHTENED",
            observation_id=observation_id,
            at=at,
            fill_status=None,
            extra={
                "proposed_stop_price": proposed,
                "protective_stop_price": proposed,
                "ex_ante_fields_unchanged": True,
                **self.position.ex_ante(),
            },
        ))

    def _open_leg(
        self,
        side: str,
        reference: Decimal,
        candidate: Decimal,
        observation_id: str,
        at: str,
        event_type: str,
    ) -> dict:
        if reference <= 0:
            return self._reject(
                reason_code="C6_INVALID_ENTRY",
                observation_id=observation_id,
                at=at,
                signal_choice=side,
                reference_price=reference,
                candidate_quantity=candidate,
                preset_stop_price=None,
                entry_price=None,
            )
        if candidate <= 0:
            entry = adverse_fill_price(side, reference)
            stop = frozen_stop_price(side, entry)
            return self._reject(
                reason_code="C6_CANDIDATE_SIZE_NON_POSITIVE",
                observation_id=observation_id,
                at=at,
                signal_choice=side,
                reference_price=reference,
                candidate_quantity=candidate,
                preset_stop_price=stop,
                entry_price=entry,
            )

        equity_at_open = self.cash if self.position is None else self.net_liquidation(reference)
        entry = adverse_fill_price(side, reference)
        stop = frozen_stop_price(side, entry)
        distance = price_stop_distance(entry, stop)
        if (side == "LONG" and stop >= entry) or (side == "SHORT" and stop <= entry) or distance <= 0:
            return self._reject(
                reason_code="C6_STOP_NOT_PROTECTIVE",
                observation_id=observation_id,
                at=at,
                signal_choice=side,
                reference_price=reference,
                candidate_quantity=candidate,
                preset_stop_price=None,
                entry_price=entry,
            )

        max_quantity, max_risk_amount, per_unit = max_allowed_quantity(
            entry, stop, reference, equity_at_open
        )
        if max_quantity <= 0 or equity_at_open <= 0:
            return self._reject(
                reason_code="C6_NO_POSITIVE_SIZE",
                observation_id=observation_id,
                at=at,
                signal_choice=side,
                reference_price=reference,
                candidate_quantity=candidate,
                preset_stop_price=stop,
                entry_price=entry,
                equity_at_open=equity_at_open,
                max_risk_amount=max_risk_amount,
                max_quantity=max_quantity,
                stop_distance=distance,
            )

        if candidate > max_quantity:
            quantity = max_quantity
            size_action = SIZE_ACTION_SHRINK
        else:
            quantity = floor_qty(candidate)
            size_action = SIZE_ACTION_UNCHANGED
            if quantity <= 0:
                return self._reject(
                    reason_code="C6_CANDIDATE_SIZE_NON_POSITIVE",
                    observation_id=observation_id,
                    at=at,
                    signal_choice=side,
                    reference_price=reference,
                    candidate_quantity=candidate,
                    preset_stop_price=stop,
                    entry_price=entry,
                    equity_at_open=equity_at_open,
                    max_risk_amount=max_risk_amount,
                    max_quantity=max_quantity,
                    stop_distance=distance,
                )
        risk_amount = per_unit * quantity
        if quantity <= 0 or risk_amount > max_risk_amount:
            return self._reject(
                reason_code="C6_RISK_STILL_EXCEEDS_CAP",
                observation_id=observation_id,
                at=at,
                signal_choice=side,
                reference_price=reference,
                candidate_quantity=candidate,
                preset_stop_price=stop,
                entry_price=entry,
                equity_at_open=equity_at_open,
                max_risk_amount=max_risk_amount,
                max_quantity=max_quantity,
                stop_distance=distance,
            )

        risk_pct = risk_amount / equity_at_open
        if risk_pct > MAX_RISK_PCT:
            raise ProtectiveBoundaryError("C6_OPEN_INVARIANT")

        entry_fee = entry * quantity * FEE_RATE
        self.cash -= entry_fee
        self.realized_pnl_cum -= entry_fee
        ledger_event_id = self._next_id()
        trade_id = "tr_%s" % ledger_event_id
        leg = OpenLeg(
            trade_id=trade_id,
            side=side,
            quantity=quantity,
            entry_price=entry,
            reference_price=reference,
            preset_stop_price=stop,
            protective_stop_price=stop,
            equity_at_open=equity_at_open,
            risk_amount=risk_amount,
            risk_pct=risk_pct,
            stop_distance=distance,
            max_risk_amount=max_risk_amount,
            max_quantity=max_quantity,
            candidate_quantity=candidate,
            size_action=size_action,
            entry_fee=entry_fee,
            entry_ledger_event_id=ledger_event_id,
        )
        self.position = leg
        notional = entry * quantity
        event = self._shell(
            event_type=event_type,
            reason_code="C6_OPEN",
            observation_id=observation_id,
            at=at,
            fill_status="FILLED",
            ledger_event_id=ledger_event_id,
            extra={
                "signal_choice": side,
                "side": side,
                "reference_price": reference,
                "signal_price": reference,
                "effective_price": entry,
                "position_before": "FLAT",
                "position_after": side,
                "fee_paid": entry_fee,
                "slippage_cost": abs(entry - reference) * quantity,
                "notional": notional,
                "fill_notional": notional,
                "fill_time_utc": at,
                "funding_pnl": None,
                "gross_pnl": None,
                "NET_PNL_EX_FUNDING": None,
                "unrealized_pnl": Decimal(0),
                "exposure": notional if side == "LONG" else -notional,
                **leg.ex_ante(),
            },
        )
        return self._append(event)

    def _close_leg(
        self,
        *,
        exit_price: Decimal,
        event_type: str,
        reason_code: str,
        observation_id: str,
        at: str,
        signal_choice: str,
        reference_price: Decimal,
    ) -> dict:
        leg = self.position
        if leg is None:
            raise ProtectiveBoundaryError("C6_NO_POSITION")
        direction = Decimal(1) if leg.side == "LONG" else Decimal(-1)
        gross = (exit_price - leg.entry_price) * leg.quantity * direction
        exit_fee = abs(exit_price) * leg.quantity * FEE_RATE
        net = gross - leg.entry_fee - exit_fee
        self.cash += gross - exit_fee
        self.realized_pnl_cum += gross - exit_fee
        self.position = None
        event = self._shell(
            event_type=event_type,
            reason_code=reason_code,
            observation_id=observation_id,
            at=at,
            fill_status="FILLED",
            extra={
                "signal_choice": signal_choice,
                "side": leg.side,
                "reference_price": reference_price,
                "signal_price": reference_price,
                "effective_price": exit_price,
                "exit_price": exit_price,
                "position_before": leg.side,
                "position_after": "FLAT",
                "fee_paid": exit_fee,
                "slippage_cost": abs(exit_price - reference_price) * leg.quantity,
                "notional": exit_price * leg.quantity,
                "fill_notional": exit_price * leg.quantity,
                "fill_time_utc": at,
                "funding_pnl": None,
                "gross_pnl": gross,
                "NET_PNL_EX_FUNDING": net,
                "unrealized_pnl": Decimal(0),
                "exposure": Decimal(0),
                "protective_stop_price": leg.protective_stop_price,
                **leg.ex_ante(),
            },
        )
        return self._append(event)

    def _reject(
        self,
        *,
        reason_code: str,
        observation_id: str,
        at: str,
        signal_choice: str,
        reference_price: Decimal,
        candidate_quantity: Decimal,
        preset_stop_price,
        entry_price,
        equity_at_open: Optional[Decimal] = None,
        max_risk_amount: Optional[Decimal] = None,
        max_quantity: Optional[Decimal] = None,
        stop_distance: Optional[Decimal] = None,
    ) -> dict:
        event = self._shell(
            event_type="NO_FILL",
            reason_code=reason_code,
            observation_id=observation_id,
            at=at,
            fill_status="NO_FILL",
            extra={
                "signal_choice": signal_choice,
                "side": signal_choice,
                "reference_price": reference_price,
                "signal_price": reference_price,
                "effective_price": entry_price,
                "entry_price": entry_price,
                "preset_stop_price": preset_stop_price,
                "equity_at_open": equity_at_open if equity_at_open is not None else self.cash,
                "risk_amount": None,
                "risk_pct": None,
                "stop_distance": stop_distance,
                "max_risk_amount": max_risk_amount,
                "max_quantity": max_quantity,
                "candidate_quantity": candidate_quantity,
                "quantity": Decimal(0),
                "trade_id": None,
                "size_action": "REJECT",
                "position_before": "FLAT" if self.position is None else self.position.side,
                "position_after": "FLAT" if self.position is None else self.position.side,
                "fill_time_utc": None,
                "funding_pnl": None,
                "fee_paid": Decimal(0),
                "slippage_cost": Decimal(0),
                "exposure": Decimal(0) if self.position is None else None,
            },
        )
        return self._append(event)

    def _shell(
        self,
        *,
        event_type: str,
        reason_code: str,
        observation_id: str,
        at: str,
        fill_status,
        extra: dict,
        ledger_event_id: Optional[str] = None,
    ) -> dict:
        event = {
            "schema_version": SCHEMA_VERSION,
            "strategy_version": STRATEGY_VERSION,
            "model_version": MODEL_VERSION,
            "data_version": DATA_VERSION,
            "stop_rule_id": STOP_RULE_ID,
            "size_policy_id": SIZE_POLICY_ID,
            "event_type": event_type,
            "reason_code": reason_code,
            "ledger_event_id": ledger_event_id or self._next_id(),
            "observation_id": observation_id,
            "market": MARKET,
            "sample_class": SAMPLE_CLASS,
            "causal_rule": "C6_PROTECTIVE_V1",
            "signal_available_at": at,
            "signal_candle_open_utc": at,
            "fill_status": fill_status,
            "FUNDING_DATA_STATUS": FUNDING_DATA_STATUS,
            "NET_PNL_STATUS": NET_PNL_STATUS,
            "funding_pnl": None,
            "fee_bps": FEE_BPS,
            "slippage_bps": SLIPPAGE_BPS,
            "deploy": DEPLOY,
            "live_trading": LIVE_TRADING,
            "execution": self.execution,
            "net_liquidation_equity": self.cash if self.position is None else self.net_liquidation(
                self.position.entry_price
            ),
            "realized_pnl_cum": self.realized_pnl_cum,
        }
        event.update(extra)
        if self.position is None and "position_after" not in event:
            event["position_after"] = "FLAT"
        return event

    def _append(self, event: dict) -> dict:
        event["prev_hash"] = self._prev_hash
        event["row_hash"] = row_hash(event)
        self._prev_hash = event["row_hash"]
        self._events.append(event)
        return deepcopy(event)

    def _next_id(self) -> str:
        self._seq += 1
        return "le-%06d" % self._seq


def _sell_buy(position_side: str) -> str:
    """Order side that closes the position."""
    if position_side == "LONG":
        return "SHORT"
    if position_side == "SHORT":
        return "LONG"
    raise ProtectiveBoundaryError("C6_INVALID_SIDE")


def _is_tighter(side: str, entry: Decimal, current: Decimal, proposed: Decimal) -> bool:
    if side == "LONG":
        return proposed > current and proposed < entry
    if side == "SHORT":
        return proposed < current and proposed > entry
    return False
