#!/usr/bin/env python3
"""Generate a read-only Project Anchor operations readiness snapshot."""

from __future__ import annotations

import json
import os
import socket
import ssl
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
PRODUCTION_NON_EXECUTABLE_COMMAND_CREATION_DRILL_REPORT = (
    REPORTS_DIR / "production_non_executable_command_creation_drill.json"
)
POST_PRODUCTION_MONITORING_RUN_REPORT = REPORTS_DIR / "post_production_monitoring_run.json"
POST_PRODUCTION_ALERTING_READINESS_REPORT = REPORTS_DIR / "post_production_alerting_readiness.json"
POST_PRODUCTION_TELEGRAM_SEND_RESULT_REPORT = (
    REPORTS_DIR / "post_production_monitoring_telegram_send_result.json"
)
POST_PRODUCTION_MONITORING_TIMER_RUNTIME_REPORT = (
    REPORTS_DIR / "post_production_monitoring_timer_runtime_validation.json"
)
POST_PRODUCTION_MONITORING_TIMER_STABILITY_REPORT = (
    REPORTS_DIR / "post_production_monitoring_timer_stability_validation.json"
)
CLOUD_OPERATIONS_EVIDENCE_LAYOUT_AUDIT_REPORT = (
    REPORTS_DIR / "cloud_operations_evidence_layout_audit.json"
)

BACKEND_PRECHECK = os.getenv("BACKEND_PRECHECK", "http://127.0.0.1:8000").rstrip("/")
OPS_DOMAIN = os.getenv("OPS_DOMAIN", "ops.anchor-infra.com")
OPS_EXPECTED_A = os.getenv("OPS_EXPECTED_A", "45.76.190.109")
OPS_HEALTHZ_URL = os.getenv("OPS_HEALTHZ_URL", f"https://{OPS_DOMAIN}/healthz")
OPS_PROTECTED_URL = os.getenv("OPS_PROTECTED_URL", f"https://{OPS_DOMAIN}/ops")
OPS_DASHBOARD_URL = os.getenv("OPS_DASHBOARD_URL", f"https://{OPS_DOMAIN}/ops")
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


def http_status(url: str, timeout: float = 5.0) -> tuple[int | None, str | None]:
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            response.read(64)
            return int(response.status), None
    except HTTPError as exc:
        return int(exc.code), None
    except URLError as exc:
        return None, f"URL_ERROR:{exc.reason}"
    except TimeoutError:
        return None, "TIMEOUT"
    except Exception as exc:  # noqa: BLE001 - snapshot should fail closed with evidence.
        return None, f"{type(exc).__name__}:{exc}"


def http_probe(url: str, timeout: float = 5.0) -> tuple[int | None, dict[str, str], str | None]:
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            response.read(64)
            return int(response.status), dict(response.headers.items()), None
    except HTTPError as exc:
        return int(exc.code), dict(exc.headers.items()), None
    except URLError as exc:
        return None, {}, f"URL_ERROR:{exc.reason}"
    except TimeoutError:
        return None, {}, "TIMEOUT"
    except Exception as exc:  # noqa: BLE001 - snapshot should fail closed with evidence.
        return None, {}, f"{type(exc).__name__}:{exc}"


def tls_not_after(hostname: str, port: int = 443, timeout: float = 5.0) -> tuple[str | None, str | None]:
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=timeout) as raw_socket:
            with context.wrap_socket(raw_socket, server_hostname=hostname) as tls_socket:
                cert = tls_socket.getpeercert()
    except Exception as exc:  # noqa: BLE001 - snapshot should fail closed with evidence.
        return None, f"{type(exc).__name__}:{exc}"
    not_after = cert.get("notAfter") if isinstance(cert, dict) else None
    return str(not_after) if not_after else None, None if not_after else "CERT_NOT_AFTER_MISSING"


