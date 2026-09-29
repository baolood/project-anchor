"""Read-only collectors for Anchor status, observation, and fake-fill ledger artifacts."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from app.mcp.commands import (
    SERVICE_UNITS_ENV,
    TIMER_UNITS_ENV,
    CommandResult,
    DEFAULT_SERVICES,
    DEFAULT_TIMERS,
    configured_units,
    journalctl_err_argv,
    systemctl_show_argv,
)
from app.mcp.sanitize import looks_sensitive_path, redact_text


TOKEN_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
JSON_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.json$")
CHECKLIST_MARKERS = ("TODO", "IN_PROGRESS", "BLOCKED", "DONE")
OBSERVATION_FILES = (
    "forward_observation.json",
    "post_production_monitoring_run.json",
    "post_production_monitoring_snapshot.json",
)
LEDGER_FILES = (
    "official_fake_fill_ledger.json",
    "final_production_send_runner.json",
    "gated_production_send_executor_entrypoint.json",
    "production_http_transport_wiring_drill.json",
)
REPORTS_DIR_ENV = "ANCHOR_CONTROL_MCP_REPORTS_DIR"
MAX_JSON_BYTES = 262144
PROP_MAP = {
    "Id": "id",
    "ActiveState": "active_state",
    "SubState": "sub_state",
    "UnitFileState": "unit_file_state",
    "Result": "result",
    "Description": "description",
    "NextElapseUSecRealtime": "next_elapse_usec_realtime",
    "LastTriggerUSecRealtime": "last_trigger_usec_realtime",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_reports_dir(env: Mapping[str, str]) -> Path:
    override = (env.get(REPORTS_DIR_ENV) or "").strip()
    if override and not looks_sensitive_path(override):
        candidate = Path(override)
        if candidate.is_dir():
            return candidate
    return repo_root() / "reports"


def _token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if TOKEN_RE.fullmatch(text):
        return text
    return None


def _iso(value: Any) -> str | None:
    if isinstance(value, str) and ISO_RE.fullmatch(value.strip()):
        return value.strip()
    return None


def safe_json_file(root: Path, name: str) -> Path | None:
    if not JSON_NAME_RE.fullmatch(name) or looks_sensitive_path(name):
        return None
    try:
        root_resolved = root.resolve()
        candidate = (root_resolved / name).resolve()
    except OSError:
        return None
    if candidate.parent != root_resolved or not candidate.is_file():
        return None
    if looks_sensitive_path(candidate.name) or looks_sensitive_path(str(candidate)):
        return None
    try:
        if candidate.stat().st_size > MAX_JSON_BYTES:
            return None
        return candidate
    except OSError:
        return None


def load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _stamp(path: Path, data: dict[str, Any]) -> str:
    generated = _iso(data.get("generated_at"))
    if generated:
        return generated
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except OSError:
        return ""


def _newest(
    root: Path,
    names: tuple[str, ...],
    accept: Callable[[str, dict[str, Any]], bool],
) -> tuple[str, dict[str, Any]] | None:
    chosen: tuple[str, str, dict[str, Any]] | None = None
    for name in names:
        path = safe_json_file(root, name)
        if path is None:
            continue
        data = load_json_file(path)
        if data is None or not accept(name, data):
            continue
        stamp = _stamp(path, data)
        if chosen is None or stamp >= chosen[0]:
            chosen = (stamp, name, data)
    if chosen is None:
        return None
    return chosen[1], chosen[2]


def project_observation(data: dict[str, Any], source: str) -> dict[str, Any]:
    boundary = data.get("boundary") if isinstance(data.get("boundary"), dict) else {}
    checks: list[dict[str, str | None]] = []
    raw_checks = data.get("checks")
    if isinstance(raw_checks, list):
        for item in raw_checks:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                continue
            checks.append({"name": item["name"][:80], "result": _token(item.get("result"))})
            if len(checks) >= 20:
                break
    errors = data.get("errors")
    error_count = len(errors) if isinstance(errors, list) else 0
    return {
        "observation_class": "forward",
        "source": source,
        "available": True,
        "generated_at": _iso(data.get("generated_at")),
        "result": _token(data.get("result")),
        "next_gate": _token(data.get("next_gate")),
        "snapshot_result": _token(data.get("snapshot_result")),
        "go_live": _token(boundary.get("go_live")),
        "live_trading": _token(boundary.get("live_trading")),
        "runtime_modified": _token(boundary.get("runtime_modified")),
        "checks": checks,
        "error_count": error_count,
        "redacted": True,
    }


def _is_fake_fill(name: str, data: dict[str, Any]) -> bool:
    if name == "official_fake_fill_ledger.json":
        return True
    return _token(data.get("fake_transport_external_status")) is not None


def project_ledger(data: dict[str, Any], source: str) -> dict[str, Any]:
    boundary = data.get("boundary") if isinstance(data.get("boundary"), dict) else {}
    called = data.get("fake_transport_called_once")
    fill_status = _token(data.get("fake_transport_external_status")) or _token(data.get("official_status"))
    return {
        "kind": "official_fake_fill",
        "source": source,
        "available": True,
        "result": _token(data.get("result")),
        "fill_status": fill_status,
        "fake_transport_called_once": called if isinstance(called, bool) else None,
        "generated_at": _iso(data.get("generated_at")),
        "go_live": _token(boundary.get("go_live")),
        "live_trading": _token(boundary.get("live_trading")),
        "production_request_sent": _token(boundary.get("production_request_sent")),
        "redacted": True,
    }


def collect_observation(reports_dir: Path) -> dict[str, Any]:
    found = _newest(reports_dir, OBSERVATION_FILES, lambda _name, _data: True)
    if found is None:
        return {"observation_class": "forward", "available": False, "reason": "observation_not_found", "redacted": True}
    name, data = found
    return project_observation(data, name)


def collect_ledger(reports_dir: Path) -> dict[str, Any]:
    found = _newest(reports_dir, LEDGER_FILES, _is_fake_fill)
    if found is None:
        return {"kind": "official_fake_fill", "available": False, "reason": "official_fake_fill_not_found", "redacted": True}
    name, data = found
    return project_ledger(data, name)


def checklist_counts(repo: Path) -> dict[str, Any]:
    path = repo / "docs" / "GO_LIVE_CHECKLIST.md"
    try:
        if path.parent.resolve() != (repo / "docs").resolve() or not path.is_file():
            return {"available": False, "reason": "checklist_not_found"}
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {"available": False, "reason": "checklist_unreadable"}
    counts = {marker.lower(): len(re.findall(rf"`{marker}`", text)) for marker in CHECKLIST_MARKERS}
    return {"available": True, "source": "docs/GO_LIVE_CHECKLIST.md", "counts": counts}


def _kill_switch_view(state: str, enabled: bool | None, source: str, reason: str) -> dict[str, Any]:
    return {"state": state, "enabled": enabled, "source": source, "reason": reason}


def normalize_kill_switch(raw: Any) -> dict[str, Any]:
    """Fail closed. An unread switch is UNKNOWN, not closed."""
    if not isinstance(raw, dict):
        return _kill_switch_view("UNKNOWN", None, "unavailable", "unreadable")
    state = raw.get("state")
    enabled = raw.get("enabled")
    source = raw.get("source")
    reason = raw.get("reason") if isinstance(raw.get("reason"), str) and TOKEN_RE.fullmatch(raw["reason"]) else "unreadable"
    if state == "CLOSED" and enabled is False and source == "redis":
        return _kill_switch_view("CLOSED", False, "redis", reason if reason != "unreadable" else "redis_read")
    if state == "OPEN" and enabled is True and source in {"env", "redis"}:
        return _kill_switch_view("OPEN", True, source, reason if reason != "unreadable" else f"{source}_read")
    if source == "redis" and enabled is False:
        return _kill_switch_view("CLOSED", False, "redis", "redis_read")
    if source in {"env", "redis"} and enabled is True:
        return _kill_switch_view("OPEN", True, source, f"{source}_read")
    return _kill_switch_view("UNKNOWN", None, "unavailable", reason if reason != "unreadable" else "unreadable")


def read_kill_switch(timeout_sec: float = 0.3) -> dict[str, Any]:
    """Read kill-switch state. Env ON is authoritative. Otherwise require a Redis read.

    Missing Redis, a missing client, or a failed read is UNKNOWN. It is not reported
    as closed. Exception text is dropped so a URL or password cannot leak.
    """
    if (os.getenv("ANCHOR_KILL_SWITCH") or "").strip() == "1":
        return _kill_switch_view("OPEN", True, "env", "env_flag")
    url = (os.getenv("REDIS_URL") or "").strip()
    if not url or looks_sensitive_path(url):
        return _kill_switch_view("UNKNOWN", None, "unavailable", "redis_url_unset")
    try:
        import redis
    except Exception:
        return _kill_switch_view("UNKNOWN", None, "unavailable", "redis_client_unavailable")
    try:
        client = redis.Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=timeout_sec,
            socket_timeout=timeout_sec,
        )
        try:
            enabled = client.get("anchor:kill_switch") == "1"
        finally:
            client.close()
    except Exception:
        return _kill_switch_view("UNKNOWN", None, "unavailable", "redis_read_failed")
    if enabled:
        return _kill_switch_view("OPEN", True, "redis", "redis_read")
    return _kill_switch_view("CLOSED", False, "redis", "redis_read")


def _parse_show(stdout: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        key, raw = line.split("=", 1)
        mapped = PROP_MAP.get(key.strip())
        if mapped is None:
            continue
        parsed[mapped] = redact_text(raw.strip())[:200]
    return parsed


def _unit_healthy(props: dict[str, str], kind: str) -> bool:
    active = props.get("active_state", "")
    result = props.get("result", "")
    if active == "active":
        return True
    if kind == "service" and active in {"inactive", "dead"} and result == "success":
        return True
    if kind == "timer" and active in {"inactive", "active"} and result in {"success", ""}:
        return active == "active" or result == "success"
    return False


def collect_units(kind: str, env: Mapping[str, str], run_command: Callable[[list[str], float], CommandResult]) -> dict[str, Any]:
    if kind == "service":
        names, warning = configured_units(env.get(SERVICE_UNITS_ENV, ""), ".service", DEFAULT_SERVICES)
        argv_for = systemctl_show_argv
    else:
        names, warning = configured_units(env.get(TIMER_UNITS_ENV, ""), ".timer", DEFAULT_TIMERS)
        argv_for = systemctl_show_argv
    units: list[dict[str, Any]] = []
    command_state = "ok"
    for name in names:
        result = run_command(argv_for(name), 3.0)
        if result.stderr in {"command_not_found", "timeout"}:
            command_state = result.stderr
            break
        if result.stderr == "command_rejected":
            command_state = "command_rejected"
            break
        props = _parse_show(result.stdout)
        if props.get("id") and props.get("id") != name:
            props = {}
        units.append(
            {
                "name": name,
                "available": bool(props),
                "healthy": _unit_healthy(props, kind) if props else False,
                "properties": props,
            }
        )
    available = command_state == "ok"
    return {
        "kind": kind,
        "mode": "read_only",
        "source": "systemctl show",
        "available": available,
        "command_state": command_state,
        "unit_config": warning,
        "units": units if available else [],
        "expected_units": names,
    }


def collect_errors(
    reports_dir: Path,
    env: Mapping[str, str],
    run_command: Callable[[list[str], float], CommandResult],
    limit: int,
) -> dict[str, Any]:
    bounded = max(1, min(int(limit), 50))
    services, warning = configured_units(env.get(SERVICE_UNITS_ENV, ""), ".service", DEFAULT_SERVICES)
    lines: list[str] = []
    command_state = "ok"
    for name in services:
        result = run_command(journalctl_err_argv(name, bounded), 3.0)
        if result.stderr in {"command_not_found", "timeout", "command_rejected"}:
            command_state = result.stderr
            break
        for raw in result.stdout.splitlines():
            cleaned = redact_text(raw).strip()
            if not cleaned:
                continue
            lines.append(cleaned[:400])
            if len(lines) >= bounded:
                break
        if len(lines) >= bounded:
            break
    observation = collect_observation(reports_dir)
    artifact_errors: list[str] = []
    if observation.get("available") and observation.get("error_count"):
        path = safe_json_file(reports_dir, str(observation.get("source") or ""))
        data = load_json_file(path) if path is not None else None
        raw_errors = data.get("errors") if isinstance(data, dict) else None
        if isinstance(raw_errors, list):
            for item in raw_errors:
                if isinstance(item, str):
                    artifact_errors.append(redact_text(item)[:400])
                if len(artifact_errors) >= bounded:
                    break
    return {
        "mode": "read_only",
        "available": command_state != "command_rejected",
        "command_state": command_state,
        "unit_config": warning,
        "limit": bounded,
        "journal_lines": lines,
        "artifact_errors": artifact_errors,
        "redacted": True,
    }


def process_from_units(services: dict[str, Any]) -> dict[str, Any]:
    """Process health is only PASS when every configured service unit was shown healthy."""
    command_state = str(services.get("command_state") or "undetermined")
    view: dict[str, Any] = {
        "source": "systemctl show",
        "command_state": command_state,
        "expected_units": list(services.get("expected_units") or []),
    }
    if command_state != "ok" or services.get("available") is not True:
        view.update({"state": "UNKNOWN", "ok": None, "reason": command_state})
        return view
    units = services.get("units")
    if not isinstance(units, list) or not units:
        view.update({"state": "UNKNOWN", "ok": None, "reason": "no_units"})
        return view
    if any(not isinstance(item, dict) or item.get("available") is not True for item in units):
        view.update({"state": "UNKNOWN", "ok": None, "reason": "unit_status_missing"})
        return view
    if not all(item.get("healthy") is True for item in units):
        view.update({"state": "FAILED", "ok": False, "reason": "unit_not_healthy"})
        return view
    view.update({"state": "PASS", "ok": True, "reason": "allowlisted_units_healthy"})
    return view


def service_state_ok(unit_report: dict[str, Any]) -> bool:
    if not unit_report.get("available"):
        return False
    units = unit_report.get("units")
    if not isinstance(units, list) or not units:
        return False
    return all(isinstance(item, dict) and item.get("healthy") is True for item in units)
