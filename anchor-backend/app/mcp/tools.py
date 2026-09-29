"""Stage-1 read-only MCP tools. The registry is exactly these seven names."""

from __future__ import annotations

from dataclasses import dataclass
from os import environ
from typing import Any, Callable, Mapping

from app.mcp.commands import CommandResult, run_readonly_command
from app.mcp.sanitize import redact_obj
from app.mcp.status import (
    checklist_counts,
    collect_errors,
    collect_ledger,
    collect_observation,
    collect_units,
    default_reports_dir,
    read_kill_switch,
    repo_root,
    service_state_ok,
    utc_now,
)


TOOL_NAMES = (
    "get_anchor_status",
    "get_latest_observation",
    "get_ledger_summary",
    "get_services",
    "get_timers",
    "get_recent_errors",
    "run_readonly_healthcheck",
)

BOUNDARIES = {
    "live_trading": "NO-GO",
    "go_live": "NO-GO",
    "orders": "disabled",
    "withdrawals": "disabled",
    "account_access": "disabled",
    "database_writes": "disabled",
    "governance_changes": "disabled",
    "service_control": "disabled",
    "shell": "disabled",
    "ssh": "disabled",
}


@dataclass
class ToolContext:
    reports_dir: Any
    repo_root: Any
    env: Mapping[str, str]
    run_command: Callable[[list[str], float], CommandResult]
    kill_switch: Callable[[], dict[str, Any]]
    clock: Callable[[], str]
    extra_secrets: tuple[str, ...] = ()


def default_context(env: Mapping[str, str] | None = None) -> ToolContext:
    selected = env if env is not None else environ
    return ToolContext(
        reports_dir=default_reports_dir(selected),
        repo_root=repo_root(),
        env=selected,
        run_command=run_readonly_command,
        kill_switch=read_kill_switch,
        clock=utc_now,
    )


