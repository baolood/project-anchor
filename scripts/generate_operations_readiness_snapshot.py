#!/usr/bin/env python3
"""Generate a read-only Project Anchor operations readiness snapshot."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "operations_readiness_snapshot.json"
MD_OUT = REPORTS_DIR / "operations_readiness_snapshot.md"
PRODUCTION_EXECUTION_READINESS_REPORT = REPORTS_DIR / "production_execution_readiness.json"
PRODUCTION_EXECUTION_AUTHORIZATION_DRY_GATE_REPORT = (
    REPORTS_DIR / "production_execution_authorization_dry_gate.json"
)
PRODUCTION_NO_SEND_EXECUTION_DRILL_REPORT = REPORTS_DIR / "production_no_send_execution_drill.json"
PRODUCTION_UNSIGNED_CANONICAL_PAYLOAD_DRY_RUN_REPORT = (
    REPORTS_DIR / "production_unsigned_canonical_payload_dry_run.json"
)
PRODUCTION_SIGNING_INTERFACE_DRY_RUN_REPORT = (
    REPORTS_DIR / "production_signing_interface_dry_run.json"
)
PRODUCTION_HTTP_REQUEST_INTERFACE_DRY_RUN_REPORT = (
    REPORTS_DIR / "production_http_request_interface_dry_run.json"
)
PRODUCTION_PRE_SEND_READINESS_AGGREGATION_REPORT = (
    REPORTS_DIR / "production_pre_send_readiness_aggregation.json"
)
PRODUCTION_REQUEST_SEND_WINDOW_PLAN_REPORT = (
    REPORTS_DIR / "production_request_send_window_plan.json"
)
PRODUCTION_SEND_ENTRYPOINT_FAIL_CLOSED_REPORT = (
    REPORTS_DIR / "production_send_entrypoint_fail_closed.json"
)

BACKEND_PRECHECK = os.getenv("BACKEND_PRECHECK", "http://127.0.0.1:8000").rstrip("/")
CONTROLLED_COMMAND_ID = os.getenv(
    "CONTROLLED_COMMAND_ID", "order-a06eed8f-cd60-4a4f-b3e9-84c540b98e6f"
)
CANARY_COMMAND_ID = os.getenv(
    "CANARY_COMMAND_ID", "order-f4fd182a-7a66-4f3c-a69f-f0a212c2c420"
)

GO_LIVE_BLOCKERS = [
    "production credential access not authorized",
    "production signing not approved",
    "production HTTP/network execution not approved",
    "rollback and stop conditions not approved for go-live",
    "monitoring window not approved for go-live",
    "go-live authorization not granted",
    "live trading authorization not granted",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def get_json(path: str, timeout: float = 5.0) -> tuple[bool, Any, str | None]:
    url = f"{BACKEND_PRECHECK}{path}"
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        return False, None, f"HTTP_{exc.code}"
    except URLError as exc:
        return False, None, f"URL_ERROR:{exc.reason}"
    except TimeoutError:
        return False, None, "TIMEOUT"
    except Exception as exc:  # noqa: BLE001 - snapshot should fail closed with evidence.
        return False, None, f"{type(exc).__name__}:{exc}"

    try:
        return True, json.loads(raw), None
    except json.JSONDecodeError as exc:
        return False, None, f"INVALID_JSON:{exc}"


def event_chain(command_id: str) -> tuple[bool, list[str], str | None]:
    ok, data, error = get_json(f"/domain-commands/{command_id}/events")
    if not ok:
        return False, [], error
    if not isinstance(data, list):
        return False, [], "EVENTS_NOT_LIST"
    return True, [str(item.get("event_type", "")) for item in data if item.get("event_type")], None


def command_snapshot(command_id: str) -> tuple[bool, dict[str, Any], str | None]:
    ok, data, error = get_json(f"/domain-commands/{command_id}")
    if not ok:
        return False, {"command_id": command_id, "status": "UNREADABLE"}, error
    if not isinstance(data, dict):
        return False, {"command_id": command_id, "status": "INVALID"}, "COMMAND_NOT_OBJECT"

    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    chain_ok, chain, chain_error = event_chain(command_id)
    external_order_id = result.get("external_order_id")

    result_ts = result.get("ts")
    executed_at = data.get("updated_at") or data.get("created_at")
    if isinstance(result_ts, str) and result_ts:
        executed_at = result_ts

    snapshot = {
        "status": data.get("status"),
        "external_status": result.get("external_status"),
        "command_id": data.get("id", command_id),
        "external_order_id_present": bool(external_order_id),
        "executed_at": executed_at,
        "attempt": data.get("attempt"),
        "execution_mode": result.get("execution_mode") or payload.get("execution_mode"),
        "market": result.get("market") or payload.get("market"),
        "symbol": result.get("symbol") or payload.get("symbol"),
        "side": result.get("side") or payload.get("side"),
        "notional": result.get("notional") or payload.get("notional"),
        "idempotency_key": result.get("idempotency_key") or payload.get("idempotency_key"),
        "event_chain": chain,
        "event_chain_resolved": chain_ok,
    }
    if chain_error:
        snapshot["event_chain_error"] = chain_error

    evidence_ok = (
        snapshot["status"] == "DONE"
        and snapshot["external_status"] == "FILLED"
        and snapshot["external_order_id_present"] is True
        and chain_ok
        and "ACTION_OK" in chain
        and "MARK_DONE" in chain
    )
    return evidence_ok, snapshot, None if evidence_ok else "COMMAND_EVIDENCE_INCOMPLETE"


def pass_fail(value: bool) -> str:
    return "PASS" if value else "FAIL"


def load_production_execution_readiness() -> dict[str, Any]:
    fallback = {
        "result": "UNREADABLE",
        "blockers": ["production execution readiness report unreadable"],
        "gates": {},
        "evidence": {},
        "boundary": {
            "secret_read": "NO",
            "production_request_sent": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    try:
        data = json.loads(PRODUCTION_EXECUTION_READINESS_REPORT.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    if not isinstance(data, dict):
        return fallback
    return {
        "result": data.get("result", "UNKNOWN"),
        "blockers": data.get("blockers") if isinstance(data.get("blockers"), list) else [],
        "gates": data.get("gates") if isinstance(data.get("gates"), dict) else {},
        "evidence": data.get("evidence") if isinstance(data.get("evidence"), dict) else {},
        "boundary": data.get("boundary") if isinstance(data.get("boundary"), dict) else {},
    }


def load_production_execution_authorization_dry_gate() -> dict[str, Any]:
    fallback = {
        "result": "UNREADABLE",
        "authorized_to_execute": False,
        "summary": {
            "readiness_checks_passed": 0,
            "readiness_checks_total": 4,
            "execution_gates_blocking": 0,
            "execution_gates_total": 5,
        },
        "boundary": {
            "secret_read": "NO",
            "production_request_sent": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    try:
        data = json.loads(
            PRODUCTION_EXECUTION_AUTHORIZATION_DRY_GATE_REPORT.read_text(encoding="utf-8")
        )
    except Exception:
        return fallback
    if not isinstance(data, dict):
        return fallback
    return {
        "result": data.get("result", "UNKNOWN"),
        "authorized_to_execute": bool(data.get("authorized_to_execute")),
        "summary": data.get("summary") if isinstance(data.get("summary"), dict) else {},
        "boundary": data.get("boundary") if isinstance(data.get("boundary"), dict) else {},
    }


def load_production_no_send_execution_drill() -> dict[str, Any]:
    fallback = {
        "result": "UNREADABLE",
        "no_send_path_verified": False,
        "authorized_to_execute": False,
        "boundary": {
            "secret_read": "NO",
            "production_request_sent": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    try:
        data = json.loads(PRODUCTION_NO_SEND_EXECUTION_DRILL_REPORT.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    if not isinstance(data, dict):
        return fallback
    return {
        "result": data.get("result", "UNKNOWN"),
        "no_send_path_verified": bool(data.get("no_send_path_verified")),
        "authorized_to_execute": bool(data.get("authorized_to_execute")),
        "dry_gate_summary": (
            data.get("dry_gate_summary") if isinstance(data.get("dry_gate_summary"), dict) else {}
        ),
        "boundary": data.get("boundary") if isinstance(data.get("boundary"), dict) else {},
    }


def load_production_unsigned_canonical_payload_dry_run() -> dict[str, Any]:
    fallback = {
        "result": "UNREADABLE",
        "unsigned_canonical_payload_generated": False,
        "sendable": False,
        "boundary": {
            "secret_read": "NO",
            "production_request_sent": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    try:
        data = json.loads(
            PRODUCTION_UNSIGNED_CANONICAL_PAYLOAD_DRY_RUN_REPORT.read_text(encoding="utf-8")
        )
    except Exception:
        return fallback
    if not isinstance(data, dict):
        return fallback
    return {
        "result": data.get("result", "UNKNOWN"),
        "unsigned_canonical_payload_generated": bool(
            data.get("unsigned_canonical_payload_generated")
        ),
        "sendable": bool(data.get("sendable")),
        "boundary": data.get("boundary") if isinstance(data.get("boundary"), dict) else {},
    }


def load_production_signing_interface_dry_run() -> dict[str, Any]:
    fallback = {
        "result": "UNREADABLE",
        "signing_interface_shape_valid": False,
        "missing_secret_fail_closed": False,
        "real_signing_executed": False,
        "authorization_header_generated": False,
        "signed_payload_sendable": False,
        "boundary": {
            "secret_read": "NO",
            "production_signing_executed": "NO",
            "production_request_sent": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    try:
        data = json.loads(PRODUCTION_SIGNING_INTERFACE_DRY_RUN_REPORT.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    if not isinstance(data, dict):
        return fallback
    return {
        "result": data.get("result", "UNKNOWN"),
        "signing_interface_shape_valid": bool(data.get("signing_interface_shape_valid")),
        "missing_secret_fail_closed": bool(data.get("missing_secret_fail_closed")),
        "real_signing_executed": bool(data.get("real_signing_executed")),
        "authorization_header_generated": bool(data.get("authorization_header_generated")),
        "signed_payload_sendable": bool(data.get("signed_payload_sendable")),
        "boundary": data.get("boundary") if isinstance(data.get("boundary"), dict) else {},
    }


def load_production_http_request_interface_dry_run() -> dict[str, Any]:
    fallback = {
        "result": "UNREADABLE",
        "request_envelope_shape_valid": False,
        "missing_authorization_fail_closed": False,
        "http_network_executed": False,
        "request_sent": False,
        "boundary": {
            "secret_read": "NO",
            "production_http_network_executed": "NO",
            "production_request_sent": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    try:
        data = json.loads(PRODUCTION_HTTP_REQUEST_INTERFACE_DRY_RUN_REPORT.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    if not isinstance(data, dict):
        return fallback
    return {
        "result": data.get("result", "UNKNOWN"),
        "request_envelope_shape_valid": bool(data.get("request_envelope_shape_valid")),
        "missing_authorization_fail_closed": bool(data.get("missing_authorization_fail_closed")),
        "http_network_executed": bool(data.get("http_network_executed")),
        "request_sent": bool(data.get("request_sent")),
        "boundary": data.get("boundary") if isinstance(data.get("boundary"), dict) else {},
    }


def load_production_pre_send_readiness_aggregation() -> dict[str, Any]:
    fallback = {
        "result": "UNREADABLE",
        "evidence_chain_complete": False,
        "request_send_authorized": False,
        "go_live_allowed": False,
        "live_trading_allowed": False,
        "next_gate": "BLOCKED_PRODUCTION_PRE_SEND_EVIDENCE_UNREADABLE",
        "boundary": {
            "secret_read": "NO",
            "production_request_sent": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    try:
        data = json.loads(
            PRODUCTION_PRE_SEND_READINESS_AGGREGATION_REPORT.read_text(encoding="utf-8")
        )
    except Exception:
        return fallback
    if not isinstance(data, dict):
        return fallback
    return {
        "result": data.get("result", "UNKNOWN"),
        "evidence_chain_complete": bool(data.get("evidence_chain_complete")),
        "request_send_authorized": bool(data.get("request_send_authorized")),
        "go_live_allowed": bool(data.get("go_live_allowed")),
        "live_trading_allowed": bool(data.get("live_trading_allowed")),
        "next_gate": data.get("next_gate", "UNKNOWN"),
        "boundary": data.get("boundary") if isinstance(data.get("boundary"), dict) else {},
    }


def load_production_request_send_window_plan() -> dict[str, Any]:
    fallback = {
        "result": "UNREADABLE",
        "plan_valid": False,
        "send_authorized": False,
        "execution_allowed_by_this_plan": False,
        "next_gate": "BLOCKED_PRODUCTION_REQUEST_SEND_WINDOW_PLAN_UNREADABLE",
        "planned_request": {},
        "planned_window": {},
        "boundary": {
            "secret_read": "NO",
            "production_request_sent": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    try:
        data = json.loads(PRODUCTION_REQUEST_SEND_WINDOW_PLAN_REPORT.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    if not isinstance(data, dict):
        return fallback
    return {
        "result": data.get("result", "UNKNOWN"),
        "plan_valid": bool(data.get("plan_valid")),
        "send_authorized": bool(data.get("send_authorized")),
        "execution_allowed_by_this_plan": bool(data.get("execution_allowed_by_this_plan")),
        "next_gate": data.get("next_gate", "UNKNOWN"),
        "planned_request": (
            data.get("planned_request") if isinstance(data.get("planned_request"), dict) else {}
        ),
        "planned_window": (
            data.get("planned_window") if isinstance(data.get("planned_window"), dict) else {}
        ),
        "boundary": data.get("boundary") if isinstance(data.get("boundary"), dict) else {},
    }


def load_production_send_entrypoint_fail_closed() -> dict[str, Any]:
    fallback = {
        "result": "UNREADABLE",
        "entrypoint_present": False,
        "send_authorized": False,
        "execution_gate_authorized": False,
        "command_created": False,
        "production_request_sent": False,
        "surface": "POST /trade-gate/production-order-intents",
        "boundary": {
            "secret_read": "NO",
            "production_request_sent": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    try:
        data = json.loads(PRODUCTION_SEND_ENTRYPOINT_FAIL_CLOSED_REPORT.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    if not isinstance(data, dict):
        return fallback
    return {
        "result": data.get("result", "UNKNOWN"),
        "entrypoint_present": bool(data.get("entrypoint_present")),
        "send_authorized": bool(data.get("send_authorized")),
        "execution_gate_authorized": bool(data.get("execution_gate_authorized")),
        "command_created": bool(data.get("command_created")),
        "production_request_sent": bool(data.get("production_request_sent")),
        "surface": data.get("surface", "POST /trade-gate/production-order-intents"),
        "boundary": data.get("boundary") if isinstance(data.get("boundary"), dict) else {},
    }


def build_snapshot() -> tuple[dict[str, Any], int]:
    generated_at = utc_now()

    health_ok, health_data, health_error = get_json("/health")
    backend_ok = bool(health_ok and isinstance(health_data, dict) and health_data.get("ok") is True)

    state_ok, state_data, state_error = get_json("/ops/state")
    worker_ok, worker_data, worker_error = get_json("/ops/worker")

    kill_switch = {}
    worker_heartbeat = {}
    if isinstance(state_data, dict):
        kill_switch = state_data.get("kill_switch") if isinstance(state_data.get("kill_switch"), dict) else {}
        worker_heartbeat = (
            state_data.get("worker_heartbeat")
            if isinstance(state_data.get("worker_heartbeat"), dict)
            else {}
        )

    worker_health = bool(
        worker_ok
        and isinstance(worker_data, dict)
        and worker_data.get("last_heartbeat_at")
        and worker_heartbeat.get("last_seen_at")
    )
    kill_switch_enabled = bool(kill_switch.get("enabled")) if kill_switch else None
    kill_switch_safe = kill_switch_enabled is False

    controlled_ok, controlled, controlled_error = command_snapshot(CONTROLLED_COMMAND_ID)
    canary_ok, canary, canary_error = command_snapshot(CANARY_COMMAND_ID)
    production_execution_readiness = load_production_execution_readiness()
    production_execution_authorization_dry_gate = (
        load_production_execution_authorization_dry_gate()
    )
    production_no_send_execution_drill = load_production_no_send_execution_drill()
    production_unsigned_canonical_payload_dry_run = (
        load_production_unsigned_canonical_payload_dry_run()
    )
    production_signing_interface_dry_run = load_production_signing_interface_dry_run()
    production_http_request_interface_dry_run = load_production_http_request_interface_dry_run()
    production_pre_send_readiness_aggregation = (
        load_production_pre_send_readiness_aggregation()
    )
    production_request_send_window_plan = load_production_request_send_window_plan()
    production_send_entrypoint_fail_closed = load_production_send_entrypoint_fail_closed()
    production_execution_ready = production_execution_readiness.get("result") == "PASS"

    hard_failures = [
        not backend_ok,
        not worker_health,
        not kill_switch_safe,
        not controlled_ok,
        not canary_ok,
    ]
    if any(hard_failures):
        overall_status = "FAIL"
    elif GO_LIVE_BLOCKERS:
        overall_status = "WARN"
    else:
        overall_status = "PASS"

    snapshot = {
        "generated_at": generated_at,
        "overall_status": overall_status,
        "health": {
            "backend": pass_fail(backend_ok),
            "backend_error": None if backend_ok else health_error or "HEALTH_NOT_OK",
            "worker": pass_fail(worker_health),
            "worker_error": None if worker_health else worker_error or state_error or "WORKER_NOT_HEALTHY",
            "worker_heartbeat_at": (
                worker_data.get("last_heartbeat_at")
                if isinstance(worker_data, dict)
                else worker_heartbeat.get("last_seen_at")
            ),
        },
        "safety": {
            "kill_switch_enabled": kill_switch_enabled,
            "kill_switch_source": kill_switch.get("source") if kill_switch else None,
            "runtime_mode": "testnet",
            "live_trading_allowed": False,
            "secret_read": False,
            "new_external_request_sent": False,
            "canary_rerun": False,
            "runtime_modified": False,
        },
        "latest_controlled_request": controlled,
        "latest_canary": canary,
        "production_execution_readiness": production_execution_readiness,
        "production_execution_authorization_dry_gate": (
            production_execution_authorization_dry_gate
        ),
        "production_no_send_execution_drill": production_no_send_execution_drill,
        "production_unsigned_canonical_payload_dry_run": (
            production_unsigned_canonical_payload_dry_run
        ),
        "production_signing_interface_dry_run": production_signing_interface_dry_run,
        "production_http_request_interface_dry_run": production_http_request_interface_dry_run,
        "production_pre_send_readiness_aggregation": (
            production_pre_send_readiness_aggregation
        ),
        "production_request_send_window_plan": production_request_send_window_plan,
        "production_send_entrypoint_fail_closed": production_send_entrypoint_fail_closed,
        "go_live": {
            "verdict": "NO-GO",
            "blocking_gates": GO_LIVE_BLOCKERS,
        },
        "evidence_resolution": {
            "source_endpoints_readable": pass_fail(health_ok and state_ok and worker_ok),
            "controlled_request_evidence_resolved": pass_fail(controlled_ok),
            "controlled_request_error": controlled_error,
            "canary_evidence_resolved": pass_fail(canary_ok),
            "canary_error": canary_error,
            "production_execution_readiness_resolved": pass_fail(
                production_execution_readiness.get("result") in {"PASS", "BLOCKED"}
            ),
            "production_execution_ready": pass_fail(production_execution_ready),
            "production_execution_authorization_dry_gate_resolved": pass_fail(
                production_execution_authorization_dry_gate.get("result") == "PASS"
            ),
            "production_execution_authorized_to_execute": pass_fail(
                production_execution_authorization_dry_gate.get("authorized_to_execute") is True
            ),
            "production_no_send_execution_drill_resolved": pass_fail(
                production_no_send_execution_drill.get("result") == "PASS"
            ),
            "production_no_send_path_verified": pass_fail(
                production_no_send_execution_drill.get("no_send_path_verified") is True
            ),
            "production_unsigned_canonical_payload_dry_run_resolved": pass_fail(
                production_unsigned_canonical_payload_dry_run.get("result") == "PASS"
            ),
            "production_unsigned_canonical_payload_generated": pass_fail(
                production_unsigned_canonical_payload_dry_run.get(
                    "unsigned_canonical_payload_generated"
                )
                is True
            ),
            "production_unsigned_canonical_payload_sendable": pass_fail(
                production_unsigned_canonical_payload_dry_run.get("sendable") is True
            ),
            "production_signing_interface_dry_run_resolved": pass_fail(
                production_signing_interface_dry_run.get("result") == "PASS"
            ),
            "production_signing_interface_shape_valid": pass_fail(
                production_signing_interface_dry_run.get("signing_interface_shape_valid") is True
            ),
            "production_signing_missing_secret_fail_closed": pass_fail(
                production_signing_interface_dry_run.get("missing_secret_fail_closed") is True
            ),
            "production_real_signing_executed": pass_fail(
                production_signing_interface_dry_run.get("real_signing_executed") is True
            ),
            "production_http_request_interface_dry_run_resolved": pass_fail(
                production_http_request_interface_dry_run.get("result") == "PASS"
            ),
            "production_http_request_envelope_shape_valid": pass_fail(
                production_http_request_interface_dry_run.get("request_envelope_shape_valid") is True
            ),
            "production_http_missing_authorization_fail_closed": pass_fail(
                production_http_request_interface_dry_run.get("missing_authorization_fail_closed") is True
            ),
            "production_http_network_executed": pass_fail(
                production_http_request_interface_dry_run.get("http_network_executed") is True
            ),
            "production_request_sent": pass_fail(
                production_http_request_interface_dry_run.get("request_sent") is True
            ),
            "production_pre_send_readiness_aggregation_resolved": pass_fail(
                production_pre_send_readiness_aggregation.get("result") == "PASS"
            ),
            "production_pre_send_evidence_chain_complete": pass_fail(
                production_pre_send_readiness_aggregation.get("evidence_chain_complete") is True
            ),
            "production_request_send_authorized": pass_fail(
                production_pre_send_readiness_aggregation.get("request_send_authorized") is True
            ),
            "production_request_send_window_plan_resolved": pass_fail(
                production_request_send_window_plan.get("result") == "PASS"
            ),
            "production_request_send_window_plan_valid": pass_fail(
                production_request_send_window_plan.get("plan_valid") is True
            ),
            "production_request_send_window_authorized": pass_fail(
                production_request_send_window_plan.get("send_authorized") is True
            ),
            "production_send_entrypoint_fail_closed_resolved": pass_fail(
                production_send_entrypoint_fail_closed.get("result") == "PASS"
            ),
            "production_send_entrypoint_present": pass_fail(
                production_send_entrypoint_fail_closed.get("entrypoint_present") is True
            ),
            "production_send_entrypoint_authorized": pass_fail(
                production_send_entrypoint_fail_closed.get("send_authorized") is True
            ),
            "production_execution_gate_authorized": pass_fail(
                production_send_entrypoint_fail_closed.get("execution_gate_authorized") is True
            ),
            "go_live_blockers_explicit": pass_fail(bool(GO_LIVE_BLOCKERS)),
        },
        "boundary": {
            "secret_read": "NO",
            "new_external_request_sent": "NO",
            "canary_rerun": "NO",
            "runtime_modified": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    return snapshot, 0 if overall_status in {"PASS", "WARN"} else 1


def markdown(snapshot: dict[str, Any]) -> str:
    controlled = snapshot["latest_controlled_request"]
    canary = snapshot["latest_canary"]
    production_readiness = snapshot["production_execution_readiness"]
    production_dry_gate = snapshot["production_execution_authorization_dry_gate"]
    no_send_drill = snapshot["production_no_send_execution_drill"]
    unsigned_payload = snapshot["production_unsigned_canonical_payload_dry_run"]
    signing_interface = snapshot["production_signing_interface_dry_run"]
    http_request_interface = snapshot["production_http_request_interface_dry_run"]
    pre_send = snapshot["production_pre_send_readiness_aggregation"]
    send_window = snapshot["production_request_send_window_plan"]
    send_entrypoint = snapshot["production_send_entrypoint_fail_closed"]
    blockers = "\n".join(f"- {item}" for item in snapshot["go_live"]["blocking_gates"])
    production_blockers = "\n".join(
        f"- {item}" for item in production_readiness.get("blockers", [])
    ) or "- none"
    production_gates = "\n".join(
        f"- {key}: {value}" for key, value in production_readiness.get("gates", {}).items()
    ) or "- none"
    controlled_chain = " -> ".join(controlled.get("event_chain") or [])
    canary_chain = " -> ".join(canary.get("event_chain") or [])

    return f"""# Project Anchor Operations Readiness Snapshot

