#!/usr/bin/env python3
"""Read-only drill for production execution hard gates.

The drill verifies that the current non-secret production execution readiness
evidence still blocks production execution for every required hard gate. It
does not read credentials, env files, runtime services, or external networks.
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
JSON_OUT = REPORTS_DIR / "production_execution_hard_gate_drill.json"
MD_OUT = REPORTS_DIR / "production_execution_hard_gate_drill.md"

EXPECTED_GATES = {
    "production_credential_access": {
        "expected_value": "NO",
        "expected_blocker": "production credential access not authorized",
    },
    "production_signing": {
        "expected_value": "NO",
        "expected_blocker": "production signing not authorized",
    },
    "production_http_network": {
        "expected_value": "NO",
        "expected_blocker": "production HTTP/network not authorized",
    },
    "go_live": {
        "expected_value": "NO",
        "expected_blocker": "go-live not authorized",
    },
    "live_trading": {
        "expected_value": "NO",
        "expected_blocker": "live trading not authorized",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - drill should report blocked evidence cleanly.
        return None, f"{path.relative_to(ROOT)}:UNREADABLE:{type(exc).__name__}"
    if not isinstance(data, dict):
        return None, f"{path.relative_to(ROOT)}:NOT_OBJECT"
    return data, None


def check_gate(name: str, readiness: dict[str, Any]) -> dict[str, Any]:
    expectation = EXPECTED_GATES[name]
    gates = readiness.get("gates") if isinstance(readiness.get("gates"), dict) else {}
    blockers = readiness.get("blockers") if isinstance(readiness.get("blockers"), list) else []
    actual_value = str(gates.get(name, "")).strip().upper()
    expected_value = expectation["expected_value"]
    expected_blocker = expectation["expected_blocker"]
    blocker_present = expected_blocker in blockers
    passed = actual_value == expected_value and blocker_present
    return {
        "gate": name,
        "expected_value": expected_value,
        "actual_value": actual_value or "MISSING",
        "expected_blocker": expected_blocker,
        "blocker_present": blocker_present,
        "result": "PASS" if passed else "FAIL",
    }


def build_report() -> tuple[dict[str, Any], int]:
    readiness, readiness_error = read_json(READINESS_REPORT)
    errors: list[str] = []
    if readiness_error:
        errors.append(readiness_error)
    readiness = readiness or {}

    gate_checks = [check_gate(name, readiness) for name in EXPECTED_GATES]
    readiness_result = readiness.get("result", "UNKNOWN")
    readiness_blocks_execution = readiness_result == "BLOCKED"
    all_gates_block = all(item["result"] == "PASS" for item in gate_checks)
    result = "PASS" if not errors and readiness_blocks_execution and all_gates_block else "FAIL"

    report = {
        "generated_at": utc_now(),
        "result": result,
        "errors": errors,
        "inputs": {
            "production_execution_readiness": str(READINESS_REPORT.relative_to(ROOT)),
        },
        "readiness_result": readiness_result,
        "readiness_blocks_execution": readiness_blocks_execution,
        "gate_checks": gate_checks,
        "summary": {
            "total_hard_gates": len(gate_checks),
            "hard_gates_blocking_as_expected": sum(1 for item in gate_checks if item["result"] == "PASS"),
            "hard_gate_failures": [item["gate"] for item in gate_checks if item["result"] != "PASS"],
        },
        "boundary": {
            "secret_read": "NO",
            "credentials_env_config_read": "NO",
            "production_signing_enabled": "NO",
            "production_http_network_enabled": "NO",
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
    gate_rows = "\n".join(
        "- {gate}: {result} (value {actual_value}, blocker present: {blocker_present})".format(**item)
        for item in report["gate_checks"]
    )
    failures = "\n".join(f"- {item}" for item in report["summary"]["hard_gate_failures"]) or "- none"
    return f"""# Production Execution Hard-Gate Drill

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- readiness result: {report["readiness_result"]}
- readiness blocks execution: {report["readiness_blocks_execution"]}

## Gate Checks

{gate_rows}

## Failures

{failures}

## Errors

{errors}

## Boundary

- secret read: {report["boundary"]["secret_read"]}
- credentials/env/config read: {report["boundary"]["credentials_env_config_read"]}
- production signing enabled: {report["boundary"]["production_signing_enabled"]}
- production HTTP/network enabled: {report["boundary"]["production_http_network_enabled"]}
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

    print("[Production Execution Hard-Gate Drill]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(f"readiness_result: {report['readiness_result']}")
    print(f"hard_gates_blocking_as_expected: {report['summary']['hard_gates_blocking_as_expected']}")
    print(f"hard_gate_failures: {len(report['summary']['hard_gate_failures'])}")
    print("secret_read: NO")
    print("production_request_sent: NO")
    print("canary_rerun: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
