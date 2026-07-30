#!/usr/bin/env python3
"""Validate non-secret production Binance API control-plane configuration evidence.

The input file records only operator-observed status labels and non-secret
control-plane settings. This validator does not call Binance, read credential
files, perform DNS lookups, open sockets, sign payloads, or send requests.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "config" / "production_api_configuration.template.json"
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "production_api_configuration_validation.json"
MD_OUT = REPORTS_DIR / "production_api_configuration_validation.md"

EXPECTED = {
    "BINANCE_API_IP_WHITELIST": "45.76.190.109",
    "READ_PERMISSION": "YES",
    "SPOT_TRADING_PERMISSION": "NO",
    "WITHDRAW_PERMISSION": "NO",
    "PRODUCTION_API_CONFIG_SAVED": "YES",
    "AUTHORIZED_PRODUCTION_SIGNING": "NO",
    "AUTHORIZED_PRODUCTION_HTTP_NETWORK": "NO",
    "AUTHORIZED_PRODUCTION_REQUEST": "NO",
    "AUTHORIZED_GO_LIVE": "NO",
    "AUTHORIZED_LIVE_TRADING": "NO",
    "FINAL_OPERATOR_VERDICT": "APPROVED_FOR_PRODUCTION_API_CONFIGURATION_READINESS_ONLY",
}

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
    return any(token.upper() in upper for token in SECRET_LIKE_TOKENS)


def validate(data: dict[str, Any], input_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    field_status: dict[str, str] = {}

    for field, expected in EXPECTED.items():
        actual = as_text(data.get(field))
        field_status[field] = actual or "MISSING"
        if not actual:
            errors.append(f"{field}:MISSING")
        elif contains_secret_like_text(actual):
            errors.append(f"{field}:SECRET_LIKE_VALUE_FORBIDDEN")
        elif actual != expected:
            errors.append(f"{field}:EXPECTED_{expected}")

    result = "PASS" if not errors else "BLOCKED"
    input_label = str(input_path.relative_to(ROOT)) if input_path.is_relative_to(ROOT) else str(input_path)
    return {
        "generated_at": utc_now(),
        "input_file": input_label,
        "result": result,
        "errors": errors,
        "field_status": field_status,
        "boundary": {
            "credential_file_read": "NO",
            "secret_value_read": "NO",
            "secret_value_disclosed": "NO",
            "binance_api_called": "NO",
            "dns_lookup": "NO",
            "socket_opened": "NO",
            "production_signing_enabled": "NO",
            "production_http_network_enabled": "NO",
            "production_request_sent": "NO",
            "spot_trading_enabled": "NO",
            "withdraw_enabled": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }


def markdown(report: dict[str, Any]) -> str:
    fields = "\n".join(f"- {field}: {value}" for field, value in report["field_status"].items())
    errors = "\n".join(f"- {item}" for item in report["errors"]) or "- none"
    boundary = report["boundary"]
    return f"""# Production API Configuration Validation

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- input file: `{report["input_file"]}`

## Field Status

{fields}

## Errors

{errors}

## Boundary

- credential file read: {boundary["credential_file_read"]}
- secret value read: {boundary["secret_value_read"]}
- secret value disclosed: {boundary["secret_value_disclosed"]}
- Binance API called: {boundary["binance_api_called"]}
- DNS lookup: {boundary["dns_lookup"]}
- socket opened: {boundary["socket_opened"]}
- production signing enabled: {boundary["production_signing_enabled"]}
- production HTTP/network enabled: {boundary["production_http_network_enabled"]}
- production request sent: {boundary["production_request_sent"]}
- spot trading enabled: {boundary["spot_trading_enabled"]}
- withdraw enabled: {boundary["withdraw_enabled"]}
- go-live: {boundary["go_live"]}
- live trading: {boundary["live_trading"]}
"""


def main(argv: list[str]) -> int:
    input_path = Path(argv[1]).resolve() if len(argv) > 1 else DEFAULT_INPUT
    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - validator should report bad input cleanly.
        print("PRODUCTION_API_CONFIGURATION_VALIDATION=FAIL")
        print(f"FAIL_REASON=INPUT_UNREADABLE:{type(exc).__name__}")
        return 2
    if not isinstance(data, dict):
        print("PRODUCTION_API_CONFIGURATION_VALIDATION=FAIL")
        print("FAIL_REASON=INPUT_NOT_OBJECT")
        return 2

    report = validate(data, input_path)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(markdown(report), encoding="utf-8")

    print("[Production API Configuration Validation]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(f"errors: {len(report['errors'])}")
    print("credential_file_read: NO")
    print("secret_value_read: NO")
    print("secret_value_disclosed: NO")
    print("binance_api_called: NO")
    print("production_request_sent: NO")
    print("spot_trading_enabled: NO")
    print("withdraw_enabled: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
