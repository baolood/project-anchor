#!/usr/bin/env python3
"""Check final production send runner with fixture credentials and fake transport."""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "final_production_send_runner.json"
MD_OUT = REPORTS_DIR / "final_production_send_runner.md"

sys.path.insert(0, str(ROOT / "anchor-backend"))

from app.executors.production_send_runner import run_final_production_send  # noqa: E402
from app.trade_gate_production import (  # noqa: E402
    PRODUCTION_IDEMPOTENCY_KEY,
    PRODUCTION_REQUEST_SEND_GATE_REQUIRED_VERDICT,
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


def gate_config() -> dict:
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


def fixture_env() -> str:
    return "\n".join(
        [
            "PRODUCTION_EXCHANGE_BASE_URL=https://api.binance.com",
            "PRODUCTION_EXCHANGE_API_KEY=fixture-production-key",
            "PRODUCTION_EXCHANGE_API_SECRET=fixture-production-secret",
            "PRODUCTION_EXCHANGE_KEY_ID=fixture-production-key-id",
        ]
    )


def build_report() -> tuple[dict, int]:
    default_outcome, _, _, _ = run_final_production_send(
        request_body(),
        gate_config(),
        "/tmp/project-anchor-production-not-read.env",
        FIXED_NOW_TS,
    )
    fake_opener = FakeProductionOpener()
    with tempfile.NamedTemporaryFile("w", encoding="utf-8") as tmp:
        tmp.write(fixture_env())
        tmp.flush()
        no_execute_outcome, _, _, _ = run_final_production_send(
            request_body(),
            gate_config(),
            tmp.name,
            FIXED_NOW_TS,
            now=FIXED_NOW,
            credential_read_enabled=True,
        )
        outcome, requested_payload, terminal_type, terminal_payload = run_final_production_send(
            request_body(),
            gate_config(),
            tmp.name,
            FIXED_NOW_TS,
            now=FIXED_NOW,
            execute=True,
            credential_read_enabled=True,
            opener=fake_opener,
        )

    rendered = json.dumps(
        {
            "default_outcome": default_outcome,
            "no_execute_outcome": no_execute_outcome,
            "outcome": outcome,
            "requested_payload": requested_payload,
            "terminal_type": terminal_type,
            "terminal_payload": terminal_payload,
        },
        sort_keys=True,
    )
    checks = {
        "default_credential_read_fails_closed": (
            default_outcome.get("ok") is False
            and default_outcome.get("error", {}).get("code")
            == "PRODUCTION_CREDENTIAL_READ_NOT_AUTHORIZED"
        ),
        "fixture_credentials_still_require_execute": (
            no_execute_outcome.get("ok") is False
            and no_execute_outcome.get("error", {}).get("code")
            == "PRODUCTION_SEND_EXECUTION_NOT_AUTHORIZED"
        ),
        "fixture_fake_transport_path_parses_response": (
            outcome.get("ok") is True
            and terminal_type == "PRODUCTION_HTTP_RESPONSE"
            and terminal_payload.get("external_status") == "FILLED"
            and terminal_payload.get("external_order_id_present") is True
            and len(fake_opener.calls) == 1
        ),
        "redaction_preserved": (
            "fixture-production-key" not in rendered
            and "fixture-production-secret" not in rendered
            and "fixture-production-key-id" not in rendered
            and "signature=" not in rendered
        ),
    }
    result = "PASS" if all(checks.values()) else "FAIL"
    report = {
        "generated_at": utc_now(),
        "result": result,
        "default_failure_code": default_outcome.get("error", {}).get("code"),
        "no_execute_failure_code": no_execute_outcome.get("error", {}).get("code"),
        "fake_transport_terminal_type": terminal_type,
        "fake_transport_external_status": terminal_payload.get("external_status"),
        "fake_transport_external_order_id_present": terminal_payload.get(
            "external_order_id_present"
        ),
        "fake_transport_called_once": len(fake_opener.calls) == 1,
        "checks": checks,
        "boundary": {
            "real_credential_file_read": "NO",
            "fixture_credential_file_read": "YES",
            "secret_value_disclosed": "NO",
            "secret_length_disclosed": "NO",
            "secret_prefix_suffix_disclosed": "NO",
            "secret_hash_disclosed": "NO",
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
    return f"""# Final Production Send Runner

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- default failure code: {report["default_failure_code"]}
- no execute failure code: {report["no_execute_failure_code"]}
- fake transport terminal type: {report["fake_transport_terminal_type"]}
- fake transport external status: {report["fake_transport_external_status"]}
- fake transport external order id present: {str(report["fake_transport_external_order_id_present"]).lower()}
- fake transport called once: {str(report["fake_transport_called_once"]).lower()}

## Checks

{checks}

## Boundary

- real credential file read: {report["boundary"]["real_credential_file_read"]}
- fixture credential file read: {report["boundary"]["fixture_credential_file_read"]}
- secret value disclosed: {report["boundary"]["secret_value_disclosed"]}
- secret length disclosed: {report["boundary"]["secret_length_disclosed"]}
- secret prefix/suffix disclosed: {report["boundary"]["secret_prefix_suffix_disclosed"]}
- secret hash disclosed: {report["boundary"]["secret_hash_disclosed"]}
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

    print("[Final Production Send Runner]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"result: {report['result']}")
    print(f"default_failure_code: {report['default_failure_code']}")
    print(f"no_execute_failure_code: {report['no_execute_failure_code']}")
    print(f"fake_transport_called_once: {report['fake_transport_called_once']}")
    print("real_credential_file_read: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
