#!/usr/bin/env python3
"""Execute exactly one production request through the gated runner.

Default mode is non-executing and fail-closed. A real production request can
only be attempted with --execute, a passing fresh readiness decision, and a
canonical credential file that matches config/production_credential_contract.json.
The report is redacted and never includes secret values, lengths, prefixes,
suffixes, hashes, signatures, or Authorization header values.
"""

from __future__ import annotations

import argparse
import grp
import json
import pwd
import stat
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
CONTRACT_PATH = ROOT / "config" / "production_credential_contract.json"
JSON_OUT = REPORTS_DIR / "production_exactly_one_send_result.json"
MD_OUT = REPORTS_DIR / "production_exactly_one_send_result.md"

sys.path.insert(0, str(ROOT / "anchor-backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.executors.production_send_runner import run_final_production_send  # noqa: E402
from app.trade_gate_production import (  # noqa: E402
    PRODUCTION_IDEMPOTENCY_KEY,
    PRODUCTION_REQUEST_SEND_GATE_REQUIRED_VERDICT,
)
import decide_fresh_production_send_readiness as fresh_decision  # noqa: E402
import plan_production_request_send_window as window_plan  # noqa: E402


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


def load_contract() -> dict[str, Any]:
    return read_json(CONTRACT_PATH)


def owner_group_mode(path: Path) -> dict[str, Any]:
    try:
        st = path.stat()
    except FileNotFoundError:
        return {
            "exists": False,
            "owner": None,
            "group": None,
            "mode": None,
        }
    try:
        owner = pwd.getpwuid(st.st_uid).pw_name
    except KeyError:
        owner = str(st.st_uid)
    try:
        group = grp.getgrgid(st.st_gid).gr_name
    except KeyError:
        group = str(st.st_gid)
    return {
        "exists": True,
        "owner": owner,
        "group": group,
        "mode": f"{stat.S_IMODE(st.st_mode):03o}",
    }


def credential_contract_status(path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    observed = owner_group_mode(path)
    expected_path = str(contract.get("canonical_path") or "")
    expected_owner = str(contract.get("expected_owner") or "")
    expected_group = str(contract.get("expected_group") or "")
    expected_mode = str(contract.get("expected_mode") or "")
    checks = {
        "path_matches_contract": str(path) == expected_path,
        "file_exists": observed["exists"] is True,
        "owner_matches": observed["owner"] == expected_owner,
        "group_matches": observed["group"] == expected_group,
        "mode_matches": observed["mode"] == expected_mode,
    }
    return {
        "path": str(path),
        "expected_path": expected_path,
        "expected_owner": expected_owner,
        "expected_group": expected_group,
        "expected_mode": expected_mode,
        "observed_owner": observed["owner"],
        "observed_group": observed["group"],
        "observed_mode": observed["mode"],
        "checks": checks,
        "compliant": all(checks.values()),
    }


def request_body() -> dict[str, Any]:
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
        "PRODUCTION_REQUEST_SEND_IDEMPOTENCY_KEY": PRODUCTION_IDEMPOTENCY_KEY,
        "FINAL_PRODUCTION_REQUEST_SEND_OPERATOR_VERDICT": (
            PRODUCTION_REQUEST_SEND_GATE_REQUIRED_VERDICT
        ),
    }


def refresh_readiness_reports() -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    window_report, _ = window_plan.build_report()
    window_plan.JSON_OUT.write_text(
        json.dumps(window_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    window_plan.MD_OUT.write_text(window_plan.markdown(window_report), encoding="utf-8")

    decision_report, _ = fresh_decision.build_report()
    fresh_decision.JSON_OUT.write_text(
        json.dumps(decision_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    fresh_decision.MD_OUT.write_text(
        fresh_decision.markdown(decision_report),
        encoding="utf-8",
    )
    return decision_report


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
    readiness_report: dict[str, Any] | None = None,
    enforce_credential_contract: bool = True,
) -> tuple[dict[str, Any], int]:
    current = now or utc_now()
    now_ts = int(current.timestamp() * 1000)
    contract = load_contract()
    contract_status = credential_contract_status(credential_path, contract)
    if readiness_report is not None:
        readiness = readiness_report
    elif execute:
        readiness = refresh_readiness_reports()
    else:
        readiness = read_json(fresh_decision.JSON_OUT)
    readiness_pass = (
        readiness.get("result") == "PASS"
        and readiness.get("decision") == "READY_FOR_EXACTLY_ONE_PRODUCTION_REQUEST_SEND_WINDOW_OPEN"
    )

    outcome: dict[str, Any] | None = None
    requested_payload = None
    terminal_type = None
    terminal_payload = None
    failure_code = None

    if not execute:
        failure_code = "PRODUCTION_SEND_EXECUTION_NOT_REQUESTED"
    elif not readiness_pass:
        failure_code = "FRESH_PRODUCTION_SEND_READINESS_NOT_PASS"
    elif enforce_credential_contract and not contract_status["compliant"]:
        failure_code = "PRODUCTION_CREDENTIAL_CONTRACT_NOT_COMPLIANT"
    else:
        outcome, requested_payload, terminal_type, terminal_payload = run_final_production_send(
            request_body(),
            gate_config(current),
            credential_path,
            now_ts,
            now=current,
            execute=True,
            credential_read_enabled=True,
            opener=opener,
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
        "readiness_result": readiness.get("result"),
        "readiness_decision": readiness.get("decision"),
        "credential_contract": contract_status,
        "request": {
            "idempotency_key": PRODUCTION_IDEMPOTENCY_KEY,
            "market": "binance_spot",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "max_notional": 4,
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
            "canary_rerun": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    return report, 0 if success else 1


def markdown(report: dict[str, Any]) -> str:
    contract = report["credential_contract"]
    terminal = report["terminal"]
    boundary = report["boundary"]
    return f"""# Production Exactly-One Send Result

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- success: {str(report["success"]).lower()}
- failure code: {report["failure_code"]}
- execution requested: {str(report["execution_requested"]).lower()}
- readiness result: {report["readiness_result"]}
- readiness decision: {report["readiness_decision"]}

## Request

- idempotency key: `{report["request"]["idempotency_key"]}`
- market: {report["request"]["market"]}
- symbol: {report["request"]["symbol"]}
- side: {report["request"]["side"]}
- max notional: {report["request"]["max_notional"]}
- order type: {report["request"]["order_type"]}

## Credential Contract

- path: `{contract["path"]}`
- expected owner: {contract["expected_owner"]}
- expected group: {contract["expected_group"]}
- expected mode: {contract["expected_mode"]}
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
- canary rerun: {boundary["canary_rerun"]}
- go-live: {boundary["go_live"]}
- live trading: {boundary["live_trading"]}
"""


def write_report(report: dict[str, Any]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(markdown(report), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    contract = load_contract()
    default_path = str(contract.get("canonical_path") or "/etc/project-anchor/production.env")
    parser = argparse.ArgumentParser(
        description="Execute exactly one gated production request or produce a blocked report.",
    )
    parser.add_argument(
        "--credential-file",
        default=default_path,
        help="Production credential file path. Defaults to the canonical contract path.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute the exactly-one production request if every gate passes.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report, exit_code = build_execution_report(
        execute=bool(args.execute),
        credential_path=Path(args.credential_file),
    )
    write_report(report)

    print("[Production Exactly-One Send Result]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"result: {report['result']}")
    print(f"success: {str(report['success']).lower()}")
    print(f"failure_code: {report['failure_code']}")
    print(f"execution_requested: {str(report['execution_requested']).lower()}")
    print(f"readiness_decision: {report['readiness_decision']}")
    print(f"credential_contract_compliant: {str(report['credential_contract']['compliant']).lower()}")
    print(f"production_request_attempted: {report['boundary']['production_request_attempted']}")
    print(f"production_request_accepted: {report['boundary']['production_request_accepted']}")
    print("secret_value_disclosed: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
