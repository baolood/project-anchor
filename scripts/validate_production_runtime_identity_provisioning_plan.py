#!/usr/bin/env python3
"""Dry-validate the production runtime identity provisioning plan.

This script validates plan shape and target alignment only. It does not execute
the provisioning commands, create users/groups, change file ownership or mode,
read secret values, sign payloads, open sockets, or send production requests.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "config" / "production_runtime_identity_provisioning_plan.json"
CONTRACT_PATH = ROOT / "config" / "production_runtime_owner_contract.json"
CONTRACT_VALIDATION_REPORT = ROOT / "reports" / "production_runtime_owner_contract_validation.json"
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "production_runtime_identity_provisioning_plan_validation.json"
MD_OUT = REPORTS_DIR / "production_runtime_identity_provisioning_plan_validation.md"

FORBIDDEN_COMMAND_TOKENS = (
    "production_request",
    "execute_exactly_one_production_request.py --execute",
    "curl ",
    "http://",
    "https://api.binance.com",
    "openssl",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - dry validation should report cleanly.
        return {}, f"{path.relative_to(ROOT)}:UNREADABLE:{type(exc).__name__}"
    if not isinstance(data, dict):
        return {}, f"{path.relative_to(ROOT)}:NOT_OBJECT"
    return data, None


def as_text(value: Any) -> str:
    return str(value or "").strip()


def steps(plan: dict[str, Any], key: str) -> list[dict[str, Any]]:
    raw = plan.get(key)
    return raw if isinstance(raw, list) and all(isinstance(item, dict) for item in raw) else []


def command_templates_are_safe(plan: dict[str, Any]) -> bool:
    for item in steps(plan, "provisioning_steps") + steps(plan, "rollback_steps"):
        command = as_text(item.get("command_template"))
        lowered = command.lower()
        if any(token in lowered for token in FORBIDDEN_COMMAND_TOKENS):
            return False
    return True


def has_step(plan: dict[str, Any], name: str, operation: str) -> bool:
    return any(
        item.get("name") == name and item.get("operation") == operation
        for item in steps(plan, "provisioning_steps")
    )


def validate(plan: dict[str, Any], contract: dict[str, Any], contract_report: dict[str, Any]) -> dict[str, Any]:
    target_identity = as_text(plan.get("target_runtime_identity"))
    target_group = as_text(plan.get("target_runtime_group"))
    target_env_dir = as_text(plan.get("target_env_dir"))
    target_env_dir_owner = as_text(plan.get("target_env_dir_owner"))
    target_env_dir_group = as_text(plan.get("target_env_dir_group"))
    target_env_dir_mode = as_text(plan.get("target_env_dir_mode"))
    target_env_path = as_text(plan.get("target_env_path"))
    target_owner = as_text(plan.get("target_env_owner"))
    target_env_group = as_text(plan.get("target_env_group"))
    target_mode = as_text(plan.get("target_env_mode"))

    contract_identity = as_text(contract.get("runtime_identity"))
    contract_group = as_text(contract.get("runtime_group"))
    contract_env_dir = as_text(contract.get("canonical_env_dir"))
    contract_env_dir_owner = as_text(contract.get("expected_env_dir_owner"))
    contract_env_dir_group = as_text(contract.get("expected_env_dir_group"))
    contract_env_dir_mode = as_text(contract.get("expected_env_dir_mode"))
    contract_env_path = as_text(contract.get("canonical_env_path"))
    contract_owner = as_text(contract.get("expected_env_owner"))
    contract_env_group = as_text(contract.get("expected_env_group"))
    contract_mode = as_text(contract.get("expected_env_mode"))

    checks = {
        "runtime_identity_target_explicit": bool(target_identity),
        "runtime_group_target_explicit": bool(target_group),
        "env_dir_target_explicit": bool(target_env_dir),
        "env_path_target_explicit": bool(target_env_path),
        "target_identity_matches_contract": target_identity == contract_identity,
        "target_group_matches_contract": target_group == contract_group,
        "target_env_dir_matches_contract": target_env_dir == contract_env_dir,
        "target_env_dir_owner_matches_contract": target_env_dir_owner == contract_env_dir_owner,
        "target_env_dir_group_matches_contract": target_env_dir_group == contract_env_dir_group,
        "target_env_dir_mode_710": target_env_dir_mode == "710" and contract_env_dir_mode == "710",
        "target_env_path_matches_contract": target_env_path == contract_env_path,
        "target_env_owner_matches_contract": target_owner == contract_owner,
        "target_env_group_matches_contract": target_env_group == contract_env_group,
        "target_env_mode_600": target_mode == "600" and contract_mode == "600",
        "execution_authorized_no": plan.get("execution_authorized") == "NO",
        "dry_validation_only_yes": plan.get("dry_validation_only") == "YES",
        "interactive_sudo_send_no": plan.get("interactive_sudo_send") == "NO",
        "secret_value_read_no": plan.get("secret_value_read") == "NO",
        "production_request_authorized_no": plan.get("production_request_authorized") == "NO",
        "go_live_no_go": plan.get("go_live") == "NO-GO",
        "live_trading_no_go": plan.get("live_trading") == "NO-GO",
        "create_group_step_present": has_step(plan, "create_runtime_group", "create_group_if_absent"),
        "create_identity_step_present": has_step(plan, "create_runtime_identity", "create_user_if_absent"),
        "chown_step_targets_contract": has_step(plan, "align_production_env_owner", "chown")
        and f"{target_owner}:{target_env_group}" in json.dumps(steps(plan, "provisioning_steps")),
        "chmod_step_targets_600": has_step(plan, "enforce_production_env_mode", "chmod")
        and "chmod 600" in json.dumps(steps(plan, "provisioning_steps")),
        "dir_chgrp_step_targets_contract": has_step(
            plan,
            "align_production_env_dir_group",
            "chgrp",
        )
        and target_env_dir_group in json.dumps(steps(plan, "provisioning_steps")),
        "dir_chmod_step_targets_710": has_step(
            plan,
            "enforce_production_env_dir_mode",
            "chmod",
        )
        and "chmod 710" in json.dumps(steps(plan, "provisioning_steps")),
        "read_only_validation_step_present": has_step(
            plan,
            "validate_runtime_owner_contract",
            "read_only_validate",
        ),
        "rollback_steps_present": len(steps(plan, "rollback_steps")) >= 2,
        "command_templates_no_send_or_network": command_templates_are_safe(plan),
        "current_contract_validation_blocked": contract_report.get("result") == "BLOCKED",
    }
    errors = [name for name, passed in checks.items() if not passed]
    result = "PASS" if not errors else "BLOCKED"
    return {
        "generated_at": utc_now(),
        "result": result,
        "errors": errors,
        "plan": {
            "target_runtime_identity": target_identity,
            "target_runtime_group": target_group,
            "target_env_dir": target_env_dir,
            "target_env_dir_owner": target_env_dir_owner,
            "target_env_dir_group": target_env_dir_group,
            "target_env_dir_mode": target_env_dir_mode,
            "target_env_path": target_env_path,
            "target_env_owner": target_owner,
            "target_env_group": target_env_group,
            "target_env_mode": target_mode,
            "execution_authorized": plan.get("execution_authorized"),
            "dry_validation_only": plan.get("dry_validation_only"),
        },
        "current_contract_validation_result": contract_report.get("result"),
        "checks": checks,
        "boundary": {
            "provisioning_executed": "NO",
            "runtime_identity_created": "NO",
            "runtime_group_created": "NO",
            "production_env_changed": "NO",
            "owner_mode_changed": "NO",
            "secret_value_read": "NO",
            "secret_value_disclosed": "NO",
            "sudo_send_executed": "NO",
            "production_signing_executed": "NO",
            "production_http_network_attempted": "NO",
            "production_request_sent": "NO",
            "production_order_sent": "NO",
            "canary_executed": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }


def markdown(report: dict[str, Any]) -> str:
    plan = report["plan"]
    checks = "\n".join(
        f"- {name}: {'PASS' if passed else 'FAIL'}"
        for name, passed in report["checks"].items()
    )
    errors = "\n".join(f"- {item}" for item in report["errors"]) or "- none"
    boundary = report["boundary"]
    return f"""# Production Runtime Identity Provisioning Plan Validation

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- current runtime owner contract validation: {report["current_contract_validation_result"]}

