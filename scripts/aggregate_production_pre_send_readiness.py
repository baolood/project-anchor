#!/usr/bin/env python3
"""Aggregate production pre-send readiness evidence without executing anything.

This script reads existing non-secret reports and answers one bounded question:
is the production pre-send evidence chain complete enough to discuss the next
authorization gate? It does not read secrets, sign payloads, resolve DNS, open
sockets, enable HTTP/network execution, or send requests.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "production_pre_send_readiness_aggregation.json"
MD_OUT = REPORTS_DIR / "production_pre_send_readiness_aggregation.md"

INPUT_REPORTS = {
    "risk_limits": REPORTS_DIR / "production_risk_limits_validation.json",
    "credential_readiness": REPORTS_DIR / "production_credential_readiness_validation.json",
    "signing_readiness": REPORTS_DIR / "production_signing_readiness_validation.json",
    "http_network_readiness": REPORTS_DIR / "production_http_network_readiness_validation.json",
    "execution_readiness": REPORTS_DIR / "production_execution_readiness.json",
    "no_send_execution_drill": REPORTS_DIR / "production_no_send_execution_drill.json",
    "unsigned_canonical_payload_dry_run": REPORTS_DIR
    / "production_unsigned_canonical_payload_dry_run.json",
    "signing_interface_dry_run": REPORTS_DIR / "production_signing_interface_dry_run.json",
    "http_request_interface_dry_run": REPORTS_DIR
    / "production_http_request_interface_dry_run.json",
    "production_request_send_gate": REPORTS_DIR / "production_request_send_gate.json",
    "production_send_decision_entrypoint": REPORTS_DIR
    / "production_send_decision_entrypoint.json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - read-only aggregation should fail closed.
        return {}, f"{path.relative_to(ROOT)}:UNREADABLE:{type(exc).__name__}"
    if not isinstance(data, dict):
        return {}, f"{path.relative_to(ROOT)}:NOT_OBJECT"
    return data, None


def check(name: str, passed: bool, evidence: str) -> dict[str, str]:
    return {
        "name": name,
        "result": "PASS" if passed else "FAIL",
        "evidence": evidence,
    }


def boundary_is_clean(report: dict[str, Any], expected: dict[str, str]) -> bool:
    boundary = report.get("boundary")
    if not isinstance(boundary, dict):
        return False
    return all(boundary.get(key) == value for key, value in expected.items())


def build_report() -> tuple[dict[str, Any], int]:
    reports: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for name, path in INPUT_REPORTS.items():
        data, error = read_json(path)
        reports[name] = data
        if error:
            errors.append(error)

    risk_limits = reports["risk_limits"]
    credential = reports["credential_readiness"]
    signing = reports["signing_readiness"]
    http_network = reports["http_network_readiness"]
    execution = reports["execution_readiness"]
    no_send = reports["no_send_execution_drill"]
    unsigned_payload = reports["unsigned_canonical_payload_dry_run"]
    signing_interface = reports["signing_interface_dry_run"]
    http_request = reports["http_request_interface_dry_run"]
    request_send_gate = reports["production_request_send_gate"]
    send_decision_entrypoint = reports["production_send_decision_entrypoint"]

    evidence_checks = [
        check("risk_limits_validation_pass", risk_limits.get("result") == "PASS", "risk limits PASS"),
        check(
            "credential_readiness_pass",
            credential.get("result") == "PASS",
            "non-secret production credential readiness PASS",
        ),
        check("signing_readiness_pass", signing.get("result") == "PASS", "signing readiness PASS"),
        check(
            "http_network_readiness_pass",
            http_network.get("result") == "PASS",
            "HTTP/network readiness PASS without execution",
        ),
        check(
            "execution_readiness_blocked",
            execution.get("result") == "BLOCKED",
            "execution readiness remains BLOCKED",
        ),
        check(
            "no_send_execution_drill_pass",
            no_send.get("result") == "PASS" and no_send.get("no_send_path_verified") is True,
            "no-send execution path verified",
        ),
        check(
            "unsigned_payload_dry_run_pass",
            unsigned_payload.get("result") == "PASS"
            and unsigned_payload.get("unsigned_canonical_payload_generated") is True
            and unsigned_payload.get("sendable") is False,
            "unsigned canonical payload generated but not sendable",
        ),
        check(
            "signing_interface_dry_run_pass",
            signing_interface.get("result") == "PASS"
            and signing_interface.get("signing_interface_shape_valid") is True
            and signing_interface.get("missing_secret_fail_closed") is True
            and signing_interface.get("authorization_header_generated") is False
            and signing_interface.get("signed_payload_sendable") is False,
            "signing interface shape valid and missing secret fails closed",
        ),
        check(
            "http_request_interface_dry_run_pass",
            http_request.get("result") == "PASS"
            and http_request.get("request_envelope_shape_valid") is True
            and http_request.get("missing_authorization_fail_closed") is True
            and http_request.get("http_network_executed") is False
            and http_request.get("request_sent") is False,
            "HTTP request envelope valid and missing Authorization fails closed",
        ),
        check(
            "production_request_send_gate_pass",
            request_send_gate.get("result") == "PASS"
            and request_send_gate.get("current_template_authorized") is False
            and request_send_gate.get("fixture_authorized") is True,
            "request-send gate exists, defaults closed, and fixture can authorize exactly-one send",
        ),
        check(
            "production_send_decision_entrypoint_pass",
            send_decision_entrypoint.get("result") == "PASS"
            and send_decision_entrypoint.get("current_template_ready_for_exactly_one_send")
            is False
            and send_decision_entrypoint.get("authorized_fixture_ready_for_exactly_one_send")
            is True,
            "send decision surface is wired to gate without sending",
        ),
    ]

    boundary_checks = [
        check(
            "risk_limits_boundary_clean",
            boundary_is_clean(
                risk_limits,
                {
                    "secret_read": "NO",
                    "production_signing_enabled": "NO",
                    "production_http_network_enabled": "NO",
                    "production_request_sent": "NO",
                    "go_live": "NO-GO",
                    "live_trading": "NO-GO",
                },
            ),
            "risk limits did not execute production behavior",
        ),
        check(
            "credential_boundary_clean",
            boundary_is_clean(
                credential,
                {
                    "secret_value_read": "NO",
                    "secret_value_disclosed": "NO",
                    "production_request_sent": "NO",
                    "go_live": "NO-GO",
                    "live_trading": "NO-GO",
                },
            ),
            "credential readiness did not read or disclose secret values",
        ),
        check(
            "signing_interface_boundary_clean",
            boundary_is_clean(
                signing_interface,
                {
                    "secret_read": "NO",
                    "secret_value_disclosed": "NO",
                    "production_signing_executed": "NO",
                    "authorization_header_generated": "NO",
                    "production_request_sent": "NO",
                    "go_live": "NO-GO",
                    "live_trading": "NO-GO",
                },
            ),
            "signing interface stayed non-executing",
        ),
        check(
            "http_request_boundary_clean",
            boundary_is_clean(
                http_request,
                {
                    "secret_read": "NO",
                    "secret_value_disclosed": "NO",
                    "authorization_header_generated": "NO",
                    "dns_lookup_performed": "NO",
                    "socket_opened": "NO",
                    "production_http_network_executed": "NO",
                    "production_request_sent": "NO",
                    "go_live": "NO-GO",
                    "live_trading": "NO-GO",
                },
            ),
            "HTTP request interface stayed offline and unsent",
        ),
    ]

    all_checks = evidence_checks + boundary_checks
    evidence_chain_complete = not errors and all(item["result"] == "PASS" for item in all_checks)
    request_send_authorized = False
    go_live_allowed = False
    live_trading_allowed = False
    next_gate = (
        "READY_FOR_EXPLICIT_PRODUCTION_REQUEST_SEND_AUTHORIZATION_DECISION"
        if evidence_chain_complete
        else "BLOCKED_PRODUCTION_PRE_SEND_EVIDENCE_INCOMPLETE"
    )

    report = {
        "generated_at": utc_now(),
        "result": "PASS" if evidence_chain_complete else "FAIL",
        "evidence_chain_complete": evidence_chain_complete,
        "request_send_authorized": request_send_authorized,
        "go_live_allowed": go_live_allowed,
        "live_trading_allowed": live_trading_allowed,
        "next_gate": next_gate,
        "errors": errors,
        "inputs": {name: str(path.relative_to(ROOT)) for name, path in INPUT_REPORTS.items()},
        "evidence_checks": evidence_checks,
        "boundary_checks": boundary_checks,
        "decision_summary": {
            "production_risk_limits": risk_limits.get("result"),
            "production_credential_readiness": credential.get("result"),
            "production_signing_readiness": signing.get("result"),
            "production_http_network_readiness": http_network.get("result"),
            "production_execution_readiness": execution.get("result"),
            "production_no_send_execution_drill": no_send.get("result"),
            "production_unsigned_canonical_payload_dry_run": unsigned_payload.get("result"),
            "production_signing_interface_dry_run": signing_interface.get("result"),
            "production_http_request_interface_dry_run": http_request.get("result"),
            "production_request_send_gate": request_send_gate.get("result"),
            "production_send_decision_entrypoint": send_decision_entrypoint.get("result"),
        },
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
    evidence_checks = "\n".join(
        "- {name}: {result} ({evidence})".format(**item) for item in report["evidence_checks"]
    )
    boundary_checks = "\n".join(
        "- {name}: {result} ({evidence})".format(**item) for item in report["boundary_checks"]
    )
    summary = "\n".join(
        f"- {key}: {value}" for key, value in report["decision_summary"].items()
    )
    return f"""# Production Pre-Send Readiness Aggregation

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- evidence chain complete: {str(report["evidence_chain_complete"]).lower()}
- request send authorized: {str(report["request_send_authorized"]).lower()}
- go-live allowed: {str(report["go_live_allowed"]).lower()}
- live trading allowed: {str(report["live_trading_allowed"]).lower()}
- next gate: {report["next_gate"]}

## Decision Summary

{summary}

## Evidence Checks

{evidence_checks}

## Boundary Checks

{boundary_checks}

## Errors

{errors}

## Locked Boundary

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

    print("[Production Pre-Send Readiness Aggregation]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(f"evidence_chain_complete: {str(report['evidence_chain_complete']).lower()}")
    print(f"request_send_authorized: {str(report['request_send_authorized']).lower()}")
    print(f"next_gate: {report['next_gate']}")
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
