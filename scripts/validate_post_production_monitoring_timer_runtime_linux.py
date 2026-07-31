#!/usr/bin/env python3
"""Validate the post-production monitoring systemd timer runtime state."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TIMER_NAME = "project-anchor-post-production-monitoring.timer"
SERVICE_NAME = "project-anchor-post-production-monitoring.service"
DEFAULT_REPORT_DIR = Path("/var/lib/project-anchor/reports")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_properties(text: str) -> dict[str, str]:
    props: dict[str, str] = {}
    for raw_line in text.splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        props[key.strip()] = value.strip()
    return props


def systemctl_show(unit: str, fields: list[str]) -> tuple[dict[str, str], str | None]:
    command = ["systemctl", "show", unit, "--no-pager"]
    for field in fields:
        command.extend(["-p", field])
    try:
        result = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001 - report fail-closed with evidence.
        return {}, f"{type(exc).__name__}:{exc}"
    if result.returncode != 0:
        return {}, result.stderr.strip() or f"systemctl exited {result.returncode}"
    return parse_properties(result.stdout), None


def load_report(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def pass_fail(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def build_runtime_report(
    report_dir: Path,
    timer_props: dict[str, str],
    service_props: dict[str, str],
    timer_error: str | None,
    service_error: str | None,
) -> dict[str, Any]:
    monitoring = load_report(report_dir / "post_production_monitoring_run.json")
    telegram = load_report(report_dir / "post_production_monitoring_telegram_send_result.json")
    monitoring_boundary = (
        monitoring.get("boundary") if isinstance(monitoring.get("boundary"), dict) else {}
    )
    telegram_boundary = telegram.get("boundary") if isinstance(telegram.get("boundary"), dict) else {}

    telegram_fail_closed_or_delivered = (
        telegram.get("result") == "PASS"
        and telegram.get("send_result") == "DELIVERED"
    ) or (
        telegram.get("result") == "BLOCKED"
        and telegram.get("send_attempted") == "NO"
        and telegram.get("failure_code") == "PAYLOAD_NOT_READY_TO_SEND"
    )

    checks = {
        "timer_loaded": pass_fail(timer_props.get("LoadState") == "loaded"),
        "timer_active": pass_fail(timer_props.get("ActiveState") == "active"),
        "timer_enabled": pass_fail(timer_props.get("UnitFileState") == "enabled"),
        "timer_last_trigger_present": pass_fail(bool(timer_props.get("LastTriggerUSec"))),
        "timer_result_success": pass_fail(timer_props.get("Result") == "success"),
        "service_loaded": pass_fail(service_props.get("LoadState") == "loaded"),
        "service_result_success": pass_fail(service_props.get("Result") == "success"),
        "service_exit_success": pass_fail(service_props.get("ExecMainStatus") in {"0", ""}),
        "monitoring_report_pass": pass_fail(monitoring.get("result") == "PASS"),
        "monitoring_report_no_new_production_request": pass_fail(
            monitoring_boundary.get("new_production_request_sent") == "NO"
        ),
        "monitoring_report_go_live_no_go": pass_fail(monitoring_boundary.get("go_live") == "NO-GO"),
        "telegram_sender_fail_closed_or_delivered": pass_fail(telegram_fail_closed_or_delivered),
        "telegram_secret_not_disclosed": pass_fail(
            telegram_boundary.get("secret_value_disclosed") != "YES"
        ),
    }
    errors = [item for item in [timer_error, service_error] if item]
    result = "PASS" if not errors and all(value == "PASS" for value in checks.values()) else "BLOCKED"

    return {
        "generated_at": utc_now(),
        "result": result,
        "status": (
            "POST_PRODUCTION_MONITORING_TIMER_RUNTIME_VALID"
            if result == "PASS"
            else "POST_PRODUCTION_MONITORING_TIMER_RUNTIME_BLOCKED"
        ),
        "timer": {
            "name": TIMER_NAME,
            "load_state": timer_props.get("LoadState"),
            "active_state": timer_props.get("ActiveState"),
            "unit_file_state": timer_props.get("UnitFileState"),
            "last_trigger": timer_props.get("LastTriggerUSec"),
            "next_elapse": timer_props.get("NextElapseUSecRealtime"),
            "result": timer_props.get("Result"),
        },
        "service": {
            "name": SERVICE_NAME,
            "load_state": service_props.get("LoadState"),
            "active_state": service_props.get("ActiveState"),
            "result": service_props.get("Result"),
            "exec_main_status": service_props.get("ExecMainStatus"),
            "restarts": service_props.get("NRestarts"),
        },
        "monitoring_report": {
            "generated_at": monitoring.get("generated_at"),
            "result": monitoring.get("result"),
            "status": monitoring.get("status"),
        },
        "telegram_sender_report": {
            "generated_at": telegram.get("generated_at"),
            "result": telegram.get("result"),
            "status": telegram.get("status"),
            "send_attempted": telegram.get("send_attempted"),
            "send_result": telegram.get("send_result"),
            "failure_code": telegram.get("failure_code"),
        },
        "checks": checks,
        "errors": errors,
        "boundary": {
            "alerting_env_read": "NO",
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


def markdown(report: dict[str, Any]) -> str:
    checks = report["checks"]
    check_lines = "\n".join(f"- {key}: {value}" for key, value in checks.items())
    boundary = report["boundary"]
    boundary_lines = "\n".join(f"- {key}: {value}" for key, value in boundary.items())
    timer = report["timer"]
    service = report["service"]
    monitoring = report["monitoring_report"]
    telegram = report["telegram_sender_report"]
    return f"""# Post-Production Monitoring Timer Runtime Validation

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- status: {report["status"]}