def _envelope(tool: str, payload: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    body = {
        "protocol": "ANCHOR_CONTROL_MCP_V1",
        "tool": tool,
        "mode": "read_only",
        "checked_at": ctx.clock(),
        "boundaries": BOUNDARIES,
        **payload,
    }
    redacted = redact_obj(body, ctx.extra_secrets)
    return redacted if isinstance(redacted, dict) else {"redacted": True}


def collect_anchor_status(ctx: ToolContext) -> dict[str, Any]:
    observation = collect_observation(ctx.reports_dir)
    ledger = collect_ledger(ctx.reports_dir)
    return {
        "process": {"ok": True},
        "kill_switch": ctx.kill_switch(),
        "checklist": checklist_counts(ctx.repo_root),
        "latest_observation_result": observation.get("result") if observation.get("available") else None,
        "latest_observation_available": bool(observation.get("available")),
        "ledger_available": bool(ledger.get("available")),
        "ledger_fill_status": ledger.get("fill_status") if ledger.get("available") else None,
    }


def get_anchor_status(ctx: ToolContext) -> dict[str, Any]:
    return _envelope("get_anchor_status", collect_anchor_status(ctx), ctx)


def get_latest_observation(ctx: ToolContext) -> dict[str, Any]:
    return _envelope("get_latest_observation", collect_observation(ctx.reports_dir), ctx)


def get_ledger_summary(ctx: ToolContext) -> dict[str, Any]:
    return _envelope("get_ledger_summary", collect_ledger(ctx.reports_dir), ctx)


def get_services(ctx: ToolContext) -> dict[str, Any]:
    return _envelope("get_services", collect_units("service", ctx.env, ctx.run_command), ctx)


def get_timers(ctx: ToolContext) -> dict[str, Any]:
    return _envelope("get_timers", collect_units("timer", ctx.env, ctx.run_command), ctx)


def get_recent_errors(ctx: ToolContext, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    limit = 20
    if arguments and "limit" in arguments:
        limit = int(arguments["limit"])
    return _envelope(
        "get_recent_errors",
        collect_errors(ctx.reports_dir, ctx.env, ctx.run_command, limit),
        ctx,
    )


def _check(name: str, ok: bool, detail: str) -> dict[str, str]:
    return {"name": name, "result": "PASS" if ok else "DEGRADED", "detail": detail}


def run_readonly_healthcheck(ctx: ToolContext) -> dict[str, Any]:
    status = collect_anchor_status(ctx)
    observation = collect_observation(ctx.reports_dir)
    ledger = collect_ledger(ctx.reports_dir)
    services = collect_units("service", ctx.env, ctx.run_command)
    timers = collect_units("timer", ctx.env, ctx.run_command)
    errors = collect_errors(ctx.reports_dir, ctx.env, ctx.run_command, 20)
    kill = status.get("kill_switch") if isinstance(status.get("kill_switch"), dict) else {}
    kill_known = kill.get("source") in {"env", "redis", "none"} and isinstance(kill.get("enabled"), bool)
    error_count = len(errors.get("journal_lines") or []) + len(errors.get("artifact_errors") or [])
    checks = [
        _check("process", status.get("process", {}).get("ok") is True, "mcp_process_up"),
        _check("kill_switch", kill_known and kill.get("enabled") is False, str(kill.get("source") or "unavailable")),
        _check(
            "observation",
            observation.get("available") is True and observation.get("result") in {"PASS", "OK"},
            str(observation.get("result") or observation.get("reason") or "missing"),
        ),
        _check(
            "ledger",
            ledger.get("available") is True,
            str(ledger.get("fill_status") or ledger.get("reason") or "missing"),
        ),
        _check("services", service_state_ok(services), str(services.get("command_state"))),
        _check("timers", service_state_ok(timers), str(timers.get("command_state"))),
        _check(
            "recent_errors",
            error_count == 0 and errors.get("command_state") == "ok",
            f"lines={error_count};state={errors.get('command_state')}",
        ),
    ]
    verdict = "PASS" if all(item["result"] == "PASS" for item in checks) else "DEGRADED"
    return _envelope(
        "run_readonly_healthcheck",
        {
            "verdict": verdict,
            "checks": checks,
            "anchor_status": status,
            "observation": observation,
            "ledger": ledger,
            "services": services,
            "timers": timers,
            "recent_errors": errors,
        },
        ctx,
    )


def tool_definitions() -> list[dict[str, Any]]:
    empty = {"type": "object", "properties": {}, "additionalProperties": False}
    errors_schema = {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 50,
                "description": "Maximum sanitized error lines to return.",
            }
        },
        "additionalProperties": False,
    }
    descriptions = {
        "get_anchor_status": "Read overall Project Anchor status. Does not trade, change config, or read secrets.",
        "get_latest_observation": "Read the latest Forward/observation sample from allowlisted report JSON. Read-only.",
        "get_ledger_summary": "Read the Official Fake-Fill / ledger summary from allowlisted report JSON. Read-only.",
        "get_services": "Read allowlisted systemd service status. Does not start, stop, or restart units.",
        "get_timers": "Read allowlisted systemd timer status. Does not start, stop, or restart units.",
        "get_recent_errors": "Read recent allowlisted journal errors and sanitized artifact errors. Read-only.",
        "run_readonly_healthcheck": "Run one combined read-only health check across the other six status views.",
    }
    tools = []
    for name in TOOL_NAMES:
        tools.append(
            {
                "name": name,
                "description": descriptions[name],
                "inputSchema": errors_schema if name == "get_recent_errors" else empty,
                "annotations": {
                    "readOnlyHint": True,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            }
        )
    return tools


def validate_arguments(name: str, arguments: Any) -> dict[str, Any]:
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")
    if name == "get_recent_errors":
        allowed = {"limit"}
    else:
        allowed = set()
    extra = set(arguments) - allowed
    if extra:
        raise ValueError("unexpected arguments")
    if "limit" in arguments:
        limit = arguments["limit"]
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
            raise ValueError("limit must be an integer from 1 to 50")
    return arguments


def call_tool(name: str, arguments: Any, ctx: ToolContext) -> dict[str, Any]:
    if name not in TOOL_NAMES:
        raise KeyError(name)
    parsed = validate_arguments(name, arguments)
    if name == "get_anchor_status":
        return get_anchor_status(ctx)
    if name == "get_latest_observation":
        return get_latest_observation(ctx)
    if name == "get_ledger_summary":
        return get_ledger_summary(ctx)
    if name == "get_services":
        return get_services(ctx)
    if name == "get_timers":
        return get_timers(ctx)
    if name == "get_recent_errors":
        return get_recent_errors(ctx, parsed)
    if name == "run_readonly_healthcheck":
        return run_readonly_healthcheck(ctx)
    raise KeyError(name)
