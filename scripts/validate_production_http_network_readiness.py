#!/usr/bin/env python3
"""Validate non-executing production HTTP/network readiness evidence.

The validator only accepts non-secret status labels. It never opens sockets,
performs DNS lookups, sends HTTP requests, reads secrets, or mutates runtime.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "config" / "production_http_network_readiness.template.json"
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "production_http_network_readiness_validation.json"
MD_OUT = REPORTS_DIR / "production_http_network_readiness_validation.md"

STATUS_FIELDS = [
    "PRODUCTION_HTTP_ENDPOINT_ALLOWLIST",
    "PRODUCTION_HTTP_DNS_RESOLUTION_PLAN",
    "PRODUCTION_HTTP_EGRESS_BOUNDARY",
    "PRODUCTION_HTTP_TIMEOUT_POLICY",
    "PRODUCTION_HTTP_RETRY_POLICY",
    "PRODUCTION_HTTP_IDEMPOTENCY_HEADER",
    "PRODUCTION_HTTP_RESPONSE_REDACTION",
    "PRODUCTION_HTTP_FAILURE_CLOSED_PATH",
]

REQUIRED_FIELDS = [
    "PRODUCTION_HTTP_NETWORK_READINESS_OPERATOR_FILLED",
    *STATUS_FIELDS,
    "AUTHORIZED_SECRET_VALUE_READ",
    "AUTHORIZED_SECRET_VALUE_DISCLOSURE",
    "AUTHORIZED_PRODUCTION_HTTP_NETWORK_EXECUTION",
    "AUTHORIZED_PRODUCTION_REQUEST",
    "AUTHORIZED_CANARY_RERUN",
    "AUTHORIZED_GO_LIVE",
    "AUTHORIZED_LIVE_TRADING",
    "FINAL_OPERATOR_VERDICT",
]

EXPECTED_LOCKED_FIELDS = {
    "AUTHORIZED_SECRET_VALUE_READ": "NO",
    "AUTHORIZED_SECRET_VALUE_DISCLOSURE": "NO",
    "AUTHORIZED_PRODUCTION_HTTP_NETWORK_EXECUTION": "NO",
    "AUTHORIZED_PRODUCTION_REQUEST": "NO",
    "AUTHORIZED_CANARY_RERUN": "NO",
    "AUTHORIZED_GO_LIVE": "NO",
    "AUTHORIZED_LIVE_TRADING": "NO",
}

PLACEHOLDERS = {"", "TO_BE_CONFIRMED", "TBD", "PENDING"}
VALID_STATUS = {"PRESENT_VALID", "NOT_REQUIRED"}
SECRET_LIKE_TOKENS = ("KEY=", "SECRET=", "TOKEN=", "PASSWORD=", "BEGIN ", "sk-", "AKIA")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def contains_secret_like_text(value: Any) -> bool:
    text = as_text(value)
    upper = text.upper()
    return any(token in upper for token in SECRET_LIKE_TOKENS)


def validate(data: dict[str, Any], input_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"{field}:MISSING")
        elif contains_secret_like_text(data[field]):
            errors.append(f"{field}:SECRET_LIKE_VALUE_FORBIDDEN")

    for field, expected in EXPECTED_LOCKED_FIELDS.items():
        if as_text(data.get(field)).upper() != expected:
            errors.append(f"{field}:MUST_REMAIN_{expected}")

    operator_filled = as_text(data.get("PRODUCTION_HTTP_NETWORK_READINESS_OPERATOR_FILLED")).upper()
    if operator_filled != "YES":
        errors.append("PRODUCTION_HTTP_NETWORK_READINESS_OPERATOR_FILLED:MUST_BE_YES")

    for field in STATUS_FIELDS:
        value = as_text(data.get(field)).upper()
        if value in PLACEHOLDERS:
            errors.append(f"{field}:TO_BE_CONFIRMED")
        elif value not in VALID_STATUS:
            errors.append(f"{field}:EXPECTED_PRESENT_VALID_OR_NOT_REQUIRED")

    final_verdict = as_text(data.get("FINAL_OPERATOR_VERDICT"))
    if final_verdict != "APPROVED_FOR_PRODUCTION_HTTP_NETWORK_READINESS_ONLY":
        errors.append("FINAL_OPERATOR_VERDICT:NOT_APPROVED_FOR_PRODUCTION_HTTP_NETWORK_READINESS_ONLY")

    result = "PASS" if not errors else "BLOCKED"
    input_label = str(input_path.relative_to(ROOT)) if input_path.is_relative_to(ROOT) else str(input_path)
    return {
        "generated_at": utc_now(),
        "input_file": input_label,
        "result": result,
        "errors": errors,
        "warnings": warnings,
        "field_status": {field: as_text(data.get(field)).upper() or "MISSING" for field in STATUS_FIELDS},
        "boundary": {
            "secret_value_read": "NO",
            "secret_value_disclosed": "NO",
            "dns_lookup_performed": "NO",
            "socket_opened": "NO",
            "production_http_network_executed": "NO",
            "production_request_sent": "NO",
            "canary_rerun": "NO",
            "runtime_modified": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }


def markdown(report: dict[str, Any]) -> str:
    errors = "\n".join(f"- {item}" for item in report["errors"]) or "- none"
    warnings = "\n".join(f"- {item}" for item in report["warnings"]) or "- none"
    field_status = "\n".join(f"- {field}: {status}" for field, status in report["field_status"].items())
    return f"""# Production HTTP/Network Readiness Validation

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- input file: `{report["input_file"]}`

## Field Status

{field_status}

## Errors

{errors}

## Warnings

{warnings}

## Boundary

- secret value read: {report["boundary"]["secret_value_read"]}
- secret value disclosed: {report["boundary"]["secret_value_disclosed"]}
- DNS lookup performed: {report["boundary"]["dns_lookup_performed"]}
- socket opened: {report["boundary"]["socket_opened"]}
- production HTTP/network executed: {report["boundary"]["production_http_network_executed"]}
- production request sent: {report["boundary"]["production_request_sent"]}
- canary rerun: {report["boundary"]["canary_rerun"]}
- runtime modified: {report["boundary"]["runtime_modified"]}
- go-live: {report["boundary"]["go_live"]}
- live trading: {report["boundary"]["live_trading"]}
"""


def main(argv: list[str]) -> int:
    input_path = Path(argv[1]).resolve() if len(argv) > 1 else DEFAULT_INPUT
    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - validator should report bad input cleanly.
        print("PRODUCTION_HTTP_NETWORK_READINESS_VALIDATION=FAIL")
        print(f"FAIL_REASON=INPUT_UNREADABLE:{type(exc).__name__}")
        return 2
    if not isinstance(data, dict):
        print("PRODUCTION_HTTP_NETWORK_READINESS_VALIDATION=FAIL")
        print("FAIL_REASON=INPUT_NOT_OBJECT")
        return 2

    report = validate(data, input_path)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(markdown(report), encoding="utf-8")

    print("[Production HTTP/Network Readiness Validation]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(f"errors: {len(report['errors'])}")
    print(f"warnings: {len(report['warnings'])}")
    print("secret_value_read: NO")
    print("dns_lookup_performed: NO")
    print("socket_opened: NO")
    print("production_http_network_executed: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
