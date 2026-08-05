#!/usr/bin/env python3
"""Execute one next manual low-frequency production request through a separate gate.

Default mode is non-executing and fail-closed. This script intentionally writes
separate reports so the completed first production send evidence is never
overwritten by later manual operations.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "next_manual_low_frequency_production_send_result.json"
MD_OUT = REPORTS_DIR / "next_manual_low_frequency_production_send_result.md"

sys.path.insert(0, str(ROOT / "anchor-backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.executors.production_send_runner import (  # noqa: E402
    run_next_manual_low_frequency_production_send,
)
from app.trade_gate_production import (  # noqa: E402
    NEXT_MANUAL_LOW_FREQUENCY_PRODUCTION_IDEMPOTENCY_KEY,
    NEXT_MANUAL_LOW_FREQUENCY_REQUEST_SEND_GATE_REQUIRED_VERDICT,
)
import check_next_manual_operation_eligibility as next_eligibility  # noqa: E402
import execute_exactly_one_production_request as first_send  # noqa: E402


NEXT_MANUAL_REQUIRED_DECISION = (
    "READY_FOR_NEXT_MANUAL_LOW_FREQUENCY_OPERATOR_AUTHORIZATION_DECISION"
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def fmt(ts: datetime) -> str:
    return ts.isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def request_body() -> dict[str, Any]:
    risk_limits = read_json(ROOT / "config" / "production_risk_limits.template.json")
    notional = risk_limits.get("AUTHORIZED_MAX_NOTIONAL") or 10
    return {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "notional": notional,
        "order_type": "market",
        "execution_mode": "production",
        "market": "binance_spot",
        "source": "ops_manual",
        "idempotency_key": NEXT_MANUAL_LOW_FREQUENCY_PRODUCTION_IDEMPOTENCY_KEY,
    }


def gate_config(now: datetime) -> dict[str, Any]:
    expires_at = now + timedelta(minutes=60)
    return {
        "AUTHORIZED_PRODUCTION_REQUEST_SEND": "YES",
        "AUTHORIZED_PRODUCTION_CREDENTIAL_ACCESS": "YES",
        "AUTHORIZED_PRODUCTION_SIGNING": "YES",
        "AUTHORIZED_PRODUCTION_HTTP_NETWORK": "YES",
        "AUTHORIZED_GO_LIVE": "NO",
        "AUTHORIZED_LIVE_TRADING": "NO",
        "PRODUCTION_REQUEST_SEND_WINDOW_OPEN": True,
        "PRODUCTION_REQUEST_SEND_WINDOW_EXPIRES_AT": fmt(expires_at),
        "PRODUCTION_REQUEST_SEND_NO_RETRY": True,
        "PRODUCTION_REQUEST_SEND_IDEMPOTENCY_KEY": (
            NEXT_MANUAL_LOW_FREQUENCY_PRODUCTION_IDEMPOTENCY_KEY
        ),
        "FINAL_PRODUCTION_REQUEST_SEND_OPERATOR_VERDICT": (
            NEXT_MANUAL_LOW_FREQUENCY_REQUEST_SEND_GATE_REQUIRED_VERDICT
        ),
    }


def refresh_next_manual_eligibility(now: datetime) -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = next_eligibility.build_report(
        next_eligibility.DEFAULT_POLICY,
        REPORTS_DIR,
        now,
    )
    next_eligibility.DEFAULT_JSON_OUT.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    next_eligibility.DEFAULT_MD_OUT.write_text(
        next_eligibility.markdown(report),
        encoding="utf-8",
    )
    return report


def _terminal_payload(outcome: dict[str, Any]) -> dict[str, Any]:
    if isinstance(outcome.get("result"), dict):
        return outcome["result"]
    if isinstance(outcome.get("error"), dict):
        return outcome["error"]
    return {}


def build_execution_report(
    *,
    execute: bool,
    credential_path: Path,
    now: datetime | None = None,
    opener: Callable[..., Any] | None = None,
    eligibility_report: dict[str, Any] | None = None,
    enforce_credential_contract: bool = True,
    platform_name: str | None = None,
    enforce_execution_host_contract: bool = True,
) -> tuple[dict[str, Any], int]:
    current = now or utc_now()
    now_ts = int(current.timestamp() * 1000)
    contract = first_send.load_contract()
    api_configuration = first_send.load_api_configuration()
    execution_host_contract = first_send.execution_host_contract_status(
        api_configuration,
        platform_name=platform_name,
    )
    execution_host_blocks = (
        execute
        and enforce_execution_host_contract
        and not execution_host_contract["compliant"]
    )
    if execution_host_blocks:
        contract_status = first_send.credential_contract_not_evaluated(
            credential_path,
            contract,
        )
    else:
        contract_status = first_send.credential_contract_status(credential_path, contract)

    if eligibility_report is not None:
        eligibility = eligibility_report
    elif execute:
        eligibility = refresh_next_manual_eligibility(current)
    else:
        eligibility = read_json(next_eligibility.DEFAULT_JSON_OUT)
    eligibility_pass = (
        eligibility.get("result") == "PASS"
        and eligibility.get("decision") == NEXT_MANUAL_REQUIRED_DECISION
    )

    outcome: dict[str, Any] | None = None
    requested_payload = None
    terminal_type = None
    failure_code = None

    if not execute:
        failure_code = "NEXT_MANUAL_PRODUCTION_SEND_EXECUTION_NOT_REQUESTED"
    elif not eligibility_pass:
        failure_code = "NEXT_MANUAL_OPERATION_ELIGIBILITY_NOT_PASS"
    elif enforce_execution_host_contract and not execution_host_contract["compliant"]:
        failure_code = str(
            execution_host_contract.get("failure_code") or "PRODUCTION_EXECUTION_HOST_NOT_ALLOWED"
        )
    elif enforce_credential_contract and not contract_status["compliant"]:
        failure_code = "PRODUCTION_CREDENTIAL_CONTRACT_NOT_COMPLIANT"
    else:
        outcome, requested_payload, terminal_type, _terminal_payload_value = (
            run_next_manual_low_frequency_production_send(
                request_body(),
                gate_config(current),
                credential_path,
                now_ts,
                now=current,
                execute=True,
                credential_read_enabled=True,
                opener=opener,
            )
        )
        terminal = _terminal_payload(outcome)
        failure_code = terminal.get("code") if outcome.get("ok") is not True else None

    terminal = _terminal_payload(outcome or {})
    external_started = bool(terminal.get("external_request_started"))
    external_order_id_present = bool(terminal.get("external_order_id_present"))
    success = bool(outcome and outcome.get("ok") is True and external_order_id_present)
    runner_entered = outcome is not None
    result = "PASS" if success else "FAIL" if external_started else "BLOCKED"
    report = {
        "generated_at": fmt(current),
        "result": result,
        "success": success,
        "failure_code": failure_code,
        "execution_requested": execute,
        "eligibility_result": eligibility.get("result"),
        "eligibility_decision": eligibility.get("decision"),
        "credential_contract": contract_status,
        "execution_host_contract": execution_host_contract,
        "request": {
            "idempotency_key": NEXT_MANUAL_LOW_FREQUENCY_PRODUCTION_IDEMPOTENCY_KEY,
            "market": "binance_spot",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "max_notional": request_body()["notional"],
            "order_type": "market",
        },
        "terminal": {
            "terminal_type": terminal_type,
            "http_status": terminal.get("http_status"),
            "external_status": terminal.get("external_status"),
            "external_request_started": external_started,
            "external_order_id_present": external_order_id_present,
            "exchange_error_code_present": terminal.get("exchange_error_code_present"),
            "exchange_error_message_present": terminal.get("exchange_error_message_present"),
            "exchange_error_code": terminal.get("exchange_error_code"),
            "exchange_error_msg": terminal.get("exchange_error_msg"),
            "transport_error_type": terminal.get("transport_error_type"),
        },
        "requested_payload_shape": requested_payload,
        "boundary": {
            "credential_file_read": "YES" if runner_entered else "NO",
            "secret_value_disclosed": "NO",
            "secret_length_disclosed": "NO",
            "secret_prefix_suffix_disclosed": "NO",
            "secret_hash_disclosed": "NO",
            "production_signing_executed": "YES" if bool(requested_payload) else "NO",
            "authorization_header_value_disclosed": "NO",
            "dns_lookup_or_socket_possible": "YES" if external_started else "NO",
            "production_http_network_attempted": "YES" if external_started else "NO",
            "production_request_attempted": "YES" if external_started else "NO",
            "production_request_accepted": "YES" if success else "NO",
            "automatic_retry": "NO",
            "second_request_sent": "NO",
            "canary_rerun": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    return report, 0 if success else 1


def markdown(report: dict[str, Any]) -> str:
    contract = report["credential_contract"]
    execution_host = report["execution_host_contract"]
    terminal = report["terminal"]
    boundary = report["boundary"]
    return f"""# Next Manual Low-Frequency Production Send Result

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- success: {str(report["success"]).lower()}
- failure code: {report["failure_code"]}
- execution requested: {str(report["execution_requested"]).lower()}
- eligibility result: {report["eligibility_result"]}
- eligibility decision: {report["eligibility_decision"]}

