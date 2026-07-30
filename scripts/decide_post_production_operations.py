#!/usr/bin/env python3
"""Decide the post-production-send operations state from repository evidence.

This is a read-only operations decision. It does not read credentials, sign,
open sockets, send orders, enable go-live, or enable live trading.
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
POST_SEND_RECONCILIATION = REPORTS_DIR / "post_production_send_reconciliation.json"
READONLY_RECONCILIATION = REPORTS_DIR / "production_post_send_readonly_reconciliation.json"
EXECUTION_READINESS = REPORTS_DIR / "production_execution_readiness.json"
RISK_LIMITS = ROOT / "config" / "production_risk_limits.template.json"
JSON_OUT = REPORTS_DIR / "post_production_operations_decision.json"
MD_OUT = REPORTS_DIR / "post_production_operations_decision.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - decision reports missing evidence cleanly.
        return {}, f"{path.relative_to(ROOT)}:UNREADABLE:{type(exc).__name__}"
    if not isinstance(data, dict):
        return {}, f"{path.relative_to(ROOT)}:NOT_OBJECT"
    return data, None


def boundary_value(report: dict[str, Any], key: str) -> Any:
    boundary = report.get("boundary")
    if isinstance(boundary, dict):
        return boundary.get(key)
    return None


def build_report() -> tuple[dict[str, Any], int]:
    send, send_error = read_json(SEND_RESULT)
    post_recon, post_recon_error = read_json(POST_SEND_RECONCILIATION)
    readonly_recon, readonly_recon_error = read_json(READONLY_RECONCILIATION)
    readiness, readiness_error = read_json(EXECUTION_READINESS)
    risk_limits, risk_limits_error = read_json(RISK_LIMITS)

    errors = [
        item
        for item in [
            send_error,
            post_recon_error,
            readonly_recon_error,
            readiness_error,
            risk_limits_error,
        ]
        if item
    ]
    checks: list[dict[str, str]] = []

    def check(name: str, passed: bool, evidence: str) -> None:
        checks.append({"name": name, "result": "PASS" if passed else "FAIL", "evidence": evidence})

    send_terminal = send.get("terminal", {}) if isinstance(send.get("terminal"), dict) else {}
    readonly_orders = (
        readonly_recon.get("order_reconciliation", {})
        if isinstance(readonly_recon.get("order_reconciliation"), dict)
        else {}
    )
    readonly_account = (
        readonly_recon.get("account_reconciliation", {})
        if isinstance(readonly_recon.get("account_reconciliation"), dict)
        else {}
    )

    check(
        "production_send_pass",
        send.get("result") == "PASS" and send.get("success") is True,
        "exactly-one production send report is PASS",
    )
    check(
        "production_terminal_filled",
        send_terminal.get("http_status") == 200
        and send_terminal.get("external_status") == "FILLED"
        and send_terminal.get("external_order_id_present") is True,
        "terminal evidence is HTTP 200 / FILLED / external order id present",
    )
    check(
        "post_send_reconciliation_pass",
        post_recon.get("result") == "PASS",
        "repository evidence reconciliation is PASS",
    )
    check(
        "readonly_reconciliation_pass",
        readonly_recon.get("result") == "PASS",
        "Binance read-only reconciliation is PASS",
    )
    check(
        "exactly_one_matching_order",
        readonly_orders.get("matching_filled_order_count") == 1
        and readonly_orders.get("symbol_order_count_in_window") == 1,
        "exactly one matching FILLED BTCUSDT BUY order in the authorized window",
    )
    check(
        "balance_rows_visible",
        readonly_account.get("usdt_balance_row_present") is True
        and readonly_account.get("btc_balance_row_present") is True,
        "USDT and BTC balance rows are visible without recording amounts",
    )
    check(
        "risk_limits_remain_bounded",
        risk_limits.get("AUTHORIZED_PRODUCTION_SYMBOLS") == "BTCUSDT"
        and risk_limits.get("AUTHORIZED_PRODUCTION_SIDES") == "BUY_ONLY"
        and str(risk_limits.get("AUTHORIZED_MAX_NOTIONAL")) == "10"
        and str(risk_limits.get("AUTHORIZED_MAX_ORDER_COUNT")) == "1",
        "risk limits remain BTCUSDT BUY_ONLY max_notional 10 max_order_count 1",
    )
    check(
        "execution_readiness_not_go_live",
        readiness.get("result") == "BLOCKED"
        and "go-live not authorized" in set(readiness.get("blockers") or [])
        and "live trading not authorized" in set(readiness.get("blockers") or []),
        "production execution readiness remains blocked for go-live/live trading",
    )
    check(
        "no_second_request",
        boundary_value(readonly_recon, "second_production_request_sent") == "NO"
        and boundary_value(post_recon, "second_production_request_sent") == "NO",
        "post-send reconciliation did not send a second request",
    )
    check(
        "no_secret_disclosure",
        boundary_value(send, "secret_value_disclosed") == "NO"
        and boundary_value(readonly_recon, "secret_value_disclosed") == "NO",
        "send and read-only reconciliation reports disclose no secret values",
    )
    check(
        "go_live_no_go",
        boundary_value(send, "go_live") == "NO-GO"
        and boundary_value(readonly_recon, "go_live") == "NO-GO",
        "go-live remains NO-GO",
    )
    check(
        "live_trading_no_go",
        boundary_value(send, "live_trading") == "NO-GO"
        and boundary_value(readonly_recon, "live_trading") == "NO-GO",
        "live trading remains NO-GO",
    )

    failed = [item for item in checks if item["result"] != "PASS"]
    decision = (
        "FIRST_PRODUCTION_VALIDATION_COMPLETE_CONTINUOUS_TRADING_DISABLED"
        if not errors and not failed
        else "POST_PRODUCTION_OPERATIONS_DECISION_BLOCKED"
    )
    result = "PASS" if decision.startswith("FIRST_PRODUCTION_VALIDATION") else "BLOCKED"
    report = {
        "generated_at": utc_now(),
        "result": result,
        "decision": decision,
        "errors": errors,
        "checks": checks,
        "summary": {
            "production_request_sent": "YES",
            "production_order_status": send_terminal.get("external_status"),
            "matching_filled_order_count": readonly_orders.get("matching_filled_order_count"),
            "symbol_order_count_in_window": readonly_orders.get("symbol_order_count_in_window"),
            "risk_limit_symbol": risk_limits.get("AUTHORIZED_PRODUCTION_SYMBOLS"),
            "risk_limit_side": risk_limits.get("AUTHORIZED_PRODUCTION_SIDES"),
            "risk_limit_max_notional": risk_limits.get("AUTHORIZED_MAX_NOTIONAL"),
            "risk_limit_max_order_count": risk_limits.get("AUTHORIZED_MAX_ORDER_COUNT"),
            "continuous_runtime_enabled": "NO",
            "automatic_trading_enabled": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
        "inputs": {
            "send_result": str(SEND_RESULT.relative_to(ROOT)),
            "post_send_reconciliation": str(POST_SEND_RECONCILIATION.relative_to(ROOT)),
            "readonly_reconciliation": str(READONLY_RECONCILIATION.relative_to(ROOT)),
            "execution_readiness": str(EXECUTION_READINESS.relative_to(ROOT)),
            "risk_limits": str(RISK_LIMITS.relative_to(ROOT)),
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
        "next_gate": "POST_PRODUCTION_MONITORING_DASHBOARD_OR_FREEZE_DECISION",
    }
    return report, 0 if result == "PASS" else 1


def markdown(report: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- {item['name']}: {item['result']} ({item['evidence']})" for item in report["checks"]
    )
    errors = "\n".join(f"- {item}" for item in report["errors"]) or "- none"
    summary = "\n".join(f"- {key}: {value}" for key, value in report["summary"].items())
    boundary = "\n".join(f"- {key}: {value}" for key, value in report["boundary"].items())
    return f"""# Post Production Operations Decision

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- decision: {report["decision"]}
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
    print("[Post Production Operations Decision]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(f"decision: {report['decision']}")
    print(f"production_request_sent: {report['summary']['production_request_sent']}")
    print(f"production_order_status: {report['summary']['production_order_status']}")
    print("new_production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
