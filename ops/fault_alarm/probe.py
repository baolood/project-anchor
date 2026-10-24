#!/usr/bin/env python3
"""Read-only host fault alarm. DEPLOY=NO.

Posts ``type=anchor_fault`` to the MF4 Grok Bot webhook when a watched unit
is down, a timer is not firing, the MF4 watcher has no decision for the latest
completed 4h close, the kill switch is open or unreadable, or the go-live /
live-trading flags are no longer blocked.

The process only runs ``systemctl show``. It does not restart units, write the
ledger, call an exchange, or read webhook material into the payload or logs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping


def _bootstrap() -> None:
    root = Path(__file__).resolve().parents[2]
    backend = root / "anchor-backend"
    for item in (str(root), str(backend)):
        if item not in sys.path:
            sys.path.insert(0, item)


_bootstrap()

from app.mcp.backend_probe import probe_backend  # noqa: E402
from app.mcp.commands import UNIT_RE  # noqa: E402
from app.mcp.inventory import (  # noqa: E402
    CLASS_INTENTIONALLY_DISABLED,
    RECOMMENDED_SERVICE_UNITS,
    RECOMMENDED_TIMER_UNITS,
    classify_unit,
)
from app.mcp.inventory import HOST_SIDECAR_ENV  # noqa: E402
from app.mcp.status import read_kill_switch  # noqa: E402
from ops.mf4.mf4_webhook import WebhookConfig, load_config, redact  # noqa: E402
from ops.mf4.sealed import sealed_reason  # noqa: E402


BAR_4H_S = 14400
MF4_GRACE_S = 20 * 60
REMIND_S = 12 * 3600
TIMER_OVERDUE_S = 10 * 60
NO_NEXT_ELAPSE_S = 2 * 3600
STATE_NAME = "fault_alarm_state.json"
DEFAULT_STATE_DIR = "/var/lib/anchor-fault-alarm"
DEFAULT_MF4_DIR = "/var/lib/anchor-mf4-watcher"
DEFAULT_REPO = "/root/project-anchor"
WEBHOOK_ENV_FILE = "/etc/anchor-mf4-watcher/webhook.env"
KILL_ENV_FILE = "/etc/project-anchor/anchor-control-mcp.env"
DECISION_EVENTS = frozenset({"SIGNAL_4H", "SIGNAL_4H_SKIPPED"})
GO_LIVE_BLOCKER = "go-live not authorized"
LIVE_TRADING_BLOCKER = "live trading not authorized"
READINESS_NAME = "production_execution_readiness.json"
DECISION_NAME = "post_production_operations_decision.json"
PAYLOAD_KEYS = (
    "type",
    "source",
    "check",
    "state",
    "since",
    "severity",
    "detail",
    "repeat",
    "event_id",
    "time_utc",
)
# Names from org.freedesktop.systemd1. `systemctl show --timestamp=utc` prints
# realtime timestamps as "Sat 2026-10-24 12:00:00 UTC", not as integers.
# LastTriggerUSecRealtime, InactiveEnterTimestampUSec, and StateChangeTimestampUSec
# are not properties. NextElapseUSecMonotonic is a timespan ("5min" or "0").
SHOW_PROPERTIES = ",".join(
    (
        "Id",
        "ActiveState",
        "SubState",
        "UnitFileState",
        "Result",
        "Type",
        "LoadState",
        "NextElapseUSecRealtime",
        "NextElapseUSecMonotonic",
        "LastTriggerUSec",
        "InactiveEnterTimestamp",
        "StateChangeTimestamp",
    )
)
PROP_MAP = {
    "Id": "id",
    "ActiveState": "active_state",
    "SubState": "sub_state",
    "UnitFileState": "unit_file_state",
    "Result": "result",
    "Type": "type",
    "LoadState": "load_state",
    "NextElapseUSecRealtime": "next_elapse_realtime",
    "NextElapseUSecMonotonic": "next_elapse_monotonic",
    "LastTriggerUSec": "last_trigger",
    "InactiveEnterTimestamp": "inactive_enter",
    "StateChangeTimestamp": "state_change",
}
_WEEKDAY_STAMP = re.compile(
    r"^(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat) "
    r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?"
    r"(?: ([A-Za-z0-9:+-]+))?$"
)
_NUMERIC_OFFSET = re.compile(r"^([+-])(\d{2}):?(\d{2})$")
_UNSET_STAMPS = frozenset({"", "0", "n/a", "infinity", "[not set]"})
# Long-running units the inventory tuples do not already name.
EXTRA_LONG_RUNNING = (
    "anchor-mf4-watcher.service",
    "anchor-control-mcp.service",
)
# Oneshot writers. Idle + Result=success is healthy. The timer carries liveness.
ONESHOT_SERVICES = (
    "anchor-official-ledger.service",
    "anchor-official-ledger-c6.service",
    "anchor-ledger-readonly-mirror.service",
)
EXTRA_TIMERS = ("anchor-official-ledger-c6.timer",)
_KILL_ENV_KEYS = ("REDIS_URL", "ANCHOR_KILL_SWITCH")
_ACTIVE_LONG_RUNNING = frozenset({"active"})
_ONESHOT_RUNNING = frozenset({"active", "activating", "reloading"})
_ONESHOT_IDLE = frozenset({"inactive", "dead"})


class StateDirError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class SystemdUnavailable(Exception):
    pass


@dataclass(frozen=True)
class Fault:
    check: str
    severity: str
    detail: str
    since: str
    fingerprint: str


@dataclass(frozen=True)
class Action:
    kind: str
    check: str
    since: str
    severity: str
    detail: str
    fingerprint: str
    repeat: bool


@dataclass(frozen=True)
class Sources:
    show: Callable[[str], Mapping[str, str]]
    now: datetime
    mf4_dir: Path
    repo: Path
    kill_switch: Callable[[], Mapping[str, Any]]
    backend: Callable[[], Mapping[str, Any]]


PostJson = Callable[[str, Mapping[str, str], bytes, float], int]


def iso(when: datetime) -> str:
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _fault(check: str, detail: str, since: str, severity: str = "critical") -> Fault:
    text = " ".join(detail.split())[:240]
    return Fault(
        check=check,
        severity=severity,
        detail=text,
        since=since,
        fingerprint=f"{severity}|{text}",
    )


def expected_long_running() -> tuple[str, ...]:
    """Inventory long-running services, plus the MF4 watcher and the MCP sidecar."""
    names: list[str] = []
    for name in tuple(RECOMMENDED_SERVICE_UNITS) + EXTRA_LONG_RUNNING:
        if name in names:
            continue
        if classify_unit(name)["unit_class"] == CLASS_INTENTIONALLY_DISABLED:
            continue
        names.append(name)
    return tuple(names)


def expected_oneshots() -> tuple[str, ...]:
    names: list[str] = []
    for name in ONESHOT_SERVICES:
        if classify_unit(name)["unit_class"] == CLASS_INTENTIONALLY_DISABLED:
            continue
        names.append(name)
    return tuple(names)


def expected_timers() -> tuple[str, ...]:
    """Inventory timers, plus the C6 series timer that is classified but not allowlisted."""
    names: list[str] = []
    for name in tuple(RECOMMENDED_TIMER_UNITS) + EXTRA_TIMERS:
        if name in names:
            continue
        if classify_unit(name)["unit_class"] == CLASS_INTENTIONALLY_DISABLED:
            continue
        names.append(name)
    return tuple(names)


def latest_completed_4h_close(now: datetime) -> datetime:
    """UTC close of the latest finished 4h BTC bar. Bars align to 14400s."""
    moment = now.astimezone(timezone.utc) if now.tzinfo else now.replace(tzinfo=timezone.utc)
    ts = int(moment.timestamp())
    close = ts - (ts % BAR_4H_S)
    return datetime.fromtimestamp(close, timezone.utc)


def _in_mf4_grace(now: datetime, close: datetime) -> bool:
    return (now - close).total_seconds() < MF4_GRACE_S


def _regular_file(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return stat.S_ISREG(info.st_mode)


def parse_show_time(raw: object) -> float | None:
    """Seconds since the epoch from one `systemctl show` timestamp field.

    Accepts ``--timestamp=utc`` (``Sat 2026-10-24 12:00:00 UTC``), ``--timestamp=unix``
    (``@1729756800``), ``n/a``, and a raw integer (microseconds when it is large
    enough to be a systemd ``t``, otherwise seconds).
    """
    if raw is None:
        return None
    text = str(raw).strip()
    lowered = text.lower()
    if lowered in _UNSET_STAMPS:
        return None
    if text.startswith("@"):
        try:
            seconds = float(text[1:])
        except ValueError:
            return None
        if seconds <= 0:
            return None
        return seconds
    if re.fullmatch(r"\d+", text):
        value = int(text)
        if value <= 0:
            return None
        # systemd usec-since-epoch is ~1e15 in 2026. Smaller integers are seconds.
        if value >= 100_000_000_000_000:
            return value / 1_000_000
        return float(value)
    matched = _WEEKDAY_STAMP.fullmatch(text)
    if matched is None:
        return None
    date_text, clock, fraction, zone = matched.groups()
    try:
        parsed = datetime.strptime(f"{date_text} {clock}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    if fraction:
        parsed = parsed.replace(microsecond=int(fraction.ljust(6, "0")))
    aware = _stamp_with_zone(parsed, zone)
    if aware is None:
        return None
    return aware.timestamp()


def _stamp_with_zone(parsed: datetime, zone: str | None) -> datetime | None:
    if zone is None or zone.upper() in {"UTC", "GMT", "Z", "UT"}:
        return parsed.replace(tzinfo=timezone.utc)
    offset = _NUMERIC_OFFSET.fullmatch(zone)
    if offset is not None:
        sign = 1 if offset.group(1) == "+" else -1
        delta = timedelta(hours=int(offset.group(2)), minutes=int(offset.group(3))) * sign
        return parsed.replace(tzinfo=timezone(delta))
    # Pretty output uses the host's local clock plus a timezone abbreviation.
    local = datetime.now().astimezone().tzinfo
    if local is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.replace(tzinfo=local)


def _monotonic_armed(raw: object) -> bool:
    """True when NextElapseUSecMonotonic is a non-zero timespan.

    `systemctl show` prints this as a timespan (``5min``, ``0``, ``infinity``),
    not as a wall clock. A monotonic-only timer leaves NextElapseUSecRealtime
    empty while this value is non-zero.
    """
    if raw is None:
        return False
    text = str(raw).strip().lower()
    return text not in _UNSET_STAMPS


def _since_from(props: Mapping[str, str], now: datetime, prefer_inactive: bool = False) -> str:
    keys = ("inactive_enter", "state_change") if prefer_inactive else ("state_change", "inactive_enter")
    for key in keys:
        stamp = parse_show_time(props.get(key))
        if stamp is not None:
            return iso(datetime.fromtimestamp(stamp, timezone.utc))
    return iso(now)


def parse_show(stdout: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        key, raw = line.split("=", 1)
        mapped = PROP_MAP.get(key.strip())
        if mapped is None:
            continue
        parsed[mapped] = raw.strip()[:200]
    return parsed


def systemctl_show(unit: str) -> dict[str, str]:
    """Read one unit. ``systemctl`` missing raises; a bad unit returns empty props."""
    if not UNIT_RE.fullmatch(unit):
        return {}
    argv = ["systemctl", "show", unit, "--no-pager", "--timestamp=utc", f"--property={SHOW_PROPERTIES}"]
    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=3,
            shell=False,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SystemdUnavailable("systemctl_missing") from exc
    except subprocess.TimeoutExpired:
        return {}
    parsed = parse_show(completed.stdout or "")
    shown = parsed.get("id")
    if shown and shown != unit:
        return {}
    return parsed


def _service_not_loaded(name: str, props: Mapping[str, str], now: datetime) -> Fault:
    load = props.get("load_state") or "missing"
    return _fault(f"service:{name}", f"{name} is not loaded ({load})", _since_from(props, now))


def long_running_fault(name: str, props: Mapping[str, str], now: datetime) -> Fault | None:
    if props.get("load_state") != "loaded":
        return _service_not_loaded(name, props, now)
    if props.get("active_state") in _ACTIVE_LONG_RUNNING:
        return None
    active = props.get("active_state") or "unknown"
    sub = props.get("sub_state") or "unknown"
    result = props.get("result") or "unknown"
    return _fault(
        f"service:{name}",
        f"{name} is not active ({active}/{sub}); result={result}",
        _since_from(props, now, prefer_inactive=True),
    )


def oneshot_fault(name: str, props: Mapping[str, str], now: datetime) -> Fault | None:
    if props.get("load_state") != "loaded":
        return _service_not_loaded(name, props, now)
    active = props.get("active_state") or ""
    if active in _ONESHOT_RUNNING:
        return None
    result = props.get("result") or ""
    if active in _ONESHOT_IDLE and result == "success":
        return None
    sub = props.get("sub_state") or "unknown"
    return _fault(
        f"service:{name}",
        f"{name} last run is not success ({active or 'unknown'}/{sub}); result={result or 'unknown'}",
        _since_from(props, now, prefer_inactive=True),
    )


def timer_fault(name: str, props: Mapping[str, str], now: datetime) -> Fault | None:
    if props.get("load_state") != "loaded":
        load = props.get("load_state") or "missing"
        return _fault(f"timer:{name}", f"{name} is not loaded ({load})", _since_from(props, now))
    active = props.get("active_state") or ""
    if active != "active":
        sub = props.get("sub_state") or "unknown"
        result = props.get("result") or "unknown"
        return _fault(
            f"timer:{name}",
            f"{name} is not active ({active or 'unknown'}/{sub}); result={result}",
            _since_from(props, now, prefer_inactive=True),
        )
    if props.get("result") == "failed":
        return _fault(f"timer:{name}", f"{name} result is failed", _since_from(props, now))
    last = parse_show_time(props.get("last_trigger"))
    nxt = parse_show_time(props.get("next_elapse_realtime"))
    now_ts = now.timestamp()
    # A future realtime elapse means systemd still has this timer armed.
    if nxt is not None and nxt > now_ts:
        return None
    # OnUnitActiveSec / OnBootSec timers leave the realtime elapse empty.
    if nxt is None and _monotonic_armed(props.get("next_elapse_monotonic")):
        return None
    if last is None:
        return _fault(f"timer:{name}", f"{name} has not fired", iso(now))
    since = iso(datetime.fromtimestamp(last, timezone.utc))
    if nxt is not None and now_ts - nxt > TIMER_OVERDUE_S:
        return _fault(f"timer:{name}", f"{name} missed its elapse", since)
    if nxt is None and now_ts - last > NO_NEXT_ELAPSE_S:
        return _fault(f"timer:{name}", f"{name} has no next elapse", since)
    return None


def unit_faults(show: Callable[[str], Mapping[str, str]], now: datetime) -> list[Fault]:
    cache: dict[str, Mapping[str, str]] = {}

    def get(name: str) -> Mapping[str, str]:
        if name not in cache:
            cache[name] = show(name) or {}
        return cache[name]

    faults: list[Fault] = []
    seen: set[str] = set()
    for name in expected_long_running():
        seen.add(name)
        fault = long_running_fault(name, get(name), now)
        if fault is not None:
            faults.append(fault)
    for name in expected_oneshots():
        seen.add(name)
        fault = oneshot_fault(name, get(name), now)
        if fault is not None:
            faults.append(fault)
    for name in expected_timers():
        seen.add(name)
        fault = timer_fault(name, get(name), now)
        if fault is not None:
            faults.append(fault)
        companion = name[: -len(".timer")] + ".service"
        if companion in seen:
            continue
        if classify_unit(companion)["unit_class"] == CLASS_INTENTIONALLY_DISABLED:
            continue
        props = get(companion)
        if props.get("load_state") != "loaded":
            continue
        seen.add(companion)
        if props.get("type") == "oneshot":
            companion_fault = oneshot_fault(companion, props, now)
        else:
            companion_fault = long_running_fault(companion, props, now)
        if companion_fault is not None:
            faults.append(companion_fault)
    return faults


def _read_tail(path: Path, limit: int = 262144) -> bytes | None:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError:
        return None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return None
        start = max(0, info.st_size - limit)
        os.lseek(fd, start, os.SEEK_SET)
        blob = os.read(fd, limit)
    except OSError:
        return None
    finally:
        os.close(fd)
    if start and blob:
        blob = blob.split(b"\n", 1)[-1]
    return blob


def mf4_decision(directory: Path, close: datetime) -> str:
    """Return ``yes``, ``no``, or ``unreadable`` for one 4h close.

    The watcher appends ``SIGNAL_4H`` or ``SIGNAL_4H_SKIPPED`` to
    ``mf4_forward_events.jsonl``. ``bar4h_close_utc`` and, on a real signal,
    ``signal_available_at`` are the close in UTC (``YYYY-MM-DDTHH:MM:SSZ``).
    """
    try:
        resolved = directory.resolve()
    except OSError:
        resolved = directory
    if sealed_reason(directory) is not None or sealed_reason(resolved) is not None:
        return "unreadable"
    path = directory / "mf4_forward_events.jsonl"
    if sealed_reason(path) is not None:
        return "unreadable"
    try:
        info = path.lstat()
    except FileNotFoundError:
        try:
            dinfo = directory.lstat()
        except FileNotFoundError:
            return "unreadable"
        except OSError:
            return "unreadable"
        if stat.S_ISLNK(dinfo.st_mode) or not stat.S_ISDIR(dinfo.st_mode):
            return "unreadable"
        return "no"
    except OSError:
        return "unreadable"
    if not stat.S_ISREG(info.st_mode):
        return "unreadable"
    blob = _read_tail(path)
    if blob is None:
        return "unreadable"
    stamp = iso(close)
    for line in blob.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict) or row.get("event_type") not in DECISION_EVENTS:
            continue
        if row.get("bar4h_close_utc") == stamp or row.get("signal_available_at") == stamp:
            return "yes"
    return "no"


def mf4_close_under_test(now: datetime) -> datetime:
    """Close this run is allowed to judge.

    The 20 minutes after a 4h close are grace for that bar. During grace the
    previous close is still in force, so an open fault is not cleared just
    because the new bar has not been written yet.
    """
    close = latest_completed_4h_close(now)
    if _in_mf4_grace(now, close):
        return datetime.fromtimestamp(close.timestamp() - BAR_4H_S, timezone.utc)
    return close


def mf4_fault(directory: Path, now: datetime) -> Fault | None:
    close = mf4_close_under_test(now)
    found = mf4_decision(directory, close)
    stamp = iso(close)
    if found == "yes":
        return None
    if found == "unreadable":
        return _fault("mf4:decision", "MF4 decision log is unreadable", stamp)
    return _fault("mf4:decision", f"no MF4 decision for 4h close {stamp}", stamp)


def kill_switch_fault(view: Mapping[str, Any], now: datetime) -> Fault | None:
    state = view.get("state")
    if state == "CLOSED" and view.get("enabled") is False:
        return None
    since = iso(now)
    if state == "OPEN" or view.get("enabled") is True:
        return _fault("kill_switch", "kill switch is OPEN", since)
    return _fault("kill_switch", "kill switch is unreadable", since)


def _read_json(path: Path) -> tuple[dict[str, Any] | None, bool]:
    if sealed_reason(path) is not None or not _regular_file(path):
        return None, True
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None, True
    if not isinstance(data, dict):
        return None, True
    return data, False


def trade_guard_faults(repo: Path, now: datetime) -> list[Fault]:
    """Port of snapshot check ``go_live_and_live_trading_blocked``, as two faults.

    Both must stay blocked: the readiness file lists the blocker string, and
    the operations decision boundary is ``NO-GO``. Unreadable evidence is a fault.
    """
    readiness, readiness_bad = _read_json(repo / "reports" / READINESS_NAME)
    decision, decision_bad = _read_json(repo / "reports" / DECISION_NAME)
    since = iso(now)
    if readiness_bad or decision_bad or readiness is None or decision is None:
        return [
            _fault("guard:go_live", "go-live evidence is unreadable", since),
            _fault("guard:live_trading", "live trading evidence is unreadable", since),
        ]
    blockers = readiness.get("blockers")
    boundary = decision.get("boundary")
    if not isinstance(blockers, list) or not isinstance(boundary, dict):
        return [
            _fault("guard:go_live", "go-live evidence is unreadable", since),
            _fault("guard:live_trading", "live trading evidence is unreadable", since),
        ]
    faults: list[Fault] = []
    if GO_LIVE_BLOCKER not in blockers or boundary.get("go_live") != "NO-GO":
        faults.append(_fault("guard:go_live", "go-live is not blocked", since))
    if LIVE_TRADING_BLOCKER not in blockers or boundary.get("live_trading") != "NO-GO":
        faults.append(_fault("guard:live_trading", "live trading is not blocked", since))
    return faults


def backend_fault(view: Mapping[str, Any], now: datetime) -> Fault | None:
    if view.get("ok") is True:
        return None
    reason = view.get("reason")
    if not isinstance(reason, str) or not reason or any(ch.isspace() for ch in reason):
        reason = "health_not_ok"
    reason = "".join(ch for ch in reason if ch.isalnum() or ch in {"_", "-"})[:40] or "health_not_ok"
    return _fault(
        "backend:127.0.0.1:8000",
        f"backend health at 127.0.0.1:8000 is not ok ({reason})",
        iso(now),
    )


def collect_faults(sources: Sources) -> list[Fault]:
    faults: list[Fault] = []
    try:
        faults.extend(unit_faults(sources.show, sources.now))
    except SystemdUnavailable:
        faults.append(_fault("systemd:show", "systemctl show is unavailable", iso(sources.now)))
    mf4 = mf4_fault(sources.mf4_dir, sources.now)
    if mf4 is not None:
        faults.append(mf4)
    try:
        kill_view = sources.kill_switch()
    except Exception:
        kill_view = {"state": "UNKNOWN", "enabled": None}
    if not isinstance(kill_view, Mapping):
        kill_view = {"state": "UNKNOWN", "enabled": None}
    kill = kill_switch_fault(kill_view, sources.now)
    if kill is not None:
        faults.append(kill)
    faults.extend(trade_guard_faults(sources.repo, sources.now))
    try:
        backend_view = sources.backend()
    except Exception:
        backend_view = {"ok": False, "reason": "unreachable"}
    if not isinstance(backend_view, Mapping):
        backend_view = {"ok": False, "reason": "unreachable"}
    backend = backend_fault(backend_view, sources.now)
    if backend is not None:
        faults.append(backend)
    faults.sort(key=lambda item: item.check)
    return faults


def plan_notifications(faults: list[Fault], previous: Mapping[str, Any], now: datetime) -> list[Action]:
    """Alert once, again when the detail changes or 12h have passed, and once on recovery."""
    prev_map = previous.get("faults") if isinstance(previous.get("faults"), dict) else {}
    actions: list[Action] = []
    current: set[str] = set()
    for fault in faults:
        current.add(fault.check)
        prev = prev_map.get(fault.check)
        since = fault.since
        repeat = False
        if isinstance(prev, dict) and prev.get("fingerprint") == fault.fingerprint:
            stored_since = prev.get("since")
            if isinstance(stored_since, str) and stored_since:
                since = stored_since
            last = parse_iso(prev.get("last_alert"))
            if last is not None and (now - last).total_seconds() < REMIND_S:
                continue
            if last is not None:
                repeat = True
        actions.append(
            Action(
                kind="fault",
                check=fault.check,
                since=since,
                severity=fault.severity,
                detail=fault.detail,
                fingerprint=fault.fingerprint,
                repeat=repeat,
            )
        )
    for check in sorted(prev_map):
        if check in current:
            continue
        prev = prev_map.get(check)
        if not isinstance(prev, dict):
            continue
        stored_since = prev.get("since")
        since = stored_since if isinstance(stored_since, str) and stored_since else iso(now)
        actions.append(
            Action(
                kind="recovery",
                check=str(check),
                since=since,
                severity="info",
                detail=f"{check} cleared",
                fingerprint="recovered",
                repeat=False,
            )
        )
    actions.sort(key=lambda item: (item.kind != "fault", item.check))
    return actions


def event_id(action: Action, now: datetime) -> str:
    bucket = str(int(now.timestamp()) // REMIND_S) if action.repeat else "0"
    raw = f"{action.kind}|{action.check}|{action.fingerprint}|{action.since}|{bucket}"
    return "fault-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def build_payload(action: Action, now: datetime) -> dict[str, Any]:
    return {
        "type": "anchor_fault",
        "source": "anchor-fault-alarm",
        "check": action.check,
        "state": "fault" if action.kind == "fault" else "recovered",
        "since": action.since,
        "severity": action.severity,
        "detail": action.detail,
        "repeat": bool(action.repeat),
        "event_id": event_id(action, now),
        "time_utc": iso(now),
    }


def finalize_payload(payload: Mapping[str, Any], secrets: tuple[str, ...] = ()) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in PAYLOAD_KEYS:
        value = payload.get(key)
        if isinstance(value, str):
            value = redact(value, secrets)
        out[key] = value
    return out


def reduce_state(previous: Mapping[str, Any], sent: list[Action], now: datetime) -> dict[str, Any]:
    faults: dict[str, Any] = {}
    prev_map = previous.get("faults") if isinstance(previous.get("faults"), dict) else {}
    for check, record in prev_map.items():
        if isinstance(record, dict):
            faults[str(check)] = dict(record)
    for action in sent:
        if action.kind == "recovery":
            faults.pop(action.check, None)
            continue
        faults[action.check] = {
            "fingerprint": action.fingerprint,
            "since": action.since,
            "last_alert": iso(now),
            "severity": action.severity,
            "detail": action.detail,
        }
    return {"version": 1, "faults": faults}


def _state_path(directory: Path) -> Path:
    return directory / STATE_NAME


def assert_state_dir_safe(directory: Path) -> None:
    try:
        resolved = directory.resolve()
    except OSError:
        resolved = directory
    if sealed_reason(directory) is not None or sealed_reason(resolved) is not None:
        raise StateDirError("state_dir_rejected")
    if directory.exists() and directory.is_symlink():
        raise StateDirError("state_dir_symlink")


def load_state(directory: Path) -> dict[str, Any]:
    path = _state_path(directory)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"version": 1, "faults": {}}
    except OSError:
        return {"version": 1, "faults": {}}
    if not stat.S_ISREG(info.st_mode):
        return {"version": 1, "faults": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"version": 1, "faults": {}}
    if not isinstance(data, dict) or not isinstance(data.get("faults"), dict):
        return {"version": 1, "faults": {}}
    return {"version": 1, "faults": data["faults"]}


def save_state(directory: Path, state: Mapping[str, Any], secrets: tuple[str, ...] = ()) -> None:
    assert_state_dir_safe(directory)
    try:
        directory.mkdir(mode=0o750, exist_ok=True)
    except OSError as exc:
        raise StateDirError("state_dir_unwritable") from exc
    if directory.is_symlink():
        raise StateDirError("state_dir_symlink")
    target = _state_path(directory)
    if target.is_symlink():
        raise StateDirError("state_symlink")
    text = redact(json.dumps(state, indent=2, sort_keys=True) + "\n", secrets)
    fd, tmp_name = tempfile.mkstemp(prefix=".fault-state-", dir=directory)
    try:
        os.write(fd, text.encode("utf-8"))
        os.fchmod(fd, 0o640)
        os.close(fd)
        fd = -1
        os.replace(tmp_name, target)
        tmp_name = ""
    finally:
        if fd >= 0:
            os.close(fd)
        if tmp_name:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def note(message: str) -> None:
    print(message, file=sys.stderr)


def _header_value(config: WebhookConfig) -> str:
    try:
        return config.key_format.format(key=config.key)
    except (KeyError, IndexError, ValueError):
        return f"Bearer {config.key}"


def deliver_payload(payload: Mapping[str, Any], config: WebhookConfig, post_json: PostJson) -> bool:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "anchor-fault-alarm/1.0",
        config.header_name: _header_value(config),
    }
    try:
        code = int(post_json(config.url, headers, body, 10.0))
    except Exception:
        note("delivery failed network_error")
        return False
    if 200 <= code < 300:
        return True
    note(f"delivery failed http_{code}")
    return False


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    """Do not follow redirects. A 3xx must not resend Authorization."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        raise urllib.error.HTTPError(req.full_url, code, "redirect_rejected", headers, fp)


