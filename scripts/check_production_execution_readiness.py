#!/usr/bin/env python3
"""Read-only production execution readiness check.

This check intentionally does not read credentials, env files, or external
services. It only evaluates non-secret repository evidence and records whether
production execution hard gates are still blocked.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RISK_LIMITS_CONFIG = ROOT / "config" / "production_risk_limits.template.json"
RISK_LIMITS_REPORT = ROOT / "reports" / "production_risk_limits_validation.json"
PRODUCTION_CREDENTIAL_READINESS_REPORT = ROOT / "reports" / "production_credential_readiness_validation.json"
PRODUCTION_SIGNING_READINESS_REPORT = ROOT / "reports" / "production_signing_readiness_validation.json"
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "production_execution_readiness.json"
MD_OUT = REPORTS_DIR / "production_execution_readiness.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - readiness should report failure cleanly.
        return None, f"{path.relative_to(ROOT)}:UNREADABLE:{type(exc).__name__}"
    if not isinstance(data, dict):
        return None, f"{path.relative_to(ROOT)}:NOT_OBJECT"
    return data, None


def yes_no(value: Any) -> str:
    return str(value or "").strip().upper()


def build_report() -> tuple[dict[str, Any], int]:
    config, config_error = read_json(RISK_LIMITS_CONFIG)
    risk_report, risk_report_error = read_json(RISK_LIMITS_REPORT)
    credential_report, credential_report_error = read_json(PRODUCTION_CREDENTIAL_READINESS_REPORT)
    signing_report, signing_report_error = read_json(PRODUCTION_SIGNING_READINESS_REPORT)

    errors: list[str] = []
    blockers: list[str] = []
    if config_error:
        errors.append(config_error)
    if risk_report_error:
        errors.append(risk_report_error)
    if credential_report_error:
        errors.append(credential_report_error)
    if signing_report_error:
        errors.append(signing_report_error)

    config = config or {}
    risk_report = risk_report or {}
    credential_report = credential_report or {}
    signing_report = signing_report or {}

    risk_limits_pass = risk_report.get("result") == "PASS" and not risk_report.get("errors")
    if not risk_limits_pass:
        blockers.append("production risk limits validation is not PASS")
    credential_readiness_pass = (
        credential_report.get("result") == "PASS" and not credential_report.get("errors")
    )
    if not credential_readiness_pass:
        blockers.append("production credential readiness validation is not PASS")
    signing_readiness_pass = signing_report.get("result") == "PASS" and not signing_report.get("errors")
    if not signing_readiness_pass:
        blockers.append("production signing readiness validation is not PASS")

    gates = {
        "production_credential_access": yes_no(config.get("AUTHORIZED_PRODUCTION_CREDENTIAL_ACCESS")),
        "production_signing": yes_no(config.get("AUTHORIZED_PRODUCTION_SIGNING")),
        "production_http_network": yes_no(config.get("AUTHORIZED_PRODUCTION_HTTP_NETWORK")),
        "go_live": yes_no(config.get("AUTHORIZED_GO_LIVE")),
        "live_trading": yes_no(config.get("AUTHORIZED_LIVE_TRADING")),
    }

    if gates["production_credential_access"] != "YES":
        blockers.append("production credential access not authorized")
    if gates["production_signing"] != "YES":
        blockers.append("production signing not authorized")
    if gates["production_http_network"] != "YES":
        blockers.append("production HTTP/network not authorized")
    if gates["go_live"] != "YES":
        blockers.append("go-live not authorized")
    if gates["live_trading"] != "YES":
        blockers.append("live trading not authorized")

    result = "PASS" if not errors and not blockers else "BLOCKED"
    report = {
        "generated_at": utc_now(),
        "result": result,
        "errors": errors,
        "blockers": blockers,
        "inputs": {
            "risk_limits_config": str(RISK_LIMITS_CONFIG.relative_to(ROOT)),
            "risk_limits_validation": str(RISK_LIMITS_REPORT.relative_to(ROOT)),
            "production_credential_readiness": str(
                PRODUCTION_CREDENTIAL_READINESS_REPORT.relative_to(ROOT)
            ),
            "production_signing_readiness": str(PRODUCTION_SIGNING_READINESS_REPORT.relative_to(ROOT)),
        },
        "evidence": {
            "risk_limits_validation": "PASS" if risk_limits_pass else "FAIL",
            "production_credential_readiness": "PASS" if credential_readiness_pass else "FAIL",
            "production_signing_readiness": "PASS" if signing_readiness_pass else "FAIL",
            "production_market": config.get("AUTHORIZED_PRODUCTION_MARKET"),
            "production_symbols": config.get("AUTHORIZED_PRODUCTION_SYMBOLS"),
            "production_sides": config.get("AUTHORIZED_PRODUCTION_SIDES"),
            "max_notional": config.get("AUTHORIZED_MAX_NOTIONAL"),
            "max_order_count": config.get("AUTHORIZED_MAX_ORDER_COUNT"),
        },
        "gates": gates,
        "boundary": {
            "secret_read": "NO",
            "credentials_env_config_read": "NO",
            "production_signing_enabled": "NO",
            "production_http_network_enabled": "NO",
            "production_request_sent": "NO",
            "canary_rerun": "NO",
            "runtime_modified": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    return report, 0 if result == "PASS" else 1


def markdown(report: dict[str, Any]) -> str:
    errors = "\n".join(f"- {item}" for item in report["errors"]) or "- none"
    blockers = "\n".join(f"- {item}" for item in report["blockers"]) or "- none"
    gates = "\n".join(f"- {key}: {value}" for key, value in report["gates"].items())
    evidence = "\n".join(f"- {key}: {value}" for key, value in report["evidence"].items())
    return f"""# Production Execution Readiness

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}

## Evidence

{evidence}

## Gates

{gates}

## Blockers

{blockers}

## Errors

{errors}

## Boundary

- secret read: {report["boundary"]["secret_read"]}
- credentials/env/config read: {report["boundary"]["credentials_env_config_read"]}
- production signing enabled: {report["boundary"]["production_signing_enabled"]}
- production HTTP/network enabled: {report["boundary"]["production_http_network_enabled"]}
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

    print("[Production Execution Readiness]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(f"blockers: {len(report['blockers'])}")
    print(f"risk_limits_validation: {report['evidence']['risk_limits_validation']}")
    print(f"production_credential_access: {report['gates']['production_credential_access']}")
    print(f"production_signing: {report['gates']['production_signing']}")
    print(f"production_http_network: {report['gates']['production_http_network']}")
    print("secret_read: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
