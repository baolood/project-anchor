#!/usr/bin/env python3
"""Validate manual low-frequency production operations policy.

This validator is intentionally read-only. It checks non-secret policy fields
and existing sanitized evidence reports; it never reads credential files and
never opens production network paths.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config" / "manual_low_frequency_operations_policy.json"
REPORTS_DIR = ROOT / "reports"
DEFAULT_JSON_OUT = REPORTS_DIR / "manual_low_frequency_operations_policy_validation.json"
DEFAULT_MD_OUT = REPORTS_DIR / "manual_low_frequency_operations_policy_validation.md"

MVP_COMPLETION_REPORT = REPORTS_DIR / "production_validated_mvp_completion_decision.json"
POST_SEND_RECONCILIATION_REPORT = REPORTS_DIR / "post_production_send_reconciliation.json"
POST_PRODUCTION_ALERTING_REPORT = REPORTS_DIR / "post_production_alerting_readiness.json"
POST_PRODUCTION_MONITORING_RUN = REPORTS_DIR / "post_production_monitoring_run.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def pass_fail(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def as_bool(value: Any) -> bool:
    return value is True


def contains_required_stop_conditions(values: Any) -> bool:
    if not isinstance(values, list):
        return False
    observed = {str(item).strip() for item in values}
    required = {
        "monitoring_not_pass",
        "telegram_not_ready",
        "reconciliation_not_pass",
        "unresolved_alert_present",
        "duplicate_or_second_request_risk",
        "secret_disclosure_risk",
        "unexpected_exchange_response",
        "operator_authorization_missing",
    }
    return required.issubset(observed)


def validate(policy: dict[str, Any]) -> dict[str, Any]:
    mvp = load_json(MVP_COMPLETION_REPORT)
    reconciliation = load_json(POST_SEND_RECONCILIATION_REPORT)
    alerting = load_json(POST_PRODUCTION_ALERTING_REPORT)
    monitoring = load_json(POST_PRODUCTION_MONITORING_RUN)

    checks = {
        "policy_mode_manual_low_frequency": pass_fail(
            policy.get("POLICY_MODE") == "manual_confirmed_low_frequency_only"
        ),
        "market_binance_spot": pass_fail(policy.get("AUTHORIZED_MARKET") == "binance_spot"),
        "symbols_limited_to_btcusdt": pass_fail(policy.get("AUTHORIZED_SYMBOLS") == ["BTCUSDT"]),
        "sides_limited_to_buy_only": pass_fail(policy.get("AUTHORIZED_SIDES") == ["BUY_ONLY"]),
        "max_notional_lte_10": pass_fail(
            isinstance(policy.get("MAX_NOTIONAL_PER_REQUEST"), (int, float))
            and 0 < policy["MAX_NOTIONAL_PER_REQUEST"] <= 10
        ),
        "max_one_order": pass_fail(policy.get("MAX_ORDER_COUNT_PER_REQUEST") == 1),
        "max_one_request_per_window": pass_fail(policy.get("MAX_REQUESTS_PER_WINDOW") == 1),
        "minimum_24h_between_requests": pass_fail(
            isinstance(policy.get("MIN_HOURS_BETWEEN_PRODUCTION_REQUESTS"), int)
            and policy["MIN_HOURS_BETWEEN_PRODUCTION_REQUESTS"] >= 24
        ),
        "weekly_frequency_lte_3": pass_fail(
            isinstance(policy.get("RECOMMENDED_MAX_REQUESTS_PER_WEEK"), int)
            and 0 < policy["RECOMMENDED_MAX_REQUESTS_PER_WEEK"] <= 3
        ),
        "explicit_operator_authorization_required": pass_fail(
            as_bool(policy.get("REQUIRES_EXPLICIT_OPERATOR_AUTHORIZATION_PER_REQUEST"))
        ),
        "fresh_pre_send_readiness_required": pass_fail(
            as_bool(policy.get("REQUIRES_FRESH_PRE_SEND_READINESS"))
        ),
        "post_send_reconciliation_required": pass_fail(
            as_bool(policy.get("REQUIRES_POST_SEND_RECONCILIATION"))
        ),
        "post_send_observation_at_least_24h": pass_fail(
            isinstance(policy.get("REQUIRES_POST_SEND_OBSERVATION_HOURS"), int)
            and policy["REQUIRES_POST_SEND_OBSERVATION_HOURS"] >= 24
        ),
        "automatic_retry_disabled": pass_fail(policy.get("ALLOW_AUTOMATIC_RETRY") is False),
        "second_request_same_window_disabled": pass_fail(
            policy.get("ALLOW_SECOND_REQUEST_IN_SAME_WINDOW") is False
        ),
        "automatic_trading_disabled": pass_fail(policy.get("ALLOW_AUTOMATIC_TRADING") is False),
        "automatic_position_management_disabled": pass_fail(
            policy.get("ALLOW_AUTOMATIC_POSITION_MANAGEMENT") is False
        ),
        "go_live_disabled": pass_fail(policy.get("ALLOW_GO_LIVE") is False),
        "live_trading_disabled": pass_fail(policy.get("ALLOW_LIVE_TRADING") is False),
        "stop_conditions_complete": pass_fail(contains_required_stop_conditions(policy.get("STOP_CONDITIONS"))),
        "operator_verdict_policy_only": pass_fail(
            policy.get("FINAL_OPERATOR_VERDICT")
            == "APPROVED_FOR_MANUAL_LOW_FREQUENCY_OPERATIONS_POLICY_ONLY"
        ),
        "production_validated_mvp_complete": pass_fail(
            mvp.get("status") == "PRODUCTION_VALIDATED_MVP_COMPLETE"
            and mvp.get("result") == "PASS"
        ),
        "post_send_reconciliation_pass": pass_fail(reconciliation.get("result") == "PASS"),
        "post_production_monitoring_pass": pass_fail(monitoring.get("result") == "PASS"),
        "post_production_alerting_ready_or_absent": pass_fail(
            alerting.get("result") in {"PASS", None}
        ),
    }
    result = "PASS" if all(value == "PASS" for value in checks.values()) else "BLOCKED"
    return {
        "generated_at": utc_now(),
        "input_file": str(DEFAULT_POLICY.relative_to(ROOT)),
        "result": result,
        "status": (
            "MANUAL_LOW_FREQUENCY_OPERATIONS_POLICY_PASS"
            if result == "PASS"
            else "MANUAL_LOW_FREQUENCY_OPERATIONS_POLICY_BLOCKED"
        ),
        "policy": {
            "mode": policy.get("POLICY_MODE"),
            "market": policy.get("AUTHORIZED_MARKET"),
            "symbols": policy.get("AUTHORIZED_SYMBOLS"),
            "sides": policy.get("AUTHORIZED_SIDES"),
            "max_notional_per_request": policy.get("MAX_NOTIONAL_PER_REQUEST"),
            "max_order_count_per_request": policy.get("MAX_ORDER_COUNT_PER_REQUEST"),
            "min_hours_between_production_requests": policy.get(
                "MIN_HOURS_BETWEEN_PRODUCTION_REQUESTS"
            ),
            "recommended_max_requests_per_week": policy.get("RECOMMENDED_MAX_REQUESTS_PER_WEEK"),
            "requires_explicit_operator_authorization_per_request": policy.get(
                "REQUIRES_EXPLICIT_OPERATOR_AUTHORIZATION_PER_REQUEST"
            ),
        },
        "evidence": {
            "production_validated_mvp_completion": mvp.get("status", "missing"),
            "post_send_reconciliation": reconciliation.get("result", "missing"),
            "post_production_monitoring": monitoring.get("result", "missing"),
            "post_production_alerting": alerting.get("result", "not_required_for_policy_validation"),
        },
        "checks": checks,
        "boundary": {
            "secret_read": "NO",
            "credential_file_read": "NO",
            "production_signing_executed": "NO",
            "production_http_network_attempted": "NO",
            "production_request_sent": "NO",
            "second_production_request_sent": "NO",
            "canary_rerun": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
        "next_single_task": (
            "manual_low_frequency_operations_runbook"
            if result == "PASS"
            else "fix_manual_low_frequency_operations_policy_blocker"
        ),
    }


def markdown(report: dict[str, Any]) -> str:
    checks = "\n".join(f"- {key}: {value}" for key, value in report["checks"].items())
    evidence = "\n".join(f"- {key}: {value}" for key, value in report["evidence"].items())
    boundary = "\n".join(f"- {key}: {value}" for key, value in report["boundary"].items())
    policy = "\n".join(f"- {key}: {value}" for key, value in report["policy"].items())
    return f"""# Manual Low-Frequency Operations Policy Validation

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- status: {report["status"]}
- input file: `{report["input_file"]}`

## Policy

{policy}

## Evidence

{evidence}

## Checks

{checks}

## Boundary

{boundary}

## Next Single Task

{report["next_single_task"]}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_OUT)
    args = parser.parse_args()

    policy = load_json(args.policy)
    report = validate(policy)
    if args.policy.resolve() != DEFAULT_POLICY:
        report["input_file"] = str(args.policy)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.md_out.write_text(markdown(report), encoding="utf-8")

    print("[Manual Low-Frequency Operations Policy Validation]")
    print(f"report JSON: {args.json_out}")
    print(f"report Markdown: {args.md_out}")
    print(f"result: {report['result']}")
    print(f"status: {report['status']}")
    print("secret_read: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
