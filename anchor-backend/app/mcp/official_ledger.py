"""Read-only Official V2 fake-fill ledger summary.

The host writer keeps this ledger outside the MCP reports directory. The
collector opens an allowlisted directory only, and only the fixed
``affl-v2-official-ledger/out/`` directory under that root, with read flags.
Snapshot copies under ``runs/`` and ``baseline/`` are not opened.
It does not create, rewrite, or truncate ledger files.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import stat
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from app.mcp.inventory import OFFICIAL_LEDGER_DIR, OFFICIAL_LEDGER_DIR_PRIVATE
from app.mcp.sanitize import looks_sensitive_path


LEDGER_DIR_ENV = "ANCHOR_CONTROL_MCP_LEDGER_DIR"
ALLOWLISTED_LEDGER_DIRS = (OFFICIAL_LEDGER_DIR, OFFICIAL_LEDGER_DIR_PRIVATE)
# Live file only. runs/*/before and baseline are snapshots and are not read.
LEDGER_OUT_RELATIVE = ("affl-v2-official-ledger", "out")
LEDGER_NAME_RE = re.compile(
    r"^anchor_fake_fill_ledger_v2_official[A-Za-z0-9._-]*\.(jsonl|csv)$"
)
TOKEN_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")
HASH_RE = re.compile(r"^[A-Za-z0-9]{1,128}$")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
EVENT_TYPE_RE = re.compile(r"^[A-Za-z0-9_]{1,40}$")
PNL_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
MAX_LEDGER_BYTES = 64 * 1024 * 1024
MAX_LEDGER_FILES = 32
EVENT_FIELDS = ("event_id", "event_time", "event_type", "event_hash", "realized_pnl_cum")
POSITIONAL = (
    "event_id",
    "event_time",
    "event_type",
    "prev_hash",
    "event_hash",
    "realized_pnl_cum",
    "net_pnl",
)
ALIASES = {
    "event_id": "event_id",
    "id": "event_id",
    "event_time": "event_time",
    "time": "event_time",
    "timestamp": "event_time",
    "ts": "event_time",
    "event_type": "event_type",
    "type": "event_type",
    "kind": "event_type",
    "prev_hash": "prev_hash",
    "previous_hash": "prev_hash",
    "event_hash": "event_hash",
    "hash": "event_hash",
    "record_hash": "event_hash",
    "chain_hash": "event_hash",
    "realized_pnl_cum": "realized_pnl_cum",
    "realized_pnl_cumulative": "realized_pnl_cum",
    "net_pnl": "net_pnl",
}
NET_PNL_NOTE = (
    "Per-exit NET_PNL rows exclude entry costs. "
    "realized_pnl_cum is the ledger cumulative figure, not an exchange cash balance."
)


class _TooLarge(Exception):
    """Combined ledger bytes exceeded the read cap."""


class _OutRejected(Exception):
    """The fixed out directory escaped the allowlisted root or is not that path."""


def official_ledger_configured(env: Mapping[str, str]) -> bool:
    return bool((env.get(LEDGER_DIR_ENV) or "").strip())


def read_official_ledger(
    env: Mapping[str, str],
    *,
    allowlist: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Summarize the Official V2 ledger. `allowlist` is for tests only."""
    raw = (env.get(LEDGER_DIR_ENV) or "").strip()
    if not raw or not Path(raw).is_absolute() or looks_sensitive_path(raw):
        return _unavailable("ledger_dir_rejected")
    try:
        resolved = Path(raw).resolve()
    except PermissionError:
        return _unavailable("ledger_unreadable")
    except OSError:
        return _unavailable("ledger_dir_rejected")
    if resolved not in _resolved_allowlist(allowlist):
        return _unavailable("ledger_dir_not_allowlisted")
    try:
        info = os.stat(resolved)
    except PermissionError:
        return _unavailable("ledger_unreadable")
    except FileNotFoundError:
        return _unavailable("ledger_dir_missing")
    except OSError:
        return _unavailable("ledger_dir_rejected")
    if not stat.S_ISDIR(info.st_mode):
        return _unavailable("ledger_dir_rejected")
    try:
        out_dir = _official_out_dir(resolved)
    except PermissionError:
        return _unavailable("ledger_unreadable")
    except _OutRejected:
        return _unavailable("ledger_out_rejected")
    if out_dir is None:
        return _unavailable("official_ledger_not_found")
    try:
        names = sorted(os.listdir(out_dir))
    except PermissionError:
        return _unavailable("ledger_unreadable")
    except OSError:
        return _unavailable("ledger_unreadable")
    matched = [name for name in names if LEDGER_NAME_RE.fullmatch(name)]
    if len(matched) > MAX_LEDGER_FILES:
        return _unavailable("official_ledger_too_many_files")
    loaded, failure = _load_files(out_dir, matched)
    if failure is not None:
        return _unavailable(failure)
    if not loaded:
        return _unavailable("official_ledger_not_found")
    return _summarize(loaded)


