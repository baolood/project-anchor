#!/usr/bin/env python3
"""Check the production send decision surface without executing a send."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "production_send_decision_entrypoint.json"
MD_OUT = REPORTS_DIR / "production_send_decision_entrypoint.md"

sys.path.insert(0, str(ROOT / "anchor-backend"))

from app.trade_gate_production import (  # noqa: E402
    PRODUCTION_IDEMPOTENCY_KEY,
    PRODUCTION_REQUEST_SEND_GATE_REQUIRED_VERDICT,
    load_production_execution_gate_config,
    production_order_send_decision_response,
    production_request_send_gate_decision,
)


FIXED_NOW = datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def valid_body() -> dict:
    return {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "notional": 4,
        "order_type": "market",
        "execution_mode": "production",
        "market": "binance_spot",
        "source": "ops_manual",
        "idempotency_key": PRODUCTION_IDEMPOTENCY_KEY,
    }


def authorized_config() -> dict:
    return {
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


def build_report() -> tuple[dict, int]:
    current_gate = production_request_send_gate_decision(
        load_production_execution_gate_config(),
        now=FIXED_NOW,
    )
    current_response = production_order_send_decision_response(valid_body(), current_gate)
    authorized_gate = production_request_send_gate_decision(
        authorized_config(),
        now=FIXED_NOW,
    )
    authorized_response = production_order_send_decision_response(valid_body(), authorized_gate)
    invalid_response = production_order_send_decision_response(
        dict(valid_body(), api_secret="redacted-fixture"),
        authorized_gate,
    )
    rendered = json.dumps(
        {
            "current_response": current_response,
            "authorized_response": authorized_response,
            "invalid_response": invalid_response,
        },
        sort_keys=True,
    )
    checks = {
        "current_template_blocks_send_decision": (
            current_response.get("status") == "blocked"
            and current_response.get("ready_for_exactly_one_send") is False
            and current_response.get("production_request_sent") is False
        ),
        "authorized_fixture_returns_ready_without_sending": (
            authorized_response.get("status") == "ready_for_exactly_one_send"
            and authorized_response.get("ready_for_exactly_one_send") is True
            and authorized_response.get("request_send_gate_authorized") is True
            and authorized_response.get("production_request_sent") is False
            and authorized_response.get("production_signing_executed") is False
            and authorized_response.get("production_http_network_executed") is False
        ),
        "invalid_secret_field_rejected": (
            invalid_response.get("status") == "error"
            and invalid_response.get("error") == "FORBIDDEN_FIELD:api_secret"
            and invalid_response.get("production_request_sent") is False
        ),
        "go_live_and_live_trading_stay_false": (
            authorized_response.get("go_live_allowed") is False
            and authorized_response.get("live_trading_allowed") is False
        ),
        "no_secret_values_rendered": (
            "redacted-fixture" not in rendered
            and "api_secret" not in json.dumps(authorized_response, sort_keys=True)
        ),
    }
    result = "PASS" if all(checks.values()) else "FAIL"
    report = {
        "generated_at": utc_now(),
        "result": result,
        "surface": "POST /trade-gate/production-order-send-decisions",
        "current_template_status": current_response.get("status"),
        "authorized_fixture_status": authorized_response.get("status"),
        "current_template_ready_for_exactly_one_send": current_response.get(
            "ready_for_exactly_one_send"
        ),
        "authorized_fixture_ready_for_exactly_one_send": authorized_response.get(
            "ready_for_exactly_one_send"
        ),
        "checks": checks,
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
    return f"""# Production Send Decision Entrypoint

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- surface: {report["surface"]}
- current template status: {report["current_template_status"]}
- authorized fixture status: {report["authorized_fixture_status"]}
- current template ready for exactly-one send: {str(report["current_template_ready_for_exactly_one_send"]).lower()}
- authorized fixture ready for exactly-one send: {str(report["authorized_fixture_ready_for_exactly_one_send"]).lower()}

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

    print("[Production Send Decision Entrypoint]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"result: {report['result']}")
    print(f"current_template_status: {report['current_template_status']}")
    print(f"authorized_fixture_status: {report['authorized_fixture_status']}")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
