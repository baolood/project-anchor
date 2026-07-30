#!/usr/bin/env python3
"""Run the read-only post-production monitoring snapshot.

This runner is intentionally narrow. It refreshes repository evidence only and
records a run report. It does not read credentials, sign, open sockets, query an
exchange, send orders, rerun canaries, or change runtime/go-live state.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
OUTPUT_DIR = Path(os.environ.get("POST_PRODUCTION_MONITORING_OUTPUT_DIR", str(REPORTS_DIR))).expanduser()
SNAPSHOT_SCRIPT = ROOT / "scripts" / "generate_post_production_monitoring_snapshot.py"
RUN_JSON_OUT = OUTPUT_DIR / "post_production_monitoring_run.json"
RUN_MD_OUT = OUTPUT_DIR / "post_production_monitoring_run.md"
SNAPSHOT_JSON_OUT = OUTPUT_DIR / "post_production_monitoring_snapshot.json"
SNAPSHOT_MD_OUT = OUTPUT_DIR / "post_production_monitoring_snapshot.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_snapshot_module() -> Any:
    spec = importlib.util.spec_from_file_location("post_production_monitoring_snapshot", SNAPSHOT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load post-production monitoring snapshot module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(name: str, passed: bool, evidence: str) -> dict[str, str]:
    return {
        "name": name,
        "result": "PASS" if passed else "FAIL",
        "evidence": evidence,
    }


def build_run_report(snapshot_report: dict[str, Any], snapshot_exit_code: int) -> tuple[dict[str, Any], int]:
    boundary = snapshot_report.get("boundary") if isinstance(snapshot_report.get("boundary"), dict) else {}
    snapshot_data = (
        snapshot_report.get("snapshot") if isinstance(snapshot_report.get("snapshot"), dict) else {}
    )
    checks = [
        check(
            "snapshot_result_pass",
            snapshot_exit_code == 0 and snapshot_report.get("result") == "PASS",
            "post-production monitoring snapshot returned PASS",
        ),
        check(
            "monitoring_status_safe",
            snapshot_report.get("status") == "MONITORING_READY_CONTINUOUS_TRADING_DISABLED",
            "monitoring is ready while continuous trading remains disabled",
        ),
        check(
            "exactly_one_production_order_still_recorded",
            snapshot_data.get("matching_filled_order_count") == 1
            and snapshot_data.get("symbol_order_count_in_window") == 1,
            "exactly one filled BTCUSDT order remains recorded in the authorized window",
        ),
        check(
            "continuous_runtime_disabled",
            snapshot_data.get("continuous_runtime_enabled") == "NO"
            and snapshot_data.get("automatic_trading_enabled") == "NO",
            "continuous runtime and automatic trading remain disabled",
        ),
        check(
            "runner_did_not_touch_runtime_boundaries",
            boundary.get("credential_file_read") == "NO"
            and boundary.get("production_signing_executed") == "NO"
            and boundary.get("production_http_network_attempted") == "NO"
            and boundary.get("new_production_request_sent") == "NO"
            and boundary.get("second_production_request_sent") == "NO"
            and boundary.get("runtime_modified") == "NO",
            "runner kept credential/signing/network/request/runtime boundaries closed",
        ),
        check(
            "go_live_and_live_trading_still_no_go",
            boundary.get("go_live") == "NO-GO" and boundary.get("live_trading") == "NO-GO",
            "go-live and live trading remain NO-GO",
        ),
    ]
    failed = [item for item in checks if item["result"] != "PASS"]
    result = "PASS" if not failed else "BLOCKED"
    report = {
        "generated_at": utc_now(),
        "result": result,
        "status": (
            "POST_PRODUCTION_MONITORING_RUN_READY"
            if result == "PASS"
            else "POST_PRODUCTION_MONITORING_RUN_BLOCKED"
        ),
        "checks": checks,
        "snapshot_status": snapshot_report.get("status"),
        "snapshot_result": snapshot_report.get("result"),
        "snapshot_generated_at": snapshot_report.get("generated_at"),
        "inputs": {
            "snapshot_script": str(SNAPSHOT_SCRIPT.relative_to(ROOT)),
            "snapshot_json": str(SNAPSHOT_JSON_OUT),
            "snapshot_markdown": str(SNAPSHOT_MD_OUT),
        },
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
        "next_gate": "POST_PRODUCTION_MONITORING_SURFACE_OR_OPERATOR_FREEZE",
    }
    return report, 0 if result == "PASS" else 1


def markdown(report: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- {item['name']}: {item['result']} ({item['evidence']})" for item in report["checks"]
    )
    boundary = "\n".join(f"- {key}: {value}" for key, value in report["boundary"].items())
    return f"""# Post Production Monitoring Run

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- status: {report["status"]}
- snapshot result: {report["snapshot_result"]}
- snapshot status: {report["snapshot_status"]}
- snapshot generated at: {report["snapshot_generated_at"]}
- next gate: {report["next_gate"]}

## Checks

{checks}

## Boundary

{boundary}
"""


def main() -> int:
    snapshot_module = load_snapshot_module()
    snapshot_report, snapshot_exit_code = snapshot_module.build_report()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_JSON_OUT.write_text(
        json.dumps(snapshot_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    SNAPSHOT_MD_OUT.write_text(snapshot_module.markdown(snapshot_report), encoding="utf-8")

    run_report, exit_code = build_run_report(snapshot_report, snapshot_exit_code)
    RUN_JSON_OUT.write_text(json.dumps(run_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    RUN_MD_OUT.write_text(markdown(run_report), encoding="utf-8")

    print("[Post Production Monitoring Run]")
    print(f"output dir: {OUTPUT_DIR}")
    print(f"run JSON: {RUN_JSON_OUT}")
    print(f"run Markdown: {RUN_MD_OUT}")
    print(f"snapshot JSON: {SNAPSHOT_JSON_OUT}")
    print(f"snapshot Markdown: {SNAPSHOT_MD_OUT}")
    print(f"result: {run_report['result']}")
    print(f"status: {run_report['status']}")
    print(f"new_production_request_sent: {run_report['boundary']['new_production_request_sent']}")
    print(f"go_live: {run_report['boundary']['go_live']}")
    print(f"live_trading: {run_report['boundary']['live_trading']}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
