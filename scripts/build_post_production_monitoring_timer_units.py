#!/usr/bin/env python3
"""Build systemd units for read-only post-production monitoring refresh."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


SERVICE_NAME = "project-anchor-post-production-monitoring.service"
TIMER_NAME = "project-anchor-post-production-monitoring.timer"
DEFAULT_OUTPUT_DIR = "/var/lib/project-anchor/reports"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def bind_paths(project_root: str, source_project_root: str | None) -> str:
    if source_project_root and source_project_root != project_root:
        return f"{source_project_root}:{project_root}"
    return project_root


def service_unit(project_root: str, output_dir: str, source_project_root: str | None = None) -> str:
    project_bind = bind_paths(project_root, source_project_root)
    return f"""[Unit]
Description=Project Anchor read-only post-production monitoring refresh
Documentation=https://github.com/baolood/project-anchor

[Service]
Type=oneshot
WorkingDirectory={project_root}
Environment=POST_PRODUCTION_MONITORING_OUTPUT_DIR={output_dir}
ExecStart=/bin/bash {project_root}/scripts/run_post_production_monitoring_once.sh
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=full
BindReadOnlyPaths={project_bind}
ReadWritePaths={output_dir}
"""


def timer_unit(interval_minutes: int) -> str:
    return f"""[Unit]
Description=Run Project Anchor read-only post-production monitoring every {interval_minutes} minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec={interval_minutes}min
AccuracySec=30s
Persistent=true
Unit={SERVICE_NAME}

[Install]
WantedBy=timers.target
"""


def validate_units(service_text: str, timer_text: str) -> list[str]:
    errors: list[str] = []
    combined = service_text + "\n" + timer_text
    forbidden = [
        "production.env",
        "execute_exactly_one_production_request.py",
        "reconcile_production_post_send_readonly.py",
        "curl ",
        "wget ",
        "ssh ",
        "scp ",
    ]
    for token in forbidden:
        if token in combined:
            errors.append(f"forbidden token present: {token}")
    required = [
        "run_post_production_monitoring_once.sh",
        "POST_PRODUCTION_MONITORING_OUTPUT_DIR",
        DEFAULT_OUTPUT_DIR,
        "NoNewPrivileges=true",
        "ProtectSystem=full",
        "BindReadOnlyPaths=",
    ]
    for token in required:
        if token not in combined:
            errors.append(f"required token missing: {token}")
    return errors


def markdown(report: dict[str, object]) -> str:
    checks = report["checks"]
    assert isinstance(checks, list)
    check_lines = "\n".join(
        f"- {item['name']}: {item['result']} ({item['evidence']})" for item in checks
    )
    boundary = report["boundary"]
    assert isinstance(boundary, dict)
    boundary_lines = "\n".join(f"- {key}: {value}" for key, value in boundary.items())
    return f"""# Post Production Monitoring Timer Unit Build

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- service: {report["service_unit"]}
- timer: {report["timer_unit"]}
- output dir: {report["output_dir"]}
- interval minutes: {report["interval_minutes"]}

## Checks

{check_lines}

## Boundary

{boundary_lines}
"""


def build_report(
    project_root: str,
    source_project_root: str | None,
    output_dir: str,
    interval_minutes: int,
    service_text: str,
    timer_text: str,
    errors: list[str],
) -> dict[str, object]:
    checks = [
        {
            "name": "service_invokes_monitoring_once",
            "result": "PASS" if "run_post_production_monitoring_once.sh" in service_text else "FAIL",
            "evidence": "service unit calls the existing read-only monitoring command",
        },
        {
            "name": "runtime_output_dir_configured",
            "result": "PASS" if output_dir in service_text else "FAIL",
            "evidence": "service unit writes reports to the runtime output directory",
        },
        {
            "name": "systemd_safety_hardening_present",
            "result": (
                "PASS"
                if "NoNewPrivileges=true" in service_text and "ProtectSystem=full" in service_text
                else "FAIL"
            ),
            "evidence": "service unit includes narrow systemd safety hardening with project-root read-only binding",
        },
        {
            "name": "timer_cadence_configured",
            "result": "PASS" if f"OnUnitActiveSec={interval_minutes}min" in timer_text else "FAIL",
            "evidence": "timer unit has the expected refresh cadence",
        },
        {
            "name": "forbidden_execution_tokens_absent",
            "result": "PASS" if not errors else "FAIL",
            "evidence": "unit content avoids credential, send, reconciliation, curl, ssh, and scp paths",
        },
    ]
    result = "PASS" if all(item["result"] == "PASS" for item in checks) else "BLOCKED"
    return {
        "generated_at": utc_now(),
        "result": result,
        "service_unit": SERVICE_NAME,
        "timer_unit": TIMER_NAME,
        "project_root": project_root,
        "source_project_root": source_project_root,
        "output_dir": output_dir,
        "interval_minutes": interval_minutes,
        "checks": checks,
        "errors": errors,
        "boundary": {
            "credential_file_read": "NO",
            "secret_value_disclosed": "NO",
            "production_signing_executed": "NO",
            "production_http_network_attempted": "NO",
            "new_production_request_sent": "NO",
            "second_production_request_sent": "NO",
            "canary_rerun": "NO",
            "runtime_modified_by_builder": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default="/root/project-anchor")
    parser.add_argument("--source-project-root", default=None)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--interval-minutes", type=int, default=15)
    parser.add_argument("--unit-dir", required=True)
    parser.add_argument("--report-dir", default="reports")
    args = parser.parse_args()

    if args.interval_minutes < 1:
        raise SystemExit("interval minutes must be >= 1")

    unit_dir = Path(args.unit_dir)
    report_dir = Path(args.report_dir)
    unit_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    service_text = service_unit(args.project_root, args.output_dir, args.source_project_root)
    timer_text = timer_unit(args.interval_minutes)
    errors = validate_units(service_text, timer_text)

    service_path = unit_dir / SERVICE_NAME
    timer_path = unit_dir / TIMER_NAME
    service_path.write_text(service_text, encoding="utf-8")
    timer_path.write_text(timer_text, encoding="utf-8")

    report = build_report(
        args.project_root,
        args.source_project_root,
        args.output_dir,
        args.interval_minutes,
        service_text,
        timer_text,
        errors,
    )
    (report_dir / "post_production_monitoring_timer_validation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (report_dir / "post_production_monitoring_timer_validation.md").write_text(
        markdown(report),
        encoding="utf-8",
    )

    print("[Post Production Monitoring Timer Unit Build]")
    print(f"service: {service_path}")
    print(f"timer: {timer_path}")
    print(f"result: {report['result']}")
    print("credential_file_read: NO")
    print("new_production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
