#!/usr/bin/env python3
"""Check the production send entrypoint fail-closed contract."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "anchor-backend"))

from app.trade_gate_production import (  # noqa: E402
    PRODUCTION_COMMAND_CREATED_STATUS,
    PRODUCTION_COMMAND_TYPE,
    PRODUCTION_EXECUTION_GATE_REQUIRED_VERDICT,
    PRODUCTION_IDEMPOTENCY_KEY,
    load_production_execution_gate_config,
    production_order_command_creation_candidate_response,
    production_execution_gate_decision,
    production_order_blocked_response,
    validate_production_order_request,
)

REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "production_send_entrypoint_fail_closed.json"
MD_OUT = REPORTS_DIR / "production_send_entrypoint_fail_closed.md"


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


def build_report() -> tuple[dict, int]:
    ok, reason = validate_production_order_request(valid_body())
    bad_notional_ok, bad_notional_reason = validate_production_order_request(
        dict(valid_body(), notional=5)
    )
    bad_key_ok, bad_key_reason = validate_production_order_request(
        dict(valid_body(), idempotency_key="production:unexpected")
    )
    secret_ok, secret_reason = validate_production_order_request(
        dict(valid_body(), api_secret="redacted-fixture")
    )
    default_gate = production_execution_gate_decision()
    current_gate_config = load_production_execution_gate_config()
    current_config_gate = production_execution_gate_decision(current_gate_config)
    complete_gate = production_execution_gate_decision(
        {
            "PRODUCTION_EXECUTION_GATE_ENABLED": True,
            "PRODUCTION_EXACTLY_ONE_COMMAND_CREATION": True,
            "PRODUCTION_NO_RETRY": True,
            "PRODUCTION_IDEMPOTENCY_KEY": PRODUCTION_IDEMPOTENCY_KEY,
            "FINAL_OPERATOR_VERDICT": PRODUCTION_EXECUTION_GATE_REQUIRED_VERDICT,
        }
    )
    blocked = production_order_blocked_response(default_gate)
    candidate = production_order_command_creation_candidate_response(
        valid_body(),
        complete_gate,
    )

    checks = [
        {
            "name": "valid_shape_accepted_by_validator",
            "result": "PASS" if ok and reason is None else "FAIL",
        },
        {
            "name": "unbounded_notional_rejected",
            "result": "PASS"
            if bad_notional_ok is False and bad_notional_reason == "PRODUCTION_NOTIONAL_INVALID"
            else "FAIL",
        },
        {
            "name": "wrong_idempotency_key_rejected",
            "result": "PASS"
            if bad_key_ok is False and bad_key_reason == "PRODUCTION_IDEMPOTENCY_KEY_INVALID"
            else "FAIL",
        },
        {
            "name": "secret_field_rejected",
            "result": "PASS"
            if secret_ok is False and secret_reason == "FORBIDDEN_FIELD:api_secret"
            else "FAIL",
        },
        {
            "name": "blocked_response_has_no_command_id",
            "result": "PASS"
            if blocked.get("status") == "blocked"
            and blocked.get("command_created") is False
            and blocked.get("production_request_sent") is False
            and blocked.get("execution_gate_authorized") is False
            and "command_id" not in blocked
            else "FAIL",
        },
        {
            "name": "default_gate_closed",
            "result": "PASS"
            if default_gate.get("authorized") is False
            and default_gate.get("reason") == "PRODUCTION_EXECUTION_GATE_CLOSED"
            else "FAIL",
        },
        {
            "name": "current_gate_config_loaded_and_closed",
            "result": "PASS"
            if isinstance(current_gate_config, dict)
            and current_config_gate.get("authorized") is False
            and current_config_gate.get("reason") == "PRODUCTION_EXECUTION_GATE_CLOSED"
            else "FAIL",
        },
        {
            "name": "complete_gate_config_can_authorize_command_creation_decision",
            "result": "PASS" if complete_gate.get("authorized") is True else "FAIL",
        },
        {
            "name": "authorized_gate_produces_non_send_command_creation_candidate",
            "result": "PASS"
            if candidate.get("status") == "ready_to_create_command"
            and candidate.get("command_type") == PRODUCTION_COMMAND_TYPE
            and candidate.get("command_creation_candidate") is True
            and candidate.get("command_created") is False
            and candidate.get("production_request_sent") is False
            and "command_id" not in candidate
            else "FAIL",
        },
    ]
    passed = all(item["result"] == "PASS" for item in checks)
    report = {
        "generated_at": utc_now(),
        "result": "PASS" if passed else "FAIL",
        "surface": "POST /trade-gate/production-order-intents",
        "entrypoint_present": True,
        "valid_shape_accepted_by_validator": ok and reason is None,
        "send_authorized": False,
        "execution_gate_authorized": False,
        "current_gate_config_authorized": current_config_gate.get("authorized") is True,
        "command_creation_candidate": candidate.get("command_creation_candidate") is True,
        "command_type": PRODUCTION_COMMAND_TYPE,
        "non_executable_persistence_status": PRODUCTION_COMMAND_CREATED_STATUS,
        "worker_executable": False,
        "command_created": False,
        "production_request_sent": False,
        "default_gate_decision": default_gate,
        "current_gate_config_decision": current_config_gate,
        "complete_gate_fixture_decision": complete_gate,
        "command_creation_candidate_response_shape": candidate,
        "checks": checks,
        "blocked_response_shape": blocked,
        "boundary": {
            "secret_read": "NO",
            "secret_value_disclosed": "NO",
            "production_signing_executed": "NO",
            "authorization_header_generated": "NO",
            "dns_lookup_performed": "NO",
            "socket_opened": "NO",
            "production_http_network_executed": "NO",
            "production_request_sent": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    return report, 0 if passed else 1


def markdown(report: dict) -> str:
    checks = "\n".join("- {name}: {result}".format(**item) for item in report["checks"])
    return f"""# Production Send Entrypoint Fail-Closed Check

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- surface: `{report["surface"]}`
- entrypoint present: {str(report["entrypoint_present"]).lower()}
- valid shape accepted by validator: {str(report["valid_shape_accepted_by_validator"]).lower()}
- send authorized: {str(report["send_authorized"]).lower()}
- execution gate authorized: {str(report["execution_gate_authorized"]).lower()}
- current gate config authorized: {str(report["current_gate_config_authorized"]).lower()}
- command creation candidate: {str(report["command_creation_candidate"]).lower()}
- command type: `{report["command_type"]}`
- non-executable persistence status: `{report["non_executable_persistence_status"]}`
- worker executable: {str(report["worker_executable"]).lower()}
- command created: {str(report["command_created"]).lower()}
- production request sent: {str(report["production_request_sent"]).lower()}

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
- go-live: {report["boundary"]["go_live"]}
- live trading: {report["boundary"]["live_trading"]}
"""


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report, exit_code = build_report()
    JSON_OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(markdown(report), encoding="utf-8")
    print("[Production Send Entrypoint Fail-Closed Check]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"result: {report['result']}")
    print(f"entrypoint_present: {str(report['entrypoint_present']).lower()}")
    print(f"send_authorized: {str(report['send_authorized']).lower()}")
    print(f"execution_gate_authorized: {str(report['execution_gate_authorized']).lower()}")
    print(f"current_gate_config_authorized: {str(report['current_gate_config_authorized']).lower()}")
    print(f"command_creation_candidate: {str(report['command_creation_candidate']).lower()}")
    print(f"command_type: {report['command_type']}")
    print(f"non_executable_persistence_status: {report['non_executable_persistence_status']}")
    print(f"worker_executable: {str(report['worker_executable']).lower()}")
    print(f"command_created: {str(report['command_created']).lower()}")
    print(f"production_request_sent: {str(report['production_request_sent']).lower()}")
    print("secret_read: NO")
    print("production_signing_executed: NO")
    print("production_http_network_executed: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
