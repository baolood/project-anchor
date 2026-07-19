#!/usr/bin/env python3
"""Read-only production execution authorization dry gate.

This check answers one operational question: with all non-secret production
readiness evidence present, is production execution authorized right now?

It intentionally reads only repository reports/config, performs no DNS lookup,
opens no sockets, reads no credentials/env files, and sends no requests.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
READINESS_REPORT = REPORTS_DIR / "production_execution_readiness.json"
JSON_OUT = REPORTS_DIR / "production_execution_authorization_dry_gate.json"
MD_OUT = REPORTS_DIR / "production_execution_authorization_dry_gate.md"

REQUIRED_READINESS = {
    "risk_limits_validation": "PASS",
    "production_credential_readiness": "PASS",
    "production_signing_readiness": "PASS",
    "production_http_network_readiness": "PASS",
}

REQUIRED_EXECUTION_GATES = {
    "production_credential_access": "YES",
    "production_signing": "YES",
    "production_http_network": "YES",
    "go_live": "YES",
    "live_trading": "YES",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - dry gate should fail closed with evidence.
        return None, f"{path.relative_to(ROOT)}:UNREADABLE:{type(exc).__name__}"
    if not isinstance(data, dict):
        return None, f"{path.relative_to(ROOT)}:NOT_OBJECT"
    return data, None


def normalized(value: Any) -> str:
    return str(value or "").strip().upper()


def build_report() -> tuple[dict[str, Any], int]:
    readiness, readiness_error = read_json(READINESS_REPORT)
    errors: list[str] = []
    if readiness_error:
        errors.append(readiness_error)
    readiness = readiness or {}

    evidence = readiness.get("evidence") if isinstance(readiness.get("evidence"), dict) else {}
    gates = readiness.get("gates") if isinstance(readiness.get("gates"), dict) else {}
    blockers = readiness.get("blockers") if isinstance(readiness.get("blockers"), list) else []

    readiness_checks = []
    for key, expected in REQUIRED_READINESS.items():
        actual = normalized(evidence.get(key))
        readiness_checks.append(
            {
                "name": key,
                "expected": expected,
                "actual": actual or "MISSING",
                "result": "PASS" if actual == expected else "FAIL",
            }
        )

    execution_gate_checks = []
    for key, expected in REQUIRED_EXECUTION_GATES.items():
        actual = normalized(gates.get(key))
        execution_gate_checks.append(
            {
                "name": key,
                "required_for_execution": expected,
                "actual": actual or "MISSING",
                "authorized": actual == expected,
            }
        )

    readiness_all_pass = all(item["result"] == "PASS" for item in readiness_checks)
    execution_gates_all_authorized = all(item["authorized"] for item in execution_gate_checks)
    authorized_to_execute = readiness_all_pass and execution_gates_all_authorized and not errors

    result = "PASS" if not errors and readiness_all_pass and not execution_gates_all_authorized else "FAIL"
    if authorized_to_execute:
        result = "FAIL"
        errors.append("PRODUCTION_EXECUTION_AUTHORIZED_UNEXPECTEDLY")

    report = {
        "generated_at": utc_now(),
        "result": result,
        "authorized_to_execute": authorized_to_execute,
        "errors": errors,
        "inputs": {
            "production_execution_readiness": str(READINESS_REPORT.relative_to(ROOT)),
        },
        "readiness_result": readiness.get("result", "UNKNOWN"),
        "readiness_checks": readiness_checks,
        "execution_gate_checks": execution_gate_checks,
        "blockers": blockers,
        "summary": {
            "readiness_checks_passed": sum(1 for item in readiness_checks if item["result"] == "PASS"),
            "readiness_checks_total": len(readiness_checks),
            "execution_gates_authorized": sum(
                1 for item in execution_gate_checks if item["authorized"]
            ),
            "execution_gates_total": len(execution_gate_checks),
            "execution_gates_blocking": sum(
                1 for item in execution_gate_checks if not item["authorized"]
            ),
        },
        "boundary": {
            "secret_read": "NO",
            "credentials_env_config_read": "NO",
            "dns_lookup_performed": "NO",
            "socket_opened": "NO",
            "production_signing_executed": "NO",
            "production_http_network_executed": "NO",
            "production_request_sent": "NO",
            "canary_rerun": "NO",
            "runtime_modified": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    return report, 0 if result == "PASS" else 1


def markdown(report: dict[str, Any]) -> str:
    errors = "\n".join(f"- {item}" for item in report["errors"]) or "- none"
    readiness_rows = "\n".join(
        "- {name}: {result} (actual: {actual}, expected: {expected})".format(**item)
        for item in report["readiness_checks"]
    )
    gate_rows = "\n".join(
        "- {name}: authorized={authorized} (actual: {actual}, required: {required_for_execution})".format(
            **item
        )
        for item in report["execution_gate_checks"]
    )
    blockers = "\n".join(f"- {item}" for item in report["blockers"]) or "- none"
    return f"""# Production Execution Authorization Dry Gate

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- authorized to execute: {str(report["authorized_to_execute"]).lower()}
- readiness result: {report["readiness_result"]}

## Readiness Checks

{readiness_rows}

## Execution Gate Checks

{gate_rows}

## Blockers

{blockers}

## Errors

{errors}

## Boundary

- secret read: {report["boundary"]["secret_read"]}
- credentials/env/config read: {report["boundary"]["credentials_env_config_read"]}
- DNS lookup performed: {report["boundary"]["dns_lookup_performed"]}
- socket opened: {report["boundary"]["socket_opened"]}
- production signing executed: {report["boundary"]["production_signing_executed"]}
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

    print("[Production Execution Authorization Dry Gate]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(f"authorized_to_execute: {str(report['authorized_to_execute']).lower()}")
    print(
        "readiness_checks: "
        f"{report['summary']['readiness_checks_passed']}/{report['summary']['readiness_checks_total']}"
    )
    print(
        "execution_gates_blocking: "
        f"{report['summary']['execution_gates_blocking']}/{report['summary']['execution_gates_total']}"
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
