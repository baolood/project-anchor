import hashlib
import hmac
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Optional, Tuple


DEFAULT_PRODUCTION_ORDER_PATH = "/api/v3/order"
DEFAULT_RECV_WINDOW_MS = 5000
SUPPORTED_MARKET = "binance_spot"
ALLOWED_PRODUCTION_ORIGINS = {"https://api.binance.com"}
DEFAULT_HTTP_TIMEOUT_SECONDS = 10.0


def _boundary_failure(code: str, **extra: Any) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], Optional[str], Optional[Dict[str, Any]]]:
    error = {
        "code": code,
        "failure_family": code,
        "gate": "production_executor_boundary",
        "external_request_started": False,
        "external_order_id_present": False,
        "execution_mode": "production",
        "executor_mode_label": "production",
        "timeout_policy_label": "single_attempt_v1",
    }
    if extra:
        error.update(extra)
    return ({"ok": False, "result": None, "error": error}, None, None, None)


def _format_decimal(value: Any) -> str:
    number = float(value)
    if number <= 0:
        raise ValueError("PRODUCTION_ORDER_NUMERIC_INPUT_INVALID")
    return f"{number:.8f}".rstrip("0").rstrip(".")


def sign_query(api_secret: str, query: str) -> str:
    return hmac.new(
        api_secret.encode("utf-8"),
        query.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def build_spot_market_order_params(transport_input: Dict[str, Any], timestamp_ms: int) -> Dict[str, Any]:
    if str(transport_input.get("market") or "") != SUPPORTED_MARKET:
        raise ValueError("PRODUCTION_MARKET_UNSUPPORTED")
    if str(transport_input.get("execution_mode") or "") != "production":
        raise ValueError("PRODUCTION_EXECUTION_MODE_REQUIRED")
    if str(transport_input.get("order_type") or "").lower() != "market":
        raise ValueError("PRODUCTION_ORDER_TYPE_UNSUPPORTED")

    return {
        "symbol": str(transport_input.get("symbol") or ""),
        "side": str(transport_input.get("side") or "").upper(),
        "type": "MARKET",
        "quoteOrderQty": _format_decimal(transport_input.get("notional")),
        "newOrderRespType": "FULL",
        "timestamp": int(timestamp_ms),
        "recvWindow": int(transport_input.get("recv_window_ms") or DEFAULT_RECV_WINDOW_MS),
    }


def build_signed_order_request(
    transport_input: Dict[str, Any],
    credentials: Dict[str, str],
    timestamp_ms: int,
) -> Dict[str, Any]:
    base_url = str(credentials.get("base_url") or "").rstrip("/")
    api_key = str(credentials.get("api_key") or "")
    api_secret = str(credentials.get("api_secret") or "")
    if base_url not in ALLOWED_PRODUCTION_ORIGINS:
        raise ValueError("PRODUCTION_BASE_URL_NOT_ALLOWLISTED")
    if not api_key or not api_secret:
        raise ValueError("PRODUCTION_CREDENTIALS_MISSING")

    params = build_spot_market_order_params(transport_input, timestamp_ms)
    query = urllib.parse.urlencode(params, doseq=True)
    signature = sign_query(api_secret, query)
    signed_query = f"{query}&signature={signature}"
    path = str(transport_input.get("request_path") or DEFAULT_PRODUCTION_ORDER_PATH)
    return {
        "method": "POST",
        "url": f"{base_url}{path}?{signed_query}",
        "headers": {"X-MBX-APIKEY": api_key},
        "request_path": path,
        "params": params,
        "signature_present": True,
        "authorization_header_generated": True,
        "sendable": True,
    }


def redacted_request_shape(request: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "method": request.get("method"),
        "request_path": request.get("request_path"),
        "symbol": request.get("params", {}).get("symbol"),
        "side": request.get("params", {}).get("side"),
        "type": request.get("params", {}).get("type"),
        "quoteOrderQty": request.get("params", {}).get("quoteOrderQty"),
        "signature_present": bool(request.get("signature_present")),
        "api_key_present": bool(request.get("headers", {}).get("X-MBX-APIKEY")),
        "sendable": bool(request.get("sendable")),
    }


def _json_body(raw_body: bytes) -> Dict[str, Any]:
    if not raw_body:
        return {}
    payload = json.loads(raw_body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("PRODUCTION_HTTP_RESPONSE_NOT_OBJECT")
    return payload


def _failure_family_for_http_error(status_code: int) -> str:
    if status_code in {400, 404, 409, 422}:
        return "PRODUCTION_HTTP_REQUEST_REJECTED"
    if status_code in {401, 403}:
        return "PRODUCTION_HTTP_AUTH_REJECTED"
    if status_code == 408:
        return "PRODUCTION_HTTP_TIMEOUT"
    if status_code == 429:
        return "PRODUCTION_HTTP_RATE_LIMITED"
    if 500 <= status_code <= 599:
        return "PRODUCTION_HTTP_EXCHANGE_UNAVAILABLE"
    return "PRODUCTION_HTTP_UNEXPECTED_STATUS"


def _redacted_exchange_result(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "symbol": payload.get("symbol"),
        "external_status": payload.get("status"),
        "external_order_id_present": payload.get("orderId") is not None,
        "client_order_id_present": payload.get("clientOrderId") is not None,
        "transact_time_present": payload.get("transactTime") is not None,
    }


def send_signed_order_request(
    request: Dict[str, Any],
    now_ts: int,
    *,
    opener: Optional[Callable[..., Any]] = None,
    timeout_seconds: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], Optional[str], Optional[Dict[str, Any]]]:
    requested_payload = redacted_request_shape(request)
    http_request = urllib.request.Request(
        str(request["url"]),
        method=str(request["method"]),
        headers=dict(request.get("headers") or {}),
    )
    open_call = opener or urllib.request.urlopen

    try:
        with open_call(http_request, timeout=timeout_seconds) as response:
            status_code = int(getattr(response, "status", 200))
            body = _json_body(response.read())
    except urllib.error.HTTPError as exc:
        body = {}
        try:
            body = _json_body(exc.read())
        except Exception:
            body = {}
        finally:
            exc.close()
        failure_family = _failure_family_for_http_error(int(exc.code))
        outcome = {
            "ok": False,
            "result": None,
            "error": {
                "code": failure_family,
                "failure_family": failure_family,
                "http_status": int(exc.code),
                "external_request_started": True,
                "external_order_id_present": False,
                "execution_mode": "production",
                "executor_mode_label": "production",
                "timeout_policy_label": "single_attempt_v1",
                "exchange_error_code_present": body.get("code") is not None,
                "exchange_error_message_present": body.get("msg") is not None,
                "ts": now_ts,
            },
        }
        return outcome, requested_payload, failure_family, outcome["error"]
    except Exception as exc:  # noqa: BLE001 - transport errors must fail closed.
        failure_family = "PRODUCTION_HTTP_TRANSPORT_FAILED"
        outcome = {
            "ok": False,
            "result": None,
            "error": {
                "code": failure_family,
                "failure_family": failure_family,
                "transport_error_type": type(exc).__name__,
                "external_request_started": True,
                "external_order_id_present": False,
                "execution_mode": "production",
                "executor_mode_label": "production",
                "timeout_policy_label": "single_attempt_v1",
                "ts": now_ts,
            },
        }
        return outcome, requested_payload, failure_family, outcome["error"]

    redacted_result = _redacted_exchange_result(body)
    outcome = {
        "ok": 200 <= status_code <= 299,
        "result": {
            **redacted_result,
            "http_status": status_code,
            "external_request_started": True,
            "execution_mode": "production",
            "executor_mode_label": "production",
            "timeout_policy_label": "single_attempt_v1",
            "ts": now_ts,
        },
        "error": None,
    }
    return outcome, requested_payload, "PRODUCTION_HTTP_RESPONSE", outcome["result"]


def run_production_order_request(
    transport_input: Dict[str, Any],
    credentials: Dict[str, str] | None,
    now_ts: int,
    *,
    execute: bool = False,
    transport_enabled: bool = False,
    opener: Optional[Callable[..., Any]] = None,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], Optional[str], Optional[Dict[str, Any]]]:
    if not execute:
        return _boundary_failure(
            "PRODUCTION_SEND_EXECUTION_NOT_AUTHORIZED",
            ts=now_ts,
        )
    if credentials is None:
        return _boundary_failure(
            "PRODUCTION_CREDENTIALS_MISSING",
            ts=now_ts,
        )

    try:
        request = build_signed_order_request(transport_input, credentials, now_ts)
    except ValueError as exc:
        return _boundary_failure(str(exc), ts=now_ts)

    requested_payload = redacted_request_shape(request)
    if not transport_enabled:
        return _boundary_failure(
            "PRODUCTION_HTTP_TRANSPORT_NOT_AUTHORIZED",
            ts=now_ts,
            external_request_started=False,
            signed_request_shape=requested_payload,
        )

    return send_signed_order_request(
        request,
        now_ts,
        opener=opener,
    )