def urllib_post_json(url: str, headers: Mapping[str, str], body: bytes, timeout: float) -> int:
    opener = urllib.request.build_opener(_RefuseRedirect)
    request = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
    try:
        with opener.open(request, timeout=timeout) as response:
            response.read(1024)
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def _selected_env(path: Path, keys: tuple[str, ...]) -> dict[str, str]:
    if not _regular_file(path):
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    found: dict[str, str] = {}
    allowed = set(keys)
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export ") :].strip()
        if key in allowed:
            found[key] = value.strip().strip('"').strip("'")
    return found


def load_webhook_config(env: Mapping[str, str] | None = None) -> WebhookConfig | None:
    selected = dict(os.environ if env is None else env)
    if not (selected.get("MF4_WEBHOOK_ENV_FILE") or "").strip() and not (selected.get("CREDENTIALS_DIRECTORY") or "").strip():
        default = Path(WEBHOOK_ENV_FILE)
        if _regular_file(default):
            selected["MF4_WEBHOOK_ENV_FILE"] = str(default)
    return load_config(selected)


def read_host_kill_switch() -> dict[str, Any]:
    """Same fail-closed reader as the MCP sidecar. The MCP token is not kept."""
    extra = _selected_env(Path(KILL_ENV_FILE), _KILL_ENV_KEYS)
    saved: dict[str, str | None] = {}
    try:
        for key, value in extra.items():
            current = os.environ.get(key)
            if current:
                continue
            saved[key] = current
            os.environ[key] = value
        return read_kill_switch()
    except Exception:
        return {"state": "UNKNOWN", "enabled": None, "source": "unavailable", "reason": "unreadable"}
    finally:
        for key, old in saved.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old


