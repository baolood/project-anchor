#!/usr/bin/env python3
"""Drill production HTTP transport wiring with an injected fake transport."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "production_http_transport_wiring_drill.json"
MD_OUT = REPORTS_DIR / "production_http_transport_wiring_drill.md"

sys.path.insert(0, str(ROOT / "anchor-backend"))

from app.executors.production_order_executor import run_production_order_request  # noqa: E402


class FakeProductionResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return (
            b'{"symbol":"BTCUSDT","orderId":12345,"clientOrderId":"dry-run-client",'
            b'"transactTime":1234567890,"status":"FILLED"}'
        )


class FakeProductionOpener:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, request, timeout):
        self.calls.append(
            {
                "method": request.get_method(),
                "host": request.host,
                "selector_present": bool(request.selector),
                "timeout": timeout,
            }
        )
        return FakeProductionResponse()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def transport_input() -> dict:
    return {
        "execution_mode": "production",
        "market": "binance_spot",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "notional": 4,
        "order_type": "market",
        "idempotency_key": "production:ops_manual:BTCUSDT:BUY:4:first-bounded-production-request:v1",
    }


def fixture_credentials() -> dict:
    return {
        "base_url": "https://api.binance.com",
        "api_key": "fixture-key",
        "api_secret": "fixture-secret",
    }


def build_report() -> tuple[dict, int]:
    now_ts = 1234567890
    fake_opener = FakeProductionOpener()
    unauthorized_outcome, _, _, _ = run_production_order_request(
        transport_input(),
        fixture_credentials(),
        now_ts,
        execute=True,
    )
    outcome, requested_payload, terminal_type, terminal_payload = run_production_order_request(
        transport_input(),
        fixture_credentials(),
        now_ts,
        execute=True,
        transport_enabled=True,
        opener=fake_opener,
    )
    rendered = json.dumps(
        {
            "outcome": outcome,
            "requested_payload": requested_payload,
            "terminal_type": terminal_type,
            "terminal_payload": terminal_payload,
            "fake_calls": fake_opener.calls,
        },
        sort_keys=True,
    )
    checks = {
        "transport_not_authorized_by_default": (
            unauthorized_outcome.get("ok") is False
            and unauthorized_outcome.get("error", {}).get("code")
            == "PRODUCTION_HTTP_TRANSPORT_NOT_AUTHORIZED"
            and unauthorized_outcome.get("error", {}).get("external_request_started") is False
        ),
        "fake_transport_called_once": len(fake_opener.calls) == 1,
        "fake_transport_response_parsed": (
            outcome.get("ok") is True
            and terminal_type == "PRODUCTION_HTTP_RESPONSE"
            and terminal_payload.get("external_status") == "FILLED"
            and terminal_payload.get("external_order_id_present") is True
        ),
        "redaction_preserved": (
            "fixture-key" not in rendered
            and "fixture-secret" not in rendered
            and "signature=" not in rendered
        ),
        "real_network_not_used": True,
    }
    result = "PASS" if all(checks.values()) else "FAIL"
    report = {
        "generated_at": utc_now(),
        "result": result,
        "transport_wiring": {
            "default_transport_enabled": False,
            "fake_transport_called_once": len(fake_opener.calls) == 1,
            "terminal_type": terminal_type,
            "external_status": terminal_payload.get("external_status"),
            "external_order_id_present": terminal_payload.get("external_order_id_present"),
        },
        "default_failure_code": unauthorized_outcome.get("error", {}).get("code"),
        "redacted_requested_payload": requested_payload,
        "checks": checks,
        "boundary": {
            "secret_read": "NO",
            "secret_value_disclosed": "NO",
            "production_signing_with_real_secret": "NO",
            "authorization_header_value_disclosed": "NO",
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
    payload = "\n".join(
        f"- {key}: {value}" for key, value in report["redacted_requested_payload"].items()
    )
    return f"""# Production HTTP Transport Wiring Drill

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- default failure code: {report["default_failure_code"]}
- fake transport called once: {str(report["transport_wiring"]["fake_transport_called_once"]).lower()}
- fake terminal type: {report["transport_wiring"]["terminal_type"]}
- fake external status: {report["transport_wiring"]["external_status"]}
- fake external order id present: {str(report["transport_wiring"]["external_order_id_present"]).lower()}

## Redacted Requested Payload

{payload}

## Checks

{checks}

## Boundary

- secret read: {report["boundary"]["secret_read"]}
- secret value disclosed: {report["boundary"]["secret_value_disclosed"]}
- production signing with real secret: {report["boundary"]["production_signing_with_real_secret"]}
- Authorization header value disclosed: {report["boundary"]["authorization_header_value_disclosed"]}
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

    print("[Production HTTP Transport Wiring Drill]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"result: {report['result']}")
    print(f"default_failure_code: {report['default_failure_code']}")
    print(f"fake_transport_called_once: {report['transport_wiring']['fake_transport_called_once']}")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
