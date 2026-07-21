#!/usr/bin/env python3
"""Generate a non-sendable unsigned production canonical payload preview.

This dry-run uses only non-secret production risk parameters to prove the
canonical payload shape can be produced before signing. It does not read
credentials or env files, does not sign, does not generate Authorization
headers, performs no DNS lookup, opens no sockets, and sends no request.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
RISK_LIMITS_CONFIG = ROOT / "config" / "production_risk_limits.template.json"
SIGNING_READINESS_REPORT = ROOT / "reports" / "production_signing_readiness_validation.json"
NO_SEND_DRILL_REPORT = ROOT / "reports" / "production_no_send_execution_drill.json"
JSON_OUT = REPORTS_DIR / "production_unsigned_canonical_payload_dry_run.json"
MD_OUT = REPORTS_DIR / "production_unsigned_canonical_payload_dry_run.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - dry-runs should fail closed with evidence.
        return None, f"{path.relative_to(ROOT)}:UNREADABLE:{type(exc).__name__}"
    if not isinstance(data, dict):
        return None, f"{path.relative_to(ROOT)}:NOT_OBJECT"
    return data, None


def decimal_string(value: Any) -> tuple[str | None, str | None]:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None, "INVALID_DECIMAL"
    if number <= 0:
        return None, "NOT_POSITIVE"
    return format(number.normalize(), "f"), None


def build_report() -> tuple[dict[str, Any], int]:
    generated_at = utc_now()
    config, config_error = read_json(RISK_LIMITS_CONFIG)
    signing_readiness, signing_error = read_json(SIGNING_READINESS_REPORT)
    no_send_drill, no_send_error = read_json(NO_SEND_DRILL_REPORT)

    errors: list[str] = []
    for error in (config_error, signing_error, no_send_error):
        if error:
            errors.append(error)

    config = config or {}
    signing_readiness = signing_readiness or {}
    no_send_drill = no_send_drill or {}

    market = str(config.get("AUTHORIZED_PRODUCTION_MARKET") or "").strip()
    symbols = str(config.get("AUTHORIZED_PRODUCTION_SYMBOLS") or "").strip()
    sides = str(config.get("AUTHORIZED_PRODUCTION_SIDES") or "").strip()
    max_notional, notional_error = decimal_string(config.get("AUTHORIZED_MAX_NOTIONAL"))
    max_order_count = str(config.get("AUTHORIZED_MAX_ORDER_COUNT") or "").strip()

    if market != "binance_spot":
        errors.append("AUTHORIZED_PRODUCTION_MARKET:UNEXPECTED")
    if symbols != "BTCUSDT":
        errors.append("AUTHORIZED_PRODUCTION_SYMBOLS:UNEXPECTED")
    if sides != "BUY_ONLY":
        errors.append("AUTHORIZED_PRODUCTION_SIDES:UNEXPECTED")
    if notional_error:
        errors.append(f"AUTHORIZED_MAX_NOTIONAL:{notional_error}")
    if max_order_count != "1":
        errors.append("AUTHORIZED_MAX_ORDER_COUNT:UNEXPECTED")

    if signing_readiness.get("result") != "PASS":
        errors.append("PRODUCTION_SIGNING_READINESS:NOT_PASS")
    if no_send_drill.get("result") != "PASS":
        errors.append("PRODUCTION_NO_SEND_DRILL:NOT_PASS")
    if no_send_drill.get("authorized_to_execute") is not False:
        errors.append("PRODUCTION_NO_SEND_DRILL:AUTHORIZED_TO_EXECUTE_NOT_FALSE")

    canonical_payload = {
        "execution_mode": "production",
        "market": market,
        "symbol": symbols,
        "side": "BUY",
        "notional": max_notional,
        "order_type": "market",
        "idempotency_key_policy": config.get("AUTHORIZED_IDEMPOTENCY_POLICY"),
        "max_order_count": max_order_count,
        "kill_switch_precondition": config.get("AUTHORIZED_KILL_SWITCH_PRECONDITION"),
        "stop_conditions": config.get("AUTHORIZED_STOP_CONDITIONS"),
        "monitoring_window": config.get("AUTHORIZED_MONITORING_WINDOW"),
    }
    canonical_payload_json = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))

    validation_checks = [
        {
            "name": "risk_limits_source_loaded",
            "result": "PASS" if not config_error else "FAIL",
        },
        {
            "name": "signing_readiness_pass",
            "result": "PASS" if signing_readiness.get("result") == "PASS" else "FAIL",
        },
        {
            "name": "no_send_drill_pass",
            "result": "PASS" if no_send_drill.get("result") == "PASS" else "FAIL",
        },
        {
            "name": "no_send_authorized_to_execute_false",
            "result": "PASS" if no_send_drill.get("authorized_to_execute") is False else "FAIL",
        },
        {
            "name": "canonical_payload_fields_present",
            "result": "PASS" if all(canonical_payload.values()) else "FAIL",
        },
    ]

    unsigned_payload_generated = not errors and all(
        item["result"] == "PASS" for item in validation_checks
    )
    report = {
        "generated_at": generated_at,
        "result": "PASS" if unsigned_payload_generated else "FAIL",
        "unsigned_canonical_payload_generated": unsigned_payload_generated,
        "sendable": False,
        "errors": errors,
        "inputs": {
            "production_risk_limits": str(RISK_LIMITS_CONFIG.relative_to(ROOT)),
            "production_signing_readiness": str(SIGNING_READINESS_REPORT.relative_to(ROOT)),
            "production_no_send_execution_drill": str(NO_SEND_DRILL_REPORT.relative_to(ROOT)),
        },
        "validation_checks": validation_checks,
        "canonical_payload": canonical_payload,
        "canonical_payload_json": canonical_payload_json,
        "omitted_by_design": [
            "api_key",
            "api_secret",
            "key_id",
            "signature",
            "authorization_header",
            "timestamp_signature_material",
            "network_endpoint_probe",
        ],
        "boundary": {
            "secret_read": "NO",
            "secret_value_disclosed": "NO",
            "production_signing_executed": "NO",
            "authorization_header_generated": "NO",
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
    return report, 0 if report["result"] == "PASS" else 1


def markdown(report: dict[str, Any]) -> str:
    errors = "\n".join(f"- {item}" for item in report["errors"]) or "- none"
    checks = "\n".join(
        "- {name}: {result}".format(**item) for item in report["validation_checks"]
    )
    payload = "\n".join(
        f"- {key}: {value}" for key, value in report["canonical_payload"].items()
    )
    omitted = "\n".join(f"- {item}" for item in report["omitted_by_design"])
    return f"""# Production Unsigned Canonical Payload Dry Run

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- unsigned canonical payload generated: {str(report["unsigned_canonical_payload_generated"]).lower()}
- sendable: {str(report["sendable"]).lower()}

