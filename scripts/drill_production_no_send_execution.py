#!/usr/bin/env python3
"""Read-only production no-send execution drill.

This drill validates the production execution authorization path without
entering any execution stage. It reads only repository config/report evidence,
does not read credentials or env files, does not sign payloads, performs no DNS
lookup, opens no sockets, and sends no production request.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
RISK_LIMITS_CONFIG = ROOT / "config" / "production_risk_limits.template.json"
AUTHORIZATION_DRY_GATE_REPORT = REPORTS_DIR / "production_execution_authorization_dry_gate.json"
JSON_OUT = REPORTS_DIR / "production_no_send_execution_drill.json"
MD_OUT = REPORTS_DIR / "production_no_send_execution_drill.md"

EXPECTED_RISK_LIMITS = {
    "AUTHORIZED_PRODUCTION_MARKET": "binance_spot",
    "AUTHORIZED_PRODUCTION_SYMBOLS": "BTCUSDT",
    "AUTHORIZED_PRODUCTION_SIDES": "BUY_ONLY",
    "AUTHORIZED_MAX_NOTIONAL": "4",
    "AUTHORIZED_MAX_ORDER_COUNT": "1",
}

EXPECTED_NO_SEND_BOUNDARY = {
    "AUTHORIZED_PRODUCTION_CREDENTIAL_ACCESS": "NO",
    "AUTHORIZED_PRODUCTION_SIGNING": "NO",
    "AUTHORIZED_PRODUCTION_HTTP_NETWORK": "NO",
    "AUTHORIZED_GO_LIVE": "NO",
    "AUTHORIZED_LIVE_TRADING": "NO",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - drills should fail closed with evidence.
        return None, f"{path.relative_to(ROOT)}:UNREADABLE:{type(exc).__name__}"
    if not isinstance(data, dict):
        return None, f"{path.relative_to(ROOT)}:NOT_OBJECT"
    return data, None


def normalized(value: Any) -> str:
    return str(value or "").strip()


def build_report() -> tuple[dict[str, Any], int]:
    config, config_error = read_json(RISK_LIMITS_CONFIG)
    dry_gate, dry_gate_error = read_json(AUTHORIZATION_DRY_GATE_REPORT)

    errors: list[str] = []
    if config_error:
        errors.append(config_error)
    if dry_gate_error:
        errors.append(dry_gate_error)

    config = config or {}
    dry_gate = dry_gate or {}

    risk_limit_checks = []
    for key, expected in EXPECTED_RISK_LIMITS.items():
        actual = normalized(config.get(key))
        risk_limit_checks.append(
            {
                "name": key,
                "expected": expected,
                "actual": actual or "MISSING",
                "result": "PASS" if actual == expected else "FAIL",
            }
        )

    no_send_boundary_checks = []
    for key, expected in EXPECTED_NO_SEND_BOUNDARY.items():
        actual = normalized(config.get(key)).upper()
        no_send_boundary_checks.append(
            {
                "name": key,
                "expected": expected,
                "actual": actual or "MISSING",
                "result": "PASS" if actual == expected else "FAIL",
            }
        )

    dry_gate_pass = dry_gate.get("result") == "PASS"
    authorized_to_execute = bool(dry_gate.get("authorized_to_execute"))
    dry_gate_summary = dry_gate.get("summary") if isinstance(dry_gate.get("summary"), dict) else {}
    readiness_checks_passed = dry_gate_summary.get("readiness_checks_passed")
    readiness_checks_total = dry_gate_summary.get("readiness_checks_total")
    execution_gates_blocking = dry_gate_summary.get("execution_gates_blocking")
    execution_gates_total = dry_gate_summary.get("execution_gates_total")

    drill_steps = [
        {
            "step": "load_non_secret_risk_limits",
            "result": "PASS" if all(item["result"] == "PASS" for item in risk_limit_checks) else "FAIL",
        },
        {
            "step": "load_authorization_dry_gate",
            "result": "PASS" if dry_gate_pass else "FAIL",
        },
        {
            "step": "confirm_readiness_evidence",
            "result": "PASS" if readiness_checks_passed == readiness_checks_total == 4 else "FAIL",
        },
        {
            "step": "confirm_execution_authorization_absent",
            "result": "PASS" if authorized_to_execute is False else "FAIL",
        },
        {
            "step": "stop_before_credentials_signing_network",
            "result": "PASS"
            if all(item["result"] == "PASS" for item in no_send_boundary_checks)
            else "FAIL",
        },
    ]

    no_send_path_pass = (
        not errors
        and all(item["result"] == "PASS" for item in risk_limit_checks)
        and all(item["result"] == "PASS" for item in no_send_boundary_checks)
        and dry_gate_pass
        and authorized_to_execute is False
        and readiness_checks_passed == readiness_checks_total == 4
        and execution_gates_blocking == execution_gates_total == 5
    )

    report = {
        "generated_at": utc_now(),
        "result": "PASS" if no_send_path_pass else "FAIL",
        "no_send_path_verified": no_send_path_pass,
        "authorized_to_execute": authorized_to_execute,
        "errors": errors,
        "inputs": {
            "production_risk_limits": str(RISK_LIMITS_CONFIG.relative_to(ROOT)),
            "production_execution_authorization_dry_gate": str(
                AUTHORIZATION_DRY_GATE_REPORT.relative_to(ROOT)
            ),
        },
        "risk_limit_checks": risk_limit_checks,
        "no_send_boundary_checks": no_send_boundary_checks,
        "dry_gate_summary": {
            "result": dry_gate.get("result", "UNKNOWN"),
            "readiness_checks_passed": readiness_checks_passed,
            "readiness_checks_total": readiness_checks_total,
            "execution_gates_blocking": execution_gates_blocking,
            "execution_gates_total": execution_gates_total,
        },
        "drill_steps": drill_steps,
        "boundary": {
            "secret_read": "NO",
            "credentials_env_config_read": "NO",
            "production_credential_accessed": "NO",
            "production_signing_executed": "NO",
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
    risk_rows = "\n".join(
        "- {name}: {result} (actual: {actual}, expected: {expected})".format(**item)
        for item in report["risk_limit_checks"]
    )
    boundary_rows = "\n".join(
        "- {name}: {result} (actual: {actual}, expected: {expected})".format(**item)
        for item in report["no_send_boundary_checks"]
    )
    step_rows = "\n".join(
        "- {step}: {result}".format(**item) for item in report["drill_steps"]
    )
    dry = report["dry_gate_summary"]
    return f"""# Production No-Send Execution Drill

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- no-send path verified: {str(report["no_send_path_verified"]).lower()}
- authorized to execute: {str(report["authorized_to_execute"]).lower()}

