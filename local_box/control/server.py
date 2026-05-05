from __future__ import annotations

import os
import time
from typing import Optional

from flask import Flask, jsonify, request

from shared.schemas import StrategyIntent
from local_box.audit.event_store import (
    count_dead_dispatches,
    count_events,
    count_executed,
    count_pending_dispatches,
    list_dead_dispatches,
    list_events,
    list_pending_dispatches,
    replay_dead_dispatch,
)
from local_box.gate.execution_gate import get_kill_switch, set_kill_switch
from local_box.metrics.summary import build_metrics_summary
from local_box.runner import recover_pending_dispatches, run_intent
from local_box.scheduler.retry_scheduler import get_scheduler_status
from local_box.self_check.checks import (
    SELF_CHECK_SCHEDULER_STALE_SEC,
    run_self_check,
    should_block_execution,
)


app = Flask(__name__)

SCHEDULER_STALE_SEC = SELF_CHECK_SCHEDULER_STALE_SEC
RECENT_RECOVERY_LIMIT = 10


def _scheduler_view() -> dict:
    scheduler = get_scheduler_status()
    last_cycle_time = scheduler.get("last_cycle_time")
    scheduler_age_sec = None
    scheduler_running = False

    if last_cycle_time is not None:
        scheduler_age_sec = max(0.0, time.time() - float(last_cycle_time))
        scheduler_running = scheduler_age_sec <= SCHEDULER_STALE_SEC

    return {
        **scheduler,
        "scheduler_age_sec": scheduler_age_sec,
        "scheduler_running": scheduler_running,
        "scheduler_stale_sec": SCHEDULER_STALE_SEC,
    }


def _execution_service_view() -> dict:
    configured_backend = ""
    for env_name in (
        "EXECUTION_BACKEND",
        "EXECUTION_SERVICE_BACKEND",
        "EXECUTOR_BACKEND",
        "EXECUTION_PROVIDER",
        "EXECUTION_TARGET",
    ):
        value = str(os.getenv(env_name, "")).strip()
        if value:
            configured_backend = value
            break

    inspection_values = [
        configured_backend,
        str(os.getenv("EXECUTION_SERVICE_URL", "")).strip(),
        str(os.getenv("EXECUTION_SERVICE_HOST", "")).strip(),
        str(os.getenv("EXECUTION_SHARED_KEYS", "")).strip(),
        str(os.getenv("EXECUTION_SHARED_KEY_ID", "")).strip(),
        str(os.getenv("EXECUTION_SHARED_KEY", "")).strip(),
    ]
    inspection_text = " ".join(value.lower() for value in inspection_values if value)

    mock_markers = ("mock", "demo", "test", "stub", "local mock", "local-mock", "local_mock")
    if any(marker in inspection_text for marker in mock_markers):
        boundary_mode = "mock"
    elif configured_backend or any(inspection_values[1:]):
        boundary_mode = "real"
    else:
        boundary_mode = "none"

    return {
        "configured_backend": configured_backend,
        "boundary_mode": boundary_mode,
    }


def _snapshot_view() -> dict:
    return {
        "local_command": "npm run --silent local-box:snapshot > /tmp/local_box_snapshot.json",
        "local_output_path": "/tmp/local_box_snapshot.json",
        "artifact_name": "local_box_snapshot",
    }


def _advice_view() -> dict:
    metrics = build_metrics_summary()
    self_check_result = run_self_check()
    execution_blocked_by_self_check = should_block_execution(self_check_result)
    self_check_blocks = metrics.get("self_check_blocks") or {}
    top_blocking_failure = self_check_blocks.get("top_blocking_failure")

    return {
        "execution_blocked_by_self_check": execution_blocked_by_self_check,
        "execution_advice": "BLOCK_NEW_EXECUTION" if execution_blocked_by_self_check else "ALLOW_NEW_EXECUTION",
        "operator_action": _operator_action(
            execution_blocked_by_self_check,
            top_blocking_failure,
        ),
        "top_blocking_failure": top_blocking_failure,
    }


def _self_check_summary_view() -> dict:
    self_check_result = run_self_check()
    checks = self_check_result.get("checks") or []
    failure_count = sum(1 for item in checks if item.get("status") == "FAIL")
    blocking_failure_count = sum(
        1
        for item in checks
        if item.get("blocking") is True and item.get("status") == "FAIL"
    )

    return {
        "overall_status": self_check_result.get("overall_status"),
        "blocking_failure_count": blocking_failure_count,
        "failure_count": failure_count,
    }


