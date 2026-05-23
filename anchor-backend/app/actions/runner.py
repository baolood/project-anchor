"""
DomainCommandRunner: pick one command → [risk lockout] → policies → pipeline(action) → mark_done / mark_failed.
Emits append-only events at key points (PICKED, POLICY_ALLOW/POLICY_BLOCK, RISK_LOCKOUT_BLOCK, ACTION_OK/ACTION_FAIL, MARK_DONE, MARK_FAILED, EXCEPTION).
No prints inside; returns a result dict for the worker to log.
"""
import json
import os
import time
from urllib.parse import urlsplit
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from app.actions.context import ActionContext
from app.actions.pipeline import run_action_with_pipeline
from app.actions.steps import default_pipeline_steps
from app.executors import testnet_order_executor as real_testnet_executor
from app.ops.kill_switch import get_kill_switch_state
from app.policies.runner import run_policies
from app.policies.protocol import Policy


_TESTNET_VENUE_PROFILES: Dict[str, Dict[str, Any]] = {
    "binance_testnet": {
        "origins": {"https://testnet.binancefuture.com"},
        "host_label": "binance_futures_testnet",
    },
}


def _result_summary(obj: Any, max_keys: int = 5) -> Dict[str, Any]:
    """Small summary for event payload (<=8KB target)."""
    if obj is None:
        return {}
    if not isinstance(obj, dict):
        return {"result_summary": str(obj)[:200]}
    return {k: obj[k] for k in list(obj.keys())[:max_keys] if k in ("ok", "type", "attempt", "ts", "code", "message")}


def _testnet_preflight_failure(code: str, **detail: Any) -> Dict[str, Any]:
    error = {"code": code, "failure_family": code}
    if detail:
        error.update(detail)
    return {"ok": False, "result": None, "error": error}


def _normalize_origin(raw_url: str) -> Optional[str]:
    try:
        parsed = urlsplit(raw_url.strip())
    except Exception:
        return None
    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").lower()
    if scheme != "https" or not host:
        return None
    if host in {"localhost", "127.0.0.1"}:
        return None
    port = parsed.port
    if port in (None, 443):
        return f"{scheme}://{host}"
    return f"{scheme}://{host}:{port}"