def _unavailable(reason: str) -> dict[str, Any]:
    return {
        "kind": "official_fake_fill_v2",
        "available": False,
        "reason": reason,
        "read_only": True,
        "redacted": True,
    }


def _official_out_dir(root: Path) -> Path | None:
    """Return the live out directory, or None when that fixed path is absent.

    Symlinks are resolved one component at a time. The canonical path must
    stay inside ``root`` and must be exactly ``affl-v2-official-ledger/out``.
    A link to ``baseline/``, ``runs/*/before/``, or anywhere else is rejected.
    """
    root_real = Path(os.path.realpath(root))
    if not root_real.is_dir():
        raise _OutRejected()
    current = root_real
    walked: list[str] = []
    for part in LEDGER_OUT_RELATIVE:
        walked.append(part)
        nxt = current / part
        try:
            info = os.lstat(nxt)
        except FileNotFoundError:
            return None
        except PermissionError:
            raise
        except OSError as exc:
            raise _OutRejected() from exc
        if not (stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)):
            raise _OutRejected()
        try:
            nxt_real = Path(os.path.realpath(nxt))
        except PermissionError:
            raise
        except OSError as exc:
            raise _OutRejected() from exc
        if not nxt_real.is_dir():
            raise _OutRejected()
        try:
            rel = nxt_real.relative_to(root_real)
        except ValueError as exc:
            raise _OutRejected() from exc
        if rel.parts != tuple(walked):
            raise _OutRejected()
        current = nxt_real
    return current


def _resolved_allowlist(allowlist: tuple[str, ...] | None) -> tuple[Path, ...]:
    raw_items = ALLOWLISTED_LEDGER_DIRS if allowlist is None else allowlist
    resolved: list[Path] = []
    for item in raw_items:
        path = Path(item)
        try:
            resolved.append(path.resolve())
        except OSError:
            if path.is_absolute():
                resolved.append(path)
    return tuple(resolved)


def _load_files(root: Path, names: list[str]) -> tuple[list[tuple[str, bytes]], str | None]:
    loaded: list[tuple[str, bytes]] = []
    total = 0
    root_real = Path(os.path.realpath(root))
    for name in names:
        path = root / name
        try:
            info = os.lstat(path)
        except PermissionError:
            return [], "ledger_unreadable"
        except OSError:
            continue
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            continue
        try:
            parent = Path(os.path.realpath(path)).parent
        except PermissionError:
            return [], "ledger_unreadable"
        except OSError:
            continue
        if parent != root_real:
            continue
        try:
            blob = _read_bytes(path)
        except PermissionError:
            return [], "ledger_unreadable"
        except _TooLarge:
            return [], "ledger_too_large"
        except OSError:
            continue
        total += len(blob)
        if total > MAX_LEDGER_BYTES:
            return [], "ledger_too_large"
        loaded.append((name, blob))
    return loaded, None


