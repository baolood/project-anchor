#!/usr/bin/env python3
"""Check production credential loader with a temporary fixture only."""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "production_credential_loader.json"
MD_OUT = REPORTS_DIR / "production_credential_loader.md"

sys.path.insert(0, str(ROOT / "anchor-backend"))

from app.executors.production_credentials import (  # noqa: E402
    load_production_credentials,
    redacted_credential_shape,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
    unauthorized_credentials, unauthorized_report = load_production_credentials(
        "/tmp/project-anchor-production-not-read.env"
    )
    with tempfile.NamedTemporaryFile("w", encoding="utf-8") as tmp:
        tmp.write(fixture_env())
        tmp.flush()
        credentials, load_report = load_production_credentials(tmp.name, allow_read=True)
        shape = redacted_credential_shape(credentials, load_report)

    rendered = json.dumps(
        {
            "unauthorized_report": unauthorized_report,
            "load_report": load_report,
            "shape": shape,
        },
        sort_keys=True,
    )
    checks = {
        "default_read_fails_closed": (
            unauthorized_credentials is None
            and unauthorized_report.get("code") == "PRODUCTION_CREDENTIAL_READ_NOT_AUTHORIZED"
        ),
        "authorized_fixture_loads": credentials is not None and load_report.get("ok") is True,
        "redacted_shape_valid": (
            shape.get("loaded") is True
            and shape.get("base_url_present") is True
            and shape.get("api_key_present") is True
            and shape.get("api_secret_present") is True
            and shape.get("key_id_present") is True
        ),
        "secret_values_not_rendered": (
            "fixture-production-key" not in rendered
            and "fixture-production-secret" not in rendered
            and "fixture-production-key-id" not in rendered
        ),
    }
    result = "PASS" if all(checks.values()) else "FAIL"
    report = {
        "generated_at": utc_now(),
        "result": result,
        "loader_default_code": unauthorized_report.get("code"),
        "loader_fixture_code": load_report.get("code"),
        "redacted_shape": shape,
        "checks": checks,
        "boundary": {
            "real_credential_file_read": "NO",
            "fixture_credential_file_read": "YES",
            "secret_value_disclosed": "NO",
            "secret_length_disclosed": "NO",
            "secret_prefix_suffix_disclosed": "NO",
            "secret_hash_disclosed": "NO",
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
    shape = "\n".join(
        f"- {key}: {value}" for key, value in report["redacted_shape"].items()
    )
    return f"""# Production Credential Loader

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- loader default code: {report["loader_default_code"]}
- loader fixture code: {report["loader_fixture_code"]}

## Redacted Shape

{shape}

## Checks

{checks}

## Boundary

- real credential file read: {report["boundary"]["real_credential_file_read"]}
- fixture credential file read: {report["boundary"]["fixture_credential_file_read"]}
- secret value disclosed: {report["boundary"]["secret_value_disclosed"]}
- secret length disclosed: {report["boundary"]["secret_length_disclosed"]}
- secret prefix/suffix disclosed: {report["boundary"]["secret_prefix_suffix_disclosed"]}
- secret hash disclosed: {report["boundary"]["secret_hash_disclosed"]}
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

    print("[Production Credential Loader]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"result: {report['result']}")
    print(f"loader_default_code: {report['loader_default_code']}")
    print(f"loader_fixture_code: {report['loader_fixture_code']}")
    print("real_credential_file_read: NO")
    print("secret_value_disclosed: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
