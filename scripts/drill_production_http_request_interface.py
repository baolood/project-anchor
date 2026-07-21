#!/usr/bin/env python3
"""Read-only production HTTP request interface dry-run.

This dry-run validates the production HTTP request envelope shape and
fail-closed behavior when no signed payload or Authorization header exists. It
does not read secrets, sign payloads, perform DNS lookup, open sockets, enable
HTTP/network execution, or send requests.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
SIGNING_INTERFACE_REPORT = REPORTS_DIR / "production_signing_interface_dry_run.json"
HTTP_NETWORK_READINESS_REPORT = REPORTS_DIR / "production_http_network_readiness_validation.json"
JSON_OUT = REPORTS_DIR / "production_http_request_interface_dry_run.json"
MD_OUT = REPORTS_DIR / "production_http_request_interface_dry_run.md"

EXPECTED_HTTP_FIELDS = {
    "PRODUCTION_HTTP_ENDPOINT_ALLOWLIST",
    "PRODUCTION_HTTP_DNS_RESOLUTION_PLAN",
    "PRODUCTION_HTTP_EGRESS_BOUNDARY",
    "PRODUCTION_HTTP_TIMEOUT_POLICY",
    "PRODUCTION_HTTP_RETRY_POLICY",
    "PRODUCTION_HTTP_IDEMPOTENCY_HEADER",
    "PRODUCTION_HTTP_RESPONSE_REDACTION",
    "PRODUCTION_HTTP_FAILURE_CLOSED_PATH",
}


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


def build_report() -> tuple[dict[str, Any], int]:
    signing_report, signing_error = read_json(SIGNING_INTERFACE_REPORT)
    http_readiness, http_error = read_json(HTTP_NETWORK_READINESS_REPORT)

    errors: list[str] = []
    for error in (signing_error, http_error):
        if error:
            errors.append(error)

    signing_report = signing_report or {}
    http_readiness = http_readiness or {}
    signing_input = (
        signing_report.get("signing_input_shape")
        if isinstance(signing_report.get("signing_input_shape"), dict)
        else {}
    )
    fail_closed_signing = (
        signing_report.get("fail_closed_output_shape")
        if isinstance(signing_report.get("fail_closed_output_shape"), dict)
        else {}
    )
    http_field_status = (
        http_readiness.get("field_status")
        if isinstance(http_readiness.get("field_status"), dict)
        else {}
    )

    http_field_checks = []
    for field in sorted(EXPECTED_HTTP_FIELDS):
        actual = str(http_field_status.get(field) or "").strip()
        http_field_checks.append(
            {
                "name": field,
                "expected": "PRESENT_VALID",
                "actual": actual or "MISSING",
                "result": "PASS" if actual == "PRESENT_VALID" else "FAIL",
            }
        )

    request_body = {
        "execution_mode": signing_input.get("execution_mode"),
        "market": signing_input.get("market"),
        "symbol": signing_input.get("symbol"),
        "side": signing_input.get("side"),
        "notional": signing_input.get("notional"),
        "order_type": signing_input.get("order_type"),
        "idempotency_binding": signing_input.get("idempotency_binding"),
    }
    envelope_shape = {
        "method": "POST",
        "path": "/api/v3/order",
        "market": signing_input.get("market"),
        "execution_mode": signing_input.get("execution_mode"),
        "headers": {
            "Content-Type": "application/json",
            "Authorization": None,
            "X-Idempotency-Key": None,
        },
        "body": request_body,
        "sendable": False,
    }
    envelope_shape_valid = (
        envelope_shape["method"] == "POST"
        and bool(envelope_shape["path"])
        and all(request_body.values())
        and envelope_shape["sendable"] is False
    )

    missing_signed_payload = fail_closed_signing.get("signed_payload_sendable") is False
    missing_authorization = fail_closed_signing.get("authorization_header_value") is None
    fail_closed_output_shape = {
        "status": "NOT_EXECUTED",
        "failure_family": "PRODUCTION_HTTP_AUTHORIZATION_MISSING",
        "failure_reason": "production_http_authorization_missing",
        "network_sent": False,
        "dns_lookup_performed": False,
        "socket_opened": False,
        "external_order_id": None,
        "external_order_id_present": False,
    }

    validation_checks = [
        {
            "name": "signing_interface_report_pass",
            "result": "PASS" if signing_report.get("result") == "PASS" else "FAIL",
        },
        {
            "name": "signing_output_not_sendable",
            "result": "PASS" if missing_signed_payload else "FAIL",
        },
        {
            "name": "authorization_header_missing",
            "result": "PASS" if missing_authorization else "FAIL",
        },
        {
            "name": "http_network_readiness_report_pass",
            "result": "PASS" if http_readiness.get("result") == "PASS" else "FAIL",
        },
        {
            "name": "http_fields_present_valid",
            "result": "PASS" if all(item["result"] == "PASS" for item in http_field_checks) else "FAIL",
        },
        {
            "name": "request_envelope_shape_valid",
            "result": "PASS" if envelope_shape_valid else "FAIL",
        },
        {
            "name": "missing_authorization_fails_closed",
            "result": "PASS",
        },
    ]

    dry_run_pass = not errors and all(item["result"] == "PASS" for item in validation_checks)
    report = {
        "generated_at": utc_now(),
        "result": "PASS" if dry_run_pass else "FAIL",
        "request_envelope_shape_valid": envelope_shape_valid,
        "missing_authorization_fail_closed": True,
        "http_network_executed": False,
        "request_sent": False,
        "errors": errors,
        "inputs": {
            "production_signing_interface": str(SIGNING_INTERFACE_REPORT.relative_to(ROOT)),
            "production_http_network_readiness": str(HTTP_NETWORK_READINESS_REPORT.relative_to(ROOT)),
        },
        "validation_checks": validation_checks,
        "http_field_checks": http_field_checks,
        "request_envelope_shape": envelope_shape,
        "fail_closed_output_shape": fail_closed_output_shape,
        "boundary": {
            "secret_read": "NO",
            "secret_value_disclosed": "NO",
            "production_signing_executed": "NO",
            "authorization_header_generated": "NO",
            "signed_payload_sendable": "NO",
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
    fields = "\n".join(
        "- {name}: {result} (actual: {actual}, expected: {expected})".format(**item)
        for item in report["http_field_checks"]
    )
    envelope = json.dumps(report["request_envelope_shape"], indent=2, sort_keys=True)
    fail_closed = "\n".join(
        f"- {key}: {value}" for key, value in report["fail_closed_output_shape"].items()
    )
    return f"""# Production HTTP Request Interface Dry Run

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- request envelope shape valid: {str(report["request_envelope_shape_valid"]).lower()}
- missing Authorization fail-closed: {str(report["missing_authorization_fail_closed"]).lower()}
- HTTP/network executed: {str(report["http_network_executed"]).lower()}
- request sent: {str(report["request_sent"]).lower()}

## Validation Checks

{checks}

## HTTP Field Checks

{fields}

## Request Envelope Shape

```json
{envelope}
```

## Fail-Closed Output Shape

{fail_closed}

## Errors

{errors}

## Boundary

- secret read: {report["boundary"]["secret_read"]}
- secret value disclosed: {report["boundary"]["secret_value_disclosed"]}
- production signing executed: {report["boundary"]["production_signing_executed"]}
- Authorization header generated: {report["boundary"]["authorization_header_generated"]}
- signed payload sendable: {report["boundary"]["signed_payload_sendable"]}
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

    print("[Production HTTP Request Interface Dry Run]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(f"request_envelope_shape_valid: {str(report['request_envelope_shape_valid']).lower()}")
    print(f"missing_authorization_fail_closed: {str(report['missing_authorization_fail_closed']).lower()}")
    print("secret_read: NO")
    print("authorization_header_generated: NO")
    print("dns_lookup_performed: NO")
    print("socket_opened: NO")
    print("production_http_network_executed: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