Generated at: `{snapshot["generated_at"]}`

## Overall

- overall status: {snapshot["overall_status"]}
- go-live verdict: {snapshot["go_live"]["verdict"]}
- live trading allowed: {snapshot["safety"]["live_trading_allowed"]}

## Health

- backend: {snapshot["health"]["backend"]}
- worker: {snapshot["health"]["worker"]}
- worker heartbeat at: `{snapshot["health"]["worker_heartbeat_at"]}`
- kill switch enabled: {snapshot["safety"]["kill_switch_enabled"]}
- kill switch source: `{snapshot["safety"]["kill_switch_source"]}`

## Latest Controlled Request

- command id: `{controlled.get("command_id")}`
- status: {controlled.get("status")}
- external status: {controlled.get("external_status")}
- external order id present: {controlled.get("external_order_id_present")}
- executed at: `{controlled.get("executed_at")}`
- event chain: {controlled_chain}

## Latest Canary

- command id: `{canary.get("command_id")}`
- status: {canary.get("status")}
- external status: {canary.get("external_status")}
- external order id present: {canary.get("external_order_id_present")}
- executed at: `{canary.get("executed_at")}`
- event chain: {canary_chain}

## Production Execution Readiness

- result: {production_readiness.get("result")}

## Production Execution Authorization Dry Gate

