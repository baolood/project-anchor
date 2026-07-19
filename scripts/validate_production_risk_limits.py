#!/usr/bin/env python3
"""Validate non-secret production risk-limit parameters."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "config" / "production_risk_limits.template.json"
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "production_risk_limits_validation.json"
MD_OUT = REPORTS_DIR / "production_risk_limits_validation.md"

REQUIRED_FIELDS = [
    "AUTHORIZED_PRODUCTION_MARKET",
    "AUTHORIZED_PRODUCTION_SYMBOLS",
    "AUTHORIZED_PRODUCTION_SIDES",
    "AUTHORIZED_MAX_NOTIONAL",
    "AUTHORIZED_MAX_ORDER_COUNT",
    "AUTHORIZED_IDEMPOTENCY_POLICY",
    "AUTHORIZED_KILL_SWITCH_PRECONDITION",
    "AUTHORIZED_STOP_CONDITIONS",
    "AUTHORIZED_MONITORING_WINDOW",
    "AUTHORIZED_PRODUCTION_CREDENTIAL_ACCESS",
    "AUTHORIZED_PRODUCTION_SIGNING",
    "AUTHORIZED_PRODUCTION_HTTP_NETWORK",
    "AUTHORIZED_GO_LIVE",
    "AUTHORIZED_LIVE_TRADING",
    "FINAL_OPERATOR_VERDICT",
]

PLACEHOLDERS = {"", "TO_BE_CONFIRMED", "TBD", "PENDING"}

EXPECTED_LOCKED_FIELDS = {
    "AUTHORIZED_PRODUCTION_CREDENTIAL_ACCESS": "NO",
    "AUTHORIZED_PRODUCTION_SIGNING": "NO",
    "AUTHORIZED_PRODUCTION_HTTP_NETWORK": "NO",
    "AUTHORIZED_GO_LIVE": "NO",
    "AUTHORIZED_LIVE_TRADING": "NO",
}

EXPECTED_STATIC_FIELDS = {
    "AUTHORIZED_IDEMPOTENCY_POLICY": "required_unique_key_per_authorized_window",
    "AUTHORIZED_KILL_SWITCH_PRECONDITION": "must_be_false_before_execution",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def split_csv(value: Any) -> list[str]:
    text = as_text(value)
    if text in PLACEHOLDERS:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def parse_positive_number(value: Any) -> float | None:
    text = as_text(value)
    if text in PLACEHOLDERS:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if number > 0 else None


def parse_positive_int(value: Any) -> int | None:
    text = as_text(value)
    if text in PLACEHOLDERS:
        return None
    try:
        number = int(text)
    except ValueError:
        return None
    return number if number > 0 else None


def validate(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"{field}:MISSING")
        elif as_text(data[field]) in PLACEHOLDERS:
            errors.append(f"{field}:TO_BE_CONFIRMED")

    for field, expected in EXPECTED_LOCKED_FIELDS.items():
        if as_text(data.get(field)) != expected:
            errors.append(f"{field}:MUST_REMAIN_{expected}")

    for field, expected in EXPECTED_STATIC_FIELDS.items():
        if as_text(data.get(field)) != expected:
            errors.append(f"{field}:EXPECTED_{expected}")

    symbols = split_csv(data.get("AUTHORIZED_PRODUCTION_SYMBOLS"))
    sides = split_csv(data.get("AUTHORIZED_PRODUCTION_SIDES"))
    max_notional = parse_positive_number(data.get("AUTHORIZED_MAX_NOTIONAL"))
    max_order_count = parse_positive_int(data.get("AUTHORIZED_MAX_ORDER_COUNT"))

    if symbols and any(not symbol.replace("-", "").replace("_", "").isalnum() for symbol in symbols):
        errors.append("AUTHORIZED_PRODUCTION_SYMBOLS:INVALID_SYMBOL_FORMAT")
    if sides and any(side not in {"BUY", "SELL", "BUY_ONLY", "SELL_ONLY"} for side in sides):
        errors.append("AUTHORIZED_PRODUCTION_SIDES:INVALID_SIDE")
    if as_text(data.get("AUTHORIZED_MAX_NOTIONAL")) not in PLACEHOLDERS and max_notional is None:
        errors.append("AUTHORIZED_MAX_NOTIONAL:INVALID_POSITIVE_NUMBER")
    if as_text(data.get("AUTHORIZED_MAX_ORDER_COUNT")) not in PLACEHOLDERS and max_order_count is None:
        errors.append("AUTHORIZED_MAX_ORDER_COUNT:INVALID_POSITIVE_INTEGER")
    if "duplicate" not in as_text(data.get("AUTHORIZED_STOP_CONDITIONS")).lower():
        warnings.append("AUTHORIZED_STOP_CONDITIONS:SHOULD_INCLUDE_DUPLICATE_ATTEMPT_STOP")
    if "minute" not in as_text(data.get("AUTHORIZED_MONITORING_WINDOW")).lower():
        warnings.append("AUTHORIZED_MONITORING_WINDOW:SHOULD_BE_TIME_WINDOW")

    result = "PASS" if not errors else "BLOCKED"
    return {
        "generated_at": utc_now(),
        "input_file": str(DEFAULT_INPUT.relative_to(ROOT)),
        "result": result,
        "errors": errors,
        "warnings": warnings,
        "field_presence": {
            field: ("PRESENT" if field in data and as_text(data[field]) not in PLACEHOLDERS else "MISSING_OR_PLACEHOLDER")
            for field in REQUIRED_FIELDS
        },
        "boundary": {
            "secret_read": "NO",
            "production_credentials_read": "NO",
            "production_signing_enabled": "NO",
            "production_http_network_enabled": "NO",
            "production_request_sent": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }


def markdown(report: dict[str, Any]) -> str:
    errors = "\n".join(f"- {item}" for item in report["errors"]) or "- none"
    warnings = "\n".join(f"- {item}" for item in report["warnings"]) or "- none"
    presence = "\n".join(
        f"- {field}: {state}" for field, state in report["field_presence"].items()
    )
    return f"""# Production Risk Limits Validation

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- input file: `{report["input_file"]}`

## Field Presence

{presence}

## Errors

{errors}

## Warnings

{warnings}

## Boundary

- secret read: {report["boundary"]["secret_read"]}
- production credentials read: {report["boundary"]["production_credentials_read"]}
- production signing enabled: {report["boundary"]["production_signing_enabled"]}
- production HTTP/network enabled: {report["boundary"]["production_http_network_enabled"]}
- production request sent: {report["boundary"]["production_request_sent"]}
- go-live: {report["boundary"]["go_live"]}
- live trading: {report["boundary"]["live_trading"]}
"""


def main(argv: list[str]) -> int:
    input_path = Path(argv[1]).resolve() if len(argv) > 1 else DEFAULT_INPUT
    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - validator should report bad input cleanly.
        print(f"PRODUCTION_RISK_LIMITS_VALIDATION=FAIL")
        print(f"FAIL_REASON=INPUT_UNREADABLE:{type(exc).__name__}")
        return 2
    if not isinstance(data, dict):
        print("PRODUCTION_RISK_LIMITS_VALIDATION=FAIL")
        print("FAIL_REASON=INPUT_NOT_OBJECT")
        return 2

    report = validate(data)
    report["input_file"] = str(input_path.relative_to(ROOT)) if input_path.is_relative_to(ROOT) else str(input_path)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(markdown(report), encoding="utf-8")

    print("[Production Risk Limits Validation]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(f"errors: {len(report['errors'])}")
    print(f"warnings: {len(report['warnings'])}")
    print("secret_read: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
