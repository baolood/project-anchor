from collections import defaultdict

from local_box.audit.event_store import (
    count_dead_dispatches,
    count_executed,
    count_pending_dispatches,
    list_events,
)
from local_box.scheduler.retry_scheduler import get_scheduler_status


REQUIRED_AUDIT_STAGES = {
    "NORMALIZATION",
    "RISK",
    "POLICY",
    "EXECUTION_GATE",
    "EXECUTOR",
}


def _kpi_status(
    value: float | None,
    *,
    warn_below: float | None = None,
    critical_below: float | None = None,
    warn_above: float | None = None,
    critical_above: float | None = None,
) -> str:
    if value is None:
        return "UNKNOWN"
    if critical_below is not None and value < critical_below:
        return "CRITICAL"
    if critical_above is not None and value > critical_above:
        return "CRITICAL"
    if warn_below is not None and value < warn_below:
        return "WARN"
    if warn_above is not None and value > warn_above:
        return "WARN"
    return "HEALTHY"


def _command_stage_map() -> dict[str, set[str]]:
    stage_map: dict[str, set[str]] = defaultdict(set)
    for event in list_events():
        stage_map[event.command_id].add(event.stage.value)
    return dict(stage_map)


def _pipeline_command_ids(stage_map: dict[str, set[str]]) -> set[str]:
    return {command_id for command_id, stages in stage_map.items() if "NORMALIZATION" in stages}


def _recovery_metrics(pipeline_command_ids: set[str]) -> dict:
    raw_recovered_done = 0
    raw_recovered_failed = 0
    pipeline_recovered_done = 0
    pipeline_recovered_failed = 0
    recovery_durations = []
    first_seen: dict[str, float] = {}

    for event in list_events():
        first_seen.setdefault(event.command_id, event.timestamp)
        payload = event.payload or {}
        if not payload.get("recovered"):
            continue

        if event.status.value == "DONE":
            raw_recovered_done += 1
            if event.command_id in pipeline_command_ids:
                pipeline_recovered_done += 1
                recovery_durations.append(max(0.0, event.timestamp - first_seen[event.command_id]))
        elif event.status.value == "FAILED":
            raw_recovered_failed += 1
            if event.command_id in pipeline_command_ids:
                pipeline_recovered_failed += 1

    raw_total_recovered = raw_recovered_done + raw_recovered_failed
    raw_recovery_success_rate = None
    if raw_total_recovered > 0:
        raw_recovery_success_rate = raw_recovered_done / raw_total_recovered

    pipeline_total_recovered = pipeline_recovered_done + pipeline_recovered_failed
    pipeline_recovery_success_rate = None
    if pipeline_total_recovered > 0:
        pipeline_recovery_success_rate = pipeline_recovered_done / pipeline_total_recovered

    average_recovery_time_sec = None
    if recovery_durations:
        average_recovery_time_sec = sum(recovery_durations) / len(recovery_durations)

    return {
        "raw_recovered_done": raw_recovered_done,
        "raw_recovered_failed": raw_recovered_failed,
        "raw_recovery_success_rate": raw_recovery_success_rate,
        "pipeline_recovered_done": pipeline_recovered_done,
        "pipeline_recovered_failed": pipeline_recovered_failed,
        "pipeline_recovery_success_rate": pipeline_recovery_success_rate,
        "average_recovery_time_sec": average_recovery_time_sec,
    }


def _audit_trail_metrics(stage_map: dict[str, set[str]], pipeline_command_ids: set[str]) -> dict:
    total_commands = len(pipeline_command_ids)
    fully_audited = 0

    for command_id in pipeline_command_ids:
        if REQUIRED_AUDIT_STAGES.issubset(stage_map.get(command_id, set())):
            fully_audited += 1

    coverage = None
    if total_commands > 0:
        coverage = fully_audited / total_commands

    return {
        "pipeline_commands": total_commands,
        "fully_audited_commands": fully_audited,
        "audit_trail_coverage": coverage,
        "required_stages": sorted(REQUIRED_AUDIT_STAGES),
    }