## Validation Checks

{checks}

## Canonical Payload

{payload}

## Canonical Payload JSON

```json
{report["canonical_payload_json"]}
```

## Omitted By Design

{omitted}

## Errors

{errors}

## Boundary

- secret read: {report["boundary"]["secret_read"]}
- secret value disclosed: {report["boundary"]["secret_value_disclosed"]}
- production signing executed: {report["boundary"]["production_signing_executed"]}
- Authorization header generated: {report["boundary"]["authorization_header_generated"]}
- DNS lookup performed: {report["boundary"]["dns_lookup_performed"]}
- socket opened: {report["boundary"]["socket_opened"]}
- production HTTP/network executed: {report["boundary"]["production_http_network_executed"]}
- production request sent: {report["boundary"]["production_request_sent"]}
- canary rerun: {report["boundary"]["canary_rerun"]}
- runtime modified: {report["boundary"]["runtime_modified"]}
- go-live: {report["boundary"]["go_live"]}
- live trading: {report["boundary"]["live_trading"]}
"""


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report, exit_code = build_report()
    JSON_OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(markdown(report), encoding="utf-8")

    print("[Production Unsigned Canonical Payload Dry Run]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(
        "unsigned_canonical_payload_generated: "
        f"{str(report['unsigned_canonical_payload_generated']).lower()}"
    )
    print(f"sendable: {str(report['sendable']).lower()}")
    print("secret_read: NO")
    print("production_signing_executed: NO")
    print("authorization_header_generated: NO")
    print("dns_lookup_performed: NO")
    print("socket_opened: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