def _entrypoints_view() -> dict:
    return {
        "health": "/health",
        "status": "/status",
        "ops_summary": "/ops-summary",
        "self_check": "/self-check",
        "metrics_summary": "/metrics-summary",
        "events": "/events",
        "pending_dispatches": "/pending-dispatches",
        "dead_dispatches": "/dead-dispatches",
        "recover": "/recover",
        "retry_pending": "/retry-pending",
        "replay_dead": "/replay-dead",
        "replay_dead_now": "/replay-dead-now",
        "run_intent": "/run-intent",
        "kill_switch": "/kill-switch",
    }


def _counts_view() -> dict:
    return {
        "events": count_events(),
        "executed_commands": count_executed(),
        "pending_dispatches": count_pending_dispatches(),
        "dead_dispatches": count_dead_dispatches(),
    }


def _pending_preview_view() -> list[dict]:
    return list_pending_dispatches()[:5]


def _dead_preview_view() -> list[dict]:
    return list_dead_dispatches()[:5]


def _preview_limits_view() -> dict:
    return {
        "pending_preview_limit": 5,
        "dead_preview_limit": 5,
        "recent_recoveries_limit": RECENT_RECOVERY_LIMIT,
    }


def _recent_recoveries(limit: int = RECENT_RECOVERY_LIMIT) -> list[dict]:
    recovered = []
    for event in reversed(list_events()):
        payload = event.payload or {}
        if event.stage != event.stage.EXECUTOR:
            continue
        if not payload.get("recovered"):
            continue
        recovered.append(
            {
                "event_id": event.event_id,
                "command_id": event.command_id,
                "status": event.status.value,
                "timestamp": event.timestamp,
                "payload": payload,
            }
        )
        if len(recovered) >= limit:
            break
    return recovered


def _ops_attention_view() -> dict:
    scheduler = _scheduler_view()
    pending_count = count_pending_dispatches()
    dead_count = count_dead_dispatches()
    kill_switch = get_kill_switch()

    flags = {
        "kill_switch_active": kill_switch,
        "scheduler_stale": not scheduler.get("scheduler_running", False),
        "has_dead_dispatches": dead_count > 0,
        "has_pending_dispatches": pending_count > 0,
    }
    attention_required = any(flags.values())

    if kill_switch:
        overall_state = "STOPPED"
    elif dead_count > 0:
        overall_state = "DEGRADED"
    elif not scheduler.get("scheduler_running", False):
        overall_state = "DEGRADED"
    elif pending_count > 0:
        overall_state = "BUSY"
    else:
        overall_state = "HEALTHY"

    return {
        "attention_required": attention_required,
        "overall_state": overall_state,
        "flags": flags,
    }


def _operator_action(
    execution_blocked_by_self_check: bool,
    top_blocking_failure: Optional[str],
) -> str:
    if not execution_blocked_by_self_check:
        return "NO_ACTION_REQUIRED"
    if top_blocking_failure == "execution_service_reachable":
        return "CHECK_EXECUTION_SERVICE"
    if top_blocking_failure == "scheduler_heartbeat":
        return "CHECK_SCHEDULER"
    return "CHECK_SELF_CHECK_BLOCKERS"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "local_box_control"})


@app.route("/status", methods=["GET"])
def status():
    return jsonify(
        {
            "ok": True,
            "generated_at": time.time(),
            "kill_switch": get_kill_switch(),
            "events": count_events(),
            "executed_commands": count_executed(),
            "pending_dispatches": count_pending_dispatches(),
            "dead_dispatches": count_dead_dispatches(),
            "scheduler": _scheduler_view(),
            "execution_service": _execution_service_view(),
            "snapshot": _snapshot_view(),
            "advice": _advice_view(),
            "attention": _ops_attention_view(),
            "recent_recoveries": _recent_recoveries(),
            "self_check_summary": _self_check_summary_view(),
            "entrypoints": _entrypoints_view(),
            "counts": _counts_view(),
            "pending_preview": _pending_preview_view(),
            "dead_preview": _dead_preview_view(),
            "preview_limits": _preview_limits_view(),
        }
    )


@app.route("/kill-switch", methods=["GET", "POST"])
def kill_switch():
    if request.method == "GET":
        return jsonify({"kill_switch": get_kill_switch()})

    body = request.json or {}
    value = bool(body.get("value", False))
    set_kill_switch(value)
    return jsonify({"kill_switch": get_kill_switch()})


