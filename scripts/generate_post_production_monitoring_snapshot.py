#!/usr/bin/env python3
"""Generate a read-only post-production monitoring snapshot.

This snapshot reads only repository evidence files. It does not read
credentials, sign, open sockets, send requests, rerun canaries, or change
runtime/go-live state.

Order counts taken from stored reports are labeled as repo-recorded. Exchange
confirmation is a separate field and stays UNKNOWN unless an offline
reconciliation file is supplied. A repo-recorded pass with UNKNOWN exchange
confirmation uses result PASS_REPO_RECORDED_ONLY. That is not a plain PASS
and it is not a paging failure. This script never calls an exchange.
"""

from __future__ import annotations

import json
import os
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
EXCHANGE_RECONCILIATION_ENV = "POST_PRODUCTION_EXCHANGE_RECONCILIATION_FILE"
REPO_RECORDED_ONLY_RESULT = "PASS_REPO_RECORDED_ONLY"
REPO_RECORDED_ONLY_STATUS = "MONITORING_REPO_RECORDED_ONLY_CONTINUOUS_TRADING_DISABLED"
EXCHANGE_CONFIRMED_RESULT = "PASS"
EXCHANGE_CONFIRMED_STATUS = "MONITORING_READY_CONTINUOUS_TRADING_DISABLED"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _path_label(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return path.name


def read_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - monitoring snapshot must fail closed.
        return {}, f"{_path_label(path)}:UNREADABLE:{type(exc).__name__}"
    if not isinstance(data, dict):
        return {}, f"{_path_label(path)}:NOT_OBJECT"
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


def status_check(name: str, result: str, evidence: str) -> dict[str, str]:
    if result not in {"PASS", "FAIL", "UNKNOWN"}:
        raise ValueError(f"unsupported check result: {result}")
    return {"name": name, "result": result, "evidence": evidence}


def exchange_reconciliation_path(explicit: Path | None = None) -> Path | None:
    """Optional offline file. Never opens a socket to an exchange."""
    if explicit is not None:
        return explicit
    raw = os.environ.get(EXCHANGE_RECONCILIATION_ENV, "").strip()
    if not raw:
        return None
    return Path(raw)


def _exchange_evidence(subject: str, result: str, supplied: str) -> str:
    if supplied != "YES":
        return (
            "no offline exchange reconciliation file was supplied; "
            "exchange confirmation is UNKNOWN and is not PASS"
        )
    if result == "PASS":
        return f"offline exchange reconciliation reports {subject}"
    if result == "FAIL":
        return f"offline exchange reconciliation does not report {subject}"
    return f"offline exchange reconciliation left {subject} UNKNOWN"


def interpret_exchange_reconciliation(path: Path | None) -> tuple[str, str, str, list[str]]:
    """Return exactly-one result, no-second-request result, supplied flag, errors.

    Missing file is UNKNOWN, never PASS. A supplied file that cannot be read
    or does not match the offline schema is FAIL.
    """
    if path is None:
        return "UNKNOWN", "UNKNOWN", "NO", []
    data, error = read_json(path)
    label = _path_label(path)
    if error:
        return "FAIL", "FAIL", "YES", [error]
    if data.get("kind") != "offline_exchange_reconciliation":
        return "FAIL", "FAIL", "YES", [f"{label}:NOT_OFFLINE_EXCHANGE_RECONCILIATION"]
    filled = data.get("matching_filled_order_count")
    symbol_count = data.get("symbol_order_count")
    second = data.get("new_or_second_request_observed")
    if type(filled) is not int or type(symbol_count) is not int or type(second) is not bool:
        return "FAIL", "FAIL", "YES", [f"{label}:INVALID_FIELDS"]
    exactly = "PASS" if filled == 1 and symbol_count == 1 else "FAIL"
    no_second = "PASS" if second is False else "FAIL"
    return exactly, no_second, "YES", []


def build_report(exchange_reconciliation: Path | None = None) -> tuple[dict[str, Any], int]:
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
    repo_filled = order_recon.get("matching_filled_order_count")
    repo_symbol_count = order_recon.get("symbol_order_count_in_window")
    repo_no_second = (
        boundary_value(decision, "new_production_request_sent") == "NO"
        and boundary_value(decision, "second_production_request_sent") == "NO"
        and boundary_value(readonly_recon, "second_production_request_sent") == "NO"
    )
    exchange_exactly, exchange_no_second, exchange_supplied, exchange_errors = (
        interpret_exchange_reconciliation(exchange_reconciliation_path(exchange_reconciliation))
    )
    errors.extend(exchange_errors)
    if exchange_exactly == "PASS" and exchange_no_second == "PASS":
        exchange_order_status = "PASS"
    elif exchange_exactly == "UNKNOWN" and exchange_no_second == "UNKNOWN":
        exchange_order_status = "UNKNOWN"
    else:
        exchange_order_status = "FAIL"

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
            "repo_recorded_exactly_one_order",
            repo_filled == 1 and repo_symbol_count == 1,
            "repo-recorded count in stored post-send reconciliation is exactly one "
            "matching filled order and one symbol order in the window; this is not "
            "an exchange confirmation",
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
            "repo_recorded_no_new_or_second_request",
            repo_no_second,
            "repo-recorded boundary flags say no new or second production request; "
            "this is not an exchange confirmation",
        ),
        status_check(
            "exchange_confirmed_exactly_one_order",
            exchange_exactly,
            _exchange_evidence(
                "exactly one filled order",
                exchange_exactly,
                exchange_supplied,
            ),
        ),
        status_check(
            "exchange_confirmed_no_new_or_second_request",
            exchange_no_second,
            _exchange_evidence(
                "no new or second request",
                exchange_no_second,
                exchange_supplied,
            ),
        ),
        check(
            "no_secret_disclosure",
            boundary_value(send, "secret_value_disclosed") == "NO"
            and boundary_value(readonly_recon, "secret_value_disclosed") == "NO"
            and boundary_value(decision, "secret_value_disclosed") == "NO",
            "stored evidence contains no secret disclosure",
        ),
    ]
    failed = [item for item in checks if item["result"] == "FAIL"]
    if errors or failed:
        result = "BLOCKED"
        status = "MONITORING_BLOCKED"
    elif exchange_order_status == "PASS":
        result = EXCHANGE_CONFIRMED_RESULT
        status = EXCHANGE_CONFIRMED_STATUS
    else:
        # Repo checks passed, but exchange confirmation is UNKNOWN. Do not
        # report a plain PASS, and do not treat this as a paging failure.
        result = REPO_RECORDED_ONLY_RESULT
        status = REPO_RECORDED_ONLY_STATUS
    report = {
        "generated_at": utc_now(),
        "result": result,
        "result_scope": "repo_recorded_evidence",
        "status": status,
        "errors": errors,
        "checks": checks,
        "snapshot": {
            "production_request_sent": "YES",
            "production_order_status": terminal.get("external_status"),
            "repo_recorded_matching_filled_order_count": repo_filled,
            "repo_recorded_symbol_order_count_in_window": repo_symbol_count,
            "matching_filled_order_count": repo_filled,
            "symbol_order_count_in_window": repo_symbol_count,
            "exchange_reconciliation_supplied": exchange_supplied,
            "exchange_confirmed_order_status": exchange_order_status,
            "exchange_confirmed_exactly_one_order": exchange_exactly,
            "exchange_confirmed_no_new_or_second_request": exchange_no_second,
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
            "exchange_reconciliation": (
                _path_label(exchange_reconciliation_path(exchange_reconciliation))
                if exchange_supplied == "YES"
                else "not_supplied"
            ),
        },
        "boundary": {
            "credential_file_read": "NO",
            "secret_value_disclosed": "NO",
            "production_signing_executed": "NO",
            "production_http_network_attempted": "NO",
            "exchange_api_called": "NO",
            "new_production_request_sent": "NO",
            "second_production_request_sent": "NO",
            "canary_rerun": "NO",
            "runtime_modified": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
        "next_gate": "POST_PRODUCTION_MONITORING_SURFACE_OR_FREEZE",
    }
    return report, 0 if result in {EXCHANGE_CONFIRMED_RESULT, REPO_RECORDED_ONLY_RESULT} else 1


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