- result: {production_dry_gate.get("result")}
- authorized to execute: {str(production_dry_gate.get("authorized_to_execute")).lower()}
- readiness checks: {production_dry_gate.get("summary", {}).get("readiness_checks_passed")}/{production_dry_gate.get("summary", {}).get("readiness_checks_total")}
- execution gates blocking: {production_dry_gate.get("summary", {}).get("execution_gates_blocking")}/{production_dry_gate.get("summary", {}).get("execution_gates_total")}

## Production No-Send Execution Drill

- result: {no_send_drill.get("result")}
- no-send path verified: {str(no_send_drill.get("no_send_path_verified")).lower()}
- authorized to execute: {str(no_send_drill.get("authorized_to_execute")).lower()}

## Production Unsigned Canonical Payload Dry Run

- result: {unsigned_payload.get("result")}
- unsigned canonical payload generated: {str(unsigned_payload.get("unsigned_canonical_payload_generated")).lower()}
- sendable: {str(unsigned_payload.get("sendable")).lower()}

## Production Signing Interface Dry Run

- result: {signing_interface.get("result")}
- signing interface shape valid: {str(signing_interface.get("signing_interface_shape_valid")).lower()}
- missing secret fail-closed: {str(signing_interface.get("missing_secret_fail_closed")).lower()}
- real signing executed: {str(signing_interface.get("real_signing_executed")).lower()}
- Authorization header generated: {str(signing_interface.get("authorization_header_generated")).lower()}
- signed payload sendable: {str(signing_interface.get("signed_payload_sendable")).lower()}