def read_host_backend() -> dict[str, Any]:
    env = {HOST_SIDECAR_ENV: "1", "ANCHOR_CONTROL_MCP_BACKEND_PROBE": "1"}
    return probe_backend(env)


def run_probe(
    sources: Sources,
    state_dir: Path,
    *,
    dry_run: bool = False,
    post_json: PostJson | None = None,
    webhook_config: WebhookConfig | None = None,
    load_webhook: Callable[[], WebhookConfig | None] | None = None,
) -> dict[str, Any]:
    faults = collect_faults(sources)
    previous = load_state(state_dir)
    actions = plan_notifications(faults, previous, sources.now)
    send = post_json or urllib_post_json
    config = webhook_config
    if config is None and actions:
        loader = load_webhook or load_webhook_config
        try:
            config = loader()
        except Exception:
            config = None
    secrets = config.secrets if config is not None else ()
    payloads = [finalize_payload(build_payload(action, sources.now), secrets) for action in actions]
    result: dict[str, Any] = {
        "dry_run": dry_run,
        "fault_count": len(faults),
        "sent": 0,
        "recovered": 0,
        "payloads": payloads,
    }
    if dry_run or not actions:
        return result
    if config is None:
        note("delivery skipped credentials_missing")
        return result
    # Persist after each success and stop on the first failure. A 10s post
    # times TimeoutStartSec=120 if a later failure keeps going, and a kill
    # before the final write would repeat posts that already succeeded.
    state = previous
    for action, payload in zip(actions, payloads):
        if not deliver_payload(payload, config, send):
            note(f"delivery not saved check={action.check}")
            break
        state = reduce_state(state, [action], sources.now)
        save_state(state_dir, state, secrets)
        if action.kind == "recovery":
            result["recovered"] += 1
        else:
            result["sent"] += 1
    return result


