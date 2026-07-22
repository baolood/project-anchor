#!/usr/bin/env python3
"""Check gated production send executor entrypoint with fake transport only."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "gated_production_send_executor_entrypoint.json"
MD_OUT = REPORTS_DIR / "gated_production_send_executor_entrypoint.md"

sys.path.insert(0, str(ROOT / "anchor-backend"))

from app.executors.production_order_executor import run_gated_production_order_request  # noqa: E402
from app.trade_gate_production import (  # noqa: E402
    PRODUCTION_IDEMPOTENCY_KEY,
    PRODUCTION_REQUEST_SEND_GATE_REQUIRED_VERDICT,
    load_production_execution_gate_config,
)


FIXED_NOW = datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc)
FIXED_NOW_TS = 1234567890


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


def request_body() -> dict:
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


def authorized_gate_config() -> dict:
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


def fixture_credentials() -> dict:
    return {
        "base_url": "https://api.binance.com",
        "api_key": "fixture-key",
        "api_secret": "fixture-secret",
    }


def build_report() -> tuple[dict, int]:
    current_fake = FakeProductionOpener()
    current_outcome, _, _, _ = run_gated_production_order_request(
        request_body(),
        load_production_execution_gate_config(),
        fixture_credentials(),
        FIXED_NOW_TS,
        now=FIXED_NOW,
        execute=True,
        opener=current_fake,
    )
    ready_no_execute_outcome, _, _, _ = run_gated_production_order_request(
        request_body(),
        authorized_gate_config(),
        fixture_credentials(),
        FIXED_NOW_TS,
        now=FIXED_NOW,
    )
    ready_fake = FakeProductionOpener()
    ready_outcome, requested_payload, terminal_type, terminal_payload = (
        run_gated_production_order_request(
            request_body(),
            authorized_gate_config(),
            fixture_credentials(),
            FIXED_NOW_TS,
            now=FIXED_NOW,
            execute=True,
            opener=ready_fake,
        )
    )
    rendered = json.dumps(
        {
            "current_outcome": current_outcome,
            "ready_no_execute_outcome": ready_no_execute_outcome,
            "ready_outcome": ready_outcome,
            "requested_payload": requested_payload,
            "terminal_type": terminal_type,
            "terminal_payload": terminal_payload,
        },
        sort_keys=True,
    )
    checks = {
        "current_template_blocks_before_executor": (
            current_outcome.get("ok") is False
            and current_outcome.get("error", {}).get("code")
            == "PRODUCTION_REQUEST_SEND_GATE_CLOSED"
            and len(current_fake.calls) == 0
        ),
        "ready_gate_still_requires_execute_flag": (
            ready_no_execute_outcome.get("ok") is False
            and ready_no_execute_outcome.get("error", {}).get("code")
            == "PRODUCTION_SEND_EXECUTION_NOT_AUTHORIZED"
        ),
        "authorized_fixture_fake_transport_parses_response": (
            ready_outcome.get("ok") is True
            and terminal_type == "PRODUCTION_HTTP_RESPONSE"
            and terminal_payload.get("external_status") == "FILLED"
            and terminal_payload.get("external_order_id_present") is True
            and len(ready_fake.calls) == 1
        ),
        "redaction_preserved": (
            "fixture-key" not in rendered
            and "fixture-secret" not in rendered
            and "signature=" not in rendered
        ),
    }
    result = "PASS" if all(checks.values()) else "FAIL"
    report = {
        "generated_at": utc_now(),
        "result": result,
        "current_template_failure_code": current_outcome.get("error", {}).get("code"),
        "ready_without_execute_failure_code": ready_no_execute_outcome.get("error", {}).get("code"),
        "fake_transport_terminal_type": terminal_type,
        "fake_transport_external_status": terminal_payload.get("external_status"),
        "fake_transport_external_order_id_present": terminal_payload.get(
            "external_order_id_present"
        ),
        "fake_transport_called_once": len(ready_fake.calls) == 1,
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
    return f"""# Gated Production Send Executor Entrypoint

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- current template failure code: {report["current_template_failure_code"]}
- ready without execute failure code: {report["ready_without_execute_failure_code"]}
- fake transport terminal type: {report["fake_transport_terminal_type"]}
- fake transport external status: {report["fake_transport_external_status"]}
- fake transport external order id present: {str(report["fake_transport_external_order_id_present"]).lower()}
- fake transport called once: {str(report["fake_transport_called_once"]).lower()}

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

    print("[Gated Production Send Executor Entrypoint]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"result: {report['result']}")
    print(f"current_template_failure_code: {report['current_template_failure_code']}")
    print(f"ready_without_execute_failure_code: {report['ready_without_execute_failure_code']}")
    print(f"fake_transport_called_once: {report['fake_transport_called_once']}")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
