from __future__ import annotations


PRODUCTION_IDEMPOTENCY_KEY = (
    "production:ops_manual:BTCUSDT:BUY:4:first-bounded-production-request:v1"
)

FORBIDDEN_PRODUCTION_INPUT_FIELDS = frozenset(
    {
        "account_id",
        "api_key",
        "api_secret",
        "exchange",
        "passphrase",
        "secret",
        "secret_key",
    }
)


def coerce_positive_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return number


def validate_production_order_request(body: dict) -> tuple[bool, str | None]:
    forbidden = next(
        (
            key
            for key in body.keys()
            if isinstance(key, str) and key.lower() in FORBIDDEN_PRODUCTION_INPUT_FIELDS
        ),
        None,
    )
    if forbidden is not None:
        return (False, f"FORBIDDEN_FIELD:{forbidden}")

    symbol = body.get("symbol")
    side = body.get("side")
    order_type = body.get("order_type")
    idempotency_key = str(body.get("idempotency_key", "")).strip()
    execution_mode = body.get("execution_mode")
    market = body.get("market")
    source = body.get("source")
    notional = coerce_positive_float(body.get("notional"))

    if symbol != "BTCUSDT":
        return (False, "PRODUCTION_SYMBOL_INVALID")
    if side != "BUY":
        return (False, "PRODUCTION_SIDE_INVALID")
    if notional is None or notional != 4.0:
        return (False, "PRODUCTION_NOTIONAL_INVALID")
    if order_type != "market":
        return (False, "PRODUCTION_ORDER_TYPE_INVALID")
    if idempotency_key != PRODUCTION_IDEMPOTENCY_KEY:
        return (False, "PRODUCTION_IDEMPOTENCY_KEY_INVALID")
    if execution_mode != "production":
        return (False, "PRODUCTION_EXECUTION_MODE_REQUIRED")
    if market != "binance_spot":
        return (False, "PRODUCTION_MARKET_INVALID")
    if source != "ops_manual":
        return (False, "PRODUCTION_SOURCE_INVALID")
    return (True, None)


def production_order_blocked_response() -> dict:
    return {
        "status": "blocked",
        "error": "PRODUCTION_SEND_NOT_AUTHORIZED",
        "command_created": False,
        "production_request_sent": False,
        "requires_explicit_execution_gate": True,
        "idempotency_key": PRODUCTION_IDEMPOTENCY_KEY,
    }