## Request

- idempotency key: `{report["request"]["idempotency_key"]}`
- market: {report["request"]["market"]}
- symbol: {report["request"]["symbol"]}
- side: {report["request"]["side"]}
- max notional: {report["request"]["max_notional"]}
- order type: {report["request"]["order_type"]}

## Execution Host Contract

- expected Binance API IP whitelist: {execution_host["expected_binance_api_ip_whitelist"]}
- observed platform: {execution_host["observed_platform"]}
- compliant: {str(execution_host["compliant"]).lower()}
- failure code: {execution_host["failure_code"]}

## Credential Contract

- path: `{contract["path"]}`
- expected owner: {contract["expected_owner"]}
- expected group: {contract["expected_group"]}
- expected mode: {contract["expected_mode"]}
- stat error: {contract["stat_error"]}
- observed owner: {contract["observed_owner"]}
- observed group: {contract["observed_group"]}
- observed mode: {contract["observed_mode"]}
- compliant: {str(contract["compliant"]).lower()}

## Terminal

- terminal type: {terminal["terminal_type"]}
- http status: {terminal["http_status"]}
- external status: {terminal["external_status"]}
- external request started: {str(terminal["external_request_started"]).lower()}
- external order id present: {str(terminal["external_order_id_present"]).lower()}
- exchange error code present: {terminal["exchange_error_code_present"]}
- exchange error message present: {terminal["exchange_error_message_present"]}
- exchange error code: {terminal["exchange_error_code"]}
- exchange error message: {terminal["exchange_error_msg"]}
- transport error type: {terminal["transport_error_type"]}

