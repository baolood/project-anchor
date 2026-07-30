#!/usr/bin/env python3
"""Generate a read-only post-production monitoring snapshot.

This snapshot reads only repository evidence files. It does not read
credentials, sign, open sockets, send requests, rerun canaries, or change
runtime/go-live state.
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
READONLY_RECONCILIATION = REPORTS_DIR / "production_post_send_readonly_reconciliation.json"
OPERATIONS_DECISION = REPORTS_DIR / "post_production_operations_decision.json"
EXECUTION_READINESS = REPORTS_DIR / "production_execution_readiness.json"
RISK_LIMITS = ROOT / "config" / "production_risk_limits.template.json"
JSON_OUT = REPORTS_DIR / "post_production_monitoring_snapshot.json"
MD_OUT = REPORTS_DIR / "post_production_monitoring_snapshot.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - monitoring snapshot must fail closed.
        return {}, f"{path.relative_to(ROOT)}:UNREADABLE:{type(exc).__name__}"
    if not isinstance(data, dict):
        return {}, f"{path.relative_to(ROOT)}:NOT_OBJECT"
    return data, None


def boundary_value(report: dict[str, Any], key: str) -> Any:
    boundary = report.get("boundary")
    if isinstance(boundary, dict):
        return boundary.get(key)
    return None


def check(name: str, passed: bool, evidence: str) -> dict[str, str]:
    return {
        "name": name,
        "result": "PASS" if passed else "FAIL",
        "evidence": evidence,
    }


def build_report() -> tuple[dict[str, Any], int]:
    send, send_error = read_json(SEND_RESULT)
    readonly_recon, readonly_error = read_json(READONLY_RECONCILIATION)
    decision, decision_error = read_json(OPERATIONS_DECISION)
    readiness, readiness_error = read_json(EXECUTION_READINESS)
    risk_limits, risk_error = read_json(RISK_LIMITS)
    errors = [
        item
        for item in (send_error, readonly_error, decision_error, readiness_error, risk_error)
        if item
    ]

    terminal = send.get("terminal") if isinstance(send.get("terminal"), dict) else {}
    order_recon = (
        readonly_recon.get("order_reconciliation")
        if isinstance(readonly_recon.get("order_reconciliation"), dict)
        else {}
    )
    account_recon = (
        readonly_recon.get("account_reconciliation")
        if isinstance(readonly_recon.get("account_reconciliation"), dict)
        else {}
    )
    decision_summary = decision.get("summary") if isinstance(decision.get("summary"), dict) else {}
    readiness_blockers = readiness.get("blockers") if isinstance(readiness.get("blockers"), list) else []

    checks = [
        check(
            "production_send_recorded_pass",
            send.get("result") == "PASS"
            and send.get("success") is True
            and terminal.get("external_status") == "FILLED",
            "stored exactly-one production send evidence is PASS / FILLED",
        ),
        check(
            "readonly_reconciliation_recorded_pass",
            readonly_recon.get("result") == "PASS",
            "stored post-send read-only reconciliation is PASS",
        ),
        check(
            "exactly_one_order_confirmed",
            order_recon.get("matching_filled_order_count") == 1
            and order_recon.get("symbol_order_count_in_window") == 1,
            "exactly one matching BTCUSDT BUY order was found in the authorized window",
        ),
        check(
            "account_rows_visible_without_amounts",
            account_recon.get("usdt_balance_row_present") is True
            and account_recon.get("btc_balance_row_present") is True
            and account_recon.get("balance_amounts_recorded") == "NO",
            "USDT/BTC rows are visible, while balance amounts remain unrecorded",
        ),
        check(
            "operations_decision_pass",
            decision.get("result") == "PASS"
            and decision.get("decision")
            == "FIRST_PRODUCTION_VALIDATION_COMPLETE_CONTINUOUS_TRADING_DISABLED",
            "post-production operations decision keeps continuous trading disabled",
        ),
        check(
            "continuous_trading_disabled",
            decision_summary.get("continuous_runtime_enabled") == "NO"
            and decision_summary.get("automatic_trading_enabled") == "NO",
            "continuous runtime and automatic trading remain disabled",
        ),
        check(
            "risk_limits_still_bounded",
            risk_limits.get("AUTHORIZED_PRODUCTION_SYMBOLS") == "BTCUSDT"
            and risk_limits.get("AUTHORIZED_PRODUCTION_SIDES") == "BUY_ONLY"
            and str(risk_limits.get("AUTHORIZED_MAX_NOTIONAL")) == "10"
            and str(risk_limits.get("AUTHORIZED_MAX_ORDER_COUNT")) == "1",
            "production risk limits remain BTCUSDT BUY_ONLY max notional 10 order count 1",
        ),
        check(
            "go_live_and_live_trading_blocked",
            "go-live not authorized" in set(readiness_blockers)
            and "live trading not authorized" in set(readiness_blockers)
            and boundary_value(decision, "go_live") == "NO-GO"
            and boundary_value(decision, "live_trading") == "NO-GO",
            "go-live and live trading remain blocked",
        ),
        check(
            "no_new_or_second_request",
            boundary_value(decision, "new_production_request_sent") == "NO"
            and boundary_value(decision, "second_production_request_sent") == "NO"
            and boundary_value(readonly_recon, "second_production_request_sent") == "NO",
            "monitoring snapshot did not send or imply another request",
        ),
        check(
            "no_secret_disclosure",
            boundary_value(send, "secret_value_disclosed") == "NO"
            and boundary_value(readonly_recon, "secret_value_disclosed") == "NO"
            and boundary_value(decision, "secret_value_disclosed") == "NO",
            "stored evidence contains no secret disclosure",
        ),
    ]
    failed = [item for item in checks if item["result"] != "PASS"]
    result = "PASS" if not errors and not failed else "BLOCKED"
    status = "MONITORING_READY_CONTINUOUS_TRADING_DISABLED" if result == "PASS" else "MONITORING_BLOCKED"
    report = {
        "generated_at": utc_now(),
        "result": result,
        "status": status,
        "errors": errors,
        "checks": checks,
        "snapshot": {
            "production_request_sent": "YES",
            "production_order_status": terminal.get("external_status"),
            "matching_filled_order_count": order_recon.get("matching_filled_order_count"),
            "symbol_order_count_in_window": order_recon.get("symbol_order_count_in_window"),
            "usdt_balance_row_present": account_recon.get("usdt_balance_row_present"),
            "btc_balance_row_present": account_recon.get("btc_balance_row_present"),
            "balance_amounts_recorded": account_recon.get("balance_amounts_recorded"),
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
            "readonly_reconciliation": str(READONLY_RECONCILIATION.relative_to(ROOT)),
            "operations_decision": str(OPERATIONS_DECISION.relative_to(ROOT)),
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
        "next_gate": "POST_PRODUCTION_MONITORING_SURFACE_OR_FREEZE",
    }
    return report, 0 if result == "PASS" else 1


def markdown(report: dict[str, Any]) -> str:
    snapshot = "\n".join(f"- {key}: {value}" for key, value in report["snapshot"].items())
    checks = "\n".join(
        f"- {item['name']}: {item['result']} ({item['evidence']})" for item in report["checks"]
    )
    errors = "\n".join(f"- {item}" for item in report["errors"]) or "- none"
    boundary = "\n".join(f"- {key}: {value}" for key, value in report["boundary"].items())
    return f"""# Post Production Monitoring Snapshot

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- status: {report["status"]}
- next gate: {report["next_gate"]}

## Snapshot

{snapshot}

## Checks

{checks}

## Errors

{errors}

## Boundary

{boundary}
"""


def main() -> int:
    report, exit_code = build_report()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(markdown(report), encoding="utf-8")
    print("[Post Production Monitoring Snapshot]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(f"status: {report['status']}")
    print(f"new_production_request_sent: {report['boundary']['new_production_request_sent']}")
    print(f"go_live: {report['boundary']['go_live']}")
    print(f"live_trading: {report['boundary']['live_trading']}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