## Drill Steps

{step_rows}

## Risk Limit Checks

{risk_rows}

## No-Send Boundary Checks

{boundary_rows}

## Authorization Dry Gate Summary

- result: {dry.get("result")}
- readiness checks: {dry.get("readiness_checks_passed")}/{dry.get("readiness_checks_total")}
- execution gates blocking: {dry.get("execution_gates_blocking")}/{dry.get("execution_gates_total")}

## Errors

{errors}

## Boundary

- secret read: {report["boundary"]["secret_read"]}
- credentials/env/config read: {report["boundary"]["credentials_env_config_read"]}
- production credential accessed: {report["boundary"]["production_credential_accessed"]}
- production signing executed: {report["boundary"]["production_signing_executed"]}
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

    print("[Production No-Send Execution Drill]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(f"no_send_path_verified: {str(report['no_send_path_verified']).lower()}")
    print(f"authorized_to_execute: {str(report['authorized_to_execute']).lower()}")
    print(
        "readiness_checks: "
        f"{report['dry_gate_summary']['readiness_checks_passed']}/"
        f"{report['dry_gate_summary']['readiness_checks_total']}"
    )
    print(
        "execution_gates_blocking: "
        f"{report['dry_gate_summary']['execution_gates_blocking']}/"
        f"{report['dry_gate_summary']['execution_gates_total']}"
    )
    print("secret_read: NO")
    print("dns_lookup_performed: NO")
    print("socket_opened: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
