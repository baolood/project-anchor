#!/usr/bin/env python3
"""Generate a production execution handoff snapshot from existing evidence.

The snapshot is read-only: it consumes existing report JSON files and writes a
decision-oriented handoff report. It does not read secrets, call runtime
endpoints, sign payloads, open sockets, or send production requests.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "production_execution_handoff_snapshot.json"
MD_OUT = REPORTS_DIR / "production_execution_handoff_snapshot.md"

OPERATIONS_SNAPSHOT = REPORTS_DIR / "operations_readiness_snapshot.json"
NON_EXECUTABLE_COMMAND_DRILL = (
    REPORTS_DIR / "production_non_executable_command_creation_drill.json"
)
SEND_ENTRYPOINT = REPORTS_DIR / "production_send_entrypoint_fail_closed.json"
PRE_SEND_AGGREGATION = REPORTS_DIR / "production_pre_send_readiness_aggregation.json"
SEND_WINDOW_PLAN = REPORTS_DIR / "production_request_send_window_plan.json"
SEND_EXECUTOR_SKELETON = REPORTS_DIR / "production_send_executor_skeleton_drill.json"
HTTP_TRANSPORT_WIRING = REPORTS_DIR / "production_http_transport_wiring_drill.json"
REQUEST_SEND_GATE = REPORTS_DIR / "production_request_send_gate.json"
SEND_DECISION_ENTRYPOINT = REPORTS_DIR / "production_send_decision_entrypoint.json"
GATED_EXECUTOR_ENTRYPOINT = REPORTS_DIR / "gated_production_send_executor_entrypoint.json"
PRODUCTION_CREDENTIAL_LOADER = REPORTS_DIR / "production_credential_loader.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - reports should fail closed with explicit evidence.
        return {}, f"{path.relative_to(ROOT)}:UNREADABLE:{type(exc).__name__}"
    if not isinstance(data, dict):
        return {}, f"{path.relative_to(ROOT)}:NOT_OBJECT"
    return data, None


def pass_fail(value: bool) -> str:
    return "PASS" if value else "FAIL"


def build_snapshot() -> tuple[dict[str, Any], int]:
    generated_at = utc_now()
    ops, ops_error = read_json(OPERATIONS_SNAPSHOT)
    creation, creation_error = read_json(NON_EXECUTABLE_COMMAND_DRILL)
    entrypoint, entrypoint_error = read_json(SEND_ENTRYPOINT)
    pre_send, pre_send_error = read_json(PRE_SEND_AGGREGATION)
    send_window, send_window_error = read_json(SEND_WINDOW_PLAN)
    executor_skeleton, executor_skeleton_error = read_json(SEND_EXECUTOR_SKELETON)
    http_transport, http_transport_error = read_json(HTTP_TRANSPORT_WIRING)
    request_send_gate, request_send_gate_error = read_json(REQUEST_SEND_GATE)
    send_decision_entrypoint, send_decision_entrypoint_error = read_json(SEND_DECISION_ENTRYPOINT)
    gated_executor_entrypoint, gated_executor_entrypoint_error = read_json(GATED_EXECUTOR_ENTRYPOINT)
    credential_loader, credential_loader_error = read_json(PRODUCTION_CREDENTIAL_LOADER)
    errors = [
        item
        for item in [
            ops_error,
            creation_error,
            entrypoint_error,
            pre_send_error,
            send_window_error,
            executor_skeleton_error,
            http_transport_error,
            request_send_gate_error,
            send_decision_entrypoint_error,
            gated_executor_entrypoint_error,
            credential_loader_error,
        ]
        if item
    ]

    controlled = ops.get("latest_controlled_request") if isinstance(ops.get("latest_controlled_request"), dict) else {}
    canary = ops.get("latest_canary") if isinstance(ops.get("latest_canary"), dict) else {}
    go_live = ops.get("go_live") if isinstance(ops.get("go_live"), dict) else {}
    blockers = go_live.get("blocking_gates") if isinstance(go_live.get("blocking_gates"), list) else []

    checks = {
        "controlled_request_filled": (
            controlled.get("status") == "DONE"
            and controlled.get("external_status") == "FILLED"
            and controlled.get("external_order_id_present") is True
        ),
        "canary_filled": (
            canary.get("status") == "DONE"
            and canary.get("external_status") == "FILLED"
            and canary.get("external_order_id_present") is True
        ),
        "production_entrypoint_present": entrypoint.get("entrypoint_present") is True,
        "production_command_candidate_available": (
            entrypoint.get("command_creation_candidate") is True
        ),
        "production_non_executable_command_created": (
            creation.get("result") == "PASS"
            and creation.get("command_status") == "CREATED_NOT_EXECUTABLE"
            and creation.get("worker_executable") is False
        ),
        "production_send_not_authorized": entrypoint.get("send_authorized") is False,
        "production_request_not_sent": (
            entrypoint.get("production_request_sent") is False
            and creation.get("boundary", {}).get("production_request_sent") == "NO"
        ),
        "go_live_no_go": go_live.get("verdict") == "NO-GO",
        "go_live_blockers_explicit": bool(blockers),
        "send_window_plan_present": send_window.get("result") == "PASS",
        "send_window_not_authorized": send_window.get("send_authorized") is False,
        "pre_send_chain_complete": pre_send.get("evidence_chain_complete") is True,
        "production_send_executor_skeleton_ready": executor_skeleton.get("result") == "PASS",
        "production_http_transport_not_authorized_by_default": (
            executor_skeleton.get("execute_failure_code") == "PRODUCTION_HTTP_TRANSPORT_NOT_AUTHORIZED"
            and http_transport.get("default_failure_code") == "PRODUCTION_HTTP_TRANSPORT_NOT_AUTHORIZED"
        ),
        "production_http_transport_wiring_ready": http_transport.get("result") == "PASS",
        "production_http_transport_fake_response_parsed": (
            http_transport.get("transport_wiring", {}).get("terminal_type")
            == "PRODUCTION_HTTP_RESPONSE"
            and http_transport.get("transport_wiring", {}).get("external_status") == "FILLED"
        ),
        "production_request_send_gate_ready": request_send_gate.get("result") == "PASS",
        "production_request_send_gate_template_closed": (
            request_send_gate.get("current_template_authorized") is False
        ),
        "production_request_send_gate_fixture_authorizes": (
            request_send_gate.get("fixture_authorized") is True
        ),
        "production_send_decision_entrypoint_ready": (
            send_decision_entrypoint.get("result") == "PASS"
        ),
        "production_send_decision_current_template_blocked": (
            send_decision_entrypoint.get("current_template_ready_for_exactly_one_send") is False
        ),
        "production_send_decision_authorized_fixture_ready": (
            send_decision_entrypoint.get("authorized_fixture_ready_for_exactly_one_send") is True
        ),
        "gated_production_send_executor_entrypoint_ready": (
            gated_executor_entrypoint.get("result") == "PASS"
        ),
        "gated_executor_current_template_closed": (
            gated_executor_entrypoint.get("current_template_failure_code")
            == "PRODUCTION_REQUEST_SEND_GATE_CLOSED"
        ),
        "gated_executor_fake_transport_ready": (
            gated_executor_entrypoint.get("fake_transport_called_once") is True
            and gated_executor_entrypoint.get("fake_transport_external_status") == "FILLED"
        ),
        "production_credential_loader_ready": credential_loader.get("result") == "PASS",
        "production_credential_loader_default_closed": (
            credential_loader.get("loader_default_code")
            == "PRODUCTION_CREDENTIAL_READ_NOT_AUTHORIZED"
        ),
    }
    critical_checks = [
        checks["controlled_request_filled"],
        checks["canary_filled"],
        checks["production_non_executable_command_created"],
        checks["production_request_not_sent"],
        checks["go_live_no_go"],
    ]
    result = "PASS" if not errors and all(critical_checks) else "FAIL"
    next_gate = (
        "EXPLICIT_EXACTLY_ONE_PRODUCTION_REQUEST_SEND_AUTHORIZATION"
        if result == "PASS"
        else "BLOCKED_HANDOFF_EVIDENCE_INCOMPLETE"
    )
    snapshot = {
        "generated_at": generated_at,
        "result": result,
        "handoff_status": "READY_FOR_DECISION" if result == "PASS" else "BLOCKED",
        "next_gate": next_gate,
        "errors": errors,
        "checks": {key: pass_fail(value) for key, value in checks.items()},
        "testnet_baseline": {
            "controlled_request": {
                "command_id": controlled.get("command_id"),
                "status": controlled.get("status"),
                "external_status": controlled.get("external_status"),
                "external_order_id_present": controlled.get("external_order_id_present"),
                "executed_at": controlled.get("executed_at"),
            },
            "canary": {
                "command_id": canary.get("command_id"),
                "status": canary.get("status"),
                "external_status": canary.get("external_status"),
                "external_order_id_present": canary.get("external_order_id_present"),
                "executed_at": canary.get("executed_at"),
            },
        },
        "production_state": {
            "entrypoint_present": entrypoint.get("entrypoint_present"),
            "command_creation_candidate": entrypoint.get("command_creation_candidate"),
            "non_executable_command_id": creation.get("command_id"),
            "non_executable_command_status": creation.get("command_status"),
            "worker_executable": creation.get("worker_executable"),
            "send_authorized": entrypoint.get("send_authorized"),
            "send_executor_skeleton": executor_skeleton.get("result"),
            "send_executor_execute_failure_code": executor_skeleton.get("execute_failure_code"),
            "http_transport_wiring": http_transport.get("result"),
            "http_transport_default_failure_code": http_transport.get("default_failure_code"),
            "http_transport_fake_terminal_type": http_transport.get("transport_wiring", {}).get("terminal_type"),
            "http_transport_fake_external_status": http_transport.get("transport_wiring", {}).get("external_status"),
            "request_send_gate": request_send_gate.get("result"),
            "request_send_gate_current_template_authorized": request_send_gate.get("current_template_authorized"),
            "request_send_gate_fixture_authorized": request_send_gate.get("fixture_authorized"),
            "send_decision_entrypoint": send_decision_entrypoint.get("result"),
            "send_decision_current_template_ready": send_decision_entrypoint.get(
                "current_template_ready_for_exactly_one_send"
            ),
            "send_decision_authorized_fixture_ready": send_decision_entrypoint.get(
                "authorized_fixture_ready_for_exactly_one_send"
            ),
            "gated_executor_entrypoint": gated_executor_entrypoint.get("result"),
            "gated_executor_current_template_failure_code": gated_executor_entrypoint.get(
                "current_template_failure_code"
            ),
            "gated_executor_fake_transport_external_status": gated_executor_entrypoint.get(
                "fake_transport_external_status"
            ),
            "credential_loader": credential_loader.get("result"),
            "credential_loader_default_code": credential_loader.get("loader_default_code"),
            "real_credential_file_read": credential_loader.get("boundary", {}).get(
                "real_credential_file_read"
            ),
            "production_request_sent": False,
        },
        "go_live": {
            "verdict": go_live.get("verdict", "NO-GO"),
            "blocking_gates": blockers,
        },
        "boundary": {
            "secret_read": "NO",
            "production_signing_executed": "NO",
            "dns_lookup_performed": "NO",
            "socket_opened": "NO",
            "production_http_network_executed": "NO",
            "production_request_sent": "NO",
            "canary_rerun": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    return snapshot, 0 if result == "PASS" else 1


def markdown(snapshot: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- {key}: {value}" for key, value in snapshot["checks"].items()
    )
    blockers = "\n".join(f"- {item}" for item in snapshot["go_live"]["blocking_gates"]) or "- none"
    errors = "\n".join(f"- {item}" for item in snapshot["errors"]) or "- none"
    controlled = snapshot["testnet_baseline"]["controlled_request"]
    canary = snapshot["testnet_baseline"]["canary"]
    production = snapshot["production_state"]
    return f"""# Production Execution Handoff Snapshot