def _read_bytes(path: Path) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_LEDGER_BYTES:
            raise _TooLarge()
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_LEDGER_BYTES:
                raise _TooLarge()
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _summarize(loaded: list[tuple[str, bytes]]) -> dict[str, Any]:
    state = _State()
    for name, blob in loaded:
        text = blob.decode("utf-8-sig", errors="replace")
        if name.endswith(".csv"):
            events, mismatches, unparsed = _parse_csv(text)
            state.mismatches += mismatches
        else:
            events, unparsed = _parse_jsonl(text)
        state.unparsed += unparsed
        for event in events:
            state.add(event, name)
    return {
        "kind": "official_fake_fill_v2",
        "available": True,
        "source": state.source or loaded[-1][0],
        "read_only": True,
        "counts": {
            "events": state.events,
            "by_type": {key: state.by_type[key] for key in sorted(state.by_type)},
            "header_row_mismatches": state.mismatches,
            "unparsed": state.unparsed,
        },
        "last_event_id": state.last_id,
        "last_event_time": state.last_time,
        "hash_chain_head": state.head,
        "realized_pnl_cum": state.pnl,
        "net_pnl_note": NET_PNL_NOTE,
        "fill_status": "OFFICIAL_V2",
        "redacted": True,
    }


class _State:
    def __init__(self) -> None:
        self.events = 0
        self.by_type: Counter[str] = Counter()
        self.mismatches = 0
        self.unparsed = 0
        self.last_id: str | None = None
        self.last_time: str | None = None
        self.head: str | None = None
        self.pnl: str | None = None
        self.source: str | None = None

    def add(self, mapped: dict[str, Any], source: str) -> None:
        self.events += 1
        self.source = source
        event_type = _event_type(mapped.get("event_type"))
        if event_type is not None:
            self.by_type[event_type] += 1
        self.last_id = _token(mapped.get("event_id"))
        self.last_time = _iso(mapped.get("event_time"))
        self.head = _hash(mapped.get("event_hash"))
        self.pnl = _pnl(mapped.get("realized_pnl_cum"))


def _canon_key(value: str) -> str | None:
    return ALIASES.get(value.strip().casefold())


def _has_event_field(mapped: Mapping[str, Any]) -> bool:
    for key in EVENT_FIELDS:
        value = mapped.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return True
    return False


def _positional(row: list[str]) -> dict[str, str] | None:
    if len(row) not in (6, 7):
        return None
    return {key: row[index] for index, key in enumerate(POSITIONAL[: len(row)])}


def _from_header(header: list[str], row: list[str]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for key, value in zip(header, row):
        canon = _canon_key(key)
        if canon and canon not in mapped:
            mapped[canon] = value
    return mapped


def _parse_jsonl(text: str) -> tuple[list[dict[str, Any]], int]:
    events: list[dict[str, Any]] = []
    unparsed = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith("{"):
            unparsed += 1
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            unparsed += 1
            continue
        if not isinstance(obj, dict):
            unparsed += 1
            continue
        mapped: dict[str, Any] = {}
        for key, value in obj.items():
            canon = _canon_key(str(key))
            if canon and canon not in mapped:
                mapped[canon] = value
        if not _has_event_field(mapped):
            unparsed += 1
            continue
        events.append(mapped)
    return events, unparsed


def _parse_csv(text: str) -> tuple[list[dict[str, Any]], int, int]:
    rows: list[list[str]] = []
    for row in csv.reader(io.StringIO(text)):
        if not row or all(not cell.strip() for cell in row):
            continue
        rows.append([cell.strip() for cell in row])
    if not rows:
        return [], 0, 0
    header: list[str] | None = None
    data = rows
    if any(_canon_key(cell) for cell in rows[0]):
        header = rows[0]
        data = rows[1:]
    events: list[dict[str, Any]] = []
    mismatches = 0
    unparsed = 0
    for row in data:
        if header is not None and len(row) != len(header):
            mismatches += 1
            mapped: dict[str, Any] | None = _positional(row)
        elif header is not None:
            mapped = _from_header(header, row)
        else:
            mapped = _positional(row)
        if not mapped or not _has_event_field(mapped):
            unparsed += 1
            continue
        events.append(mapped)
    return events, mismatches, unparsed


def _token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if TOKEN_RE.fullmatch(text):
        return text
    return None


def _hash(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if HASH_RE.fullmatch(text):
        return text
    return None


def _iso(value: Any) -> str | None:
    if isinstance(value, str) and ISO_RE.fullmatch(value.strip()):
        return value.strip()
    return None


def _event_type(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if EVENT_TYPE_RE.fullmatch(text):
        return text
    return None


def _pnl(value: Any) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        text = str(value)
    elif isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        return None
    if PNL_RE.fullmatch(text):
        return text
    return None