def _run_testnet_boundary_preflight(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    enabled, source = get_kill_switch_state()
    kill_switch_meta = {"enabled": bool(enabled), "source": source or "unknown"}
    if enabled:
        return (
            _testnet_preflight_failure(
                "KILL_SWITCH_ON",
                gate="kill_switch",
                external_request_started=False,
                external_order_id_present=False,
                execution_mode="testnet",
                kill_switch_source=kill_switch_meta["source"],
                canonical_path="ORDER:testnet",
            ),
            kill_switch_meta,
        )

    market = str(payload.get("market") or "").strip().lower()
    profile = _TESTNET_VENUE_PROFILES.get(market)
    raw_base_url = str(os.getenv("TESTNET_EXCHANGE_BASE_URL") or "").strip()
    normalized_origin = _normalize_origin(raw_base_url) if raw_base_url else None
    if profile is None or normalized_origin is None or normalized_origin not in profile["origins"]:
        return (
            _testnet_preflight_failure(
                "TESTNET_BASE_URL_INVALID",
                gate="host_safety",
                external_request_started=False,
                external_order_id_present=False,
                execution_mode="testnet",
                market=market or None,
                configured_origin=normalized_origin,
                host_label=profile["host_label"] if profile else None,
                canonical_path="ORDER:testnet",
            ),
            kill_switch_meta,
        )

    credential_values = {
        "api_key": str(os.getenv("TESTNET_EXCHANGE_API_KEY") or "").strip(),
        "api_secret": str(os.getenv("TESTNET_EXCHANGE_API_SECRET") or "").strip(),
        "key_id": str(os.getenv("TESTNET_EXCHANGE_KEY_ID") or "").strip(),
    }
    if not all(credential_values.values()):
        return (
            _testnet_preflight_failure(
                "TESTNET_CREDENTIALS_MISSING",
                gate="credential_presence",
                external_request_started=False,
                external_order_id_present=False,
                execution_mode="testnet",
                host_label=profile["host_label"],
                configured_origin=normalized_origin,
                key_id_present=bool(credential_values["key_id"]),
                canonical_path="ORDER:testnet",
            ),
            kill_switch_meta,
        )

    return (
        {
            "ok": True,
            "result": {
                "execution_mode": "testnet",
                "preflight_passed": True,
                "host_label": profile["host_label"],
                "configured_origin": normalized_origin,
                "key_id_present": True,
                "canonical_path": "ORDER:testnet",
            },
            "error": None,
        },
        kill_switch_meta,
    )


def _build_testnet_transport_input(
    command_id: str,
    attempt: int,
    payload: Dict[str, Any],
    preflight_result: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "command_id": command_id,
        "attempt": attempt,
        "execution_mode": "testnet",
        "market": payload.get("market"),
        "symbol": payload.get("symbol"),
        "side": payload.get("side"),
        "notional": float(payload.get("notional") or 0),
        "order_type": payload.get("order_type"),
        "source": payload.get("source"),
        "created_by": payload.get("created_by"),
        "stop_price": float(payload.get("stop_price") or 0),
        "idempotency_key": payload.get("idempotency_key"),
        "host_label": preflight_result.get("host_label"),
        "configured_origin": preflight_result.get("configured_origin"),
        "canonical_path": preflight_result.get("canonical_path", "ORDER:testnet"),
        "key_id_present": bool(preflight_result.get("key_id_present")),
    }


def _run_mocked_testnet_external_executor(
    transport_input: Dict[str, Any],
    now_ts: int,
) -> Tuple[Dict[str, Any], Dict[str, Any], str, Dict[str, Any]]:
    outcome = str(os.getenv("TESTNET_EXECUTOR_MOCK_OUTCOME") or "success").strip().lower()
    host_label = str(transport_input.get("host_label") or "")
    configured_origin = str(transport_input.get("configured_origin") or "")
    canonical_path = str(transport_input.get("canonical_path") or "ORDER:testnet")
    common = {
        "type": "ORDER",
        "attempt": int(transport_input.get("attempt") or 0),
        "execution_mode": "testnet",
        "host_label": host_label,
        "configured_origin": configured_origin,
        "canonical_path": canonical_path,
        "executor_mode_label": "mock",
        "timeout_policy_label": "single_attempt_v1",
    }
    requested_payload = {
        **common,
        "external_request_started": True,
    }

    failure_map = {
        "auth_failed": ("TESTNET_EXECUTOR_AUTH_FAILED", "mock_auth_failed"),
        "validation_failed": ("TESTNET_EXECUTOR_VALIDATION_FAILED", "mock_validation_failed"),
        "rejected": ("TESTNET_EXECUTOR_REJECTED", "mock_rejected"),
        "timeout": ("TESTNET_EXECUTOR_TIMEOUT", "mock_timeout"),
        "network_error": ("TESTNET_EXECUTOR_NETWORK_ERROR", "mock_network_error"),
    }
    if outcome == "success":
        external_order_id = f"mock-testnet-order-{transport_input.get('command_id')}"
        return (
            {
                "ok": True,
                "result": {
                    "ok": True,
                    "type": "order",
                    "execution_mode": "testnet",
                    "market": transport_input.get("market"),
                    "symbol": transport_input.get("symbol"),
                    "side": transport_input.get("side"),
                    "notional": float(transport_input.get("notional") or 0),
                    "order_type": transport_input.get("order_type"),
                    "source": transport_input.get("source"),
                    "created_by": transport_input.get("created_by"),
                    "stop_price": float(transport_input.get("stop_price") or 0),
                    "idempotency_key": transport_input.get("idempotency_key"),
                    "host_label": host_label,
                    "executor_mode_label": "mock",
                    "timeout_policy_label": "single_attempt_v1",
                    "external_order_id": external_order_id,
                    "external_status": "MOCK_ACCEPTED",
                    "mocked_external_request": True,
                    "ts": now_ts,
                },
                "error": None,
            },
            requested_payload,
            "TESTNET_EXECUTOR_ACCEPTED",
            {
                **common,
                "external_request_started": True,
                "external_order_id": external_order_id,
                "external_status": "MOCK_ACCEPTED",
            },
        )

    failure_family, failure_reason = failure_map.get(
        outcome,
        ("TESTNET_EXECUTOR_UNEXPECTED", f"mock_{outcome or 'unexpected'}"),
    )
    return (
        {
            "ok": False,
            "result": None,
            "error": {
                "code": failure_family,
                "failure_family": failure_family,
                "failure_reason": failure_reason,
                "gate": "external_executor",
                "external_request_started": True,
                "external_order_id_present": False,
                "execution_mode": "testnet",
                "host_label": host_label,
                "configured_origin": configured_origin,
                "canonical_path": canonical_path,
                "executor_mode_label": "mock",
                "timeout_policy_label": "single_attempt_v1",
            },
        },
        requested_payload,
        "TESTNET_EXECUTOR_REJECTED",
        {
            **common,
            "failure_family": failure_family,
            "failure_reason": failure_reason,
            "external_request_started": True,
        },
    )


class DomainCommandRunner:
    """
    Encapsulates: pick one domain command, resolve action, run it, persist outcome.
    Reuses existing pick_one_domain, mark_done, mark_failed (injected).
    Optional append_event_fn(command_id, event_type, attempt, payload) for audit trail.
    """

    def __init__(
        self,
        pick_one_fn: Callable,
        get_action_fn: Callable[[str], Any],
        mark_done_fn: Callable,
        mark_failed_fn: Callable,
        now_ts_fn: Optional[Callable[[], int]] = None,
        append_event_fn: Optional[Callable] = None,
        policies: Optional[List[Policy]] = None,
        policy_engine: Any = None,
        is_lockout_blocked_fn: Optional[Callable[[str], Awaitable[Tuple[bool, str, str]]]] = None,
        risk_guard_fn: Optional[Callable[[str, dict], Awaitable[Tuple[bool, Optional[str]]]]] = None,
    ):
        self._pick_one = pick_one_fn
        self._get_action = get_action_fn
        self._mark_done = mark_done_fn
        self._mark_failed = mark_failed_fn
        self._now_ts = now_ts_fn or (lambda: int(time.time() * 1000))
        self._append_event = append_event_fn
        self._policies = list(policies) if policies else []
        self._policy_engine = policy_engine
        self._is_lockout_blocked = is_lockout_blocked_fn
        self._risk_guard_fn = risk_guard_fn

    async def run_one(self) -> Optional[Dict[str, Any]]:
        """
        Pick one PENDING command, run its action, persist DONE or FAILED.
        Returns None if no command was picked; otherwise {"id", "type", "final_status": "DONE"|"FAILED"}.
        Never raises; any exception is turned into FAILED or None.
        """
        try:
            item = await self._pick_one()
        except Exception:
            return None
        if not item:
            return None

        cid = item.get("id") or ""
        cmd_type = (str(item.get("type") or "")).strip().upper()
        attempt = int(item.get("attempt") or 0)
        payload = item.get("payload") or {}
        raw = dict(item)

        if self._append_event:
            try:
                await self._append_event(cid, "PICKED", attempt, {"type": cmd_type, "attempt": attempt})
            except Exception:
                pass

        if self._is_lockout_blocked:
            try:
                blocked, lockout_until, lockout_reason = await self._is_lockout_blocked(cmd_type)
                if blocked:
                    try:
                        await self._mark_failed(cid, "RISK_LOCKOUT_ACTIVE", {"lockout_until": lockout_until, "lockout_reason": lockout_reason})
                    except Exception:
                        pass
                    if self._append_event:
                        try:
                            await self._append_event(
                                cid, "RISK_LOCKOUT_BLOCK", attempt,
                                {"type": cmd_type, "reason": "RISK_LOCKOUT_ACTIVE", "lockout_until": lockout_until, "lockout_reason": lockout_reason},
                            )
                        except Exception:
                            pass
                    return {"id": cid, "type": cmd_type, "final_status": "FAILED"}
            except Exception:
                pass

        if self._risk_guard_fn:
            try:
                ok, reason = await self._risk_guard_fn(cmd_type, payload)
                if not ok and reason:
                    try:
                        await self._mark_failed(cid, reason, {"reason": reason})
                    except Exception:
                        pass
                    if self._append_event:
                        try:
                            await self._append_event(
                                cid, "RISK_HARD_LIMITS_BLOCK", attempt,
                                {"type": cmd_type, "reason": reason},
                            )
                        except Exception:
                            pass
                    return {"id": cid, "type": cmd_type, "final_status": "FAILED"}
            except Exception:
                pass

        context = ActionContext(
            now_ts=self._now_ts(),
            command_id=cid,
            cmd_type=cmd_type,
            attempt=attempt,
            payload=payload,
            raw=raw,
        )
        command = context.to_command_dict()

        # Policy guardrails: block => mark_failed + POLICY_BLOCK + MARK_FAILED
        if self._policies and self._policy_engine is not None:
            try:
                allowed, decision = await run_policies(
                    self._policies, context, command, self._policy_engine
                )
            except Exception:
                allowed, decision = True, None
            if not allowed and decision:
                if self._append_event:
                    try:
                        await self._append_event(
                            cid, "POLICY_BLOCK", attempt,
                            {"type": cmd_type, "attempt": attempt, "code": decision.get("code"), "message": decision.get("message"), "detail": decision.get("detail")},
                        )
                    except Exception:
                        pass
                try:
                    reason = decision.get("code") or "POLICY_BLOCK"
                    detail = decision.get("detail") or {"message": decision.get("message")}
                    await self._mark_failed(cid, reason, detail)
                except Exception:
                    pass
                if self._append_event:
                    try:
                        await self._append_event(cid, "MARK_FAILED", attempt, {"type": cmd_type, "attempt": attempt, "error": decision})
                    except Exception:
                        pass
                return {"id": cid, "type": cmd_type, "final_status": "FAILED"}
            if self._append_event and allowed:
                try:
                    await self._append_event(
                        cid, "POLICY_ALLOW", attempt,
                        {"type": cmd_type, "attempt": attempt, "policies": [p.name for p in self._policies]},
                    )
                except Exception:
                    pass

        # BINANCE TESTNET execution (opt-in): QUOTE → place_limit_ioc instead of local QuoteAction
        if os.getenv("EXECUTION_MODE", "").upper() == "BINANCE_TESTNET" and cmd_type == "QUOTE":
            from app.executors.binance_futures_testnet import (
                BinanceFuturesTestnetExecutor,
                notional_to_qty,
            )

            symbol = str(payload.get("symbol") or "BTCUSDT").strip()
            notional = payload.get("notional")
            if notional is None:
                notional = payload.get("notional_usd")
            side = str(payload.get("side") or "BUY").strip().upper()
            if side not in ("BUY", "SELL"):
                side = "BUY"

            try:
                ex = BinanceFuturesTestnetExecutor()
                mp = ex.get_mark_price(symbol)
                qty = notional_to_qty(symbol=symbol, notional_usd=float(notional or 0), mark_price=mp)
                px = mp * 1.005 if side == "BUY" else mp * 0.995

                resp = ex.place_limit_ioc(symbol=symbol, side=side, quantity=qty, price=px)
                st = (resp.get("status") or "").upper()
                if st != "FILLED":
                    raise RuntimeError(f"BINANCE_ORDER_NOT_FILLED:{resp}")

                result = {
                    "ok": True,
                    "type": "quote",
                    "symbol": symbol,
                    "side": side,
                    "notional": float(notional or 0),
                    "price": float(resp.get("avgPrice") or px),
                    "qty": float(resp.get("executedQty") or qty),
                    "_binance_testnet": {
                        "orderId": resp.get("orderId"),
                        "status": resp.get("status"),
                        "executedQty": resp.get("executedQty"),
                        "avgPrice": resp.get("avgPrice"),
                    },
                }
                if self._append_event:
                    try:
                        await self._append_event(cid, "ACTION_OK", attempt, {"type": cmd_type, "binance": True})
                    except Exception:
                        pass
                await self._mark_done(cid, result)
                if self._append_event:
                    try:
                        await self._append_event(cid, "MARK_DONE", attempt, {"type": cmd_type})
                    except Exception:
                        pass
                return {"id": cid, "type": cmd_type, "final_status": "DONE"}
            except Exception as e:
                err_str = str(e)
                if self._append_event:
                    try:
                        await self._append_event(cid, "ACTION_FAIL", attempt, {"type": cmd_type, "error": err_str})
                    except Exception:
                        pass
                await self._mark_failed(cid, err_str, {"error": err_str})
                if self._append_event:
                    try:
                        await self._append_event(cid, "MARK_FAILED", attempt, {"type": cmd_type, "error": err_str})
                    except Exception:
                        pass
                return {"id": cid, "type": cmd_type, "final_status": "FAILED"}

        action = self._get_action(cmd_type)
        if action is None:
            if self._append_event:
                try:
                    await self._append_event(cid, "ACTION_FAIL", attempt, {"type": cmd_type, "attempt": attempt, "error": {"code": "UNKNOWN_TYPE", "type": cmd_type}})
                except Exception:
                    pass
            try:
                await self._mark_failed(cid, "UNKNOWN_TYPE", {"type": cmd_type})
            except Exception:
                pass
            if self._append_event:
                try:
                    await self._append_event(cid, "MARK_FAILED", attempt, {"type": cmd_type, "attempt": attempt, "reason": "UNKNOWN_TYPE"})
                except Exception:
                    pass
            return {"id": cid, "type": cmd_type, "final_status": "FAILED"}

        try:
            out = run_action_with_pipeline(action, context, command, default_pipeline_steps)
        except Exception as e:
            out = {
                "ok": False,
                "result": None,
                "error": {"code": "ACTION_EXCEPTION", "message": str(e)},
            }
            if self._append_event:
                try:
                    await self._append_event(cid, "EXCEPTION", attempt, {"type": cmd_type, "attempt": attempt, "code": "ACTION_EXCEPTION", "message": str(e)})
                except Exception:
                    pass

        emit_kill_switch_checked: Optional[Dict[str, Any]] = None
        emit_testnet_requested: Optional[Dict[str, Any]] = None
        emit_testnet_terminal_type: Optional[str] = None
        emit_testnet_terminal_payload: Optional[Dict[str, Any]] = None
        result_obj = out.get("result")
        if (
            cmd_type == "ORDER"
            and out.get("ok") is True
            and isinstance(result_obj, dict)
            and result_obj.get("execution_mode") == "testnet"
            and result_obj.get("testnet_stub") is True
        ):
            preflight_out, emit_kill_switch_checked = _run_testnet_boundary_preflight(payload)
            if preflight_out.get("ok") is True:
                preflight_result = preflight_out.get("result") or {}
                transport_input = _build_testnet_transport_input(
                    cid,
                    attempt,
                    payload,
                    preflight_result if isinstance(preflight_result, dict) else {},
                )
                executor_mode = str(os.getenv("TESTNET_EXECUTOR_MODE") or "").strip().lower()
                if executor_mode == "mock":
                    out, emit_testnet_requested, emit_testnet_terminal_type, emit_testnet_terminal_payload = (
                        _run_mocked_testnet_external_executor(
                            transport_input,
                            self._now_ts(),
                        )
                    )
                elif executor_mode == "real":
                    out, emit_testnet_requested, emit_testnet_terminal_type, emit_testnet_terminal_payload = (
                        real_testnet_executor.run_real_testnet_order_request(
                            transport_input,
                            self._now_ts(),
                        )
                    )
                elif executor_mode:
                    out = _testnet_preflight_failure(
                        "TESTNET_EXECUTOR_MODE_INVALID",
                        gate="executor_boundary",
                        external_request_started=False,
                        external_order_id_present=False,
                        execution_mode="testnet",
                        configured_executor_mode=executor_mode,
                        host_label=preflight_result.get("host_label"),
                        configured_origin=preflight_result.get("configured_origin"),
                        key_id_present=bool(preflight_result.get("key_id_present")),
                        preflight_passed=True,
                        canonical_path=preflight_result.get("canonical_path", "ORDER:testnet"),
                    )
                else:
                    out = _testnet_preflight_failure(
                        "TESTNET_EXECUTOR_NOT_IMPLEMENTED",
                        gate="executor_boundary",
                        external_request_started=False,
                        external_order_id_present=False,
                        execution_mode="testnet",
                        host_label=preflight_result.get("host_label"),
                        configured_origin=preflight_result.get("configured_origin"),
                        key_id_present=bool(preflight_result.get("key_id_present")),
                        preflight_passed=True,
                        canonical_path=preflight_result.get("canonical_path", "ORDER:testnet"),
                    )
            else:
                out = preflight_out

        if self._append_event:
            try:
                if emit_kill_switch_checked is not None:
                    await self._append_event(
                        cid,
                        "KILL_SWITCH_CHECKED",
                        attempt,
                        {
                            "type": cmd_type,
                            "attempt": attempt,
                            "enabled": emit_kill_switch_checked["enabled"],
                            "source": emit_kill_switch_checked["source"],
                            "execution_mode": "testnet",
                            "gate": "kill_switch",
                            "canonical_path": "ORDER:testnet",
                        },
                    )
                if emit_testnet_requested is not None:
                    await self._append_event(
                        cid,
                        "TESTNET_EXECUTOR_REQUESTED",
                        attempt,
                        emit_testnet_requested,
                    )
                if emit_testnet_terminal_type is not None and emit_testnet_terminal_payload is not None:
                    await self._append_event(
                        cid,
                        emit_testnet_terminal_type,
                        attempt,
                        emit_testnet_terminal_payload,
                    )
                result_obj = out.get("result")
                if (
                    out.get("ok") is True
                    and cmd_type == "ORDER"
                    and isinstance(result_obj, dict)
                    and result_obj.get("execution_mode") == "testnet"
                    and result_obj.get("testnet_stub") is True
                ):
                    await self._append_event(
                        cid,
                        "TESTNET_EXECUTOR_STUB",
                        attempt,
                        {
                            "type": cmd_type,
                            "attempt": attempt,
                            "execution_mode": "testnet",
                            "external_call": bool(result_obj.get("external_call", False)),
                        },
                    )
                if out.get("ok") is True:
                    await self._append_event(cid, "ACTION_OK", attempt, {"type": cmd_type, "attempt": attempt, "result": _result_summary(result_obj)})
                else:
                    await self._append_event(cid, "ACTION_FAIL", attempt, {"type": cmd_type, "attempt": attempt, "error": out.get("error")})
            except Exception:
                pass

        try:
            if out.get("ok") is True:
                result = out.get("result")
                if result is not None and "ts" not in result:
                    result = {**result, "ts": self._now_ts()}
                await self._mark_done(cid, result)
                if self._append_event:
                    try:
                        await self._append_event(cid, "MARK_DONE", attempt, {"type": cmd_type, "attempt": attempt, "result_summary": _result_summary(result)})
                    except Exception:
                        pass
                return {"id": cid, "type": cmd_type, "final_status": "DONE"}
            else:
                err = out.get("error")
                reason = (
                    json.dumps(err, ensure_ascii=False)
                    if isinstance(err, dict)
                    else str(err or "ACTION_FAILED")
                )
                detail = err if isinstance(err, dict) else {"error": str(err)}
                await self._mark_failed(cid, reason, detail)
                if self._append_event:
                    try:
                        await self._append_event(cid, "MARK_FAILED", attempt, {"type": cmd_type, "attempt": attempt, "error": detail})
                    except Exception:
                        pass
                return {"id": cid, "type": cmd_type, "final_status": "FAILED"}
        except Exception as e:
            if self._append_event:
                try:
                    await self._append_event(cid, "EXCEPTION", attempt, {"type": cmd_type, "attempt": attempt, "code": "RUNNER_PERSIST", "message": str(e)})
                except Exception:
                    pass
            try:
                await self._mark_failed(
                    cid,
                    "RUNNER_PERSIST_ERROR",
                    {"message": "runner could not persist outcome"},
                )
            except Exception:
                pass
            return {"id": cid, "type": cmd_type, "final_status": "FAILED"}
