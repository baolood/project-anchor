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
    print("secret_read: NO")
    print("new_external_request_sent: NO")
    print("canary_rerun: NO")
    print("runtime_modified: NO")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
