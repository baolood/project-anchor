import hashlib
import hmac
import urllib.parse
from typing import Any, Dict, Optional, Tuple


DEFAULT_PRODUCTION_ORDER_PATH = "/api/v3/order"
DEFAULT_RECV_WINDOW_MS = 5000
SUPPORTED_MARKET = "binance_spot"
ALLOWED_PRODUCTION_ORIGINS = {"https://api.binance.com"}


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


def run_production_order_request(
    transport_input: Dict[str, Any],
    credentials: Dict[str, str] | None,
    now_ts: int,
    *,
    execute: bool = False,
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
    return _boundary_failure(
        "PRODUCTION_HTTP_TRANSPORT_NOT_WIRED",
        ts=now_ts,
        external_request_started=False,
        signed_request_shape=requested_payload,
    )
