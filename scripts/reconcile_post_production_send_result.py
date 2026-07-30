#!/usr/bin/env python3
"""Reconcile the exactly-one production send result from repository evidence.

This script is intentionally read-only. It does not read production credentials,
does not sign, does not open sockets, and does not send any production request.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
SEND_RESULT = REPORTS_DIR / "production_exactly_one_send_result.json"
WINDOW_PLAN = REPORTS_DIR / "production_request_send_window_plan.json"
FRESH_DECISION = REPORTS_DIR / "fresh_production_send_readiness_decision.json"
RISK_LIMITS = ROOT / "config" / "production_risk_limits.template.json"
JSON_OUT = REPORTS_DIR / "post_production_send_reconciliation.json"
MD_OUT = REPORTS_DIR / "post_production_send_reconciliation.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - reconciliation reports failures cleanly.
        return {}, f"{path.relative_to(ROOT)}:UNREADABLE:{type(exc).__name__}"
    if not isinstance(data, dict):
        return {}, f"{path.relative_to(ROOT)}:NOT_OBJECT"
    return data, None


def yes(value: Any) -> bool:
    return value is True or str(value).strip().upper() == "YES"


def no(value: Any) -> bool:
    return value is False or str(value).strip().upper() == "NO"


def expected_idempotency_key(risk_limits: dict[str, Any]) -> str:
    notional = str(risk_limits.get("AUTHORIZED_MAX_NOTIONAL") or "").strip()
    if notional:
        return f"production:ops_manual:BTCUSDT:BUY:{notional}:first-bounded-production-request:v1"
    return ""


def build_report() -> tuple[dict[str, Any], int]:
    send, send_error = read_json(SEND_RESULT)
    window, window_error = read_json(WINDOW_PLAN)
    fresh, fresh_error = read_json(FRESH_DECISION)
    risk_limits, risk_error = read_json(RISK_LIMITS)

    errors = [err for err in [send_error, window_error, fresh_error, risk_error] if err]
    checks: list[dict[str, str]] = []

    def check(name: str, passed: bool, evidence: str) -> None:
        checks.append({"name": name, "result": "PASS" if passed else "FAIL", "evidence": evidence})

    terminal = send.get("terminal", {}) if isinstance(send.get("terminal"), dict) else {}
    boundary = send.get("boundary", {}) if isinstance(send.get("boundary"), dict) else {}
    request = send.get("request", {}) if isinstance(send.get("request"), dict) else {}
    window_request = window.get("planned_request", {}) if isinstance(window.get("planned_request"), dict) else {}

    expected_key = expected_idempotency_key(risk_limits)
    observed_key = str(request.get("idempotency_key") or "")

    check("send_result_pass", send.get("result") == "PASS" and send.get("success") is True, "send report result is PASS")
    check("production_request_attempted", yes(boundary.get("production_request_attempted")), "production request was attempted exactly by the send report")
    check("production_request_accepted", yes(boundary.get("production_request_accepted")), "production request was accepted")
    check("http_200", terminal.get("http_status") == 200, "terminal HTTP status is 200")
    check("terminal_filled", terminal.get("external_status") == "FILLED", "terminal external status is FILLED")
    check("external_order_id_present", terminal.get("external_order_id_present") is True, "external order id presence is true")
    check("idempotency_key_matches_risk_limit", observed_key == expected_key, "idempotency key matches current max notional risk limit")
    check("window_plan_pass", window.get("result") == "PASS" and window.get("plan_valid") is True, "send window plan is PASS")
    check("fresh_decision_pass", fresh.get("result") == "PASS", "fresh send readiness decision was PASS")
    check("window_plan_did_not_authorize_send", window.get("send_authorized") is False, "window plan remains non-authorizing")
    check("fresh_decision_did_not_authorize_send", fresh.get("send_authorized_by_this_decision") is False, "fresh readiness decision remains non-authorizing")
    check("bounded_symbol", request.get("symbol") == "BTCUSDT" == window_request.get("symbol"), "symbol is BTCUSDT")
    check("bounded_side", request.get("side") == "BUY" == window_request.get("side"), "side is BUY")
    check("bounded_notional", str(request.get("max_notional")) == "10" == str(window_request.get("max_notional")), "max notional is 10")
    check("exactly_one_order_count", str(window_request.get("max_order_count")) == "1", "max order count is one")
    check("no_secret_disclosure", no(boundary.get("secret_value_disclosed")) and no(boundary.get("secret_length_disclosed")) and no(boundary.get("secret_prefix_suffix_disclosed")) and no(boundary.get("secret_hash_disclosed")), "secret values, lengths, prefixes/suffixes, and hashes were not disclosed")
    check("authorization_header_not_disclosed", no(boundary.get("authorization_header_value_disclosed")), "Authorization header value was not disclosed")
    check("no_canary_rerun", no(boundary.get("canary_rerun")), "canary was not rerun")
    check("go_live_no_go", boundary.get("go_live") == "NO-GO", "go-live remains NO-GO")
    check("live_trading_no_go", boundary.get("live_trading") == "NO-GO", "live trading remains NO-GO")

    failed = [item for item in checks if item["result"] != "PASS"]
    result = "PASS" if not errors and not failed else "BLOCKED"
    report = {
        "generated_at": utc_now(),
        "result": result,
        "errors": errors,
        "checks": checks,
        "summary": {
            "production_send_result": send.get("result"),
            "production_send_success": send.get("success"),
            "production_request_attempted": boundary.get("production_request_attempted"),
            "production_request_accepted": boundary.get("production_request_accepted"),
            "http_status": terminal.get("http_status"),
            "external_status": terminal.get("external_status"),
            "external_order_id_present": terminal.get("external_order_id_present"),
            "idempotency_key": observed_key,
            "symbol": request.get("symbol"),
            "side": request.get("side"),
            "max_notional": request.get("max_notional"),
        },
        "inputs": {
            "send_result": str(SEND_RESULT.relative_to(ROOT)),
            "window_plan": str(WINDOW_PLAN.relative_to(ROOT)),
            "fresh_decision": str(FRESH_DECISION.relative_to(ROOT)),
            "risk_limits": str(RISK_LIMITS.relative_to(ROOT)),
        },
        "boundary": {
            "secret_value_disclosed": "NO",
            "secret_length_disclosed": "NO",
            "secret_prefix_suffix_disclosed": "NO",
            "secret_hash_disclosed": "NO",
            "authorization_header_value_disclosed": "NO",
            "new_production_request_sent_by_reconciliation": "NO",
            "second_production_request_sent": "NO",
            "retry_performed": "NO",
            "canary_rerun": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
        "next_gate": "POST_PRODUCTION_SEND_MONITORING_AND_BALANCE_RECONCILIATION",
    }
    return report, 0 if result == "PASS" else 1


def markdown(report: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- {item['name']}: {item['result']} ({item['evidence']})" for item in report["checks"]
    )
    errors = "\n".join(f"- {item}" for item in report["errors"]) or "- none"
    summary = "\n".join(f"- {key}: {value}" for key, value in report["summary"].items())
    boundary = "\n".join(f"- {key}: {value}" for key, value in report["boundary"].items())
    return f"""# Post Production Send Reconciliation

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- next gate: {report["next_gate"]}

## Summary

{summary}

## Checks

{checks}

## Errors

{errors}

## Boundary

{boundary}
"""


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report, exit_code = build_report()
    JSON_OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(markdown(report), encoding="utf-8")
    print("[Post Production Send Reconciliation]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(f"production_send_result: {report['summary']['production_send_result']}")
    print(f"external_status: {report['summary']['external_status']}")
    print(f"external_order_id_present: {report['summary']['external_order_id_present']}")
    print("new_production_request_sent_by_reconciliation: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