## Boundary

- credential file read: {boundary["credential_file_read"]}
- secret value disclosed: {boundary["secret_value_disclosed"]}
- secret length disclosed: {boundary["secret_length_disclosed"]}
- secret prefix/suffix disclosed: {boundary["secret_prefix_suffix_disclosed"]}
- secret hash disclosed: {boundary["secret_hash_disclosed"]}
- production signing executed: {boundary["production_signing_executed"]}
- Authorization header value disclosed: {boundary["authorization_header_value_disclosed"]}
- DNS lookup or socket possible: {boundary["dns_lookup_or_socket_possible"]}
- production HTTP/network attempted: {boundary["production_http_network_attempted"]}
- production request attempted: {boundary["production_request_attempted"]}
- production request accepted: {boundary["production_request_accepted"]}
- automatic retry: {boundary["automatic_retry"]}
- second request sent: {boundary["second_request_sent"]}
- canary rerun: {boundary["canary_rerun"]}
- go-live: {boundary["go_live"]}
- live trading: {boundary["live_trading"]}
"""


def write_report(report: dict[str, Any]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(markdown(report), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    contract = first_send.load_contract()
    default_path = str(contract.get("canonical_path") or "/etc/project-anchor/production.env")
    parser = argparse.ArgumentParser(
        description="Execute one next manual low-frequency production request.",
    )
    parser.add_argument(
        "--credential-file",
        default=default_path,
        help="Production credential file path. Defaults to the canonical contract path.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute the request if every next-manual gate passes.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report, exit_code = build_execution_report(
        execute=bool(args.execute),
        credential_path=Path(args.credential_file),
    )
    write_report(report)

    print("[Next Manual Low-Frequency Production Send Result]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"result: {report['result']}")
    print(f"success: {str(report['success']).lower()}")
    print(f"failure_code: {report['failure_code']}")
    print(f"execution_requested: {str(report['execution_requested']).lower()}")
    print(f"eligibility_decision: {report['eligibility_decision']}")
    print(f"credential_contract_compliant: {str(report['credential_contract']['compliant']).lower()}")
    print(f"production_request_attempted: {report['boundary']['production_request_attempted']}")
    print(f"production_request_accepted: {report['boundary']['production_request_accepted']}")
    print("secret_value_disclosed: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