def ops_domain_ingress_snapshot() -> dict[str, Any]:
    try:
        resolved = sorted({item[4][0] for item in socket.getaddrinfo(OPS_DOMAIN, 443, type=socket.SOCK_STREAM)})
        dns_error = None
    except Exception as exc:  # noqa: BLE001 - snapshot should fail closed with evidence.
        resolved = []
        dns_error = f"{type(exc).__name__}:{exc}"

    health_status, health_error = http_status(OPS_HEALTHZ_URL)
    protected_status, protected_headers, protected_error = http_probe(OPS_PROTECTED_URL)
    cert_not_after, cert_error = tls_not_after(OPS_DOMAIN)

    dns_pass = OPS_EXPECTED_A in resolved
    health_pass = health_status == 200
    protected_pass = protected_status in {401, 403}
    authenticate_header = protected_headers.get("WWW-Authenticate", "")
    basic_auth_challenge_pass = (
        protected_status == 401 and "basic" in authenticate_header.lower()
    )
    tls_pass = cert_not_after is not None and cert_error is None
    result = (
        "PASS"
        if dns_pass and health_pass and protected_pass and basic_auth_challenge_pass and tls_pass
        else "WARN"
    )

    return {
        "result": result,
        "domain": OPS_DOMAIN,
        "expected_a": OPS_EXPECTED_A,
        "resolved_a_records": resolved,
        "dns_error": dns_error,
        "dns_result": pass_fail(dns_pass),
        "https_healthz_url": OPS_HEALTHZ_URL,
        "https_healthz_status": health_status,
        "https_healthz_error": health_error,
        "https_healthz_result": pass_fail(health_pass),
        "protected_url": OPS_PROTECTED_URL,
        "protected_status": protected_status,
        "protected_error": protected_error,
        "protected_result": pass_fail(protected_pass),
        "protected_expected_statuses": [401, 403],
        "ops_basic_auth_challenge_result": pass_fail(basic_auth_challenge_pass),
        "ops_basic_auth_realm_present": pass_fail(
            "project anchor ops" in authenticate_header.lower()
        ),
        "ops_basic_auth_status": protected_status,
        "tls_certificate_not_after": cert_not_after,
        "tls_error": cert_error,
        "tls_result": pass_fail(tls_pass),
        "boundary": {
            "credential_file_read": "NO",
            "secret_value_disclosed": "NO",
            "authenticated_ops_access_attempted": "NO",
            "production_request_sent": "NO",
            "second_production_request_sent": "NO",
            "canary_rerun": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }


def ops_dashboard_snapshot(ops_domain_ingress: dict[str, Any]) -> dict[str, Any]:
    auth_challenge_pass = ops_domain_ingress.get("ops_basic_auth_challenge_result") == "PASS"
    realm_present = ops_domain_ingress.get("ops_basic_auth_realm_present") == "PASS"
    protected_pass = ops_domain_ingress.get("protected_result") == "PASS"
    result = "PASS" if auth_challenge_pass and realm_present and protected_pass else "WARN"
    return {
        "result": result,
        "url": OPS_DASHBOARD_URL,
        "published_entrypoint": "/ops",
        "read_only_dashboard_expected": True,
        "entrypoint_requires_basic_auth": pass_fail(auth_challenge_pass),
        "basic_auth_realm_present": pass_fail(realm_present),
        "unauthenticated_access_blocked": pass_fail(protected_pass),
        "authenticated_content_probe": "NOT_ATTEMPTED_BY_SNAPSHOT",
        "authenticated_content_probe_reason": "snapshot does not read Basic Auth credentials",
        "execution_controls_expected": "NO",
        "production_send_control_expected": "NO",
        "canary_rerun_control_expected": "NO",
        "go_live_control_expected": "NO",
        "live_trading_control_expected": "NO",
        "boundary": {
            "basic_auth_secret_read": "NO",
            "credential_file_read": "NO",
            "secret_value_disclosed": "NO",
            "production_request_sent": "NO",
            "second_production_request_sent": "NO",
            "canary_rerun": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }


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
        "command_creation_candidate": False,
        "command_type": None,
        "non_executable_persistence_status": None,
        "worker_executable": False,
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
        "command_creation_candidate": bool(data.get("command_creation_candidate")),
        "command_type": data.get("command_type"),
        "non_executable_persistence_status": data.get("non_executable_persistence_status"),
        "worker_executable": bool(data.get("worker_executable")),
        "command_created": bool(data.get("command_created")),
        "production_request_sent": bool(data.get("production_request_sent")),
        "surface": data.get("surface", "POST /trade-gate/production-order-intents"),
        "boundary": data.get("boundary") if isinstance(data.get("boundary"), dict) else {},
    }


def load_production_non_executable_command_creation_drill() -> dict[str, Any]:
    fallback = {
        "result": "UNREADABLE",
        "command_id": None,
        "command_type": None,
        "command_status": None,
        "worker_executable": True,
        "production_request_sent": "UNKNOWN",
        "boundary": {
            "secret_read": "NO",
            "production_request_sent": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    try:
        data = json.loads(
            PRODUCTION_NON_EXECUTABLE_COMMAND_CREATION_DRILL_REPORT.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return fallback
    if not isinstance(data, dict):
        return fallback
    return {
        "result": data.get("result", "UNKNOWN"),
        "command_id": data.get("command_id"),
        "command_type": data.get("command_type"),
        "command_status": data.get("command_status"),
        "worker_executable": bool(data.get("worker_executable")),
        "pre_worker_executable_count": data.get("pre_worker_executable_count"),
        "post_worker_executable_count": data.get("post_worker_executable_count"),
        "boundary": data.get("boundary") if isinstance(data.get("boundary"), dict) else {},
    }


def load_post_production_monitoring_run() -> dict[str, Any]:
    fallback = {
        "result": "UNREADABLE",
        "status": "POST_PRODUCTION_MONITORING_RUN_UNREADABLE",
        "snapshot_result": "UNREADABLE",
        "snapshot_status": "UNREADABLE",
        "generated_at": None,
        "checks": [],
        "boundary": {
            "credential_file_read": "NO",
            "secret_value_disclosed": "NO",
            "production_signing_executed": "NO",
            "production_http_network_attempted": "NO",
            "new_production_request_sent": "NO",
            "second_production_request_sent": "NO",
            "canary_rerun": "NO",
            "runtime_modified": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    try:
        data = json.loads(POST_PRODUCTION_MONITORING_RUN_REPORT.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    if not isinstance(data, dict):
        return fallback
    return {
        "result": data.get("result", "UNKNOWN"),
        "status": data.get("status", "UNKNOWN"),
        "snapshot_result": data.get("snapshot_result", "UNKNOWN"),
        "snapshot_status": data.get("snapshot_status", "UNKNOWN"),
        "generated_at": data.get("generated_at"),
        "checks": data.get("checks") if isinstance(data.get("checks"), list) else [],
        "boundary": data.get("boundary") if isinstance(data.get("boundary"), dict) else {},
    }


def load_post_production_alerting_readiness() -> dict[str, Any]:
    fallback = {
        "result": "UNREADABLE",
        "status": "POST_PRODUCTION_ALERTING_READINESS_UNREADABLE",
        "failure_code": "REPORT_UNREADABLE",
        "checks": {},
        "boundary": {
            "alerting_env_content_read": "NO",
            "telegram_bot_token_value_disclosed": "NO",
            "telegram_chat_id_value_disclosed": "NO",
            "telegram_http_attempted": "NO",
            "telegram_message_sent": "NO",
            "production_request_sent": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    try:
        data = json.loads(POST_PRODUCTION_ALERTING_READINESS_REPORT.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    if not isinstance(data, dict):
        return fallback
    return {
        "result": data.get("result", "UNKNOWN"),
        "status": data.get("status", "UNKNOWN"),
        "failure_code": data.get("failure_code", ""),
        "inspect_env_requested": bool(data.get("inspect_env_requested")),
        "checks": data.get("checks") if isinstance(data.get("checks"), dict) else {},
        "boundary": data.get("boundary") if isinstance(data.get("boundary"), dict) else {},
    }


def load_post_production_telegram_send_result() -> dict[str, Any]:
    fallback = {
        "result": "UNREADABLE",
        "status": "POST_PRODUCTION_MONITORING_TELEGRAM_SEND_UNREADABLE",
        "failure_code": "REPORT_UNREADABLE",
        "execute_requested": False,
        "source_payload_result": "UNKNOWN",
        "send_attempted": "NO",
        "send_result": "NOT_ATTEMPTED",
        "boundary": {
            "alerting_env_read": "NO",
            "secret_value_disclosed": "NO",
            "telegram_http_attempted": "NO",
            "production_request_sent": "NO",
            "second_production_request_sent": "NO",
            "canary_rerun": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    try:
        data = json.loads(POST_PRODUCTION_TELEGRAM_SEND_RESULT_REPORT.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    if not isinstance(data, dict):
        return fallback
    return {
        "result": data.get("result", "UNKNOWN"),
        "status": data.get("status", "UNKNOWN"),
        "failure_code": data.get("failure_code", ""),
        "execute_requested": bool(data.get("execute_requested")),
        "source_payload_result": data.get("source_payload_result"),
        "send_attempted": data.get("send_attempted", "NO"),
        "send_result": data.get("send_result", "NOT_ATTEMPTED"),
        "boundary": data.get("boundary") if isinstance(data.get("boundary"), dict) else {},
    }


def load_post_production_monitoring_timer_runtime() -> dict[str, Any]:
    fallback = {
        "result": "UNREADABLE",
        "status": "POST_PRODUCTION_MONITORING_TIMER_RUNTIME_UNREADABLE",
        "timer": {},
        "service": {},
        "monitoring_report": {},
        "telegram_sender_report": {},
        "checks": {},
        "boundary": {
            "alerting_env_read": "NO",
            "secret_value_disclosed": "NO",
            "production_signing_executed": "NO",
            "production_http_network_attempted": "NO",
            "new_production_request_sent": "NO",
            "second_production_request_sent": "NO",
            "canary_rerun": "NO",
            "runtime_modified": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    try:
        data = json.loads(POST_PRODUCTION_MONITORING_TIMER_RUNTIME_REPORT.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    if not isinstance(data, dict):
        return fallback
    return {
        "result": data.get("result", "UNKNOWN"),
        "status": data.get("status", "UNKNOWN"),
        "timer": data.get("timer") if isinstance(data.get("timer"), dict) else {},
        "service": data.get("service") if isinstance(data.get("service"), dict) else {},
        "monitoring_report": (
            data.get("monitoring_report") if isinstance(data.get("monitoring_report"), dict) else {}
        ),
        "telegram_sender_report": (
            data.get("telegram_sender_report")
            if isinstance(data.get("telegram_sender_report"), dict)
            else {}
        ),
        "checks": data.get("checks") if isinstance(data.get("checks"), dict) else {},
        "boundary": data.get("boundary") if isinstance(data.get("boundary"), dict) else {},
    }


def load_post_production_monitoring_timer_stability() -> dict[str, Any]:
    fallback = {
        "result": "UNREADABLE",
        "status": "POST_PRODUCTION_MONITORING_TIMER_STABILITY_UNREADABLE",
        "observed_run_count": 0,
        "latest_consecutive_success_count": 0,
        "min_successful_runs": 3,
        "latest_run": {},
        "checks": {},
        "boundary": {
            "alerting_env_read": "NO",
            "secret_value_disclosed": "NO",
            "production_signing_executed": "NO",
            "production_http_network_attempted": "NO",
            "new_production_request_sent": "NO",
            "second_production_request_sent": "NO",
            "canary_rerun": "NO",
            "runtime_modified": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    try:
        data = json.loads(POST_PRODUCTION_MONITORING_TIMER_STABILITY_REPORT.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    if not isinstance(data, dict):
        return fallback
    return {
        "result": data.get("result", "UNKNOWN"),
        "status": data.get("status", "UNKNOWN"),
        "observed_run_count": data.get("observed_run_count", 0),
        "latest_consecutive_success_count": data.get(
            "latest_consecutive_success_count", 0
        ),
        "min_successful_runs": data.get("min_successful_runs", 3),
        "latest_run": data.get("latest_run") if isinstance(data.get("latest_run"), dict) else {},
        "checks": data.get("checks") if isinstance(data.get("checks"), dict) else {},
        "boundary": data.get("boundary") if isinstance(data.get("boundary"), dict) else {},
    }


def load_cloud_operations_evidence_layout_audit() -> dict[str, Any]:
    fallback = {
        "result": "UNREADABLE",
        "status": "CLOUD_OPERATIONS_EVIDENCE_LAYOUT_AUDIT_UNREADABLE",
        "runtime_reports_dir": None,
        "source_reports_dir": None,
        "layout": {},
        "summary": {},
        "checks": {},
        "boundary": {
            "production_env_read": "NO",
            "secret_value_disclosed": "NO",
            "production_signing_executed": "NO",
            "production_http_network_attempted": "NO",
            "new_production_request_sent": "NO",
            "second_production_request_sent": "NO",
            "canary_rerun": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    try:
        data = json.loads(CLOUD_OPERATIONS_EVIDENCE_LAYOUT_AUDIT_REPORT.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    if not isinstance(data, dict):
        return fallback
    return {
        "result": data.get("result", "UNKNOWN"),
        "status": data.get("status", "UNKNOWN"),
        "runtime_reports_dir": data.get("runtime_reports_dir"),
        "source_reports_dir": data.get("source_reports_dir"),
        "layout": data.get("layout") if isinstance(data.get("layout"), dict) else {},
        "runtime_files": data.get("runtime_files") if isinstance(data.get("runtime_files"), dict) else {},
        "source_files": data.get("source_files") if isinstance(data.get("source_files"), dict) else {},
        "summary": data.get("summary") if isinstance(data.get("summary"), dict) else {},
        "checks": data.get("checks") if isinstance(data.get("checks"), dict) else {},
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
    production_non_executable_command_creation_drill = (
        load_production_non_executable_command_creation_drill()
    )
    post_production_monitoring_run = load_post_production_monitoring_run()
    post_production_alerting_readiness = load_post_production_alerting_readiness()
    post_production_telegram_send_result = load_post_production_telegram_send_result()
    post_production_monitoring_timer_runtime = (
        load_post_production_monitoring_timer_runtime()
    )
    post_production_monitoring_timer_stability = (
        load_post_production_monitoring_timer_stability()
    )
    cloud_operations_evidence_layout_audit = (
        load_cloud_operations_evidence_layout_audit()
    )
    ops_domain_ingress = ops_domain_ingress_snapshot()
    ops_dashboard = ops_dashboard_snapshot(ops_domain_ingress)
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
        "production_non_executable_command_creation_drill": (
            production_non_executable_command_creation_drill
        ),
        "post_production_monitoring_run": post_production_monitoring_run,
        "post_production_alerting_readiness": post_production_alerting_readiness,
        "post_production_telegram_send_result": post_production_telegram_send_result,
        "post_production_monitoring_timer_runtime": (
            post_production_monitoring_timer_runtime
        ),
        "post_production_monitoring_timer_stability": (
            post_production_monitoring_timer_stability
        ),
        "cloud_operations_evidence_layout_audit": cloud_operations_evidence_layout_audit,
        "ops_domain_ingress": ops_domain_ingress,
        "ops_dashboard": ops_dashboard,
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
            "production_command_creation_candidate_available": pass_fail(
                production_send_entrypoint_fail_closed.get("command_creation_candidate") is True
            ),
            "production_non_executable_command_creation_drill_resolved": pass_fail(
                production_non_executable_command_creation_drill.get("result") == "PASS"
            ),
            "post_production_monitoring_run_resolved": pass_fail(
                post_production_monitoring_run.get("result") == "PASS"
            ),
            "post_production_alerting_readiness_resolved": pass_fail(
                post_production_alerting_readiness.get("result") == "PASS"
            ),
            "post_production_alerting_secret_disclosure": pass_fail(
                post_production_alerting_readiness.get("boundary", {}).get(
                    "telegram_bot_token_value_disclosed"
                )
                != "YES"
                and post_production_alerting_readiness.get("boundary", {}).get(
                    "telegram_chat_id_value_disclosed"
                )
                != "YES"
            ),
            "post_production_telegram_sender_result_resolved": pass_fail(
                post_production_telegram_send_result.get("result") in {"PASS", "BLOCKED"}
            ),
            "post_production_telegram_sender_fail_closed_or_delivered": pass_fail(
                (
                    post_production_telegram_send_result.get("result") == "PASS"
                    and post_production_telegram_send_result.get("send_result") == "DELIVERED"
                )
                or (
                    post_production_telegram_send_result.get("result") == "BLOCKED"
                    and post_production_telegram_send_result.get("send_attempted") == "NO"
                )
            ),
            "post_production_telegram_secret_disclosed": pass_fail(
                post_production_telegram_send_result.get("boundary", {}).get(
                    "secret_value_disclosed"
                )
                != "YES"
            ),
            "post_production_monitoring_timer_runtime_resolved": pass_fail(
                post_production_monitoring_timer_runtime.get("result") == "PASS"
            ),
            "post_production_monitoring_timer_enabled": pass_fail(
                post_production_monitoring_timer_runtime.get("timer", {}).get(
                    "unit_file_state"
                )
                == "enabled"
            ),
            "post_production_monitoring_timer_active": pass_fail(
                post_production_monitoring_timer_runtime.get("timer", {}).get(
                    "active_state"
                )
                == "active"
            ),
            "post_production_monitoring_timer_secret_disclosed": pass_fail(
                post_production_monitoring_timer_runtime.get("boundary", {}).get(
                    "secret_value_disclosed"
                )
                != "YES"
            ),
            "post_production_monitoring_timer_stability_resolved": pass_fail(
                post_production_monitoring_timer_stability.get("result") == "PASS"
            ),
            "post_production_monitoring_timer_minimum_successes_observed": pass_fail(
                int(
                    post_production_monitoring_timer_stability.get(
                        "latest_consecutive_success_count", 0
                    )
                    or 0
                )
                >= int(
                    post_production_monitoring_timer_stability.get(
                        "min_successful_runs", 3
                    )
                    or 3
                )
            ),
            "post_production_monitoring_timer_stability_secret_disclosed": pass_fail(
                post_production_monitoring_timer_stability.get("boundary", {}).get(
                    "secret_value_disclosed"
                )
                != "YES"
            ),
            "cloud_operations_evidence_layout_audit_resolved": pass_fail(
                cloud_operations_evidence_layout_audit.get("result") == "PASS"
            ),
            "cloud_operations_evidence_layout_source_evidence_present": (
                cloud_operations_evidence_layout_audit.get("checks", {}).get(
                    "source_production_evidence_present", "FAIL"
                )
            ),
            "cloud_operations_evidence_layout_runtime_reports_present": (
                cloud_operations_evidence_layout_audit.get("checks", {}).get(
                    "runtime_monitoring_reports_present", "FAIL"
                )
            ),
            "cloud_operations_evidence_layout_no_new_request": pass_fail(
                cloud_operations_evidence_layout_audit.get("boundary", {}).get(
                    "new_production_request_sent"
                )
                == "NO"
            ),
            "cloud_operations_evidence_layout_secret_disclosed": pass_fail(
                cloud_operations_evidence_layout_audit.get("boundary", {}).get(
                    "secret_value_disclosed"
                )
                != "YES"
            ),
            "ops_domain_ingress_resolved": pass_fail(
                ops_domain_ingress.get("result") == "PASS"
            ),
            "ops_domain_dns_result": ops_domain_ingress.get("dns_result", "FAIL"),
            "ops_domain_https_healthz_result": ops_domain_ingress.get(
                "https_healthz_result", "FAIL"
            ),
            "ops_domain_protected_result": ops_domain_ingress.get(
                "protected_result", "FAIL"
            ),
            "ops_domain_tls_result": ops_domain_ingress.get("tls_result", "FAIL"),
            "ops_basic_auth_challenge_result": ops_domain_ingress.get(
                "ops_basic_auth_challenge_result", "FAIL"
            ),
            "ops_basic_auth_realm_present": ops_domain_ingress.get(
                "ops_basic_auth_realm_present", "FAIL"
            ),
            "ops_dashboard_resolved": pass_fail(ops_dashboard.get("result") == "PASS"),
            "ops_dashboard_entrypoint_requires_basic_auth": ops_dashboard.get(
                "entrypoint_requires_basic_auth", "FAIL"
            ),
            "ops_dashboard_unauthenticated_access_blocked": ops_dashboard.get(
                "unauthenticated_access_blocked", "FAIL"
            ),
            "ops_dashboard_secret_read": pass_fail(
                ops_dashboard.get("boundary", {}).get("basic_auth_secret_read") != "YES"
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
    non_executable_creation = snapshot["production_non_executable_command_creation_drill"]
    post_monitoring = snapshot["post_production_monitoring_run"]
    post_alerting = snapshot["post_production_alerting_readiness"]
    post_telegram = snapshot["post_production_telegram_send_result"]
    post_timer = snapshot["post_production_monitoring_timer_runtime"]
    post_timer_stability = snapshot["post_production_monitoring_timer_stability"]
    cloud_layout = snapshot["cloud_operations_evidence_layout_audit"]
    ops_domain = snapshot["ops_domain_ingress"]
    ops_dashboard = snapshot["ops_dashboard"]
    blockers = "\n".join(f"- {item}" for item in snapshot["go_live"]["blocking_gates"])
    production_blockers = "\n".join(
        f"- {item}" for item in production_readiness.get("blockers", [])
    ) or "- none"
    production_gates = "\n".join(
        f"- {key}: {value}" for key, value in production_readiness.get("gates", {}).items()
    ) or "- none"
    controlled_chain = " -> ".join(controlled.get("event_chain") or [])
    canary_chain = " -> ".join(canary.get("event_chain") or [])
    post_alerting_failure_code = post_alerting.get("failure_code") or "none"
    post_telegram_failure_code = post_telegram.get("failure_code") or "none"

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
- command creation candidate: {str(send_entrypoint.get("command_creation_candidate")).lower()}
- command type: `{send_entrypoint.get("command_type")}`
- non-executable persistence status: `{send_entrypoint.get("non_executable_persistence_status")}`
- worker executable: {str(send_entrypoint.get("worker_executable")).lower()}
- command created: {str(send_entrypoint.get("command_created")).lower()}
- production request sent: {str(send_entrypoint.get("production_request_sent")).lower()}

## Production Non-Executable Command Creation Drill

- result: {non_executable_creation.get("result")}
- command id: `{non_executable_creation.get("command_id")}`
- command type: `{non_executable_creation.get("command_type")}`
- command status: `{non_executable_creation.get("command_status")}`
- worker executable: {str(non_executable_creation.get("worker_executable")).lower()}
- pre worker executable count: {non_executable_creation.get("pre_worker_executable_count")}
- post worker executable count: {non_executable_creation.get("post_worker_executable_count")}

## Post-Production Monitoring

- result: {post_monitoring.get("result")}
- status: {post_monitoring.get("status")}
- snapshot result: {post_monitoring.get("snapshot_result")}
- snapshot status: {post_monitoring.get("snapshot_status")}
- generated at: `{post_monitoring.get("generated_at")}`

## Post-Production Alerting Readiness

- result: {post_alerting.get("result")}
- status: {post_alerting.get("status")}
- failure code: {post_alerting_failure_code}
- alerting env content read: {post_alerting.get("boundary", {}).get("alerting_env_content_read")}
- Telegram HTTP attempted: {post_alerting.get("boundary", {}).get("telegram_http_attempted")}
- Telegram message sent: {post_alerting.get("boundary", {}).get("telegram_message_sent")}

## Post-Production Telegram Sender

- result: {post_telegram.get("result")}
- status: {post_telegram.get("status")}
- source payload result: {post_telegram.get("source_payload_result")}
- execute requested: {str(post_telegram.get("execute_requested")).lower()}
- send attempted: {post_telegram.get("send_attempted")}
- send result: {post_telegram.get("send_result")}
- failure code: {post_telegram_failure_code}
- alerting env read: {post_telegram.get("boundary", {}).get("alerting_env_read")}
- Telegram HTTP attempted: {post_telegram.get("boundary", {}).get("telegram_http_attempted")}

## Post-Production Monitoring Timer

- result: {post_timer.get("result")}
- status: {post_timer.get("status")}
- timer active state: {post_timer.get("timer", {}).get("active_state")}
- timer unit state: {post_timer.get("timer", {}).get("unit_file_state")}
- last trigger: `{post_timer.get("timer", {}).get("last_trigger")}`
- service result: {post_timer.get("service", {}).get("result")}
- latest monitoring result: {post_timer.get("monitoring_report", {}).get("result")}
- latest Telegram sender result: {post_timer.get("telegram_sender_report", {}).get("result")}
- secret disclosed: {post_timer.get("boundary", {}).get("secret_value_disclosed")}
- new production request sent: {post_timer.get("boundary", {}).get("new_production_request_sent")}

## Post-Production Monitoring Timer Stability

- result: {post_timer_stability.get("result")}
- status: {post_timer_stability.get("status")}
- observed runs: {post_timer_stability.get("observed_run_count")}
- latest consecutive successes: {post_timer_stability.get("latest_consecutive_success_count")}
- required consecutive successes: {post_timer_stability.get("min_successful_runs")}
- latest run status: {post_timer_stability.get("latest_run", {}).get("run_status")}
- latest run started at: `{post_timer_stability.get("latest_run", {}).get("started_at")}`
- latest run finished at: `{post_timer_stability.get("latest_run", {}).get("finished_at")}`
- new production request sent: {post_timer_stability.get("boundary", {}).get("new_production_request_sent")}
- go-live: {post_timer_stability.get("boundary", {}).get("go_live")}
- live trading: {post_timer_stability.get("boundary", {}).get("live_trading")}

## Cloud Operations Evidence Layout Audit

- result: {cloud_layout.get("result")}
- status: {cloud_layout.get("status")}
- runtime reports dir: `{cloud_layout.get("runtime_reports_dir")}`
- source reports dir: `{cloud_layout.get("source_reports_dir")}`
- single directory layout required: {cloud_layout.get("layout", {}).get("single_directory_layout_required")}
- runtime monitoring reports present: {cloud_layout.get("checks", {}).get("runtime_monitoring_reports_present")}
- source production evidence present: {cloud_layout.get("checks", {}).get("source_production_evidence_present")}
- production send result: {cloud_layout.get("summary", {}).get("production_send_result")}
- production order status: {cloud_layout.get("summary", {}).get("production_order_status")}
- matching filled order count: {cloud_layout.get("summary", {}).get("matching_filled_order_count")}
- new production request sent: {cloud_layout.get("boundary", {}).get("new_production_request_sent")}
- second production request sent: {cloud_layout.get("boundary", {}).get("second_production_request_sent")}
- secret disclosed: {cloud_layout.get("boundary", {}).get("secret_value_disclosed")}
- go-live: {cloud_layout.get("boundary", {}).get("go_live")}
- live trading: {cloud_layout.get("boundary", {}).get("live_trading")}

## Ops Domain Ingress

- result: {ops_domain.get("result")}
- domain: `{ops_domain.get("domain")}`
- expected A: `{ops_domain.get("expected_a")}`
- resolved A records: {", ".join(ops_domain.get("resolved_a_records") or []) or "none"}
- DNS result: {ops_domain.get("dns_result")}
- HTTPS healthz status: {ops_domain.get("https_healthz_status")}
- HTTPS healthz result: {ops_domain.get("https_healthz_result")}
- protected URL status: {ops_domain.get("protected_status")}
- protected result: {ops_domain.get("protected_result")}
- Basic Auth challenge result: {ops_domain.get("ops_basic_auth_challenge_result")}
- Basic Auth realm present: {ops_domain.get("ops_basic_auth_realm_present")}
- authenticated ops access attempted: {ops_domain.get("boundary", {}).get("authenticated_ops_access_attempted")}
- TLS certificate not after: `{ops_domain.get("tls_certificate_not_after")}`
- TLS result: {ops_domain.get("tls_result")}

## Ops Dashboard

- result: {ops_dashboard.get("result")}
- URL: `{ops_dashboard.get("url")}`
- published entrypoint: `{ops_dashboard.get("published_entrypoint")}`
- read-only dashboard expected: {ops_dashboard.get("read_only_dashboard_expected")}
- entrypoint requires Basic Auth: {ops_dashboard.get("entrypoint_requires_basic_auth")}
- unauthenticated access blocked: {ops_dashboard.get("unauthenticated_access_blocked")}
- authenticated content probe: {ops_dashboard.get("authenticated_content_probe")}
- authenticated content probe reason: {ops_dashboard.get("authenticated_content_probe_reason")}
- production send control expected: {ops_dashboard.get("production_send_control_expected")}
- canary rerun control expected: {ops_dashboard.get("canary_rerun_control_expected")}
- go-live control expected: {ops_dashboard.get("go_live_control_expected")}
- live trading control expected: {ops_dashboard.get("live_trading_control_expected")}

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
    print(
        "production_command_creation_candidate: "
        f"{str(snapshot['production_send_entrypoint_fail_closed'].get('command_creation_candidate')).lower()}"
    )
    print(
        "production_non_executable_command_creation_drill: "
        f"{snapshot['production_non_executable_command_creation_drill'].get('result')}"
    )
    print(
        "production_non_executable_command_status: "
        f"{snapshot['production_non_executable_command_creation_drill'].get('command_status')}"
    )
    print(
        "production_non_executable_worker_executable: "
        f"{str(snapshot['production_non_executable_command_creation_drill'].get('worker_executable')).lower()}"
    )
    print(
        "post_production_monitoring_run: "
        f"{snapshot['post_production_monitoring_run'].get('result')}"
    )
    print(
        "post_production_monitoring_status: "
        f"{snapshot['post_production_monitoring_run'].get('status')}"
    )
    print(
        "post_production_alerting_readiness: "
        f"{snapshot['post_production_alerting_readiness'].get('result')}"
    )
    print(
        "post_production_alerting_status: "
        f"{snapshot['post_production_alerting_readiness'].get('status')}"
    )
    print(
        "post_production_telegram_sender_result: "
        f"{snapshot['post_production_telegram_send_result'].get('result')}"
    )
    print(
        "post_production_telegram_sender_status: "
        f"{snapshot['post_production_telegram_send_result'].get('status')}"
    )
    print(
        "post_production_telegram_send_attempted: "
        f"{snapshot['post_production_telegram_send_result'].get('send_attempted')}"
    )
    print(
        "post_production_telegram_http_attempted: "
        f"{snapshot['post_production_telegram_send_result'].get('boundary', {}).get('telegram_http_attempted')}"
    )
    print(
        "post_production_monitoring_timer_runtime: "
        f"{snapshot['post_production_monitoring_timer_runtime'].get('result')}"
    )
    print(
        "post_production_monitoring_timer_active: "
        f"{snapshot['post_production_monitoring_timer_runtime'].get('timer', {}).get('active_state')}"
    )
    print(
        "post_production_monitoring_timer_enabled: "
        f"{snapshot['post_production_monitoring_timer_runtime'].get('timer', {}).get('unit_file_state')}"
    )
    print(
        "post_production_monitoring_timer_stability: "
        f"{snapshot['post_production_monitoring_timer_stability'].get('result')}"
    )
    print(
        "post_production_monitoring_timer_observed_runs: "
        f"{snapshot['post_production_monitoring_timer_stability'].get('observed_run_count')}"
    )
    print(
        "post_production_monitoring_timer_consecutive_successes: "
        f"{snapshot['post_production_monitoring_timer_stability'].get('latest_consecutive_success_count')}"
    )
    print(
        "cloud_operations_evidence_layout_audit: "
        f"{snapshot['cloud_operations_evidence_layout_audit'].get('result')}"
    )
    print(
        "cloud_operations_evidence_layout_status: "
        f"{snapshot['cloud_operations_evidence_layout_audit'].get('status')}"
    )
    print(
        "cloud_operations_source_evidence_present: "
        f"{snapshot['cloud_operations_evidence_layout_audit'].get('checks', {}).get('source_production_evidence_present')}"
    )
    print(f"ops_domain_ingress: {snapshot['ops_domain_ingress'].get('result')}")
    print(f"ops_domain_dns: {snapshot['ops_domain_ingress'].get('dns_result')}")
    print(
        "ops_domain_https_healthz: "
        f"{snapshot['ops_domain_ingress'].get('https_healthz_result')}"
    )
    print(
        "ops_domain_protected: "
        f"{snapshot['ops_domain_ingress'].get('protected_result')}"
    )
    print(f"ops_domain_tls: {snapshot['ops_domain_ingress'].get('tls_result')}")
    print(
        "ops_basic_auth_challenge: "
        f"{snapshot['ops_domain_ingress'].get('ops_basic_auth_challenge_result')}"
    )
    print(f"ops_dashboard: {snapshot['ops_dashboard'].get('result')}")
    print(
        "ops_dashboard_auth_required: "
        f"{snapshot['ops_dashboard'].get('entrypoint_requires_basic_auth')}"
    )
    print(
        "ops_dashboard_authenticated_content_probe: "
        f"{snapshot['ops_dashboard'].get('authenticated_content_probe')}"
    )
    print("secret_read: NO")
    print("new_external_request_sent: NO")
    print("canary_rerun: NO")
    print("runtime_modified: NO")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
