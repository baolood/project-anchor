#!/usr/bin/env python3
"""Validate the cloud operations evidence layout without reading secrets."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUNTIME_REQUIRED = [
    "post_production_monitoring_run.json",
    "post_production_monitoring_timer_runtime_validation.json",
    "post_production_monitoring_timer_stability_validation.json",
    "post_production_monitoring_telegram_send_result.json",
]
SOURCE_REQUIRED = [
    "production_exactly_one_send_result.json",
    "post_production_send_reconciliation.json",
    "production_post_send_readonly_reconciliation.json",
    "post_production_operations_decision.json",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def exists_map(directory: Path, names: list[str]) -> dict[str, bool]:
    return {name: (directory / name).exists() for name in names}


def boundary(report: dict[str, Any], key: str) -> Any:
    data = report.get("boundary")
    return data.get(key) if isinstance(data, dict) else None


def pass_fail(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def build_report(runtime_dir: Path, source_dir: Path) -> dict[str, Any]:
    runtime_files = exists_map(runtime_dir, RUNTIME_REQUIRED)
    source_files = exists_map(source_dir, SOURCE_REQUIRED)
    monitoring = load_json(runtime_dir / "post_production_monitoring_run.json")
    timer_runtime = load_json(runtime_dir / "post_production_monitoring_timer_runtime_validation.json")
    timer_stability = load_json(runtime_dir / "post_production_monitoring_timer_stability_validation.json")
    telegram = load_json(runtime_dir / "post_production_monitoring_telegram_send_result.json")
    send = load_json(source_dir / "production_exactly_one_send_result.json")
    readonly = load_json(source_dir / "production_post_send_readonly_reconciliation.json")
    decision = load_json(source_dir / "post_production_operations_decision.json")

    send_terminal = send.get("terminal") if isinstance(send.get("terminal"), dict) else {}
    readonly_orders = (
        readonly.get("order_reconciliation")
        if isinstance(readonly.get("order_reconciliation"), dict)
        else {}
    )
    decision_summary = decision.get("summary") if isinstance(decision.get("summary"), dict) else {}
    telegram_ok = (
        telegram.get("result") == "PASS"
        and telegram.get("send_result") == "DELIVERED"
    ) or (
        telegram.get("result") == "BLOCKED"
        and telegram.get("send_attempted") == "NO"
    )

    checks = {
        "runtime_monitoring_reports_present": pass_fail(all(runtime_files.values())),
        "source_production_evidence_present": pass_fail(all(source_files.values())),
        "monitoring_run_pass": pass_fail(monitoring.get("result") == "PASS"),
        "timer_runtime_pass": pass_fail(timer_runtime.get("result") == "PASS"),
        "timer_stability_pass": pass_fail(timer_stability.get("result") == "PASS"),
        "telegram_sender_fail_closed_or_delivered": pass_fail(telegram_ok),
        "production_send_pass": pass_fail(send.get("result") == "PASS" and send.get("success") is True),
        "production_terminal_filled": pass_fail(
            send_terminal.get("external_status") == "FILLED"
            and send_terminal.get("external_order_id_present") is True
        ),
        "readonly_reconciliation_pass": pass_fail(readonly.get("result") == "PASS"),
        "exactly_one_matching_order": pass_fail(
            readonly_orders.get("matching_filled_order_count") == 1
            and readonly_orders.get("symbol_order_count_in_window") == 1
        ),
        "operations_decision_pass": pass_fail(decision.get("result") == "PASS"),
        "decision_records_single_production_request": pass_fail(
            decision_summary.get("production_request_sent") == "YES"
            and decision_summary.get("matching_filled_order_count") == 1
        ),
        "no_new_request_from_monitoring": pass_fail(
            boundary(monitoring, "new_production_request_sent") == "NO"
        ),
        "no_second_request_from_monitoring": pass_fail(
            boundary(monitoring, "second_production_request_sent") == "NO"
        ),
        "go_live_no_go": pass_fail(
            boundary(monitoring, "go_live") == "NO-GO"
            and boundary(readonly, "go_live") == "NO-GO"
        ),
        "live_trading_no_go": pass_fail(
            boundary(monitoring, "live_trading") == "NO-GO"
            and boundary(readonly, "live_trading") == "NO-GO"
        ),
    }
    result = "PASS" if all(value == "PASS" for value in checks.values()) else "BLOCKED"
    return {
        "generated_at": utc_now(),
        "result": result,
        "status": (
            "CLOUD_OPERATIONS_EVIDENCE_LAYOUT_VALID"
            if result == "PASS"
            else "CLOUD_OPERATIONS_EVIDENCE_LAYOUT_BLOCKED"
        ),
        "runtime_reports_dir": str(runtime_dir),
        "source_reports_dir": str(source_dir),
        "layout": {
            "runtime_reports_role": "timer output and current monitoring status",
            "source_reports_role": "repository historical production send and reconciliation evidence",
            "single_directory_layout_required": "NO",
        },
        "runtime_files": runtime_files,
        "source_files": source_files,
        "summary": {
            "monitoring_generated_at": monitoring.get("generated_at"),
            "monitoring_result": monitoring.get("result"),
            "timer_runtime_result": timer_runtime.get("result"),
            "timer_stability_result": timer_stability.get("result"),
            "timer_consecutive_successes": timer_stability.get(
                "latest_consecutive_success_count"
            ),
            "telegram_sender_result": telegram.get("result"),
            "production_send_result": send.get("result"),
            "production_order_status": send_terminal.get("external_status"),
            "matching_filled_order_count": readonly_orders.get("matching_filled_order_count"),
            "symbol_order_count_in_window": readonly_orders.get("symbol_order_count_in_window"),
            "operations_decision": decision.get("decision"),
        },
        "checks": checks,
        "boundary": {
            "production_env_read": "NO",
            "secret_value_disclosed": "NO",
            "production_signing_executed": "NO",
            "production_http_network_attempted": "NO",
            "new_production_request_sent": "NO",
            "second_production_request_sent": "NO",
            "canary_rerun": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }


def markdown(report: dict[str, Any]) -> str:
    runtime_files = "\n".join(
        f"- {name}: {'PRESENT' if present else 'MISSING'}"
        for name, present in report["runtime_files"].items()
    )
    source_files = "\n".join(
        f"- {name}: {'PRESENT' if present else 'MISSING'}"
        for name, present in report["source_files"].items()
    )
    summary = "\n".join(f"- {key}: {value}" for key, value in report["summary"].items())
    checks = "\n".join(f"- {key}: {value}" for key, value in report["checks"].items())
    boundary = "\n".join(f"- {key}: {value}" for key, value in report["boundary"].items())
    return f"""# Cloud Operations Evidence Layout Audit

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- status: {report["status"]}
- runtime reports dir: `{report["runtime_reports_dir"]}`
- source reports dir: `{report["source_reports_dir"]}`
- single directory layout required: {report["layout"]["single_directory_layout_required"]}

