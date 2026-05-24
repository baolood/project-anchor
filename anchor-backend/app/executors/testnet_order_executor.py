import hashlib
import hmac
import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

DEFAULT_RECV_WINDOW_MS = 5000
DEFAULT_TESTNET_ORDER_PATH = "/fapi/v1/order"
SUPPORTED_MARKET = "binance_testnet"


def _executor_boundary_failure(
    code: str,
    *,
    host_label: str,
    configured_origin: str,
    canonical_path: str,
    now_ts: Optional[int] = None,
    **extra: Any,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], Optional[str], Optional[Dict[str, Any]]]:
    error = {
        "code": code,
        "failure_family": code,
        "gate": "executor_boundary",
        "external_request_started": False,
        "external_order_id_present": False,
        "execution_mode": "testnet",
        "host_label": host_label,
        "configured_origin": configured_origin,
        "canonical_path": canonical_path,
        "executor_mode_label": "real",
        "timeout_policy_label": "single_attempt_v1",
    }
    if now_ts is not None:
        error["ts"] = now_ts
    if extra:
        error.update(extra)
    return ({"ok": False, "result": None, "error": error}, None, None, None)


def _sign_query(secret: str, query: str) -> str:
    return hmac.new(secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()


def _coerce_quantity(notional: Any, stop_price: Any) -> float:
    notional_f = float(notional or 0)
    stop_f = float(stop_price or 0)
    if notional_f <= 0 or stop_f <= 0:
        raise ValueError("TESTNET_REAL_TRANSPORT_INPUT_INVALID")
    # Use the already-required stop_price as a conservative size hint so the
    # first guarded request can remain one outbound call without a price lookup.
    qty = max(notional_f / stop_f, 0.001)
    return round(qty, 6)


def _format_quantity(quantity: float) -> str:
    return f"{quantity:.6f}".rstrip("0").rstrip(".")


def _normalize_http_error(code: int, body: str) -> Tuple[str, str]:
    if code in (401, 403):
        return ("TESTNET_EXECUTOR_AUTH_FAILED", f"http_{code}")
    if code == 408:
        return ("TESTNET_EXECUTOR_TIMEOUT", f"http_{code}")
    if code in (400, 404, 409, 422):
        return ("TESTNET_EXECUTOR_VALIDATION_FAILED", f"http_{code}")
    if code in (429,):
        return ("TESTNET_EXECUTOR_REJECTED", f"http_{code}")
    if 500 <= code <= 599:
        return ("TESTNET_EXECUTOR_NETWORK_ERROR", f"http_{code}")
    return ("TESTNET_EXECUTOR_UNEXPECTED", f"http_{code}:{body[:120]}")


def run_real_testnet_order_request(
    transport_input: Dict[str, Any],
    now_ts: int,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], Optional[str], Optional[Dict[str, Any]]]:
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
        "executor_mode_label": "real",
        "timeout_policy_label": "single_attempt_v1",
    }
    real_wire_enabled = (str(os.getenv("TESTNET_EXECUTOR_REAL_ENABLE") or "").strip() == "1")
    if not real_wire_enabled:
        return _executor_boundary_failure(
            "TESTNET_REAL_WIRE_DISABLED",
            host_label=host_label,
            configured_origin=configured_origin,
            canonical_path=canonical_path,
        )

    if str(transport_input.get("market") or "") != SUPPORTED_MARKET:
        return _executor_boundary_failure(
            "TESTNET_REAL_TRANSPORT_INPUT_INVALID",
            host_label=host_label,
            configured_origin=configured_origin,
            canonical_path=canonical_path,
            now_ts=now_ts,
            failure_reason="unsupported_market",
            market=transport_input.get("market"),
        )

    if str(transport_input.get("order_type") or "").strip().lower() != "market":
        return _executor_boundary_failure(
            "TESTNET_REAL_TRANSPORT_INPUT_INVALID",
            host_label=host_label,
            configured_origin=configured_origin,
            canonical_path=canonical_path,
            now_ts=now_ts,
            failure_reason="unsupported_order_type",
            order_type=transport_input.get("order_type"),
        )

    api_key = str(os.getenv("TESTNET_EXCHANGE_API_KEY") or "")
    api_secret = str(os.getenv("TESTNET_EXCHANGE_API_SECRET") or "")
    if not api_key or not api_secret:
        return _executor_boundary_failure(
            "TESTNET_CREDENTIALS_MISSING",
            host_label=host_label,
            configured_origin=configured_origin,
            canonical_path=canonical_path,
            now_ts=now_ts,
        )

    try:
        quantity = _coerce_quantity(
            transport_input.get("notional"),
            transport_input.get("stop_price"),
        )
    except (TypeError, ValueError):
        return _executor_boundary_failure(
            "TESTNET_REAL_TRANSPORT_INPUT_INVALID",
            host_label=host_label,
            configured_origin=configured_origin,
            canonical_path=canonical_path,
            now_ts=now_ts,
            failure_reason="invalid_notional_or_stop_price",
        )

    recv_window = int(os.getenv("TESTNET_EXCHANGE_RECV_WINDOW") or DEFAULT_RECV_WINDOW_MS)
    order_path = str(os.getenv("TESTNET_EXCHANGE_ORDER_PATH") or DEFAULT_TESTNET_ORDER_PATH).strip()
    params = {
        "symbol": str(transport_input.get("symbol") or ""),
        "side": str(transport_input.get("side") or "").upper(),
        "type": "MARKET",
        "quantity": _format_quantity(quantity),
        "newOrderRespType": "RESULT",
        "timestamp": now_ts,
        "recvWindow": recv_window,
    }
    query = urllib.parse.urlencode(params, doseq=True)
    signature = _sign_query(api_secret, query)
    url = f"{configured_origin.rstrip('/')}{order_path}?{query}&signature={signature}"
    requested_payload = {
        **common,
        "external_request_started": True,
        "request_path": order_path,
        "market": transport_input.get("market"),
        "symbol": transport_input.get("symbol"),
        "side": transport_input.get("side"),
        "order_type": "MARKET",
        "quantity": _format_quantity(quantity),
    }
    request = urllib.request.Request(url=url, method="POST")
    request.add_header("X-MBX-APIKEY", api_key)

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        failure_family, failure_reason = _normalize_http_error(exc.code, body)
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
                    "executor_mode_label": "real",
                    "timeout_policy_label": "single_attempt_v1",
                    "http_status": exc.code,
                    "ts": now_ts,
                },
            },
            requested_payload,
            "TESTNET_EXECUTOR_REJECTED",
            {
                **common,
                "failure_family": failure_family,
                "failure_reason": failure_reason,
                "external_request_started": True,
                "http_status": exc.code,
            },
        )
    except (TimeoutError, socket.timeout):
        return (
            {
                "ok": False,
                "result": None,
                "error": {
                    "code": "TESTNET_EXECUTOR_TIMEOUT",
                    "failure_family": "TESTNET_EXECUTOR_TIMEOUT",
                    "failure_reason": "request_timeout",
                    "gate": "external_executor",
                    "external_request_started": True,
                    "external_order_id_present": False,
                    "execution_mode": "testnet",
                    "host_label": host_label,
                    "configured_origin": configured_origin,
                    "canonical_path": canonical_path,
                    "executor_mode_label": "real",
                    "timeout_policy_label": "single_attempt_v1",
                    "ts": now_ts,
                },
            },
            requested_payload,
            "TESTNET_EXECUTOR_REJECTED",
            {
                **common,
                "failure_family": "TESTNET_EXECUTOR_TIMEOUT",
                "failure_reason": "request_timeout",
                "external_request_started": True,
            },
        )
    except urllib.error.URLError as exc:
        return (
            {
                "ok": False,
                "result": None,
                "error": {
                    "code": "TESTNET_EXECUTOR_NETWORK_ERROR",
                    "failure_family": "TESTNET_EXECUTOR_NETWORK_ERROR",
                    "failure_reason": str(exc.reason or exc),
                    "gate": "external_executor",
                    "external_request_started": True,
                    "external_order_id_present": False,
                    "execution_mode": "testnet",
                    "host_label": host_label,
                    "configured_origin": configured_origin,
                    "canonical_path": canonical_path,
                    "executor_mode_label": "real",
                    "timeout_policy_label": "single_attempt_v1",
                    "ts": now_ts,
                },
            },
            requested_payload,
            "TESTNET_EXECUTOR_REJECTED",
            {
                **common,
                "failure_family": "TESTNET_EXECUTOR_NETWORK_ERROR",
                "failure_reason": str(exc.reason or exc),
                "external_request_started": True,
            },
        )

    external_order_id = payload.get("orderId")
    external_status = str(payload.get("status") or "")
    if external_order_id is None or not external_status:
        return (
            {
                "ok": False,
                "result": None,
                "error": {
                    "code": "TESTNET_EXECUTOR_UNEXPECTED",
                    "failure_family": "TESTNET_EXECUTOR_UNEXPECTED",
                    "failure_reason": "missing_order_id_or_status",
                    "gate": "external_executor",
                    "external_request_started": True,
                    "external_order_id_present": bool(external_order_id),
                    "execution_mode": "testnet",
                    "host_label": host_label,
                    "configured_origin": configured_origin,
                    "canonical_path": canonical_path,
                    "executor_mode_label": "real",
                    "timeout_policy_label": "single_attempt_v1",
                    "ts": now_ts,
                },
            },
            requested_payload,
            "TESTNET_EXECUTOR_REJECTED",
            {
                **common,
                "failure_family": "TESTNET_EXECUTOR_UNEXPECTED",
                "failure_reason": "missing_order_id_or_status",
                "external_request_started": True,
            },
        )

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
                "executor_mode_label": "real",
                "timeout_policy_label": "single_attempt_v1",
                "external_order_id": str(external_order_id),
                "external_status": external_status,
                "ts": now_ts,
            },
            "error": None,
        },
        requested_payload,
        "TESTNET_EXECUTOR_ACCEPTED",
        {
            **common,
            "external_request_started": True,
            "external_order_id": str(external_order_id),
            "external_status": external_status,
        },
    )