## Timer

- name: `{timer.get("name")}`
- load state: {timer.get("load_state")}
- active state: {timer.get("active_state")}
- unit file state: {timer.get("unit_file_state")}
- last trigger: `{timer.get("last_trigger")}`
- next elapse: `{timer.get("next_elapse")}`
- result: {timer.get("result")}

## Service

- name: `{service.get("name")}`
- load state: {service.get("load_state")}
- active state: {service.get("active_state")}
- result: {service.get("result")}
- exit status: {service.get("exec_main_status")}
- restarts: {service.get("restarts")}

## Latest Monitoring Evidence

- generated at: `{monitoring.get("generated_at")}`
- result: {monitoring.get("result")}
- status: {monitoring.get("status")}

## Latest Telegram Sender Evidence

- generated at: `{telegram.get("generated_at")}`
- result: {telegram.get("result")}
- status: {telegram.get("status")}
- send attempted: {telegram.get("send_attempted")}
- send result: {telegram.get("send_result")}
- failure code: {telegram.get("failure_code") or "none"}

## Checks

{check_lines}

## Boundary

{boundary_lines}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args()

    timer_props, timer_error = systemctl_show(
        TIMER_NAME,
        [
            "LoadState",
            "ActiveState",
            "UnitFileState",
            "LastTriggerUSec",
            "NextElapseUSecRealtime",
            "Result",
        ],
    )
    service_props, service_error = systemctl_show(
        SERVICE_NAME,
        ["LoadState", "ActiveState", "Result", "ExecMainStatus", "NRestarts"],
    )

    args.report_dir.mkdir(parents=True, exist_ok=True)
    report = build_runtime_report(
        args.report_dir,
        timer_props,
        service_props,
        timer_error,
        service_error,
    )
    (args.report_dir / "post_production_monitoring_timer_runtime_validation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.report_dir / "post_production_monitoring_timer_runtime_validation.md").write_text(
        markdown(report),
        encoding="utf-8",
    )

    print("[Post-Production Monitoring Timer Runtime Validation]")
    print(f"result: {report['result']}")
    print(f"status: {report['status']}")
    print(f"timer active: {report['timer'].get('active_state')}")
    print(f"timer enabled: {report['timer'].get('unit_file_state')}")
    print(f"last trigger: {report['timer'].get('last_trigger')}")
    print(f"monitoring result: {report['monitoring_report'].get('result')}")
    print(f"telegram sender result: {report['telegram_sender_report'].get('result')}")
    print("alerting_env_read: NO")
    print("secret_value_disclosed: NO")
    print("new_production_request_sent: NO")
    print("second_production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
