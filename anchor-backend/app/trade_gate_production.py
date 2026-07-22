from __future__ import annotations


PRODUCTION_IDEMPOTENCY_KEY = (
    "production:ops_manual:BTCUSDT:BUY:4:first-bounded-production-request:v1"
)
PRODUCTION_EXECUTION_GATE_REQUIRED_VERDICT = (
    "APPROVED_FOR_EXACTLY_ONE_PRODUCTION_REQUEST_COMMAND_CREATION_ONLY"
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

PRODUCTION_COMMAND_TYPE = "PRODUCTION_ORDER_INTENT"


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


def production_execution_gate_decision(config: dict | None = None) -> dict:
    data = config if isinstance(config, dict) else {}
    verdict = str(data.get("FINAL_OPERATOR_VERDICT", "")).strip()
    enabled = data.get("PRODUCTION_EXECUTION_GATE_ENABLED") is True
    exactly_one = data.get("PRODUCTION_EXACTLY_ONE_COMMAND_CREATION") is True
    no_retry = data.get("PRODUCTION_NO_RETRY") is True
    idempotency_key = str(data.get("PRODUCTION_IDEMPOTENCY_KEY", "")).strip()

    checks = {
        "gate_enabled": enabled,
        "exactly_one_command_creation": exactly_one,
        "no_retry": no_retry,
        "idempotency_key_matches": idempotency_key == PRODUCTION_IDEMPOTENCY_KEY,
        "operator_verdict_matches": verdict == PRODUCTION_EXECUTION_GATE_REQUIRED_VERDICT,
    }
    authorized = all(checks.values())
    return {
        "authorized": authorized,
        "reason": "AUTHORIZED" if authorized else "PRODUCTION_EXECUTION_GATE_CLOSED",
        "checks": checks,
        "required_verdict": PRODUCTION_EXECUTION_GATE_REQUIRED_VERDICT,
    }


def production_order_blocked_response(gate_decision: dict | None = None) -> dict:
    decision = gate_decision if isinstance(gate_decision, dict) else production_execution_gate_decision()
    return {
        "status": "blocked",
        "error": decision.get("reason") or "PRODUCTION_EXECUTION_GATE_CLOSED",
        "command_creation_candidate": False,
        "command_created": False,
        "production_request_sent": False,
        "requires_explicit_execution_gate": True,
        "execution_gate_authorized": bool(decision.get("authorized")),
        "idempotency_key": PRODUCTION_IDEMPOTENCY_KEY,
    }


def production_order_command_creation_payload(body: dict) -> dict:
    notional = coerce_positive_float(body.get("notional"))
    return {
        "command_type": PRODUCTION_COMMAND_TYPE,
        "execution_mode": "production",
        "market": "binance_spot",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "notional": notional,
        "order_type": "market",
        "source": "ops_manual",
        "idempotency_key": PRODUCTION_IDEMPOTENCY_KEY,
        "command_creation_only": True,
        "production_signing_executed": False,
        "production_http_network_executed": False,
        "production_request_sent": False,
    }


def production_order_command_creation_candidate_response(
    body: dict,
    gate_decision: dict | None = None,
) -> dict:
    decision = gate_decision if isinstance(gate_decision, dict) else production_execution_gate_decision()
    is_valid, reject_reason = validate_production_order_request(body)
    if not is_valid:
        return {
            "status": "error",
            "error": reject_reason,
            "command_creation_candidate": False,
            "command_created": False,
            "production_request_sent": False,
        }
    if not decision.get("authorized"):
        return production_order_blocked_response(decision)

    return {
        "status": "ready_to_create_command",
        "error": None,
        "command_type": PRODUCTION_COMMAND_TYPE,
        "command_creation_candidate": True,
        "command_created": False,
        "production_request_sent": False,
        "requires_explicit_execution_gate": True,
        "execution_gate_authorized": True,
        "idempotency_key": PRODUCTION_IDEMPOTENCY_KEY,
        "payload": production_order_command_creation_payload(body),
    }