def resolve_repo(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit)
    env = (os.environ.get("ANCHOR_FAULT_REPO_ROOT") or "").strip()
    if env:
        return Path(env)
    deployed = Path(DEFAULT_REPO)
    marker = deployed / "anchor-backend" / "app" / "mcp" / "inventory.py"
    try:
        deployed_present = marker.is_file()
    except OSError:
        # /root is mode 0700 on a GitHub runner. An unreadable path is not the host checkout.
        deployed_present = False
    if deployed_present:
        return deployed
    return Path(__file__).resolve().parents[2]


def resolve_mf4_dir(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit)
    env = (os.environ.get("ANCHOR_FAULT_MF4_DIR") or os.environ.get("MF4_OUT_DIR") or "").strip()
    if env:
        return Path(env)
    return Path(DEFAULT_MF4_DIR)


def resolve_state_dir(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit)
    env = (os.environ.get("STATE_DIRECTORY") or os.environ.get("ANCHOR_FAULT_STATE_DIR") or "").strip()
    if env:
        return Path(env)
    return Path(DEFAULT_STATE_DIR)


def build_sources(repo: Path, mf4_dir: Path, now: datetime | None = None) -> Sources:
    moment = now or datetime.now(timezone.utc)
    return Sources(
        show=systemctl_show,
        now=moment,
        mf4_dir=mf4_dir,
        repo=repo,
        kill_switch=read_host_kill_switch,
        backend=read_host_backend,
    )