## Production HTTP Request Interface Dry Run

- result: {http_request_interface.get("result")}
- request envelope shape valid: {str(http_request_interface.get("request_envelope_shape_valid")).lower()}
- missing Authorization fail-closed: {str(http_request_interface.get("missing_authorization_fail_closed")).lower()}
- HTTP/network executed: {str(http_request_interface.get("http_network_executed")).lower()}
- request sent: {str(http_request_interface.get("request_sent")).lower()}

## Production Pre-Send Readiness Aggregation

- result: {pre_send.get("result")}
- evidence chain complete: {str(pre_send.get("evidence_chain_complete")).lower()}
- request send authorized: {str(pre_send.get("request_send_authorized")).lower()}
- go-live allowed: {str(pre_send.get("go_live_allowed")).lower()}
- live trading allowed: {str(pre_send.get("live_trading_allowed")).lower()}
- next gate: {pre_send.get("next_gate")}

## Production Request Send Window Plan

- result: {send_window.get("result")}
- plan valid: {str(send_window.get("plan_valid")).lower()}
- send authorized: {str(send_window.get("send_authorized")).lower()}
- execution allowed by this plan: {str(send_window.get("execution_allowed_by_this_plan")).lower()}
- planned idempotency key template: `{send_window.get("planned_request", {}).get("idempotency_key_template")}`
- window expires at: `{send_window.get("planned_window", {}).get("expires_at")}`
- next gate: {send_window.get("next_gate")}