@app.route("/events", methods=["GET"])
def events():
    command_id = request.args.get("command_id")
    rows = list_events(command_id=command_id)
    return jsonify(
        [
            {
                "event_id": e.event_id,
                "command_id": e.command_id,
                "stage": e.stage.value,
                "status": e.status.value,
                "timestamp": e.timestamp,
                "payload": e.payload,
            }
            for e in rows
        ]
    )


@app.route("/pending-dispatches", methods=["GET"])
def pending_dispatches():
    return jsonify(list_pending_dispatches())


@app.route("/dead-dispatches", methods=["GET"])
def dead_dispatches():
    return jsonify(list_dead_dispatches())


@app.route("/recover", methods=["POST"])
def recover():
    return jsonify({"recovered": recover_pending_dispatches()})


@app.route("/retry-pending", methods=["POST"])
def retry_pending():
    return jsonify({"recovered": recover_pending_dispatches()})


@app.route("/ops-summary", methods=["GET"])
def ops_summary():
    metrics = build_metrics_summary()
    self_check_result = run_self_check()
    execution_blocked_by_self_check = should_block_execution(self_check_result)
    self_check_blocks = metrics.get("self_check_blocks") or {}
    self_check_history = {
        "block_count": self_check_blocks.get("self_check_block_count", 0),
        "last_block_at": self_check_blocks.get("last_self_check_block_at"),
        "top_blocking_failure": self_check_blocks.get("top_blocking_failure"),
    }
    return jsonify(
        {
            "ok": True,
            "generated_at": time.time(),
            "kill_switch": get_kill_switch(),
            "scheduler": _scheduler_view(),
            "self_check": self_check_result,
            "self_check_history": self_check_history,
            "execution_blocked_by_self_check": execution_blocked_by_self_check,
            "execution_advice": "BLOCK_NEW_EXECUTION" if execution_blocked_by_self_check else "ALLOW_NEW_EXECUTION",
            "operator_action": _operator_action(
                execution_blocked_by_self_check,
                self_check_history["top_blocking_failure"],
            ),
            "advice": _advice_view(),
            "self_check_summary": _self_check_summary_view(),
            "execution_service": _execution_service_view(),
            "snapshot": _snapshot_view(),
            "attention": _ops_attention_view(),
            "entrypoints": _entrypoints_view(),
            "counts": _counts_view(),
            "pending_preview": _pending_preview_view(),
            "dead_preview": _dead_preview_view(),
            "preview_limits": _preview_limits_view(),
            "pending": list_pending_dispatches(),
            "dead": list_dead_dispatches(),
            "recent_recoveries": _recent_recoveries(),
        }
    )


@app.route("/self-check", methods=["GET"])
def self_check():
    return jsonify(
        {
            "ok": True,
            "generated_at": time.time(),
            "self_check": run_self_check(),
        }
    )


@app.route("/metrics-summary", methods=["GET"])
def metrics_summary():
    return jsonify(
        {
            "ok": True,
            "generated_at": time.time(),
            "metrics": build_metrics_summary(),
        }
    )


@app.route("/replay-dead", methods=["POST"])
def replay_dead():
    body = request.json or {}
    ticket_id = str(body.get("ticket_id") or "").strip()
    if not ticket_id:
        return jsonify({"error": "ticket_id required"}), 400

    row = replay_dead_dispatch(ticket_id)
    if row is None:
        return jsonify({"error": "dead dispatch not found"}), 404

    return jsonify({"replayed": row})


@app.route("/replay-dead-now", methods=["POST"])
def replay_dead_now():
    body = request.json or {}
    ticket_id = str(body.get("ticket_id") or "").strip()
    if not ticket_id:
        return jsonify({"error": "ticket_id required"}), 400

    row = replay_dead_dispatch(ticket_id)
    if row is None:
        return jsonify({"error": "dead dispatch not found"}), 404

    recovered = recover_pending_dispatches()
    matched = next((item for item in recovered if item.get("ticket_id") == ticket_id), None)

    return jsonify(
        {
            "replayed": row,
            "recovered": matched,
            "recovered_all": recovered,
        }
    )


@app.route("/run-intent", methods=["POST"])
def run_intent_route():
    body = request.json or {}
    try:
        intent = StrategyIntent(**body)
    except Exception as e:
        return jsonify({"error": f"invalid intent: {str(e)}"}), 400
    return jsonify(run_intent(intent))


if __name__ == "__main__":
    app.run(port=9002)
