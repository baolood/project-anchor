#!/usr/bin/env python3
"""Check the production exactly-one request send gate without sending."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "production_request_send_gate.json"
MD_OUT = REPORTS_DIR / "production_request_send_gate.md"

sys.path.insert(0, str(ROOT / "anchor-backend"))

from app.trade_gate_production import (  # noqa: E402
    PRODUCTION_IDEMPOTENCY_KEY,
    PRODUCTION_REQUEST_SEND_GATE_REQUIRED_VERDICT,
    load_production_execution_gate_config,
    production_request_send_gate_decision,
)


FIXED_NOW = datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def authorized_fixture(**overrides) -> dict:
    data = {
        "AUTHORIZED_PRODUCTION_REQUEST_SEND": "YES",
        "AUTHORIZED_PRODUCTION_CREDENTIAL_ACCESS": "YES",
        "AUTHORIZED_PRODUCTION_SIGNING": "YES",
        "AUTHORIZED_PRODUCTION_HTTP_NETWORK": "YES",
        "AUTHORIZED_GO_LIVE": "NO",
        "AUTHORIZED_LIVE_TRADING": "NO",
        "PRODUCTION_REQUEST_SEND_WINDOW_OPEN": True,
        "PRODUCTION_REQUEST_SEND_WINDOW_EXPIRES_AT": "2026-07-22T09:00:00Z",
        "PRODUCTION_REQUEST_SEND_NO_RETRY": True,
        "PRODUCTION_REQUEST_SEND_IDEMPOTENCY_KEY": PRODUCTION_IDEMPOTENCY_KEY,
        "FINAL_PRODUCTION_REQUEST_SEND_OPERATOR_VERDICT": (
            PRODUCTION_REQUEST_SEND_GATE_REQUIRED_VERDICT
        ),
    }
    data.update(overrides)
    return data


def build_report() -> tuple[dict, int]:
    current_config = load_production_execution_gate_config()
    default_gate = production_request_send_gate_decision(now=FIXED_NOW)
    current_gate = production_request_send_gate_decision(current_config, now=FIXED_NOW)
    authorized_gate = production_request_send_gate_decision(
        authorized_fixture(),
        now=FIXED_NOW,
    )
    expired_gate = production_request_send_gate_decision(
        authorized_fixture(PRODUCTION_REQUEST_SEND_WINDOW_EXPIRES_AT="2026-07-22T07:59:59Z"),
        now=FIXED_NOW,
    )
    go_live_gate = production_request_send_gate_decision(
        authorized_fixture(AUTHORIZED_GO_LIVE="YES", AUTHORIZED_LIVE_TRADING="YES"),
        now=FIXED_NOW,
    )
    checks = {
        "default_gate_closed": (
            default_gate.get("authorized") is False
            and default_gate.get("reason") == "PRODUCTION_REQUEST_SEND_GATE_CLOSED"
        ),
        "current_template_gate_closed": (
            current_gate.get("authorized") is False
            and current_gate.get("reason") == "PRODUCTION_REQUEST_SEND_GATE_CLOSED"
        ),
        "complete_fixture_authorizes_exactly_one_send": authorized_gate.get("authorized") is True,
        "expired_window_rejected": (
            expired_gate.get("authorized") is False
            and expired_gate.get("checks", {}).get("window_not_expired") is False
        ),
        "go_live_and_live_trading_rejected": (
            go_live_gate.get("authorized") is False
            and go_live_gate.get("checks", {}).get("go_live_not_authorized") is False
            and go_live_gate.get("checks", {}).get("live_trading_not_authorized") is False
        ),
    }
    result = "PASS" if all(checks.values()) else "FAIL"
    report = {
        "generated_at": utc_now(),
        "result": result,
        "fixed_now": FIXED_NOW.isoformat().replace("+00:00", "Z"),
        "current_template_authorized": current_gate.get("authorized"),
        "fixture_authorized": authorized_gate.get("authorized"),
        "fixture_required_verdict": PRODUCTION_REQUEST_SEND_GATE_REQUIRED_VERDICT,
        "checks": checks,
        "default_gate": default_gate,
        "current_template_gate": current_gate,
        "authorized_fixture_gate": authorized_gate,
        "expired_window_gate": expired_gate,
        "go_live_gate": go_live_gate,
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
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    return report, 0 if result == "PASS" else 1


def markdown(report: dict) -> str:
    checks = "\n".join(
        f"- {key}: {'PASS' if value else 'FAIL'}"
        for key, value in report["checks"].items()
    )
    return f"""# Production Request Send Gate

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- current template authorized: {str(report["current_template_authorized"]).lower()}
- complete fixture authorized: {str(report["fixture_authorized"]).lower()}
- fixture required verdict: {report["fixture_required_verdict"]}

## Checks

{checks}

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
- go-live: {report["boundary"]["go_live"]}
- live trading: {report["boundary"]["live_trading"]}
"""


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report, exit_code = build_report()
    JSON_OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(markdown(report), encoding="utf-8")

    print("[Production Request Send Gate]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"result: {report['result']}")
    print(f"current_template_authorized: {str(report['current_template_authorized']).lower()}")
    print(f"fixture_authorized: {str(report['fixture_authorized']).lower()}")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
