import os
import socket
import time

from local_box.audit.event_store import count_dead_dispatches, count_pending_dispatches
from local_box.gate.execution_gate import get_kill_switch
from local_box.scheduler.retry_scheduler import get_scheduler_status


EXECUTION_SERVICE_HOST = os.getenv("EXECUTION_SERVICE_HOST", "127.0.0.1")
EXECUTION_SERVICE_PORT = int(os.getenv("EXECUTION_SERVICE_PORT", "9001"))
SELF_CHECK_SCHEDULER_STALE_SEC = float(os.getenv("SELF_CHECK_SCHEDULER_STALE_SEC", "5"))
SOCKET_TIMEOUT_SEC = float(os.getenv("SELF_CHECK_SOCKET_TIMEOUT_SEC", "1"))


def _port_reachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=SOCKET_TIMEOUT_SEC):
            return True
    except OSError:
        return False


def _check_scheduler() -> dict:
    scheduler = get_scheduler_status()
    last_cycle_time = scheduler.get("last_cycle_time")
    age_sec = None if last_cycle_time is None else max(0.0, time.time() - float(last_cycle_time))
    healthy = age_sec is not None and age_sec <= SELF_CHECK_SCHEDULER_STALE_SEC

    return {
        "name": "scheduler_heartbeat",
        "status": "PASS" if healthy else "FAIL",
        "blocking": True,
        "detail": {
            "last_cycle_time": last_cycle_time,
            "age_sec": age_sec,
            "stale_sec": SELF_CHECK_SCHEDULER_STALE_SEC,
        },
    }


def _check_execution_service() -> dict:
    healthy = _port_reachable(EXECUTION_SERVICE_HOST, EXECUTION_SERVICE_PORT)
    return {
        "name": "execution_service_reachable",
        "status": "PASS" if healthy else "FAIL",
        "blocking": True,
        "detail": {
            "host": EXECUTION_SERVICE_HOST,
            "port": EXECUTION_SERVICE_PORT,
        },
    }


def _check_dispatch_queues() -> dict:
    pending = count_pending_dispatches()
    dead = count_dead_dispatches()
    if dead > 0:
        status = "FAIL"
    elif pending > 0:
        status = "WARN"
    else:
        status = "PASS"
    return {
        "name": "dispatch_queues",
        "status": status,
        "blocking": False,
        "detail": {
            "pending_dispatches": pending,
            "dead_dispatches": dead,
        },
    }


def _check_kill_switch() -> dict:
    kill_switch = get_kill_switch()
    return {
        "name": "kill_switch",
        "status": "WARN" if kill_switch else "PASS",
        "blocking": False,
        "detail": {
            "kill_switch": kill_switch,
        },
    }


def should_block_execution(self_check: dict) -> bool:
    checks = self_check.get("checks") or []
    for item in checks:
        if item.get("blocking") and item.get("status") == "FAIL":
            return True
    return False


def run_self_check() -> dict:
    checks = [
        _check_scheduler(),
        _check_execution_service(),
        _check_dispatch_queues(),
        _check_kill_switch(),
    ]

    if any(item["status"] == "FAIL" for item in checks):
        overall_status = "FAIL"
    elif any(item["status"] == "WARN" for item in checks):
        overall_status = "WARN"
    else:
        overall_status = "PASS"

    return {
        "overall_status": overall_status,
        "checks": checks,
        "checked_at": time.time(),
    }
