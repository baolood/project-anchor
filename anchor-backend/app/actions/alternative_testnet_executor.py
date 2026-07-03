"""Minimal deterministic skeleton for an approved alternative testnet adapter.

This module is intentionally not registered with any runtime runner. It performs
no network I/O, reads no credentials, and loads no environment variables.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Literal, Optional


AlternativeTestnetScenario = Literal["ACCEPTED", "REJECTED", "FAILED"]
AlternativeTestnetStatus = Literal["ACCEPTED", "REJECTED", "FAILED"]


@dataclass(frozen=True)
class AlternativeTestnetOrderRequest:
    command_id: str
    idempotency_key: str
    venue: str
    symbol: str
    side: str
    notional: float
    scenario: AlternativeTestnetScenario
    execution_mode: str = "testnet"


@dataclass(frozen=True)
class AlternativeTestnetOrderResult:
    command_id: str
    idempotency_key: str
    execution_mode: str
    venue: str
    status: AlternativeTestnetStatus
    failure_family: Optional[str]
    failure_reason: Optional[str]
    external_order_id: Optional[str]
    external_order_id_present: bool


def _deterministic_external_order_id(request: AlternativeTestnetOrderRequest) -> str:
    seed = f"{request.venue}:{request.idempotency_key}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"alt-testnet-order-{digest}"


def _validation_failure(
    request: AlternativeTestnetOrderRequest,
    failure_reason: str,
) -> AlternativeTestnetOrderResult:
    return AlternativeTestnetOrderResult(
        command_id=request.command_id,
        idempotency_key=request.idempotency_key,
        execution_mode=request.execution_mode,
        venue=request.venue,
        status="FAILED",
        failure_family="ALTERNATIVE_TESTNET_REQUEST_INVALID",
        failure_reason=failure_reason,
        external_order_id=None,
        external_order_id_present=False,
    )


def _positive_notional(value: float) -> bool:
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def _validation_reason(request: AlternativeTestnetOrderRequest) -> str:
    if not str(request.venue or "").strip():
        return "venue_missing"
    if not str(request.execution_mode or "").strip():
        return "execution_mode_missing"
    if str(request.execution_mode).strip() != "testnet":
        return "execution_mode_not_testnet"
    if not str(request.scenario or "").strip():
        return "scenario_missing"
    if str(request.scenario).strip().upper() not in {"ACCEPTED", "REJECTED", "FAILED"}:
        return "scenario_invalid"
    if not str(request.idempotency_key or "").strip():
        return "idempotency_key_missing"
    if not str(request.symbol or "").strip():
        return "symbol_missing"
    if str(request.side or "").strip().upper() not in {"BUY", "SELL"}:
        return "side_invalid"
    if not _positive_notional(request.notional):
        return "notional_invalid"
    return ""


def run_alternative_testnet_order_stub(
    request: AlternativeTestnetOrderRequest,
) -> AlternativeTestnetOrderResult:
    """Return deterministic adapter evidence without touching runtime or network."""

    invalid_reason = _validation_reason(request)
    if invalid_reason:
        return _validation_failure(request, invalid_reason)

    scenario = request.scenario.strip().upper()
    if scenario == "ACCEPTED":
        external_order_id = _deterministic_external_order_id(request)
        return AlternativeTestnetOrderResult(
            command_id=request.command_id,
            idempotency_key=request.idempotency_key,
            execution_mode=request.execution_mode,
            venue=request.venue,
            status="ACCEPTED",
            failure_family=None,
            failure_reason=None,
            external_order_id=external_order_id,
            external_order_id_present=True,
        )
    if scenario == "REJECTED":
        return AlternativeTestnetOrderResult(
            command_id=request.command_id,
            idempotency_key=request.idempotency_key,
            execution_mode=request.execution_mode,
            venue=request.venue,
            status="REJECTED",
            failure_family="ALTERNATIVE_TESTNET_EXECUTOR_REJECTED",
            failure_reason="alternative_testnet_rejected",
            external_order_id=None,
            external_order_id_present=False,
        )
    return AlternativeTestnetOrderResult(
        command_id=request.command_id,
        idempotency_key=request.idempotency_key,
        execution_mode=request.execution_mode,
        venue=request.venue,
        status="FAILED",
        failure_family="ALTERNATIVE_TESTNET_EXECUTOR_FAILED",
        failure_reason="alternative_testnet_failed",
        external_order_id=None,
        external_order_id_present=False,
    )