def build_selftest_payload(now: datetime) -> dict[str, Any]:
    stamp = iso(now)
    raw = f"selftest|{stamp}"
    return {
        "type": "anchor_fault",
        "source": "anchor-fault-alarm",
        "check": "selftest",
        "state": "test",
        "since": stamp,
        "severity": "info",
        "detail": "anchor fault alarm self-test",
        "repeat": False,
        "event_id": "fault-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20],
        "time_utc": stamp,
    }


def send_selftest(
    *,
    dry_run: bool = False,
    post_json: PostJson | None = None,
    webhook_config: WebhookConfig | None = None,
    load_webhook: Callable[[], WebhookConfig | None] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """POST one self-test. Does not read or write dedupe state."""
    moment = now or datetime.now(timezone.utc)
    config = webhook_config
    if config is None and not dry_run:
        loader = load_webhook or load_webhook_config
        try:
            config = loader()
        except Exception:
            config = None
    secrets = config.secrets if config is not None else ()
    payload = finalize_payload(build_selftest_payload(moment), secrets)
    result: dict[str, Any] = {"dry_run": dry_run, "sent": 0, "payloads": [payload]}
    if dry_run:
        return result
    if config is None:
        note("delivery skipped credentials_missing")
        return result
    send = post_json or urllib_post_json
    if deliver_payload(payload, config, send):
        result["sent"] = 1
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Anchor host fault alarm. DEPLOY=NO.")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads that would be sent. Do not post or write state.")
    parser.add_argument("--send-test", action="store_true", help="POST one self-test alert. Does not read or write dedupe state.")
    parser.add_argument("--state-dir", default=None)
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--mf4-dir", default=None)
    args = parser.parse_args(argv)
    if args.send_test:
        result = send_selftest(dry_run=bool(args.dry_run))
        if args.dry_run:
            json.dump(result, sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write("\n")
            return 0
        if result["sent"] != 1:
            print("SELFTEST=NOT_SENT")
            print("READ_ONLY=YES")
            print("LEDGER_STATEDIRECTORY_UNCHANGED=YES")
            return 1
        print("SELFTEST=SENT")
        print("READ_ONLY=YES")
        print("LEDGER_STATEDIRECTORY_UNCHANGED=YES")
        return 0
    sources = build_sources(resolve_repo(args.repo_root), resolve_mf4_dir(args.mf4_dir))
    state_dir = resolve_state_dir(args.state_dir)
    try:
        result = run_probe(sources, state_dir, dry_run=bool(args.dry_run))
    except StateDirError as exc:
        note(f"FAULT_ALARM=BLOCKED reason={exc.reason}")
        return 1
    if args.dry_run:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    print(
        f"FAULT_ALARM faults={result['fault_count']} sent={result['sent']} recovered={result['recovered']}"
    )
    print("READ_ONLY=YES")
    print("LEDGER_STATEDIRECTORY_UNCHANGED=YES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
