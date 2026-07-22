#!/usr/bin/env python3
"""Decide fresh production send readiness from existing evidence only.

This script does not read credentials, sign payloads, resolve DNS, open sockets,
enable HTTP/network execution, or send a production request. It turns the latest
pre-send evidence into a short, reproducible decision for the exactly-one
production request send gate.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
HANDOFF = REPORTS_DIR / "production_execution_handoff_snapshot.json"
PRE_SEND = REPORTS_DIR / "production_pre_send_readiness_aggregation.json"
WINDOW_PLAN = REPORTS_DIR / "production_request_send_window_plan.json"
FINAL_RUNNER = REPORTS_DIR / "final_production_send_runner.json"
RISK_LIMITS = ROOT / "config" / "production_risk_limits.template.json"
JSON_OUT = REPORTS_DIR / "fresh_production_send_readiness_decision.json"
MD_OUT = REPORTS_DIR / "fresh_production_send_readiness_decision.md"


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def fmt(ts: datetime) -> str:
    return ts.isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - decision must fail closed.
        return {}, f"{path.relative_to(ROOT)}:UNREADABLE:{type(exc).__name__}"
    if not isinstance(data, dict):
        return {}, f"{path.relative_to(ROOT)}:NOT_OBJECT"
    return data, None


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def check(name: str, passed: bool, evidence: str) -> dict[str, str]:
    return {
        "name": name,
        "result": "PASS" if passed else "FAIL",
        "evidence": evidence,
    }


def build_report() -> tuple[dict[str, Any], int]:
    now = utc_now()
    handoff, handoff_error = read_json(HANDOFF)
    pre_send, pre_send_error = read_json(PRE_SEND)
    window, window_error = read_json(WINDOW_PLAN)
    runner, runner_error = read_json(FINAL_RUNNER)
    limits, limits_error = read_json(RISK_LIMITS)
    errors = [
        item
        for item in (
            handoff_error,
            pre_send_error,
            window_error,
            runner_error,
            limits_error,
        )
        if item
    ]

    expires_at = parse_time(window.get("planned_window", {}).get("expires_at"))
    not_before = parse_time(window.get("planned_window", {}).get("not_before"))
    window_current = bool(not_before and expires_at and not_before <= now <= expires_at)
    risk_limit_summary = {
        "market": limits.get("AUTHORIZED_PRODUCTION_MARKET"),
        "symbols": limits.get("AUTHORIZED_PRODUCTION_SYMBOLS"),
        "sides": limits.get("AUTHORIZED_PRODUCTION_SIDES"),
        "max_notional": limits.get("AUTHORIZED_MAX_NOTIONAL"),
        "max_order_count": limits.get("AUTHORIZED_MAX_ORDER_COUNT"),
        "idempotency_policy": limits.get("AUTHORIZED_IDEMPOTENCY_POLICY"),
    }

    checks = [
        check(
            "handoff_ready_for_decision",
            handoff.get("result") == "PASS"
            and handoff.get("handoff_status") == "READY_FOR_DECISION",
            "handoff snapshot PASS / READY_FOR_DECISION",
        ),
        check(
            "pre_send_chain_complete",
            pre_send.get("result") == "PASS"
            and pre_send.get("evidence_chain_complete") is True,
            "pre-send aggregation PASS and complete",
        ),
        check(
            "final_runner_ready",
            runner.get("result") == "PASS"
            and runner.get("default_failure_code")
            == "PRODUCTION_CREDENTIAL_READ_NOT_AUTHORIZED"
            and runner.get("no_execute_failure_code")
            == "PRODUCTION_SEND_EXECUTION_NOT_AUTHORIZED"
            and runner.get("fake_transport_called_once") is True,
            "final runner PASS with fail-closed defaults and fake transport evidence",
        ),
        check(
            "window_plan_valid",
            window.get("result") == "PASS" and window.get("plan_valid") is True,
            "send window plan PASS",
        ),
        check(
            "window_plan_not_authorizing",
            window.get("send_authorized") is False
            and window.get("execution_allowed_by_this_plan") is False,
            "window plan remains non-authorizing",
        ),
        check(
            "fresh_window_current",
            window_current,
            "current time is within the latest planned window",
        ),
        check(
            "production_request_not_sent",
            handoff.get("production_state", {}).get("production_request_sent") is False
            and pre_send.get("boundary", {}).get("production_request_sent") == "NO"
            and runner.get("boundary", {}).get("production_request_sent") == "NO",
            "all evidence says production request has not been sent",
        ),
        check(
            "risk_limits_bounded",
            risk_limit_summary["market"] == "binance_spot"
            and risk_limit_summary["symbols"] == "BTCUSDT"
            and risk_limit_summary["sides"] == "BUY_ONLY"
            and str(risk_limit_summary["max_notional"]) == "4"
            and str(risk_limit_summary["max_order_count"]) == "1",
            "production risk limits remain exactly-one BTCUSDT BUY max notional 4",
        ),
        check(
            "go_live_still_no_go",
            handoff.get("go_live", {}).get("verdict") == "NO-GO"
            and pre_send.get("boundary", {}).get("go_live") == "NO-GO"
            and runner.get("boundary", {}).get("go_live") == "NO-GO",
            "go-live remains NO-GO",
        ),
        check(
            "live_trading_still_no_go",
            handoff.get("boundary", {}).get("live_trading") == "NO-GO"
            and pre_send.get("boundary", {}).get("live_trading") == "NO-GO"
            and runner.get("boundary", {}).get("live_trading") == "NO-GO",
            "live trading remains NO-GO",
        ),
    ]

    ready = not errors and all(item["result"] == "PASS" for item in checks)
    report = {
        "generated_at": fmt(now),
        "result": "PASS" if ready else "FAIL",
        "decision": (
            "READY_FOR_EXACTLY_ONE_PRODUCTION_REQUEST_SEND_WINDOW_OPEN"
            if ready
            else "BLOCKED_FRESH_PRODUCTION_SEND_READINESS_FAILED"
        ),
        "execution_performed_by_this_decision": False,
        "send_authorized_by_this_decision": False,
        "errors": errors,
        "inputs": {
            "handoff": str(HANDOFF.relative_to(ROOT)),
            "pre_send": str(PRE_SEND.relative_to(ROOT)),
            "window_plan": str(WINDOW_PLAN.relative_to(ROOT)),
            "final_runner": str(FINAL_RUNNER.relative_to(ROOT)),
            "risk_limits": str(RISK_LIMITS.relative_to(ROOT)),
        },
        "risk_limit_summary": risk_limit_summary,
        "planned_window": window.get("planned_window", {}),
        "planned_request": window.get("planned_request", {}),
        "checks": checks,
        "boundary": {
            "credential_file_read": "NO",
            "secret_value_disclosed": "NO",
            "production_signing_executed": "NO",
            "authorization_header_generated": "NO",
            "dns_lookup_performed": "NO",
            "socket_opened": "NO",
            "production_http_network_executed": "NO",
            "production_request_sent": "NO",
            "canary_rerun": "NO",
            "runtime_modified": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    return report, 0 if ready else 1


def markdown(report: dict[str, Any]) -> str:
    checks = "\n".join(
        "- {name}: {result} ({evidence})".format(**item)
        for item in report["checks"]
    )
    errors = "\n".join(f"- {item}" for item in report["errors"]) or "- none"
    risk = "\n".join(
        f"- {key}: {value}" for key, value in report["risk_limit_summary"].items()
    )
    window = "\n".join(
        f"- {key}: {value}" for key, value in report["planned_window"].items()
    )
    request = "\n".join(
        f"- {key}: {value}" for key, value in report["planned_request"].items()
    )
    return f"""# Fresh Production Send Readiness Decision

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- decision: {report["decision"]}
- send authorized by this decision: {str(report["send_authorized_by_this_decision"]).lower()}
- execution performed by this decision: {str(report["execution_performed_by_this_decision"]).lower()}

## Risk Limit Summary

{risk}

## Planned Window

{window}

## Planned Request

{request}

## Checks

{checks}

## Errors

{errors}

## Boundary

- credential file read: {report["boundary"]["credential_file_read"]}
- secret value disclosed: {report["boundary"]["secret_value_disclosed"]}
- production signing executed: {report["boundary"]["production_signing_executed"]}
- Authorization header generated: {report["boundary"]["authorization_header_generated"]}
- DNS lookup performed: {report["boundary"]["dns_lookup_performed"]}
- socket opened: {report["boundary"]["socket_opened"]}
- production HTTP/network executed: {report["boundary"]["production_http_network_executed"]}
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

    print("[Fresh Production Send Readiness Decision]")
    print(f"result: {report['result']}")
    print(f"decision: {report['decision']}")
    print("credential_file_read: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    if report["errors"]:
        print("errors:")
        for error in report["errors"]:
            print(f"- {error}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
