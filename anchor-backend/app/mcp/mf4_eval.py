"""Read-only MF4 status and manual eval snapshot.

``ANCHOR_CONTROL_MCP_MF4_DIR`` points at the watcher directory. When it is
unset the tools report ``available: false`` and open nothing. Reads are
bounded to 64 KB, do not follow symlinks, and reject Line A / sealed paths.
Kraken Prop has no API. ``get_eval_state`` is labeled ``manual-snapshot``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from app.mcp.c6_series import _sealed_line_a
from app.mcp.sanitize import looks_sensitive_path, redact_obj


MF4_DIR_ENV = "ANCHOR_CONTROL_MCP_MF4_DIR"
MAX_READ_BYTES = 64 * 1024
MAX_TOOL_BYTES = 2560
_SOURCE = "manual-snapshot"

_BOUNDARIES = {
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


def parse_clock(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_mf4_status(env: Mapping[str, str], now: datetime) -> dict[str, Any]:
    root, reason = _root(env)
    if root is None:
        return _unavailable(reason)
    payload = _read_json(root / "status.json", root, tail=False)
    if not isinstance(payload, dict):
        return _unavailable("mf4_status_missing")
    price = payload.get("price") if isinstance(payload.get("price"), dict) else {}
    age = _age_seconds(price.get("at"), now)
    fresh = age is not None and 0 <= age < 120
    last_close = payload.get("last_4h_close") if isinstance(payload.get("last_4h_close"), dict) else {}
    last_signal = payload.get("last_signal") if isinstance(payload.get("last_signal"), dict) else None
    webhook = payload.get("webhook") if isinstance(payload.get("webhook"), dict) else {}
    compare = payload.get("compare") if isinstance(payload.get("compare"), dict) else {}
    body = {
        "available": True,
        "read_only": True,
        "state": _short(payload.get("state")),
        "pos": _position(payload.get("pos")),
        "trend": _short(payload.get("trend")),
        "long_trigger_gt": _number(payload.get("long_trigger_gt")),
        "short_trigger_lt": _number(payload.get("short_trigger_lt")),
        "last_4h_close": {"at_sh": _short(last_close.get("at_sh")), "close": _number(last_close.get("close"))},
        "last_signal": None
        if last_signal is None
        else {
            "type": _short(last_signal.get("type")),
            "side": _short(last_signal.get("side")),
            "price": _number(last_signal.get("price")),
            "at_sh": _short(last_signal.get("at_sh")),
        },
        "price": {"last": _number(price.get("last")), "age_s": age, "fresh": fresh},
        "shadow_equity": _number(payload.get("shadow_equity")),
        "webhook": {
            "enabled": webhook.get("enabled") is True,
            "last_ok_at_sh": _short(webhook.get("last_ok_at_sh")),
            "outbox_n": _count_outbox(root),
        },
        "compare": {
            "consecutive_matches": _int(compare.get("consecutive_matches")),
            "last_diff_at": _short(compare.get("last_diff_at")),
        },
        "reason": _short(payload.get("reason"), 160),
    }
    return cap_tool_payload("get_mf4_status", redact_obj(body), now)


def read_eval_state(env: Mapping[str, str], now: datetime) -> dict[str, Any]:
    root, reason = _root(env)
    if root is None:
        return _unavailable(reason, source=_SOURCE)
    account = _read_json(root / "eval_account.json", root, tail=False)
    if not isinstance(account, dict):
        return _unavailable("eval_account_missing", source=_SOURCE)
    status = _read_json(root / "status.json", root, tail=False)
    mark = None
    if isinstance(status, dict) and isinstance(status.get("price"), dict):
        mark = status["price"].get("last")
    guard = _evaluate(account, mark, now)
    if guard is None:
        return _unavailable("eval_guard_unavailable", source=_SOURCE)
    body = {
        "available": True,
        "read_only": True,
        "source": _SOURCE,
        "balance": _number(account.get("balance")),
        "est_equity": guard.get("est_equity"),
        "daily_line": guard.get("daily_line"),
        "floor": guard.get("floor"),
        "target": guard.get("target"),
        "headroom_daily": guard.get("headroom_daily"),
        "headroom_floor": guard.get("headroom_floor"),
        "worst_case_at_sl": guard.get("worst_case_at_sl"),
        "position": _position(account.get("position")),
        "snapshot_age_s": guard.get("snapshot_age_s"),
        "guard_verdict": guard.get("verdict"),
        "reason": _short(guard.get("reason"), 160),
    }
    return cap_tool_payload("get_eval_state", redact_obj(body), now)


def cap_tool_payload(tool: str, payload: Mapping[str, Any], now: datetime) -> dict[str, Any]:
    """Shrink a tool body until the MCP envelope is at most 2.5 KB."""
    body = dict(payload)
    stamp = _stamp(now)
    for _ in range(12):
        if _envelope_len(tool, body, stamp) <= MAX_TOOL_BYTES:
            return body
        reason = body.get("reason")
        if isinstance(reason, str) and len(reason) > 24:
            body["reason"] = reason[: max(24, len(reason) // 2)]
            continue
        dropped = False
        for key in ("last_signal", "compare", "webhook", "position", "last_4h_close"):
            if key in body:
                body.pop(key)
                dropped = True
                break
        if not dropped:
            break
    fallback = {
        "available": False,
        "read_only": True,
        "reason": "response_capped",
    }
    if "source" in payload:
        fallback["source"] = _SOURCE
    return fallback


def _envelope_len(tool: str, payload: Mapping[str, Any], stamp: str) -> int:
    envelope = {
        "protocol": "ANCHOR_CONTROL_MCP_V1",
        "tool": tool,
        "mode": "read_only",
        "checked_at": stamp,
        "boundaries": _BOUNDARIES,
        **dict(payload),
    }
    return len(json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _root(env: Mapping[str, str]) -> tuple[Path | None, str]:
    raw = (env.get(MF4_DIR_ENV) or "").strip()
    if not raw:
        return None, "mf4_dir_unset"
    if looks_sensitive_path(raw):
        return None, "mf4_dir_rejected"
    candidate = Path(raw)
    if not candidate.is_absolute():
        return None, "mf4_dir_rejected"
    try:
        info = os.lstat(candidate)
    except FileNotFoundError:
        return None, "mf4_dir_missing"
    except OSError:
        return None, "mf4_dir_rejected"
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        return None, "mf4_dir_rejected"
    try:
        resolved = candidate.resolve()
    except OSError:
        return None, "mf4_dir_rejected"
    if _sealed_line_a(resolved) or _sealed_line_a(candidate) or looks_sensitive_path(str(resolved)):
        return None, "mf4_dir_rejected"
    return candidate, ""


def _read_json(path: Path, root: Path, *, tail: bool) -> Any:
    blob = _read_bounded(path, root, tail=tail)
    if blob is None:
        return None
    try:
        return json.loads(blob.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return None


def _read_bounded(path: Path, root: Path, *, tail: bool) -> bytes | None:
    try:
        if path.is_symlink():
            return None
        resolved = path.resolve()
        resolved.relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    if _sealed_line_a(resolved):
        return None
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    try:
        fd = os.open(path, flags)
    except OSError:
        return None
    try:
        info = os.fstat(fd)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            return None
        size = info.st_size
        if size > MAX_READ_BYTES:
            if not tail:
                return None
            os.lseek(fd, size - MAX_READ_BYTES, os.SEEK_SET)
        blob = os.read(fd, MAX_READ_BYTES)
        return blob
    finally:
        os.close(fd)


def _count_outbox(root: Path) -> int:
    blob = _read_bounded(root / "webhook_outbox.jsonl", root, tail=True)
    if not blob:
        return 0
    return sum(1 for line in blob.splitlines() if line.strip())


def _evaluate(account: Mapping[str, Any], mark: Any, now: datetime) -> dict[str, Any] | None:
    evaluate = _guard()
    if evaluate is None:
        return None
    try:
        result = evaluate(account, mark, now=now)
    except Exception:
        return None
    return result if isinstance(result, dict) else None


def _guard() -> Callable[..., dict[str, Any]] | None:
    path = Path(__file__).resolve().parents[3] / "ops" / "mf4" / "eval_guard.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("anchor_mf4_eval_guard", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return None
    evaluate = getattr(module, "evaluate", None)
    return evaluate if callable(evaluate) else None


def _unavailable(reason: str, source: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"available": False, "read_only": True, "reason": reason}
    if source is not None:
        body["source"] = source
    return body


def _position(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {
        "side": _short(value.get("side")),
        "size": _number(value.get("size")),
        "entry": _number(value.get("entry")),
        "sl": _number(value.get("sl")),
        "tp": _number(value.get("tp")),
    }


def _short(value: Any, limit: int = 80) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\n", " ").strip()
    if not text:
        return None
    return text[:limit]


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _int(value: Any) -> int:
    number = _number(value)
    if number is None:
        return 0
    return int(number)


def _age_seconds(value: Any, now: datetime) -> int | None:
    if not isinstance(value, str) or not value.strip():
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
    moment = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    return int((moment - parsed.astimezone(timezone.utc)).total_seconds())


def _stamp(now: datetime) -> str:
    moment = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
