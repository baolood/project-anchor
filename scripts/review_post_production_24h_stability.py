#!/usr/bin/env python3
"""Review post-production stability from sanitized monitoring evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_REPORT_DIR = Path("/var/lib/project-anchor/reports")
DEFAULT_JSON_OUT = Path("reports/post_production_24h_stability_review.json")
DEFAULT_MD_OUT = Path("reports/post_production_24h_stability_review.md")
TIMER_NAME = "project-anchor-post-production-monitoring.timer"
SERVICE_NAME = "project-anchor-post-production-monitoring.service"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def pass_fail(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def next_single_task(window_label: str) -> str:
    normalized = window_label.strip().lower()
    if normalized == "24h":
        return "continue_to_48h_read_only_observation"
    if normalized == "48h":
        return "continue_to_72h_read_only_observation"
    if normalized == "72h":
        return "operator_stability_review_or_freeze_decision"
    return "continue_read_only_observation_or_operator_freeze_decision"


def systemctl_active(unit: str) -> str:
    try:
        result = subprocess.run(
            ["systemctl", "is-active", unit],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        return "UNKNOWN"
    return result.stdout.strip() or "UNKNOWN"


def systemctl_enabled(unit: str) -> str:
    try:
        result = subprocess.run(
            ["systemctl", "is-enabled", unit],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        return "UNKNOWN"
    return result.stdout.strip() or "UNKNOWN"


def journal_success_count(since: str) -> tuple[int | None, str | None]:
    try:
        result = subprocess.run(
            ["journalctl", "-u", SERVICE_NAME, "--since", since, "--no-pager"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001 - review must fail closed.
        return None, f"{type(exc).__name__}:{exc}"
    if result.returncode != 0:
        return None, result.stderr.strip() or f"journalctl exited {result.returncode}"
    return result.stdout.count("POST_PRODUCTION_MONITORING_ONCE_RESULT=PASS"), None


def build_review(
    report_dir: Path,
    since: str,
    min_successes: int,
    window_label: str = "24h",
) -> dict[str, Any]:
    run = load_json(report_dir / "post_production_monitoring_run.json")
    snapshot = load_json(report_dir / "post_production_monitoring_snapshot.json")
    alert = load_json(report_dir / "post_production_monitoring_alert.json")
    telegram = load_json(report_dir / "post_production_monitoring_alert_notification.json")
    timer_runtime = load_json(report_dir / "post_production_monitoring_timer_runtime_validation.json")
    timer_stability = load_json(report_dir / "post_production_monitoring_timer_stability_validation.json")

    boundary = run.get("boundary") if isinstance(run.get("boundary"), dict) else {}
    snapshot_boundary = snapshot.get("boundary") if isinstance(snapshot.get("boundary"), dict) else {}
    success_count, journal_error = journal_success_count(since)
    timer_active = systemctl_active(TIMER_NAME)
    timer_enabled = systemctl_enabled(TIMER_NAME)

    checks = {
        "monitoring_run_pass": pass_fail(run.get("result") == "PASS"),
        "monitoring_snapshot_pass": pass_fail(snapshot.get("result") == "PASS"),
        "alert_clear": pass_fail(alert.get("result") == "CLEAR"),
        "timer_active": pass_fail(timer_active == "active"),
        "timer_enabled": pass_fail(timer_enabled == "enabled"),
        "timer_runtime_validation_pass": pass_fail(timer_runtime.get("result") == "PASS"),
        "timer_stability_validation_pass": pass_fail(timer_stability.get("result") == "PASS"),
        f"minimum_{window_label}_successes_observed": pass_fail(
            success_count is not None and success_count >= min_successes
        ),
        "no_new_production_request": pass_fail(
            boundary.get("new_production_request_sent") == "NO"
            or snapshot_boundary.get("new_production_request_sent") == "NO"
        ),
        "no_second_production_request": pass_fail(
            boundary.get("second_production_request_sent") == "NO"
            or snapshot_boundary.get("second_production_request_sent") == "NO"
        ),
        "no_canary_rerun": pass_fail(
            boundary.get("canary_rerun") == "NO" or snapshot_boundary.get("canary_rerun") == "NO"
        ),
        "go_live_no_go": pass_fail(
            boundary.get("go_live") == "NO-GO" or snapshot_boundary.get("go_live") == "NO-GO"
        ),
        "live_trading_no_go": pass_fail(
            boundary.get("live_trading") == "NO-GO"
            or snapshot_boundary.get("live_trading") == "NO-GO"
        ),
    }
    if journal_error:
        checks["journal_readable"] = "FAIL"
    else:
        checks["journal_readable"] = "PASS"

    result = "PASS" if all(value == "PASS" for value in checks.values()) else "BLOCKED"
    return {
        "generated_at": utc_now(),
        "result": result,
        "status": (
            f"POST_PRODUCTION_{window_label.upper()}_STABILITY_REVIEW_PASS"
            if result == "PASS"
            else f"POST_PRODUCTION_{window_label.upper()}_STABILITY_REVIEW_BLOCKED"
        ),
        "review_window": {
            "label": window_label,
            "since": since,
            "minimum_successful_runs_required": min_successes,
            "observed_successful_runs": success_count,
        },
        "evidence": {
            "monitoring_generated_at": run.get("generated_at"),
            "monitoring_result": run.get("result"),
            "monitoring_status": run.get("status"),
            "snapshot_generated_at": snapshot.get("generated_at"),
            "snapshot_result": snapshot.get("result"),
            "alert_result": alert.get("result"),
            "alert_status": alert.get("status"),
            "telegram_notification_result": telegram.get("result"),
            "telegram_notification_status": telegram.get("status"),
            "timer_active": timer_active,
            "timer_enabled": timer_enabled,
            "timer_runtime_result": timer_runtime.get("result"),
            "timer_stability_result": timer_stability.get("result"),
            "timer_stability_successes": timer_stability.get("latest_consecutive_success_count"),
            "worker_heartbeat_at": nested(
                snapshot,
                "snapshot",
                "worker",
                "last_heartbeat_at",
                default="not_reported_by_snapshot",
            ),
        },
        "checks": checks,
        "errors": [journal_error] if journal_error else [],
        "boundary": {
            "alerting_env_read": "NO",
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
        "next_single_task": next_single_task(window_label),
    }


def markdown(report: dict[str, Any]) -> str:
    evidence = "\n".join(f"- {key}: {value}" for key, value in report["evidence"].items())
    checks = "\n".join(f"- {key}: {value}" for key, value in report["checks"].items())
    boundary = "\n".join(f"- {key}: {value}" for key, value in report["boundary"].items())
    window = report["review_window"]
    return f"""# Post-Production {window["label"]} Stability Review

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- status: {report["status"]}
- review since: `{window["since"]}`
- observed successful runs: {window["observed_successful_runs"]}
- minimum successful runs required: {window["minimum_successful_runs_required"]}

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
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_OUT)
    parser.add_argument("--since", default="24 hours ago")
    parser.add_argument("--min-successes", type=int, default=12)
    parser.add_argument("--window-label", default="24h")
    args = parser.parse_args()

    report = build_review(args.report_dir, args.since, args.min_successes, args.window_label)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.md_out.write_text(markdown(report), encoding="utf-8")

    print(f"[Post-Production {args.window_label} Stability Review]")
    print(f"result: {report['result']}")
    print(f"status: {report['status']}")
    print(f"observed successful runs: {report['review_window']['observed_successful_runs']}")
    print(f"new production request sent: {report['boundary']['new_production_request_sent']}")
    print(f"go-live: {report['boundary']['go_live']}")
    print(f"live trading: {report['boundary']['live_trading']}")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