## Production Send Entrypoint Fail-Closed

- result: {send_entrypoint.get("result")}
- surface: `{send_entrypoint.get("surface")}`
- entrypoint present: {str(send_entrypoint.get("entrypoint_present")).lower()}
- send authorized: {str(send_entrypoint.get("send_authorized")).lower()}
- execution gate authorized: {str(send_entrypoint.get("execution_gate_authorized")).lower()}
- command created: {str(send_entrypoint.get("command_created")).lower()}
- production request sent: {str(send_entrypoint.get("production_request_sent")).lower()}

### Production Gates

{production_gates}

### Production Blockers

{production_blockers}

## Go-Live Blocking Gates

{blockers}

## Boundary

- secret read: {snapshot["boundary"]["secret_read"]}
- new external request sent: {snapshot["boundary"]["new_external_request_sent"]}
- canary rerun: {snapshot["boundary"]["canary_rerun"]}
- runtime modified: {snapshot["boundary"]["runtime_modified"]}
- go-live: {snapshot["boundary"]["go_live"]}
- live trading: {snapshot["boundary"]["live_trading"]}
"""


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    snapshot, exit_code = build_snapshot()
    JSON_OUT.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(markdown(snapshot), encoding="utf-8")

    print("[Project Anchor Operations Readiness Snapshot]")
    print(f"snapshot JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"snapshot Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {snapshot['generated_at']}")
    print(f"overall_status: {snapshot['overall_status']}")
    print(f"backend health: {snapshot['health']['backend']}")
    print(f"worker: {snapshot['health']['worker']}")
    print(f"kill_switch_enabled: {snapshot['safety']['kill_switch_enabled']}")
    print(
        "latest_controlled_request: "
        f"{snapshot['latest_controlled_request'].get('status')} / "
        f"{snapshot['latest_controlled_request'].get('external_status')}"
    )
    print(
        "latest_canary: "
        f"{snapshot['latest_canary'].get('status')} / "
        f"{snapshot['latest_canary'].get('external_status')}"
    )
    print(f"go_live_verdict: {snapshot['go_live']['verdict']}")
    print(f"blocking_gates: {len(snapshot['go_live']['blocking_gates'])}")
    print(f"production_execution_readiness: {snapshot['production_execution_readiness'].get('result')}")
    print(f"production_execution_blockers: {len(snapshot['production_execution_readiness'].get('blockers', []))}")
    print(
        "production_execution_authorization_dry_gate: "
        f"{snapshot['production_execution_authorization_dry_gate'].get('result')}"
    )
    print(
        "production_execution_authorized_to_execute: "
        f"{str(snapshot['production_execution_authorization_dry_gate'].get('authorized_to_execute')).lower()}"
    )
    print(
        "production_no_send_execution_drill: "
        f"{snapshot['production_no_send_execution_drill'].get('result')}"
    )
    print(
        "production_no_send_path_verified: "
        f"{str(snapshot['production_no_send_execution_drill'].get('no_send_path_verified')).lower()}"
    )
    print(
        "production_unsigned_canonical_payload_dry_run: "
        f"{snapshot['production_unsigned_canonical_payload_dry_run'].get('result')}"
    )
    print(
        "production_unsigned_canonical_payload_generated: "
        f"{str(snapshot['production_unsigned_canonical_payload_dry_run'].get('unsigned_canonical_payload_generated')).lower()}"
    )
    print(
        "production_signing_interface_dry_run: "
        f"{snapshot['production_signing_interface_dry_run'].get('result')}"
    )
    print(
        "production_signing_missing_secret_fail_closed: "
        f"{str(snapshot['production_signing_interface_dry_run'].get('missing_secret_fail_closed')).lower()}"
    )
    print(
        "production_http_request_interface_dry_run: "
        f"{snapshot['production_http_request_interface_dry_run'].get('result')}"
    )
    print(
        "production_http_missing_authorization_fail_closed: "
        f"{str(snapshot['production_http_request_interface_dry_run'].get('missing_authorization_fail_closed')).lower()}"
    )
    print(
        "production_pre_send_readiness_aggregation: "
        f"{snapshot['production_pre_send_readiness_aggregation'].get('result')}"
    )
    print(
        "production_pre_send_evidence_chain_complete: "
        f"{str(snapshot['production_pre_send_readiness_aggregation'].get('evidence_chain_complete')).lower()}"
    )
    print(
        "production_request_send_authorized: "
        f"{str(snapshot['production_pre_send_readiness_aggregation'].get('request_send_authorized')).lower()}"
    )
    print(
        "production_pre_send_next_gate: "
        f"{snapshot['production_pre_send_readiness_aggregation'].get('next_gate')}"
    )
    print(
        "production_request_send_window_plan: "
        f"{snapshot['production_request_send_window_plan'].get('result')}"
    )
    print(
        "production_request_send_window_plan_valid: "
        f"{str(snapshot['production_request_send_window_plan'].get('plan_valid')).lower()}"
    )
    print(
        "production_request_send_window_authorized: "
        f"{str(snapshot['production_request_send_window_plan'].get('send_authorized')).lower()}"
    )
    print(
        "production_request_send_window_next_gate: "
        f"{snapshot['production_request_send_window_plan'].get('next_gate')}"
    )
    print(
        "production_send_entrypoint_fail_closed: "
        f"{snapshot['production_send_entrypoint_fail_closed'].get('result')}"
    )
    print(
        "production_send_entrypoint_present: "
        f"{str(snapshot['production_send_entrypoint_fail_closed'].get('entrypoint_present')).lower()}"
    )
    print(
        "production_send_entrypoint_authorized: "
        f"{str(snapshot['production_send_entrypoint_fail_closed'].get('send_authorized')).lower()}"
    )
    print(
        "production_execution_gate_authorized: "
        f"{str(snapshot['production_send_entrypoint_fail_closed'].get('execution_gate_authorized')).lower()}"
    )
    print("secret_read: NO")
    print("new_external_request_sent: NO")
    print("canary_rerun: NO")
    print("runtime_modified: NO")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
