#!/usr/bin/env python3
"""Validate non-secret production credential readiness evidence.

The input file must contain only status labels such as PRESENT_VALID or
TO_BE_CONFIRMED. This validator never reads credential files, env files, or
secret values.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "config" / "production_credential_readiness.template.json"
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "production_credential_readiness_validation.json"
MD_OUT = REPORTS_DIR / "production_credential_readiness_validation.md"

STATUS_FIELDS = [
    "PRODUCTION_CREDENTIAL_SOURCE",
    "PRODUCTION_CREDENTIAL_OWNER",
    "PRODUCTION_CREDENTIAL_MODE",
    "PRODUCTION_EXCHANGE_BASE_URL",
    "PRODUCTION_EXCHANGE_API_KEY",
    "PRODUCTION_EXCHANGE_API_SECRET",
    "PRODUCTION_EXCHANGE_KEY_ID",
]

REQUIRED_FIELDS = [
    "PRODUCTION_CREDENTIAL_READINESS_OPERATOR_FILLED",
    *STATUS_FIELDS,
    "AUTHORIZED_SECRET_VALUE_DISCLOSURE",
    "AUTHORIZED_PRODUCTION_SIGNING",
    "AUTHORIZED_PRODUCTION_HTTP_NETWORK",
    "AUTHORIZED_PRODUCTION_REQUEST",
    "AUTHORIZED_GO_LIVE",
    "AUTHORIZED_LIVE_TRADING",
    "FINAL_OPERATOR_VERDICT",
]

EXPECTED_LOCKED_FIELDS = {
    "AUTHORIZED_SECRET_VALUE_DISCLOSURE": "NO",
    "AUTHORIZED_PRODUCTION_SIGNING": "NO",
    "AUTHORIZED_PRODUCTION_HTTP_NETWORK": "NO",
    "AUTHORIZED_PRODUCTION_REQUEST": "NO",
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

    operator_filled = as_text(data.get("PRODUCTION_CREDENTIAL_READINESS_OPERATOR_FILLED")).upper()
    if operator_filled != "YES":
        errors.append("PRODUCTION_CREDENTIAL_READINESS_OPERATOR_FILLED:MUST_BE_YES")

    for field in STATUS_FIELDS:
        value = as_text(data.get(field)).upper()
        if value in PLACEHOLDERS:
            errors.append(f"{field}:TO_BE_CONFIRMED")
        elif value not in VALID_STATUS:
            errors.append(f"{field}:EXPECTED_PRESENT_VALID_OR_NOT_REQUIRED")

    final_verdict = as_text(data.get("FINAL_OPERATOR_VERDICT"))
    if final_verdict != "APPROVED_FOR_PRODUCTION_CREDENTIAL_READINESS_ONLY":
        errors.append("FINAL_OPERATOR_VERDICT:NOT_APPROVED_FOR_PRODUCTION_CREDENTIAL_READINESS_ONLY")

    if as_text(data.get("PRODUCTION_EXCHANGE_KEY_ID")).upper() == "NOT_REQUIRED":
        warnings.append("PRODUCTION_EXCHANGE_KEY_ID:NOT_REQUIRED_RECORDED")

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
            "credential_file_read": "NO",
            "env_config_read": "NO",
            "secret_value_read": "NO",
            "secret_value_disclosed": "NO",
            "production_signing_enabled": "NO",
            "production_http_network_enabled": "NO",
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
    return f"""# Production Credential Readiness Validation

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

- credential file read: {report["boundary"]["credential_file_read"]}
- env/config read: {report["boundary"]["env_config_read"]}
- secret value read: {report["boundary"]["secret_value_read"]}
- secret value disclosed: {report["boundary"]["secret_value_disclosed"]}
- production signing enabled: {report["boundary"]["production_signing_enabled"]}
- production HTTP/network enabled: {report["boundary"]["production_http_network_enabled"]}
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
        print("PRODUCTION_CREDENTIAL_READINESS_VALIDATION=FAIL")
        print(f"FAIL_REASON=INPUT_UNREADABLE:{type(exc).__name__}")
        return 2
    if not isinstance(data, dict):
        print("PRODUCTION_CREDENTIAL_READINESS_VALIDATION=FAIL")
        print("FAIL_REASON=INPUT_NOT_OBJECT")
        return 2

    report = validate(data, input_path)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(markdown(report), encoding="utf-8")

    print("[Production Credential Readiness Validation]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(f"errors: {len(report['errors'])}")
    print(f"warnings: {len(report['warnings'])}")
    print("credential_file_read: NO")
    print("secret_value_read: NO")
    print("secret_value_disclosed: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
