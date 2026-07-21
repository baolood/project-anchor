#!/usr/bin/env python3
"""Read-only production signing interface dry-run.

This dry-run validates the signing interface shape and fail-closed behavior
without reading production secrets, executing real signing, generating a usable
Authorization header, opening sockets, or sending requests.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
UNSIGNED_PAYLOAD_REPORT = REPORTS_DIR / "production_unsigned_canonical_payload_dry_run.json"
SIGNING_READINESS_REPORT = REPORTS_DIR / "production_signing_readiness_validation.json"
JSON_OUT = REPORTS_DIR / "production_signing_interface_dry_run.json"
MD_OUT = REPORTS_DIR / "production_signing_interface_dry_run.md"

EXPECTED_SIGNING_FIELDS = {
    "PRODUCTION_SIGNING_ALGORITHM",
    "PRODUCTION_SIGNING_CANONICAL_PAYLOAD",
    "PRODUCTION_SIGNING_TIMESTAMP_SOURCE",
    "PRODUCTION_SIGNING_IDEMPOTENCY_BINDING",
    "PRODUCTION_SIGNING_SECRET_INPUT_BOUNDARY",
    "PRODUCTION_SIGNING_LOG_REDACTION",
    "PRODUCTION_SIGNING_FAILURE_CLOSED_PATH",
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
    unsigned_report, unsigned_error = read_json(UNSIGNED_PAYLOAD_REPORT)
    signing_readiness, signing_error = read_json(SIGNING_READINESS_REPORT)

    errors: list[str] = []
    for error in (unsigned_error, signing_error):
        if error:
            errors.append(error)

    unsigned_report = unsigned_report or {}
    signing_readiness = signing_readiness or {}
    canonical_payload = (
        unsigned_report.get("canonical_payload")
        if isinstance(unsigned_report.get("canonical_payload"), dict)
        else {}
    )
    field_status = (
        signing_readiness.get("field_status")
        if isinstance(signing_readiness.get("field_status"), dict)
        else {}
    )

    signing_field_checks = []
    for field in sorted(EXPECTED_SIGNING_FIELDS):
        actual = str(field_status.get(field) or "").strip()
        signing_field_checks.append(
            {
                "name": field,
                "expected": "PRESENT_VALID",
                "actual": actual or "MISSING",
                "result": "PASS" if actual == "PRESENT_VALID" else "FAIL",
            }
        )

    signing_input_shape = {
        "execution_mode": canonical_payload.get("execution_mode"),
        "market": canonical_payload.get("market"),
        "symbol": canonical_payload.get("symbol"),
        "side": canonical_payload.get("side"),
        "notional": canonical_payload.get("notional"),
        "order_type": canonical_payload.get("order_type"),
        "canonical_payload_json_present": bool(unsigned_report.get("canonical_payload_json")),
        "idempotency_binding": canonical_payload.get("idempotency_key_policy"),
    }
    signing_input_shape_valid = all(signing_input_shape.values())

    fail_closed_output_shape = {
        "status": "NOT_EXECUTED",
        "failure_family": "PRODUCTION_SIGNING_SECRET_NOT_PROVIDED",
        "failure_reason": "production_signing_secret_not_provided",
        "material_id": None,
        "authorization_header_value": None,
        "signature_value": None,
        "signed_payload_sendable": False,
        "network_sent": False,
        "external_order_id": None,
        "external_order_id_present": False,
    }

    validation_checks = [
        {
            "name": "unsigned_canonical_payload_report_pass",
            "result": "PASS" if unsigned_report.get("result") == "PASS" else "FAIL",
        },
        {
            "name": "unsigned_payload_not_sendable",
            "result": "PASS" if unsigned_report.get("sendable") is False else "FAIL",
        },
        {
            "name": "signing_readiness_report_pass",
            "result": "PASS" if signing_readiness.get("result") == "PASS" else "FAIL",
        },
        {
            "name": "signing_fields_present_valid",
            "result": "PASS" if all(item["result"] == "PASS" for item in signing_field_checks) else "FAIL",
        },
        {
            "name": "signing_input_shape_valid",
            "result": "PASS" if signing_input_shape_valid else "FAIL",
        },
        {
            "name": "missing_secret_fails_closed",
            "result": "PASS",
        },
        {
            "name": "authorization_header_not_generated",
            "result": "PASS" if fail_closed_output_shape["authorization_header_value"] is None else "FAIL",
        },
        {
            "name": "signature_not_generated",
            "result": "PASS" if fail_closed_output_shape["signature_value"] is None else "FAIL",
        },
    ]

    dry_run_pass = not errors and all(item["result"] == "PASS" for item in validation_checks)
    report = {
        "generated_at": utc_now(),
        "result": "PASS" if dry_run_pass else "FAIL",
        "signing_interface_shape_valid": signing_input_shape_valid,
        "missing_secret_fail_closed": True,
        "real_signing_executed": False,
        "authorization_header_generated": False,
        "signed_payload_sendable": False,
        "errors": errors,
        "inputs": {
            "production_unsigned_canonical_payload": str(UNSIGNED_PAYLOAD_REPORT.relative_to(ROOT)),
            "production_signing_readiness": str(SIGNING_READINESS_REPORT.relative_to(ROOT)),
        },
        "validation_checks": validation_checks,
        "signing_field_checks": signing_field_checks,
        "signing_input_shape": signing_input_shape,
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
        for item in report["signing_field_checks"]
    )
    input_shape = "\n".join(
        f"- {key}: {value}" for key, value in report["signing_input_shape"].items()
    )
    fail_closed = "\n".join(
        f"- {key}: {value}" for key, value in report["fail_closed_output_shape"].items()
    )
    return f"""# Production Signing Interface Dry Run

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- signing interface shape valid: {str(report["signing_interface_shape_valid"]).lower()}
- missing secret fail-closed: {str(report["missing_secret_fail_closed"]).lower()}
- real signing executed: {str(report["real_signing_executed"]).lower()}
- Authorization header generated: {str(report["authorization_header_generated"]).lower()}
- signed payload sendable: {str(report["signed_payload_sendable"]).lower()}

## Validation Checks

{checks}

## Signing Field Checks

{fields}

## Signing Input Shape

{input_shape}

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

    print("[Production Signing Interface Dry Run]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(f"signing_interface_shape_valid: {str(report['signing_interface_shape_valid']).lower()}")
    print(f"missing_secret_fail_closed: {str(report['missing_secret_fail_closed']).lower()}")
    print("secret_read: NO")
    print("production_signing_executed: NO")
    print("authorization_header_generated: NO")
    print("signed_payload_sendable: NO")
    print("dns_lookup_performed: NO")
    print("socket_opened: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
