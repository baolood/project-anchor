"""Allowlisted read-only process calls. No shell, no SSH, no service control."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass


UNIT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:_.@-]{0,127}\.(service|timer)$")
MAX_UNITS = 8
SYSTEMCTL_PROPERTIES = (
    "Id,ActiveState,SubState,UnitFileState,Result,Type,Description,"
    "NextElapseUSecRealtime,LastTriggerUSecRealtime"
)
DEFAULT_SERVICES = ("project-anchor-post-production-monitoring.service",)
DEFAULT_TIMERS = ("project-anchor-post-production-monitoring.timer",)
SERVICE_UNITS_ENV = "ANCHOR_CONTROL_MCP_SERVICE_UNITS"
TIMER_UNITS_ENV = "ANCHOR_CONTROL_MCP_TIMER_UNITS"
COMMAND_TIMEOUT_SEC = 3.0


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    code: int | None
    stdout: str
    stderr: str


class CommandRejected(Exception):
    pass


def parse_units(raw: str, suffix: str) -> list[str]:
    """Accept comma-separated or whitespace-separated unit lists.

    The Vultr inventory writes the recommended values as a quoted
    space-separated assignment. A comma list still fits a systemd Environment
    line, which treats an unquoted space as a separator.
    """
    text = raw.strip().strip('"').strip("'")
    out: list[str] = []
    for part in re.split(r"[\s,]+", text):
        name = part.strip().strip('"').strip("'")
        if not name:
            continue
        if not UNIT_RE.fullmatch(name) or not name.endswith(suffix):
            raise ValueError("invalid unit")
        if name not in out:
            out.append(name)
        if len(out) > MAX_UNITS:
            raise ValueError("too many units")
    return out


def configured_units(env_value: str, suffix: str, defaults: tuple[str, ...]) -> tuple[list[str], str | None]:
    raw = (env_value or "").strip()
    if not raw:
        return list(defaults), None
    try:
        parsed = parse_units(raw, suffix)
    except ValueError:
        return list(defaults), "invalid_override_ignored"
    if not parsed:
        return list(defaults), None
    return parsed, None


def _unit_ok(unit: str) -> bool:
    return bool(UNIT_RE.fullmatch(unit))


def assert_readonly_argv(argv: list[str]) -> None:
    if not argv or any(not isinstance(part, str) or part != part.strip() or "\x00" in part for part in argv):
        raise CommandRejected("invalid argv")
    if argv[0] == "systemctl":
        expected = ["systemctl", "show", argv[2] if len(argv) > 2 else "", "--no-pager", f"--property={SYSTEMCTL_PROPERTIES}"]
        if argv == expected and _unit_ok(argv[2]):
            return
        raise CommandRejected("argv not allowlisted")
    if argv[0] == "journalctl":
        if (
            len(argv) == 9
            and argv[1:] == ["-u", argv[2], "-p", "err", "-n", argv[6], "--no-pager", "--output=cat"]
            and _unit_ok(argv[2])
            and argv[2].endswith(".service")
            and argv[6].isdigit()
            and 1 <= int(argv[6]) <= 50
        ):
            return
        raise CommandRejected("argv not allowlisted")
    raise CommandRejected("argv not allowlisted")


def systemctl_show_argv(unit: str) -> list[str]:
    argv = ["systemctl", "show", unit, "--no-pager", f"--property={SYSTEMCTL_PROPERTIES}"]
    assert_readonly_argv(argv)
    return argv


def journalctl_err_argv(unit: str, limit: int) -> list[str]:
    argv = ["journalctl", "-u", unit, "-p", "err", "-n", str(int(limit)), "--no-pager", "--output=cat"]
    assert_readonly_argv(argv)
    return argv


def run_readonly_command(argv: list[str], timeout: float = COMMAND_TIMEOUT_SEC) -> CommandResult:
    try:
        assert_readonly_argv(argv)
    except CommandRejected:
        return CommandResult(ok=False, code=None, stdout="", stderr="command_rejected")
    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            check=False,
        )
    except FileNotFoundError:
        return CommandResult(ok=False, code=None, stdout="", stderr="command_not_found")
    except subprocess.TimeoutExpired:
        return CommandResult(ok=False, code=None, stdout="", stderr="timeout")
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    return CommandResult(
        ok=completed.returncode == 0,
        code=completed.returncode,
        stdout=stdout[:16384],
        stderr=stderr[:4000],
    )
