#!/usr/bin/env python3
"""Validate consecutive post-production monitoring timer runs from systemd journal."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SERVICE_NAME = "project-anchor-post-production-monitoring.service"
DEFAULT_REPORT_DIR = Path("/var/lib/project-anchor/reports")
START_RE = re.compile(r"^(?P<prefix>\w+\s+\d+\s+\d+:\d+:\d+).*Starting Project Anchor")
FINISH_RE = re.compile(r"^(?P<prefix>\w+\s+\d+\s+\d+:\d+:\d+).*Finished Project Anchor")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def journal_lines(since: str) -> tuple[list[str], str | None]:
    try:
        result = subprocess.run(
            ["journalctl", "-u", SERVICE_NAME, "--since", since, "--no-pager"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001 - stability check should fail closed.
        return [], f"{type(exc).__name__}:{exc}"
    if result.returncode != 0:
        return [], result.stderr.strip() or f"journalctl exited {result.returncode}"
    return result.stdout.splitlines(), None


def parse_runs(lines: list[str]) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in lines:
        start = START_RE.search(line)
        if start:
            if current:
                runs.append(current)
            current = {
                "started_at": start.group("prefix"),
                "finished": False,
                "monitoring_result": None,
                "run_status": None,
                "telegram_send_status": None,
                "telegram_send_attempted": None,
                "new_production_request_sent": None,
                "second_production_request_sent": None,
                "go_live": None,
                "live_trading": None,
            }
            continue
        if current is None:
            continue
        if "POST_PRODUCTION_MONITORING_ONCE_RESULT=" in line:
            current["monitoring_result"] = line.rsplit("=", 1)[-1].strip()
        elif "RUN_STATUS=" in line:
            current["run_status"] = line.rsplit("=", 1)[-1].strip()
        elif "TELEGRAM_SEND_STATUS=" in line:
            current["telegram_send_status"] = line.rsplit("=", 1)[-1].strip()
        elif "TELEGRAM_SEND_ATTEMPTED=" in line:
            current["telegram_send_attempted"] = line.rsplit("=", 1)[-1].strip()
        elif "NEW_PRODUCTION_REQUEST_SENT=" in line:
            current["new_production_request_sent"] = line.rsplit("=", 1)[-1].strip()
        elif "SECOND_PRODUCTION_REQUEST_SENT=" in line:
            current["second_production_request_sent"] = line.rsplit("=", 1)[-1].strip()
        elif "GO_LIVE=" in line:
            current["go_live"] = line.rsplit("=", 1)[-1].strip()
        elif "LIVE_TRADING=" in line:
            current["live_trading"] = line.rsplit("=", 1)[-1].strip()
        finish = FINISH_RE.search(line)
        if finish:
            current["finished"] = True
            current["finished_at"] = finish.group("prefix")
            runs.append(current)
            current = None
    if current:
        runs.append(current)
    return runs


def run_passed(run: dict[str, Any]) -> bool:
    return (
        run.get("finished") is True
        and run.get("monitoring_result") == "PASS"
        and run.get("run_status") == "POST_PRODUCTION_MONITORING_RUN_READY"
        and run.get("new_production_request_sent") == "NO"
        and run.get("second_production_request_sent") == "NO"
        and run.get("go_live") == "NO-GO"
        and run.get("live_trading") == "NO-GO"
    )


def latest_consecutive_successes(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    successes: list[dict[str, Any]] = []
    for run in reversed(runs):
        if run_passed(run):
            successes.append(run)
        else:
            break
    return list(reversed(successes))


def load_runtime_report(report_dir: Path) -> dict[str, Any]:
    path = report_dir / "post_production_monitoring_timer_runtime_validation.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def pass_fail(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def build_report(
    report_dir: Path,
    since: str,
    min_successful_runs: int,
    lines: list[str],
    journal_error: str | None,
) -> dict[str, Any]:
    runs = parse_runs(lines)
    consecutive = latest_consecutive_successes(runs)
    runtime = load_runtime_report(report_dir)
    checks = {
        "journal_readable": pass_fail(journal_error is None),
        "minimum_successful_runs_observed": pass_fail(len(consecutive) >= min_successful_runs),
        "latest_run_finished": pass_fail(bool(runs and runs[-1].get("finished") is True)),
        "latest_run_passed": pass_fail(bool(runs and run_passed(runs[-1]))),
        "no_new_production_request_in_observed_runs": pass_fail(
            all(run.get("new_production_request_sent") == "NO" for run in runs)
        ),
        "no_second_production_request_in_observed_runs": pass_fail(
            all(run.get("second_production_request_sent") == "NO" for run in runs)
        ),
        "go_live_stayed_no_go": pass_fail(all(run.get("go_live") == "NO-GO" for run in runs)),
        "live_trading_stayed_no_go": pass_fail(
            all(run.get("live_trading") == "NO-GO" for run in runs)
        ),
        "runtime_timer_validation_pass": pass_fail(runtime.get("result") == "PASS"),
    }
    result = "PASS" if journal_error is None and all(v == "PASS" for v in checks.values()) else "BLOCKED"
    return {
        "generated_at": utc_now(),
        "result": result,
        "status": (
            "POST_PRODUCTION_MONITORING_TIMER_STABILITY_VALID"
            if result == "PASS"
            else "POST_PRODUCTION_MONITORING_TIMER_STABILITY_BLOCKED"
        ),
        "service": SERVICE_NAME,
        "since": since,
        "min_successful_runs": min_successful_runs,
        "observed_run_count": len(runs),
        "latest_consecutive_success_count": len(consecutive),
        "latest_run": runs[-1] if runs else None,
        "latest_consecutive_successes": consecutive[-min_successful_runs:],
        "runtime_timer_validation_result": runtime.get("result", "UNKNOWN"),
        "checks": checks,
        "errors": [journal_error] if journal_error else [],
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
    checks = "\n".join(f"- {key}: {value}" for key, value in report["checks"].items())
    boundary = "\n".join(f"- {key}: {value}" for key, value in report["boundary"].items())
    latest = report.get("latest_run") or {}
    runs = "\n".join(
        f"- {run.get('started_at')} -> {run.get('finished_at')}: "
        f"{run.get('monitoring_result')} / {run.get('run_status')}"
        for run in report.get("latest_consecutive_successes", [])
    ) or "- none"
    return f"""# Post-Production Monitoring Timer Stability Validation

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- status: {report["status"]}
- service: `{report["service"]}`
- since: `{report["since"]}`
- observed runs: {report["observed_run_count"]}
- latest consecutive successes: {report["latest_consecutive_success_count"]}
- required consecutive successes: {report["min_successful_runs"]}
- runtime timer validation result: {report["runtime_timer_validation_result"]}