Generated at: `{snapshot["generated_at"]}`

## Result

- result: {snapshot["result"]}
- handoff status: {snapshot["handoff_status"]}
- next gate: {snapshot["next_gate"]}

## Testnet Baseline

- controlled request: `{controlled.get("command_id")}` / {controlled.get("status")} / {controlled.get("external_status")}
- controlled external order id present: {controlled.get("external_order_id_present")}
- controlled executed at: `{controlled.get("executed_at")}`
- canary: `{canary.get("command_id")}` / {canary.get("status")} / {canary.get("external_status")}
- canary external order id present: {canary.get("external_order_id_present")}
- canary executed at: `{canary.get("executed_at")}`

## Production State

- entrypoint present: {str(production.get("entrypoint_present")).lower()}
- command creation candidate: {str(production.get("command_creation_candidate")).lower()}
- non-executable command id: `{production.get("non_executable_command_id")}`
- non-executable command status: `{production.get("non_executable_command_status")}`
- worker executable: {str(production.get("worker_executable")).lower()}
- send authorized: {str(production.get("send_authorized")).lower()}
- send executor skeleton: {production.get("send_executor_skeleton")}
- send executor execute failure code: {production.get("send_executor_execute_failure_code")}
- HTTP transport wiring: {production.get("http_transport_wiring")}
- HTTP transport default failure code: {production.get("http_transport_default_failure_code")}
- HTTP transport fake terminal type: {production.get("http_transport_fake_terminal_type")}
- HTTP transport fake external status: {production.get("http_transport_fake_external_status")}
- request-send gate: {production.get("request_send_gate")}
- request-send current template authorized: {str(production.get("request_send_gate_current_template_authorized")).lower()}
- request-send fixture authorized: {str(production.get("request_send_gate_fixture_authorized")).lower()}
- send decision entrypoint: {production.get("send_decision_entrypoint")}
- send decision current template ready: {str(production.get("send_decision_current_template_ready")).lower()}
- send decision authorized fixture ready: {str(production.get("send_decision_authorized_fixture_ready")).lower()}
- gated executor entrypoint: {production.get("gated_executor_entrypoint")}
- gated executor current template failure code: {production.get("gated_executor_current_template_failure_code")}
- gated executor fake transport external status: {production.get("gated_executor_fake_transport_external_status")}
- credential loader: {production.get("credential_loader")}
- credential loader default code: {production.get("credential_loader_default_code")}
- real credential file read: {production.get("real_credential_file_read")}
- production request sent: {str(production.get("production_request_sent")).lower()}