## Plan Target

- target runtime identity: {plan["target_runtime_identity"]}
- target runtime group: {plan["target_runtime_group"]}
- target env dir: `{plan["target_env_dir"]}`
- target env dir owner: {plan["target_env_dir_owner"]}
- target env dir group: {plan["target_env_dir_group"]}
- target env dir mode: {plan["target_env_dir_mode"]}
- target env path: `{plan["target_env_path"]}`
- target env owner: {plan["target_env_owner"]}
- target env group: {plan["target_env_group"]}
- target env mode: {plan["target_env_mode"]}
- execution authorized: {plan["execution_authorized"]}
- dry validation only: {plan["dry_validation_only"]}

## Checks

{checks}

## Errors

{errors}

## Boundary

- provisioning executed: {boundary["provisioning_executed"]}
- runtime identity created: {boundary["runtime_identity_created"]}
- runtime group created: {boundary["runtime_group_created"]}
- production env changed: {boundary["production_env_changed"]}
- owner/mode changed: {boundary["owner_mode_changed"]}
- secret value read: {boundary["secret_value_read"]}
- secret value disclosed: {boundary["secret_value_disclosed"]}
- sudo send executed: {boundary["sudo_send_executed"]}
- production signing executed: {boundary["production_signing_executed"]}
- production HTTP/network attempted: {boundary["production_http_network_attempted"]}
- production request sent: {boundary["production_request_sent"]}
- production order sent: {boundary["production_order_sent"]}
- canary executed: {boundary["canary_executed"]}
- go-live: {boundary["go_live"]}
- live trading: {boundary["live_trading"]}
"""


def main() -> int:
    plan, plan_error = read_json(PLAN_PATH)
    contract, contract_error = read_json(CONTRACT_PATH)
    contract_report, contract_report_error = read_json(CONTRACT_VALIDATION_REPORT)
    report = validate(plan, contract, contract_report)
    errors = [item for item in (plan_error, contract_error, contract_report_error) if item]
    if errors:
        report["errors"] = errors + report["errors"]
        report["result"] = "BLOCKED"

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(markdown(report), encoding="utf-8")

    print("[Production Runtime Identity Provisioning Plan Validation]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(f"errors: {len(report['errors'])}")
    print(f"target_runtime_identity: {report['plan']['target_runtime_identity']}")
    print("provisioning_executed: NO")
    print("production_env_changed: NO")
    print("secret_value_read: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