## Latest Run

- started at: `{latest.get("started_at")}`
- finished at: `{latest.get("finished_at")}`
- monitoring result: {latest.get("monitoring_result")}
- run status: {latest.get("run_status")}
- Telegram send status: {latest.get("telegram_send_status")}
- Telegram send attempted: {latest.get("telegram_send_attempted")}
- new production request sent: {latest.get("new_production_request_sent")}
- second production request sent: {latest.get("second_production_request_sent")}
- go-live: {latest.get("go_live")}
- live trading: {latest.get("live_trading")}

## Latest Consecutive Successes

{runs}

## Checks

{checks}

## Boundary

{boundary}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--since", default="90 minutes ago")
    parser.add_argument("--min-successful-runs", type=int, default=3)
    args = parser.parse_args()

    args.report_dir.mkdir(parents=True, exist_ok=True)
    lines, error = journal_lines(args.since)
    report = build_report(args.report_dir, args.since, args.min_successful_runs, lines, error)
    (args.report_dir / "post_production_monitoring_timer_stability_validation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.report_dir / "post_production_monitoring_timer_stability_validation.md").write_text(
        markdown(report),
        encoding="utf-8",
    )

    print("[Post-Production Monitoring Timer Stability Validation]")
    print(f"result: {report['result']}")
    print(f"status: {report['status']}")
    print(f"observed runs: {report['observed_run_count']}")
    print(f"latest consecutive successes: {report['latest_consecutive_success_count']}")
    print(f"required consecutive successes: {report['min_successful_runs']}")
    print("alerting_env_read: NO")
    print("secret_value_disclosed: NO")
    print("new_production_request_sent: NO")
    print("second_production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
