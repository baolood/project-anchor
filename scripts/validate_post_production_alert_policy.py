#!/usr/bin/env python3
"""Validate post-production alert policy without sending Telegram messages."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
RUNNER_SCRIPT = ROOT / "scripts" / "run_post_production_monitoring.py"
PAYLOAD_SCRIPT = ROOT / "scripts" / "render_post_production_monitoring_telegram_payload.py"
SENDER_SCRIPT = ROOT / "scripts" / "send_post_production_monitoring_telegram_alert.py"
DEFAULT_JSON_OUT = REPORTS_DIR / "post_production_alert_policy_validation.json"
DEFAULT_MD_OUT = REPORTS_DIR / "post_production_alert_policy_validation.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pass_fail(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def sample_run_report(result: str) -> dict[str, Any]:
    failed_checks = []
    if result != "PASS":
        failed_checks = [
            {
                "name": "snapshot_result_pass",
                "result": "FAIL",
                "evidence": "synthetic policy validation failure",
            }
        ]
    return {
        "result": result,
        "status": (
            "POST_PRODUCTION_MONITORING_RUN_READY"
            if result == "PASS"
            else "POST_PRODUCTION_MONITORING_RUN_BLOCKED"
        ),
        "checks": [
            {
                "name": "snapshot_result_pass",
                "result": "PASS" if result == "PASS" else "FAIL",
                "evidence": "synthetic policy validation input",
            }
        ]
        + failed_checks,
        "boundary": {
            "credential_file_read": "NO",
            "secret_value_disclosed": "NO",
            "production_signing_executed": "NO",
            "production_http_network_attempted": "NO",
            "new_production_request_sent": "NO",
            "second_production_request_sent": "NO",
            "canary_rerun": "NO",
            "runtime_modified": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }


def evaluate_case(
    *,
    name: str,
    run_result: str,
    previous_alert_result: str | None,
    runner: Any,
    payload_renderer: Any,
    sender: Any,
) -> dict[str, Any]:
    alert = runner.build_alert_report(sample_run_report(run_result))
    previous_state = {}
    if previous_alert_result is not None:
        previous_state["last_alert_result"] = previous_alert_result
    _state, notification = runner.build_alert_notification(alert, previous_state)
    payload = payload_renderer.build_payload(notification)
    send_result, send_exit_code = sender.build_result(
        payload,
        execute=False,
        env_path=Path("/path/that/must/not/be/read"),
    )

    expected_notification = "EMITTED" if (
        alert.get("result") == "ACTIVE" and previous_alert_result != "ACTIVE"
    ) else "SUPPRESSED"
    expected_payload = "READY_TO_SEND" if expected_notification == "EMITTED" else "SUPPRESSED"
    expected_send_status = (
        "EXECUTE_FLAG_REQUIRED"
        if expected_payload == "READY_TO_SEND"
        else "PAYLOAD_NOT_READY_TO_SEND"
    )
    checks = {
        "notification_policy": pass_fail(notification.get("result") == expected_notification),
        "payload_policy": pass_fail(payload.get("result") == expected_payload),
        "send_not_attempted_without_execute": pass_fail(send_result.get("send_attempted") == "NO"),
        "telegram_http_not_attempted": pass_fail(
            send_result.get("boundary", {}).get("telegram_http_attempted") == "NO"
        ),
        "alerting_env_not_read": pass_fail(
            send_result.get("boundary", {}).get("alerting_env_read") == "NO"
        ),
        "failure_code_expected": pass_fail(send_result.get("failure_code") == expected_send_status),
        "production_request_not_sent": pass_fail(
            send_result.get("boundary", {}).get("production_request_sent") == "NO"
        ),
        "go_live_no_go": pass_fail(send_result.get("boundary", {}).get("go_live") == "NO-GO"),
        "live_trading_no_go": pass_fail(
            send_result.get("boundary", {}).get("live_trading") == "NO-GO"
        ),
    }
    return {
        "name": name,
        "input": {
            "run_result": run_result,
            "previous_alert_result": previous_alert_result,
        },
        "observed": {
            "alert_result": alert.get("result"),
            "notification_result": notification.get("result"),
            "payload_result": payload.get("result"),
            "send_result": send_result.get("result"),
            "send_status": send_result.get("status"),
            "send_failure_code": send_result.get("failure_code"),
            "send_exit_code": send_exit_code,
        },
        "expected": {
            "notification_result": expected_notification,
            "payload_result": expected_payload,
            "send_failure_code": expected_send_status,
        },
        "checks": checks,
        "result": "PASS" if all(value == "PASS" for value in checks.values()) else "FAIL",
    }


def build_report() -> dict[str, Any]:
    runner = load_module(RUNNER_SCRIPT, "run_post_production_monitoring")
    payload_renderer = load_module(PAYLOAD_SCRIPT, "render_post_production_monitoring_telegram_payload")
    sender = load_module(SENDER_SCRIPT, "send_post_production_monitoring_telegram_alert")
    cases = [
        evaluate_case(
            name="clear_state_stays_silent",
            run_result="PASS",
            previous_alert_result=None,
            runner=runner,
            payload_renderer=payload_renderer,
            sender=sender,
        ),
        evaluate_case(
            name="active_transition_prepares_single_notification",
            run_result="BLOCKED",
            previous_alert_result=None,
            runner=runner,
            payload_renderer=payload_renderer,
            sender=sender,
        ),
        evaluate_case(
            name="repeated_active_is_suppressed",
            run_result="BLOCKED",
            previous_alert_result="ACTIVE",
            runner=runner,
            payload_renderer=payload_renderer,
            sender=sender,
        ),
        evaluate_case(
            name="recovered_then_active_notifies_again",
            run_result="BLOCKED",
            previous_alert_result="CLEAR",
            runner=runner,
            payload_renderer=payload_renderer,
            sender=sender,
        ),
    ]
    result = "PASS" if all(case["result"] == "PASS" for case in cases) else "BLOCKED"
    return {
        "generated_at": utc_now(),
        "result": result,
        "status": (
            "POST_PRODUCTION_ALERT_POLICY_VALID"
            if result == "PASS"
            else "POST_PRODUCTION_ALERT_POLICY_BLOCKED"
        ),
        "policy": {
            "clear_state_telegram_send": "SUPPRESSED",
            "first_active_transition_telegram_payload": "READY_TO_SEND",
            "repeated_active_telegram_send": "SUPPRESSED",
            "recovered_then_active_telegram_payload": "READY_TO_SEND",
            "telegram_delivery_requires_execute_flag": "YES",
        },
        "cases": cases,
        "boundary": {
            "alerting_env_read": "NO",
            "telegram_http_attempted": "NO",
            "secret_value_disclosed": "NO",
            "production_env_read": "NO",
            "production_request_sent": "NO",
            "second_production_request_sent": "NO",
            "canary_rerun": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }


def markdown(report: dict[str, Any]) -> str:
    policy = "\n".join(f"- {key}: {value}" for key, value in report["policy"].items())
    cases = "\n".join(
        "\n".join(
            [
                f"### {case['name']}",
                "",
                f"- result: {case['result']}",
                f"- alert result: {case['observed']['alert_result']}",
                f"- notification result: {case['observed']['notification_result']}",
                f"- payload result: {case['observed']['payload_result']}",
                f"- send failure code: {case['observed']['send_failure_code']}",
            ]
        )
        for case in report["cases"]
    )
    boundary = "\n".join(f"- {key}: {value}" for key, value in report["boundary"].items())
    return f"""# Post Production Alert Policy Validation

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- status: {report["status"]}

## Policy

{policy}

## Cases

{cases}

## Boundary

{boundary}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MD_OUT)
    args = parser.parse_args()

    report = build_report()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_out.write_text(markdown(report), encoding="utf-8")

    print("[Post Production Alert Policy Validation]")
    print(f"result: {report['result']}")
    print(f"status: {report['status']}")
    print("clear_state_telegram_send: SUPPRESSED")
    print("first_active_transition_telegram_payload: READY_TO_SEND")
    print("repeated_active_telegram_send: SUPPRESSED")
    print("recovered_then_active_telegram_payload: READY_TO_SEND")
    print("alerting_env_read: NO")
    print("telegram_http_attempted: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