def _dispatch_metrics() -> dict:
    executed = count_executed()
    pending = count_pending_dispatches()
    dead = count_dead_dispatches()

    denominator = executed + pending + dead
    dead_dispatch_ratio = None
    if denominator > 0:
        dead_dispatch_ratio = dead / denominator

    return {
        "executed_commands": executed,
        "pending_dispatches": pending,
        "dead_dispatches": dead,
        "dead_dispatch_ratio": dead_dispatch_ratio,
    }


def _scheduler_metrics() -> dict:
    scheduler = get_scheduler_status()
    last_cycle_summary = scheduler.get("last_cycle_summary")
    last_cycle_time = scheduler.get("last_cycle_time")

    return {
        "scheduler_last_cycle_time": last_cycle_time,
        "scheduler_last_cycle_summary": last_cycle_summary,
        "scheduler_has_heartbeat": last_cycle_time is not None,
    }


def _self_check_block_metrics() -> dict:
    self_check_block_count = 0
    last_self_check_block_at = None
    blocking_failures_breakdown: dict[str, int] = {}

    for event in list_events():
        payload = event.payload or {}
        if payload.get("code") != "SELF_CHECK_BLOCKED":
            continue

        self_check_block_count += 1
        last_self_check_block_at = event.timestamp

        for name in payload.get("blocking_failures") or []:
            blocking_failures_breakdown[name] = blocking_failures_breakdown.get(name, 0) + 1

    top_blocking_failure = None
    if blocking_failures_breakdown:
        top_blocking_failure = max(
            sorted(blocking_failures_breakdown),
            key=lambda name: blocking_failures_breakdown[name],
        )

    return {
        "self_check_block_count": self_check_block_count,
        "last_self_check_block_at": last_self_check_block_at,
        "blocking_failures_breakdown": blocking_failures_breakdown,
        "top_blocking_failure": top_blocking_failure,
    }


def build_metrics_summary() -> dict:
    stage_map = _command_stage_map()
    pipeline_command_ids = _pipeline_command_ids(stage_map)
    scheduler = _scheduler_metrics()
    dispatch = _dispatch_metrics()
    recovery = _recovery_metrics(pipeline_command_ids)
    audit = _audit_trail_metrics(stage_map, pipeline_command_ids)
    self_check_blocks = _self_check_block_metrics()

    kpis = {
        "scheduler_heartbeat": {
            "value": 1.0 if scheduler["scheduler_has_heartbeat"] else 0.0,
            "status": "HEALTHY" if scheduler["scheduler_has_heartbeat"] else "CRITICAL",
            "target": "heartbeat present",
        },
        "dead_dispatch_ratio": {
            "value": dispatch["dead_dispatch_ratio"],
            "status": _kpi_status(
                dispatch["dead_dispatch_ratio"],
                warn_above=0.05,
                critical_above=0.15,
            ),
            "target": "<= 0.05",
        },
        "recovery_success_rate": {
            "value": recovery["pipeline_recovery_success_rate"],
            "status": _kpi_status(
                recovery["pipeline_recovery_success_rate"],
                warn_below=0.8,
                critical_below=0.5,
            ),
            "target": ">= 0.80",
        },
        "average_recovery_time_sec": {
            "value": recovery["average_recovery_time_sec"],
            "status": _kpi_status(
                recovery["average_recovery_time_sec"],
                warn_above=10.0,
                critical_above=30.0,
            ),
            "target": "<= 10s",
        },
        "audit_trail_coverage": {
            "value": audit["audit_trail_coverage"],
            "status": _kpi_status(
                audit["audit_trail_coverage"],
                warn_below=0.9,
                critical_below=0.7,
            ),
            "target": ">= 0.90",
        },
    }

    overall_status = "HEALTHY"
    if any(item["status"] == "CRITICAL" for item in kpis.values()):
        overall_status = "CRITICAL"
    elif any(item["status"] == "WARN" for item in kpis.values()):
        overall_status = "WARN"
    elif any(item["status"] == "UNKNOWN" for item in kpis.values()):
        overall_status = "UNKNOWN"

    return {
        "overall_status": overall_status,
        "scheduler": scheduler,
        "dispatch": dispatch,
        "recovery": recovery,
        "audit": audit,
        "self_check_blocks": self_check_blocks,
        "kpis": kpis,
    }
