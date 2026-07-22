#!/usr/bin/env python3
"""Drill the production send executor skeleton without sending a request."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "production_send_executor_skeleton_drill.json"
MD_OUT = REPORTS_DIR / "production_send_executor_skeleton_drill.md"

sys.path.insert(0, str(ROOT / "anchor-backend"))

from app.executors.production_order_executor import (  # noqa: E402
    build_signed_order_request,
    build_spot_market_order_params,
    redacted_request_shape,
    run_production_order_request,
)


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
    errors: list[str] = []
    try:
        params = build_spot_market_order_params(transport_input(), now_ts)
        signed_request = build_signed_order_request(
            transport_input(),
            fixture_credentials(),
            now_ts,
        )
        request_shape = redacted_request_shape(signed_request)
    except Exception as exc:  # noqa: BLE001 - drill should report fail-closed evidence.
        params = {}
        request_shape = {}
        errors.append(f"REQUEST_SHAPE_FAILED:{type(exc).__name__}")

    unauthorized_outcome, _, _, _ = run_production_order_request(
        transport_input(),
        None,
        now_ts,
    )
    execute_outcome, _, _, _ = run_production_order_request(
        transport_input(),
        fixture_credentials(),
        now_ts,
        execute=True,
    )

    checks = {
        "params_shape_valid": (
            params.get("symbol") == "BTCUSDT"
            and params.get("side") == "BUY"
            and params.get("type") == "MARKET"
            and params.get("quoteOrderQty") == "4"
        ),
        "redacted_request_shape_valid": (
            request_shape.get("signature_present") is True
            and request_shape.get("api_key_present") is True
            and "fixture-key" not in str(request_shape)
            and "fixture-secret" not in str(request_shape)
            and "signature=" not in str(request_shape)
        ),
        "unauthorized_path_fails_closed": (
            unauthorized_outcome.get("ok") is False
            and unauthorized_outcome.get("error", {}).get("code")
            == "PRODUCTION_SEND_EXECUTION_NOT_AUTHORIZED"
            and unauthorized_outcome.get("error", {}).get("external_request_started") is False
        ),
        "execute_path_stops_before_http_transport": (
            execute_outcome.get("ok") is False
            and execute_outcome.get("error", {}).get("code")
            == "PRODUCTION_HTTP_TRANSPORT_NOT_WIRED"
            and execute_outcome.get("error", {}).get("external_request_started") is False
        ),
    }
    result = "PASS" if not errors and all(checks.values()) else "FAIL"
    report = {
        "generated_at": utc_now(),
        "result": result,
        "params_shape": params,
        "redacted_request_shape": request_shape,
        "unauthorized_failure_code": unauthorized_outcome.get("error", {}).get("code"),
        "execute_failure_code": execute_outcome.get("error", {}).get("code"),
        "checks": checks,
        "errors": errors,
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
    errors = "\n".join(f"- {item}" for item in report["errors"]) or "- none"
    shape = "\n".join(
        f"- {key}: {value}" for key, value in report["redacted_request_shape"].items()
    )
    return f"""# Production Send Executor Skeleton Drill

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- unauthorized failure code: {report["unauthorized_failure_code"]}
- execute failure code: {report["execute_failure_code"]}

## Redacted Request Shape

{shape}

## Checks

{checks}

## Errors

{errors}

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

    print("[Production Send Executor Skeleton Drill]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"result: {report['result']}")
    print(f"unauthorized_failure_code: {report['unauthorized_failure_code']}")
    print(f"execute_failure_code: {report['execute_failure_code']}")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
