#!/usr/bin/env python3
"""Check eligibility for the next manual low-frequency production operation.

This checker is read-only. It uses sanitized repository reports and policy
files only; it never reads credential files, opens sockets, signs payloads, or
sends production requests.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
DEFAULT_POLICY = ROOT / "config" / "manual_low_frequency_operations_policy.json"
DEFAULT_JSON_OUT = REPORTS_DIR / "next_manual_operation_eligibility.json"
DEFAULT_MD_OUT = REPORTS_DIR / "next_manual_operation_eligibility.md"

SEND_REPORT = REPORTS_DIR / "production_exactly_one_send_result.json"
RECONCILIATION_REPORT = REPORTS_DIR / "production_post_send_readonly_reconciliation.json"
STABILITY_72H_REPORT = REPORTS_DIR / "post_production_72h_stability_review.json"
MONITORING_REPORT = REPORTS_DIR / "post_production_monitoring_run.json"
TELEGRAM_REPORT = REPORTS_DIR / "post_production_telegram_channel_evidence.json"

FORBIDDEN_MARKDOWN_FRAGMENTS = [
    "API_KEY",
    "API_SECRET",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "Authorization",
    "external_order_id",
    "client_order_id",
    "idempotency",
    "production.env",
    "/etc/project-anchor",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def pass_fail(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def _add_blocker(blockers: list[str], name: str, condition: bool) -> None:
    if not condition:
        blockers.append(name)


def build_report(policy_path: Path, reports_dir: Path, now: datetime) -> dict[str, Any]:
    policy = load_json(policy_path)
    send = load_json(reports_dir / SEND_REPORT.name)
    reconciliation = load_json(reports_dir / RECONCILIATION_REPORT.name)
    stability = load_json(reports_dir / STABILITY_72H_REPORT.name)
    monitoring = load_json(reports_dir / MONITORING_REPORT.name)
    telegram = load_json(reports_dir / TELEGRAM_REPORT.name)

    min_hours = policy.get("MIN_HOURS_BETWEEN_PRODUCTION_REQUESTS")
    if not isinstance(min_hours, int):
        min_hours = 24
    weekly_limit = policy.get("RECOMMENDED_MAX_REQUESTS_PER_WEEK")
    if not isinstance(weekly_limit, int):
        weekly_limit = 3

    last_send_at = parse_utc(send.get("generated_at"))
    next_eligible_at = last_send_at + timedelta(hours=min_hours) if last_send_at else None
    hours_since_last = (
        round((now - last_send_at).total_seconds() / 3600, 2) if last_send_at else None
    )
    observed_requests_last_7d = 1 if last_send_at and now - last_send_at <= timedelta(days=7) else 0

    checks = {
        "policy_manual_low_frequency": pass_fail(
            policy.get("POLICY_MODE") == "manual_confirmed_low_frequency_only"
        ),
        "operator_authorization_required": pass_fail(
            policy.get("REQUIRES_EXPLICIT_OPERATOR_AUTHORIZATION_PER_REQUEST") is True
        ),
        "automatic_retry_disabled": pass_fail(policy.get("ALLOW_AUTOMATIC_RETRY") is False),
        "automatic_trading_disabled": pass_fail(policy.get("ALLOW_AUTOMATIC_TRADING") is False),
        "go_live_disabled": pass_fail(policy.get("ALLOW_GO_LIVE") is False),
        "live_trading_disabled": pass_fail(policy.get("ALLOW_LIVE_TRADING") is False),
        "last_production_send_pass": pass_fail(send.get("result") == "PASS"),
        "last_production_send_filled": pass_fail(
            nested(send, "terminal", "external_status") == "FILLED"
        ),
        "last_production_send_timestamp_present": pass_fail(last_send_at is not None),
        "minimum_interval_satisfied": pass_fail(
            last_send_at is not None and next_eligible_at is not None and now >= next_eligible_at
        ),
        "weekly_recommended_limit_not_reached": pass_fail(observed_requests_last_7d < weekly_limit),
        "post_send_reconciliation_pass": pass_fail(reconciliation.get("result") == "PASS"),
        "post_production_72h_stability_pass": pass_fail(stability.get("result") == "PASS"),
        "post_production_monitoring_pass": pass_fail(monitoring.get("result") == "PASS"),
        "telegram_channel_delivery_confirmed": pass_fail(telegram.get("result") == "PASS"),
    }

    blockers: list[str] = []
    for key, value in checks.items():
        _add_blocker(blockers, key, value == "PASS")

    result = "PASS" if not blockers else "BLOCKED"
    decision = (
        "READY_FOR_NEXT_MANUAL_LOW_FREQUENCY_OPERATOR_AUTHORIZATION_DECISION"
        if result == "PASS"
        else "NEXT_MANUAL_LOW_FREQUENCY_OPERATION_ELIGIBILITY_BLOCKED"
    )

    return {
        "generated_at": format_utc(now),
        "result": result,
        "decision": decision,
        "policy": {
            "market": policy.get("AUTHORIZED_MARKET"),
            "symbols": policy.get("AUTHORIZED_SYMBOLS"),
            "sides": policy.get("AUTHORIZED_SIDES"),
            "max_notional_per_request": policy.get("MAX_NOTIONAL_PER_REQUEST"),
            "max_order_count_per_request": policy.get("MAX_ORDER_COUNT_PER_REQUEST"),
            "minimum_hours_between_production_requests": min_hours,
            "recommended_max_requests_per_week": weekly_limit,
            "explicit_operator_authorization_required": policy.get(
                "REQUIRES_EXPLICIT_OPERATOR_AUTHORIZATION_PER_REQUEST"
            ),
        },
        "eligibility": {
            "last_production_request_at": format_utc(last_send_at),
            "next_eligible_at": format_utc(next_eligible_at),
            "hours_since_last_production_request": hours_since_last,
            "observed_production_requests_last_7d": observed_requests_last_7d,
            "eligible_for_operator_authorization_decision": "YES" if result == "PASS" else "NO",
            "production_send_authorization_granted": "NO",
        },
        "evidence": {
            "last_production_send_result": send.get("result", "missing"),
            "last_production_send_external_status": nested(
                send, "terminal", "external_status", default="missing"
            ),
            "external_order_reference_present": nested(
                send, "terminal", "external_order_id_present", default=False
            ),
            "post_send_reconciliation": reconciliation.get("result", "missing"),
            "post_production_72h_stability": stability.get("result", "missing"),
            "post_production_monitoring": monitoring.get("result", "missing"),
            "telegram_channel_delivery": telegram.get("result", "missing"),
        },
        "checks": checks,
        "blockers": blockers,
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
            "operator_decision_for_next_manual_low_frequency_operation"
            if result == "PASS"
            else "resolve_next_manual_operation_eligibility_blocker"
        ),
    }


def markdown(report: dict[str, Any]) -> str:
    policy = "\n".join(f"- {key}: {value}" for key, value in report["policy"].items())
    eligibility = "\n".join(
        f"- {key}: {value}" for key, value in report["eligibility"].items()
    )
    evidence = "\n".join(f"- {key}: {value}" for key, value in report["evidence"].items())
    checks = "\n".join(f"- {key}: {value}" for key, value in report["checks"].items())
    boundary = "\n".join(f"- {key}: {value}" for key, value in report["boundary"].items())
    blockers = "\n".join(f"- {item}" for item in report["blockers"]) or "- none"
    text = f"""# Next Manual Operation Eligibility

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- decision: {report["decision"]}
- next single task: {report["next_single_task"]}

## Policy

{policy}

## Eligibility

{eligibility}

## Evidence

{evidence}

## Checks

{checks}

## Blockers

{blockers}

## Boundary

{boundary}
"""
    for fragment in FORBIDDEN_MARKDOWN_FRAGMENTS:
        if fragment in text:
            raise ValueError(f"forbidden fragment leaked into markdown: {fragment}")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_OUT)
    parser.add_argument("--now", help="UTC timestamp override for reproducible checks")
    args = parser.parse_args()

    now = parse_utc(args.now) if args.now else utc_now()
    if now is None:
        raise SystemExit("invalid --now timestamp")

    report = build_report(args.policy, args.reports_dir, now)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.md_out.write_text(markdown(report), encoding="utf-8")

    print("[Next Manual Operation Eligibility]")
    print(f"report JSON: {args.json_out}")
    print(f"report Markdown: {args.md_out}")
    print(f"result: {report['result']}")
    print(f"decision: {report['decision']}")
    print(f"eligible_for_operator_authorization_decision: {report['eligibility']['eligible_for_operator_authorization_decision']}")
    print("production_send_authorization_granted: NO")
    print("secret_read: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
