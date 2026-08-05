#!/usr/bin/env python3
"""Validate the manual low-frequency operations runbook.

This is a read-only check. It validates the runbook shape, the linked policy,
and sanitized evidence reports. It never reads credential files, opens sockets,
or sends production requests.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNBOOK = ROOT / "config" / "manual_low_frequency_operations_runbook.json"
POLICY_VALIDATION = ROOT / "reports" / "manual_low_frequency_operations_policy_validation.json"
MONITORING_RUN = ROOT / "reports" / "post_production_monitoring_run.json"
POST_SEND_RECONCILIATION = ROOT / "reports" / "post_production_send_reconciliation.json"
TELEGRAM_EVIDENCE = ROOT / "reports" / "post_production_telegram_channel_evidence.json"
REPORTS_DIR = ROOT / "reports"
DEFAULT_JSON_OUT = REPORTS_DIR / "manual_low_frequency_operations_runbook_validation.json"
DEFAULT_MD_OUT = REPORTS_DIR / "manual_low_frequency_operations_runbook_validation.md"


REQUIRED_BEFORE = {
    "confirm_ops_dashboard_health_pass",
    "confirm_post_production_monitoring_pass",
    "confirm_telegram_alert_channel_ready",
    "confirm_previous_post_send_reconciliation_pass",
    "confirm_no_unresolved_alert",
    "confirm_policy_validation_pass",
    "confirm_fresh_pre_send_readiness_pass",
    "confirm_explicit_operator_authorization_present",
}
REQUIRED_DURING = {
    "send_exactly_one_request_only",
    "use_unique_idempotency_key",
    "do_not_retry",
    "do_not_send_second_request",
    "stop_on_unclear_exchange_result",
    "do_not_enable_continuous_runtime",
}
REQUIRED_AFTER = {
    "run_read_only_post_send_reconciliation",
    "confirm_external_order_id_present",
    "confirm_no_duplicate_request",
    "confirm_telegram_alerting_ready",
    "observe_for_at_least_24h_before_next_request",
    "keep_go_live_no_go",
    "keep_live_trading_no_go",
}
REQUIRED_STOP = {
    "ops_dashboard_unhealthy",
    "worker_heartbeat_missing",
    "monitoring_not_pass",
    "telegram_not_ready",
    "policy_validation_not_pass",
    "fresh_pre_send_readiness_not_pass",
    "explicit_operator_authorization_missing",
    "secret_disclosure_risk",
    "duplicate_or_second_request_risk",
    "unexpected_exchange_response",
    "reconciliation_not_pass",
    "unresolved_post_send_alert",
}
REQUIRED_PROHIBITED = {
    "automatic_trading",
    "automatic_retry",
    "second_request_same_window",
    "continuous_runtime_enablement",
    "go_live",
    "live_trading",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def pass_fail(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def includes_all(values: Any, required: set[str]) -> bool:
    if not isinstance(values, list):
        return False
    return required.issubset({str(item).strip() for item in values})


def nested_get(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def validate(runbook: dict[str, Any]) -> dict[str, Any]:
    policy_validation = load_json(POLICY_VALIDATION)
    monitoring = load_json(MONITORING_RUN)
    reconciliation = load_json(POST_SEND_RECONCILIATION)
    telegram = load_json(TELEGRAM_EVIDENCE)

    checks = {
        "runbook_mode_manual_confirmed": pass_fail(
            runbook.get("RUNBOOK_MODE") == "manual_confirmed_low_frequency_execution_only"
        ),
        "policy_file_linked": pass_fail(
            runbook.get("POLICY_FILE") == "config/manual_low_frequency_operations_policy.json"
        ),
        "before_request_complete": pass_fail(includes_all(runbook.get("BEFORE_REQUEST"), REQUIRED_BEFORE)),
        "during_request_complete": pass_fail(includes_all(runbook.get("DURING_REQUEST"), REQUIRED_DURING)),
        "after_request_complete": pass_fail(includes_all(runbook.get("AFTER_REQUEST"), REQUIRED_AFTER)),
        "stop_conditions_complete": pass_fail(includes_all(runbook.get("STOP_CONDITIONS"), REQUIRED_STOP)),
        "prohibited_actions_complete": pass_fail(
            includes_all(runbook.get("PROHIBITED_ACTIONS"), REQUIRED_PROHIBITED)
        ),
        "operator_verdict_runbook_only": pass_fail(
            runbook.get("FINAL_OPERATOR_VERDICT")
            == "APPROVED_FOR_MANUAL_LOW_FREQUENCY_OPERATIONS_RUNBOOK_ONLY"
        ),
        "policy_validation_pass": pass_fail(policy_validation.get("result") == "PASS"),
        "monitoring_pass_or_available": pass_fail(monitoring.get("result") in {"PASS", None}),
        "post_send_reconciliation_pass": pass_fail(reconciliation.get("result") == "PASS"),
        "telegram_channel_evidence_pass_or_available": pass_fail(
            telegram.get("result") in {"PASS", None}
            or nested_get(telegram, ("telegram", "message_sent")) in {"YES", True}
        ),
    }
    result = "PASS" if all(value == "PASS" for value in checks.values()) else "BLOCKED"
    return {
        "generated_at": utc_now(),
        "input_file": str(DEFAULT_RUNBOOK.relative_to(ROOT)),
        "result": result,
        "status": (
            "MANUAL_LOW_FREQUENCY_OPERATIONS_RUNBOOK_PASS"
            if result == "PASS"
            else "MANUAL_LOW_FREQUENCY_OPERATIONS_RUNBOOK_BLOCKED"
        ),
        "runbook": {
            "mode": runbook.get("RUNBOOK_MODE"),
            "policy_file": runbook.get("POLICY_FILE"),
            "before_request_steps": len(runbook.get("BEFORE_REQUEST", [])),
            "during_request_steps": len(runbook.get("DURING_REQUEST", [])),
            "after_request_steps": len(runbook.get("AFTER_REQUEST", [])),
            "stop_conditions": len(runbook.get("STOP_CONDITIONS", [])),
        },
        "evidence": {
            "policy_validation": policy_validation.get("result", "missing"),
            "post_production_monitoring": monitoring.get("result", "missing"),
            "post_send_reconciliation": reconciliation.get("result", "missing"),
            "telegram_channel_evidence": telegram.get("result", "available_or_not_required"),
        },
        "checks": checks,
        "boundary": {
            "secret_read": "NO",
            "credential_file_read": "NO",
            "production_signing_executed": "NO",
            "production_http_network_attempted": "NO",
            "production_request_sent": "NO",
            "second_production_request_sent": "NO",
            "telegram_sent_by_validator": "NO",
            "canary_rerun": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
        "next_single_task": (
            "merge_manual_low_frequency_operations_policy_and_runbook"
            if result == "PASS"
            else "fix_manual_low_frequency_operations_runbook_blocker"
        ),
    }


def markdown(report: dict[str, Any]) -> str:
    checks = "\n".join(f"- {key}: {value}" for key, value in report["checks"].items())
    evidence = "\n".join(f"- {key}: {value}" for key, value in report["evidence"].items())
    boundary = "\n".join(f"- {key}: {value}" for key, value in report["boundary"].items())
    runbook = "\n".join(f"- {key}: {value}" for key, value in report["runbook"].items())
    return f"""# Manual Low-Frequency Operations Runbook Validation

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- status: {report["status"]}
- input file: `{report["input_file"]}`

## Runbook

{runbook}

## Evidence

{evidence}

## Checks

{checks}

## Boundary

{boundary}

## Next Single Task

{report["next_single_task"]}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runbook", type=Path, default=DEFAULT_RUNBOOK)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_OUT)
    args = parser.parse_args()

    runbook = load_json(args.runbook)
    report = validate(runbook)
    if args.runbook.resolve() != DEFAULT_RUNBOOK:
        report["input_file"] = str(args.runbook)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.md_out.write_text(markdown(report), encoding="utf-8")

    print("[Manual Low-Frequency Operations Runbook Validation]")
    print(f"report JSON: {args.json_out}")
    print(f"report Markdown: {args.md_out}")
    print(f"result: {report['result']}")
    print(f"status: {report['status']}")
    print("secret_read: NO")
    print("production_request_sent: NO")
    print("telegram_sent_by_validator: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
