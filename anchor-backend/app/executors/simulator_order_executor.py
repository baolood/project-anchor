import hashlib
import os
from typing import Any, Dict, Tuple


def _float_value(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _scenario_from_input(transport_input: Dict[str, Any]) -> str:
    explicit = transport_input.get("simulator_scenario") or transport_input.get("scenario")
    if explicit:
        return str(explicit).strip().lower()
    return str(os.getenv("TESTNET_EXECUTOR_MOCK_OUTCOME") or "success").strip().lower()


def _common_payload(transport_input: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "ORDER",
        "attempt": int(transport_input.get("attempt") or 0),
        "execution_mode": "testnet",
        "host_label": str(transport_input.get("host_label") or ""),
        "configured_origin": str(transport_input.get("configured_origin") or ""),
        "canonical_path": str(transport_input.get("canonical_path") or "ORDER:testnet"),
        "executor_mode_label": "mock",
        "timeout_policy_label": "single_attempt_v1",
    }


def _simulator_order_id(transport_input: Dict[str, Any]) -> str:
    seed = str(transport_input.get("idempotency_key") or transport_input.get("command_id") or "")
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"mock-testnet-order-{digest}"


def _validate_transport_input(transport_input: Dict[str, Any]) -> str:
    if str(transport_input.get("execution_mode") or "testnet") != "testnet":
        return "execution_mode_not_testnet"
    if str(transport_input.get("market") or "") != "binance_testnet":
        return "market_not_binance_testnet"
    if not str(transport_input.get("symbol") or "").strip():
        return "symbol_missing"
    if str(transport_input.get("side") or "").upper() not in {"BUY", "SELL"}:
        return "side_invalid"
    if _float_value(transport_input.get("notional")) <= 0:
        return "notional_invalid"
    if not str(transport_input.get("idempotency_key") or "").strip():
        return "idempotency_key_missing"
    return ""


def _failure_tuple(
    transport_input: Dict[str, Any],
    requested_payload: Dict[str, Any],
    now_ts: int,
    failure_family: str,
    failure_reason: str,
    terminal_type: str,
    external_request_started: bool,
) -> Tuple[Dict[str, Any], Dict[str, Any], str, Dict[str, Any]]:
    common = _common_payload(transport_input)
    error = {
        "code": failure_family,
        "failure_family": failure_family,
        "failure_reason": failure_reason,
        "gate": "external_executor",
        "external_request_started": external_request_started,
        "external_order_id_present": False,
        "execution_mode": "testnet",
        "host_label": common["host_label"],
        "configured_origin": common["configured_origin"],
        "canonical_path": common["canonical_path"],
        "executor_mode_label": common["executor_mode_label"],
        "timeout_policy_label": common["timeout_policy_label"],
        "ts": now_ts,
    }
    return (
        {"ok": False, "result": None, "error": error},
        requested_payload,
        terminal_type,
        {
            **common,
            "failure_family": failure_family,
            "failure_reason": failure_reason,
            "external_request_started": external_request_started,
        },
    )


def run_simulator_order_request(
    transport_input: Dict[str, Any],
    now_ts: int,
) -> Tuple[Dict[str, Any], Dict[str, Any], str, Dict[str, Any]]:
    common = _common_payload(transport_input)
    scenario = _scenario_from_input(transport_input)
    requested_payload = {
        **common,
        "external_request_started": True,
        "simulator_scenario": scenario,
    }
    invalid_reason = _validate_transport_input(transport_input)
    if invalid_reason:
        return _failure_tuple(
            transport_input,
            requested_payload,
            now_ts,
            "TESTNET_SIMULATOR_INPUT_INVALID",
            invalid_reason,
            "TESTNET_EXECUTOR_FAILED",
            False,
        )

    if scenario in {"success", "accepted", "accept"}:
        simulator_order_id = _simulator_order_id(transport_input)
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
                    "notional": _float_value(transport_input.get("notional")),
                    "order_type": transport_input.get("order_type"),
                    "source": transport_input.get("source"),
                    "created_by": transport_input.get("created_by"),
                    "stop_price": _float_value(transport_input.get("stop_price")),
                    "idempotency_key": transport_input.get("idempotency_key"),
                    "host_label": common["host_label"],
                    "executor_mode_label": common["executor_mode_label"],
                    "timeout_policy_label": common["timeout_policy_label"],
                    "simulator_order_id": simulator_order_id,
                    "external_order_id": simulator_order_id,
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
                "simulator_order_id": simulator_order_id,
                "external_order_id": simulator_order_id,
                "external_status": "MOCK_ACCEPTED",
            },
        )

    failure_map = {
        "auth_failed": ("TESTNET_EXECUTOR_AUTH_FAILED", "mock_auth_failed", "TESTNET_EXECUTOR_REJECTED"),
        "validation_failed": (
            "TESTNET_EXECUTOR_VALIDATION_FAILED",
            "mock_validation_failed",
            "TESTNET_EXECUTOR_REJECTED",
        ),
        "rejected": ("TESTNET_EXECUTOR_REJECTED", "mock_rejected", "TESTNET_EXECUTOR_REJECTED"),
        "timeout": ("TESTNET_EXECUTOR_TIMEOUT", "mock_timeout", "TESTNET_EXECUTOR_REJECTED"),
        "network_error": ("TESTNET_EXECUTOR_NETWORK_ERROR", "mock_network_error", "TESTNET_EXECUTOR_REJECTED"),
        "failed": ("TESTNET_EXECUTOR_SIMULATOR_FAILED", "simulator_failed", "TESTNET_EXECUTOR_FAILED"),
    }
    failure_family, failure_reason, terminal_type = failure_map.get(
        scenario,
        ("TESTNET_EXECUTOR_UNEXPECTED", f"mock_{scenario or 'unexpected'}", "TESTNET_EXECUTOR_REJECTED"),
    )
    return _failure_tuple(
        transport_input,
        requested_payload,
        now_ts,
        failure_family,
        failure_reason,
        terminal_type,
        True,
    )
