#!/usr/bin/env python3
"""Plan a production request send window without authorizing or executing it.

This planner turns the current pre-send evidence into a bounded, non-sendable
window plan. It does not read secrets, sign payloads, resolve DNS, open sockets,
enable HTTP/network execution, or send production requests.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
RISK_LIMITS_CONFIG = ROOT / "config" / "production_risk_limits.template.json"
PRE_SEND_AGGREGATION_REPORT = REPORTS_DIR / "production_pre_send_readiness_aggregation.json"
JSON_OUT = REPORTS_DIR / "production_request_send_window_plan.json"
MD_OUT = REPORTS_DIR / "production_request_send_window_plan.md"


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def fmt(ts: datetime) -> str:
    return ts.isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - planner should fail closed with evidence.
        return {}, f"{path.relative_to(ROOT)}:UNREADABLE:{type(exc).__name__}"
    if not isinstance(data, dict):
        return {}, f"{path.relative_to(ROOT)}:NOT_OBJECT"
    return data, None


def value(data: dict[str, Any], key: str) -> str:
    item = data.get(key)
    return str(item).strip() if item is not None else ""


def check(name: str, passed: bool, evidence: str) -> dict[str, str]:
    return {
        "name": name,
        "result": "PASS" if passed else "FAIL",
        "evidence": evidence,
    }


def build_report() -> tuple[dict[str, Any], int]:
    now = utc_now()
    not_before = now
    expires_at = now + timedelta(minutes=60)
    monitor_until = expires_at + timedelta(minutes=15)

    risk_limits, risk_error = read_json(RISK_LIMITS_CONFIG)
    pre_send, pre_send_error = read_json(PRE_SEND_AGGREGATION_REPORT)
    errors = [item for item in (risk_error, pre_send_error) if item]

    market = value(risk_limits, "AUTHORIZED_PRODUCTION_MARKET")
    symbol = value(risk_limits, "AUTHORIZED_PRODUCTION_SYMBOLS")
    sides = value(risk_limits, "AUTHORIZED_PRODUCTION_SIDES")
    max_notional = value(risk_limits, "AUTHORIZED_MAX_NOTIONAL")
    max_order_count = value(risk_limits, "AUTHORIZED_MAX_ORDER_COUNT")
    idempotency_policy = value(risk_limits, "AUTHORIZED_IDEMPOTENCY_POLICY")
    kill_switch_precondition = value(risk_limits, "AUTHORIZED_KILL_SWITCH_PRECONDITION")
    stop_conditions = value(risk_limits, "AUTHORIZED_STOP_CONDITIONS")
    monitoring_window = value(risk_limits, "AUTHORIZED_MONITORING_WINDOW")

    planned_side = "BUY" if sides == "BUY_ONLY" else "UNRESOLVED"
    idempotency_key_template = (
        f"production:ops_manual:{symbol}:{planned_side}:{max_notional}:"
        "first-bounded-production-request:v1"
    )

    validation_checks = [
        check(
            "pre_send_evidence_chain_complete",
            pre_send.get("result") == "PASS"
            and pre_send.get("evidence_chain_complete") is True,
            "pre-send aggregation PASS and complete",
        ),
        check(
            "pre_send_does_not_authorize_send",
            pre_send.get("request_send_authorized") is False,
            "pre-send evidence remains non-authorizing",
        ),
        check("market_present", bool(market), "production market present"),
        check("symbol_present", bool(symbol), "production symbol present"),
        check("side_bounded", planned_side != "UNRESOLVED", "production side bounded"),
        check("max_notional_present", bool(max_notional), "max notional present"),
        check("max_order_count_one", max_order_count == "1", "max order count is one"),
        check(
            "idempotency_policy_present",
            bool(idempotency_policy),
            "idempotency policy present",
        ),
        check(
            "kill_switch_precondition_present",
            bool(kill_switch_precondition),
            "kill-switch precondition present",
        ),
        check("stop_conditions_present", bool(stop_conditions), "stop conditions present"),
        check("monitoring_window_present", bool(monitoring_window), "monitoring window present"),
    ]

    plan_valid = not errors and all(item["result"] == "PASS" for item in validation_checks)
    report = {
        "generated_at": fmt(now),
        "result": "PASS" if plan_valid else "FAIL",
        "plan_valid": plan_valid,
        "send_authorized": False,
        "execution_allowed_by_this_plan": False,
        "next_gate": (
            "WAITING_FOR_EXPLICIT_EXACTLY_ONE_PRODUCTION_REQUEST_SEND_AUTHORIZATION"
            if plan_valid
            else "BLOCKED_PRODUCTION_REQUEST_SEND_WINDOW_PLAN_INVALID"
        ),
        "errors": errors,
        "inputs": {
            "risk_limits_config": str(RISK_LIMITS_CONFIG.relative_to(ROOT)),
            "pre_send_aggregation": str(PRE_SEND_AGGREGATION_REPORT.relative_to(ROOT)),
        },
        "validation_checks": validation_checks,
        "planned_window": {
            "window_type": "fresh_bounded_authorization_window",
            "not_before": fmt(not_before),
            "expires_at": fmt(expires_at),
            "duration_minutes": 60,
            "monitor_until": fmt(monitor_until),
            "monitoring_window": monitoring_window,
        },
        "planned_request": {
            "market": market,
            "symbol": symbol,
            "side": planned_side,
            "max_notional": max_notional,
            "max_order_count": max_order_count,
            "order_type": "market",
            "idempotency_policy": idempotency_policy,
            "idempotency_key_template": idempotency_key_template,
            "sendable": False,
        },
        "preconditions": {
            "kill_switch": kill_switch_precondition,
            "pre_send_evidence_chain_complete": bool(pre_send.get("evidence_chain_complete")),
            "operator_must_provide_explicit_send_authorization": True,
            "no_retry": True,
            "exactly_one_request_only": True,
        },
        "stop_conditions": {
            "policy": stop_conditions,
            "stop_on_any_error": True,
            "stop_on_unexpected_status": True,
            "stop_on_duplicate_attempt": True,
            "stop_on_scope_drift": True,
            "stop_on_secret_disclosure_risk": True,
        },
        "boundary": {
            "secret_read": "NO",
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
    return report, 0 if report["result"] == "PASS" else 1


def markdown(report: dict[str, Any]) -> str:
    checks = "\n".join(
        "- {name}: {result} ({evidence})".format(**item)
        for item in report["validation_checks"]
    )
    errors = "\n".join(f"- {item}" for item in report["errors"]) or "- none"
    planned_request = "\n".join(
        f"- {key}: {value}" for key, value in report["planned_request"].items()
    )
    planned_window = "\n".join(
        f"- {key}: {value}" for key, value in report["planned_window"].items()
    )
    preconditions = "\n".join(
        f"- {key}: {value}" for key, value in report["preconditions"].items()
    )
    stop_conditions = "\n".join(
        f"- {key}: {value}" for key, value in report["stop_conditions"].items()
    )
    return f"""# Production Request Send Window Plan

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- plan valid: {str(report["plan_valid"]).lower()}
- send authorized: {str(report["send_authorized"]).lower()}
- execution allowed by this plan: {str(report["execution_allowed_by_this_plan"]).lower()}
- next gate: {report["next_gate"]}

## Planned Window

{planned_window}

## Planned Request

{planned_request}

## Preconditions

{preconditions}

## Stop Conditions

{stop_conditions}

## Validation Checks

{checks}

## Errors

{errors}

## Boundary

- secret read: {report["boundary"]["secret_read"]}
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

    print("[Production Request Send Window Plan]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(f"plan_valid: {str(report['plan_valid']).lower()}")
    print(f"send_authorized: {str(report['send_authorized']).lower()}")
    print(f"next_gate: {report['next_gate']}")
    print("secret_read: NO")
    print("authorization_header_generated: NO")
    print("dns_lookup_performed: NO")
    print("socket_opened: NO")
    print("production_http_network_executed: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