## Checks

{checks}

## Go-Live Blocking Gates

{blockers}

## Errors

{errors}

## Boundary

- secret read: {snapshot["boundary"]["secret_read"]}
- production signing executed: {snapshot["boundary"]["production_signing_executed"]}
- DNS lookup performed: {snapshot["boundary"]["dns_lookup_performed"]}
- socket opened: {snapshot["boundary"]["socket_opened"]}
- production HTTP/network executed: {snapshot["boundary"]["production_http_network_executed"]}
- production request sent: {snapshot["boundary"]["production_request_sent"]}
- canary rerun: {snapshot["boundary"]["canary_rerun"]}
- go-live: {snapshot["boundary"]["go_live"]}
- live trading: {snapshot["boundary"]["live_trading"]}
"""


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    snapshot, exit_code = build_snapshot()
    JSON_OUT.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(markdown(snapshot), encoding="utf-8")

    print("[Production Execution Handoff Snapshot]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"result: {snapshot['result']}")
    print(f"handoff_status: {snapshot['handoff_status']}")
    print(f"next_gate: {snapshot['next_gate']}")
    print(f"non_executable_command_id: {snapshot['production_state']['non_executable_command_id']}")
    print(f"production_request_sent: {snapshot['boundary']['production_request_sent']}")
    print(f"go_live: {snapshot['boundary']['go_live']}")
    print(f"live_trading: {snapshot['boundary']['live_trading']}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