## Runtime Reports

{runtime_files}

## Source Evidence Reports

{source_files}

## Summary

{summary}

## Checks

{checks}

## Boundary

{boundary}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-reports-dir", type=Path, default=Path("/var/lib/project-anchor/reports"))
    parser.add_argument("--source-reports-dir", type=Path, default=Path("/root/project-anchor/reports"))
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--markdown-out", type=Path, default=None)
    args = parser.parse_args()

    report = build_report(args.runtime_reports_dir, args.source_reports_dir)
    json_out = args.json_out or args.runtime_reports_dir / "cloud_operations_evidence_layout_audit.json"
    md_out = args.markdown_out or args.runtime_reports_dir / "cloud_operations_evidence_layout_audit.md"
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_out.write_text(markdown(report), encoding="utf-8")

    print("[Cloud Operations Evidence Layout Audit]")
    print(f"result: {report['result']}")
    print(f"status: {report['status']}")
    print(f"runtime reports dir: {report['runtime_reports_dir']}")
    print(f"source reports dir: {report['source_reports_dir']}")
    print(f"monitoring result: {report['summary'].get('monitoring_result')}")
    print(f"timer stability result: {report['summary'].get('timer_stability_result')}")
    print(f"production send result: {report['summary'].get('production_send_result')}")
    print(f"matching filled order count: {report['summary'].get('matching_filled_order_count')}")
    print("production_env_read: NO")
    print("secret_value_disclosed: NO")
    print("new_production_request_sent: NO")
    print("second_production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
