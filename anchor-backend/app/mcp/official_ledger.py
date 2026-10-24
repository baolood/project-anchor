"""Read-only Official V2 fake-fill ledger summary.

The host writer keeps this ledger outside the MCP reports directory. The
MCP reads only the root-owned mirror at ``/var/lib/anchor-ledger-mirror``.
It checks the ``.sha256`` sidecar before summarizing and reports how old
``copied_at`` is. It does not open the ledger StateDirectory and does not
write the mirror or the source.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import stat
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.mcp.inventory import LEDGER_MIRROR_DIR
from app.mcp.ledger_run_index import BOUNDARY_NAME, MAX_RUN_SEQ, write_times_for_rows
from app.mcp.sanitize import looks_sensitive_path


LEDGER_DIR_ENV = "ANCHOR_CONTROL_MCP_LEDGER_DIR"
ALLOWLISTED_LEDGER_DIRS = (LEDGER_MIRROR_DIR,)
MIRROR_STALE_AFTER_SEC = 90 * 60
SHA256_RE = re.compile(r"^([0-9a-fA-F]{64})(?:\s+\S+)?\s*$")
LEDGER_NAME_RE = re.compile(
    r"^anchor_fake_fill_ledger_v2_official[A-Za-z0-9._-]*\.(jsonl|csv)$"
)
TOKEN_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")
HASH_RE = re.compile(r"^[A-Za-z0-9]{1,128}$")
TIME_RE = re.compile(
    r"^(?P<body>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?)"
    r"(?P<tz>Z|[+-]\d{2}:\d{2})?$"
)
EVENT_TYPE_RE = re.compile(r"^[A-Za-z0-9_]{1,40}$")
PNL_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
MAX_LEDGER_BYTES = 64 * 1024 * 1024
MAX_LEDGER_FILES = 32
EVENT_FIELDS = (
    "event_id",
    "event_time",
    "signal_available_at",
    "fill_time_utc",
    "signal_candle_open_utc",
    "event_type",
    "event_hash",
    "realized_pnl_cum",
)
# Latest timestamp on the last row wins. Equal timestamps use this order.
LAST_EVENT_TIME_FIELDS = (
    "signal_available_at",
    "fill_time_utc",
    "signal_candle_open_utc",
    "event_time",
)
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
    "ledger_event_id": "event_id",
    "event_time": "event_time",
    "time": "event_time",
    "timestamp": "event_time",
    "ts": "event_time",
    "signal_available_at": "signal_available_at",
    "fill_time_utc": "fill_time_utc",
    "signal_candle_open_utc": "signal_candle_open_utc",
    "event_type": "event_type",
    "type": "event_type",
    "kind": "event_type",
    "prev_hash": "prev_hash",
    "previous_hash": "prev_hash",
    "event_hash": "event_hash",
    "hash": "event_hash",
    "record_hash": "event_hash",
    "chain_hash": "event_hash",
    "row_hash": "event_hash",
    "realized_pnl_cum": "realized_pnl_cum",
    "realized_pnl_cumulative": "realized_pnl_cum",
    "net_pnl": "net_pnl",
    "observation_id": "observation_id",
}
PENDING_EVENT = "PENDING_NEXT_BAR"
BAR_NOT_YET_CLOSED = "BAR_NOT_YET_CLOSED"
DATA_GAP = "DATA_GAP"
IN_FLIGHT = "IN_FLIGHT"
PRE_INDEX = "PRE_INDEX"
FILL_BAR = timedelta(hours=1)
# A later row of one of these types, with fill_time_utc, resolves the fill bar.
RESOLVING_EVENTS = frozenset({"OPEN", "REVERSE_ENTRY", "REVERSE_EXIT", "FLAT_EXIT", "NO_FILL"})
NET_PNL_NOTE = (
    "Per-exit NET_PNL rows exclude entry costs. "
    "realized_pnl_cum is the ledger cumulative figure, not an exchange cash balance."
)


class _TooLarge(Exception):
    """Combined ledger bytes exceeded the read cap."""


def official_ledger_configured(env: Mapping[str, str]) -> bool:
    return bool((env.get(LEDGER_DIR_ENV) or "").strip())


def read_official_ledger(
    env: Mapping[str, str],
    *,
    allowlist: tuple[str, ...] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Summarize the mirrored Official V2 ledger. `allowlist` and `now` are for tests only."""
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
        names = sorted(os.listdir(resolved))
    except PermissionError:
        return _unavailable("ledger_unreadable")
    except OSError:
        return _unavailable("ledger_unreadable")
    matched = [name for name in names if LEDGER_NAME_RE.fullmatch(name)]
    if len(matched) > MAX_LEDGER_FILES:
        return _unavailable("official_ledger_too_many_files")
    loaded, failure = _load_files(resolved, matched)
    if failure is not None:
        return _unavailable(failure)
    if not loaded:
        return _unavailable("official_ledger_not_found")
    checked_at = now or datetime.now(timezone.utc)
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    failure = _verify_sha256(resolved, loaded)
    if failure is not None:
        return _unavailable(failure)
    summary = _summarize(loaded, boundaries=_load_run_boundaries(resolved), now=checked_at)
    summary.update(_mirror_fields(resolved, loaded, summary.get("source"), checked_at))
    return summary


def _unavailable(reason: str) -> dict[str, Any]:
    return {
        "kind": "official_fake_fill_v2",
        "available": False,
        "reason": reason,
        "read_only": True,
        "redacted": True,
    }


def _verify_sha256(root: Path, loaded: list[tuple[str, bytes]]) -> str | None:
    for name, blob in loaded:
        reason = _check_sha256(root, name, blob)
        if reason is not None:
            return reason
    return None


def _mirror_fields(
    root: Path,
    loaded: list[tuple[str, bytes]],
    source_name: Any,
    now: datetime,
) -> dict[str, Any]:
    by_name = {name: blob for name, blob in loaded}
    name = source_name if isinstance(source_name, str) and source_name in by_name else loaded[-1][0]
    meta = _read_meta(root, name)
    age_sec: int | None = None
    copied_at: str | None = None
    stale = True
    source_mtime: str | None = None
    source_size: int | None = None
    if meta is not None:
        parsed_mtime = _parse_time(meta.get("source_mtime"))
        source_mtime = parsed_mtime[1] if parsed_mtime is not None else None
        size = meta.get("source_size")
        source_size = size if isinstance(size, int) and not isinstance(size, bool) else None
        parsed = _parse_time(meta.get("copied_at"))
        if parsed is not None:
            copied_at = parsed[1]
            age_sec = int((now - parsed[0]).total_seconds())
            stale = age_sec > MIRROR_STALE_AFTER_SEC
        if source_size is not None and source_size != len(by_name[name]):
            stale = True
    return {
        "mirror_copied_at": copied_at,
        "mirror_age_sec": age_sec,
        "mirror_stale": stale,
        "mirror_stale_after_sec": MIRROR_STALE_AFTER_SEC,
        "mirror_source_mtime": source_mtime,
        "mirror_source_size": source_size,
        "mirror_sha256_ok": True,
    }


def _check_sha256(root: Path, name: str, blob: bytes) -> str | None:
    path = root / f"{name}.sha256"
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return "ledger_mirror_hash_missing"
    except OSError:
        return "ledger_mirror_hash_rejected"
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        return "ledger_mirror_hash_rejected"
    try:
        text = _read_bytes(path).decode("ascii")
    except (OSError, _TooLarge, UnicodeError):
        return "ledger_mirror_hash_rejected"
    line = next((item.strip() for item in text.splitlines() if item.strip()), "")
    match = SHA256_RE.fullmatch(line)
    if match is None:
        return "ledger_mirror_hash_rejected"
    actual = hashlib.sha256(blob).hexdigest()
    if match.group(1).lower() != actual:
        return "ledger_mirror_hash_mismatch"
    return None


def _read_meta(root: Path, name: str) -> dict[str, Any] | None:
    path = root / f"{name}.meta.json"
    try:
        info = os.lstat(path)
    except OSError:
        return None
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_size > 65536:
        return None
    try:
        payload = json.loads(_read_bytes(path).decode("utf-8"))
    except (OSError, _TooLarge, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


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


def _load_run_boundaries(root: Path) -> list[dict[str, Any]] | None:
    """Read the mirror's run-boundary index. Missing or rejected means unlabeled pending counts."""
    path = root / BOUNDARY_NAME
    try:
        info = os.lstat(path)
    except OSError:
        return None
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        return None
    try:
        blob = _read_bytes(path)
    except (OSError, _TooLarge):
        return None
    if _check_sha256(root, BOUNDARY_NAME, blob) is not None:
        return None
    boundaries: list[dict[str, Any]] = []
    for line in blob.decode("utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            return None
        if not isinstance(obj, dict):
            return None
        run = obj.get("run")
        seq = obj.get("run_seq")
        at = obj.get("committed_at")
        end = obj.get("ledger_events")
        before = obj.get("ledger_events_before")
        if not isinstance(run, str) or not isinstance(at, str) or not at.strip():
            return None
        if type(seq) is not int or type(end) is not int or type(before) is not int:
            return None
        if seq < 1 or seq > MAX_RUN_SEQ or f"run-{seq:06d}" != run:
            return None
        if before < 0 or end < before:
            return None
        boundaries.append(
            {
                "run": run,
                "run_seq": seq,
                "committed_at": at.strip(),
                "ledger_events_before": before,
                "ledger_events": end,
            }
        )
    if not _boundary_chain(boundaries):
        return None
    return boundaries


def _boundary_chain(boundaries: Sequence[Mapping[str, Any]]) -> bool:
    """True when run_seq is 1..N and each later span starts where the previous one ended.

    Run 1 may start after a pre-index offset. That offset is
    ``ledger_events_before`` on the first boundary.
    """
    previous_seq = 0
    previous_end: int | None = None
    for boundary in boundaries:
        seq = boundary["run_seq"]
        before = boundary["ledger_events_before"]
        end = boundary["ledger_events"]
        if seq != previous_seq + 1:
            return False
        if previous_end is None:
            if before < 0:
                return False
        elif before != previous_end:
            return False
        previous_seq = seq
        previous_end = end
    return True


def _summarize(
    loaded: list[tuple[str, bytes]],
    *,
    boundaries: list[dict[str, Any]] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
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
        "last_event_time_field": state.last_time_field,
        "hash_chain_head": state.head,
        "realized_pnl_cum": state.pnl,
        "net_pnl_note": NET_PNL_NOTE,
        "fill_status": "OFFICIAL_V2",
        "redacted": True,
        "pending_observations": pending_observation_summary(state.rows, boundaries, now),
    }


class _State:
    def __init__(self) -> None:
        self.events = 0
        self.by_type: Counter[str] = Counter()
        self.mismatches = 0
        self.unparsed = 0
        self.last_id: str | None = None
        self.last_time: str | None = None
        self.last_time_field: str | None = None
        self.head: str | None = None
        self.pnl: str | None = None
        self.source: str | None = None
        self.rows: list[dict[str, Any]] = []

    def add(self, mapped: dict[str, Any], source: str) -> None:
        self.events += 1
        self.source = source
        event_type = _event_type(mapped.get("event_type"))
        if event_type is not None:
            self.by_type[event_type] += 1
        self.last_id = _token(mapped.get("event_id"))
        self.last_time, self.last_time_field = _latest_time(mapped)
        self.head = _hash(mapped.get("event_hash"))
        self.pnl = _pnl(mapped.get("realized_pnl_cum"))
        self.rows.append(mapped)


def pending_observation_summary(
    events: Sequence[Mapping[str, Any]],
    boundaries: Sequence[Mapping[str, Any]] | None,
    now: datetime | None,
) -> dict[str, int]:
    """Collapse repeated PENDING_NEXT_BAR rows. Does not write the ledger.

    Write time is the committed ``at`` of the run that appended the row.
    A ledger field such as ``event_time`` is not that time. Rows at or below
    run 1's before-snapshot offset are ``PRE_INDEX`` and stay unlabeled.
    When some other pending row cannot be placed in a run, the result has
    only ``raw_rows``, ``observations``, and ``runs_waited``.
    """
    writes = None
    pre_index_ids: set[str] | None = None
    if boundaries is not None:
        placed = write_times_for_rows(events, boundaries)
        if placed is not None:
            writes, pre_index_ids = placed
    return classify_pending_observations(
        events,
        write_times=writes,
        pre_index_ids=pre_index_ids,
        now=now,
    )


def classify_pending_observations(
    events: Sequence[Mapping[str, Any]],
    *,
    write_times: Mapping[str, tuple[str, str]] | None = None,
    pre_index_ids: set[str] | None = None,
    now: datetime | None = None,
) -> dict[str, int]:
    """Collapse repeated PENDING_NEXT_BAR rows for one observation into one count.

    ``write_times`` maps event id to ``(committed_at, run)``. ``pre_index_ids``
    are pending rows at or below run 1's before-snapshot offset. Those
    observations are ``PRE_INDEX`` and are not given a time label. Other
    labels are omitted when a pending row has no entry. ``IN_FLIGHT`` is an
    unresolved observation whose fill-bar close is still after ``now``.
    """
    checked = now or datetime.now(timezone.utc)
    if checked.tzinfo is None:
        checked = checked.replace(tzinfo=timezone.utc)
    groups: dict[tuple[Any, ...], dict[str, Any]] = {}
    order: list[tuple[Any, ...]] = []
    for index, event in enumerate(events):
        event_type = event.get("event_type")
        if event_type != PENDING_EVENT and event_type not in RESOLVING_EVENTS:
            continue
        key = _observation_key(event, index)
        group = groups.get(key)
        if group is None:
            group = {
                "raw": 0,
                "runs": set(),
                "earliest_write": None,
                "saw_pending": False,
                "fill_open": None,
                "signal": None,
                "unplaced": False,
                "pre_rows": 0,
            }
            groups[key] = group
            order.append(key)
        if event_type == PENDING_EVENT:
            group["raw"] += 1
            group["saw_pending"] = True
            signal = _parse_time(event.get("signal_available_at"))
            if signal is not None and group["signal"] is None:
                group["signal"] = signal[0]
            event_id = event.get("event_id")
            text_id = event_id.strip() if isinstance(event_id, str) else ""
            if pre_index_ids is not None and text_id in pre_index_ids:
                group["pre_rows"] += 1
            else:
                placed = _placed_write(event, write_times)
                if placed is None:
                    group["unplaced"] = True
                else:
                    written, run = placed
                    group["runs"].add(run)
                    earliest = group["earliest_write"]
                    if earliest is None or written < earliest:
                        group["earliest_write"] = written
        elif group["saw_pending"] and group["fill_open"] is None:
            parsed = _parse_time(event.get("fill_time_utc"))
            if parsed is not None:
                group["fill_open"] = parsed[0]
    raw_rows = 0
    observations = 0
    runs_waited = 0
    not_yet_closed = 0
    data_gap = 0
    in_flight = 0
    pre_index = 0
    unlabeled = write_times is None
    for key in order:
        group = groups[key]
        if not group["saw_pending"]:
            continue
        raw_rows += group["raw"]
        observations += 1
        if group["pre_rows"] == group["raw"] and not group["unplaced"] and not group["runs"]:
            pre_index += 1
            continue
        if group["unplaced"] or not group["runs"]:
            unlabeled = True
        runs_waited += len(group["runs"]) if group["runs"] else group["raw"]
        kind = _pending_label(group, checked)
        if kind == BAR_NOT_YET_CLOSED:
            not_yet_closed += 1
        elif kind == IN_FLIGHT:
            in_flight += 1
        elif kind == DATA_GAP:
            data_gap += 1
        else:
            unlabeled = True
    if observations == 0:
        return {
            "raw_rows": 0,
            "observations": 0,
            "runs_waited": 0,
            PRE_INDEX: 0,
            BAR_NOT_YET_CLOSED: 0,
            DATA_GAP: 0,
            IN_FLIGHT: 0,
        }
    if unlabeled:
        return {
            "raw_rows": raw_rows,
            "observations": observations,
            "runs_waited": raw_rows,
        }
    return {
        "raw_rows": raw_rows,
        "observations": observations,
        "runs_waited": runs_waited,
        PRE_INDEX: pre_index,
        BAR_NOT_YET_CLOSED: not_yet_closed,
        DATA_GAP: data_gap,
        IN_FLIGHT: in_flight,
    }


def _placed_write(
    event: Mapping[str, Any],
    write_times: Mapping[str, tuple[str, str]] | None,
) -> tuple[datetime, str] | None:
    if write_times is None:
        return None
    event_id = event.get("event_id")
    if not isinstance(event_id, str):
        return None
    placed = write_times.get(event_id.strip())
    if placed is None:
        return None
    parsed = _parse_time(placed[0])
    if parsed is None:
        return None
    return parsed[0], placed[1]


def _pending_label(group: Mapping[str, Any], now: datetime) -> str | None:
    written = group["earliest_write"]
    fill_open = group["fill_open"]
    if fill_open is None:
        signal = group["signal"]
        if signal is None or written is None:
            return None
        close = _fill_bar_open(signal) + FILL_BAR
        if now < close:
            return IN_FLIGHT
        return DATA_GAP
    if written is None:
        return None
    if written < fill_open + FILL_BAR:
        return BAR_NOT_YET_CLOSED
    return DATA_GAP


def _fill_bar_open(signal: datetime) -> datetime:
    """First 1h bar that opens strictly after ``signal``. 10:05 → 11:00; 11:00 → 12:00."""
    floored = signal.replace(minute=0, second=0, microsecond=0)
    return floored + FILL_BAR


def _observation_key(event: Mapping[str, Any], index: int) -> tuple[Any, ...]:
    observation = event.get("observation_id")
    if isinstance(observation, str):
        text = observation.strip()
        if TOKEN_RE.fullmatch(text):
            return ("observation", text)
    signal = event.get("signal_available_at")
    candle = event.get("signal_candle_open_utc")
    if isinstance(signal, str) and isinstance(candle, str) and signal.strip() and candle.strip():
        return ("signal", signal.strip(), candle.strip())
    return ("row", index)


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


def _parse_time(value: Any) -> tuple[datetime, str] | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    match = TIME_RE.fullmatch(text)
    if match is None:
        return None
    body = match.group("body").replace(" ", "T")
    tz = match.group("tz")
    suffix = "+00:00" if tz is None or tz == "Z" else tz
    try:
        parsed = datetime.fromisoformat(body + suffix)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed, text


def _latest_time(mapped: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """Pick the latest recognized time on this row and name the field used."""
    best_at: datetime | None = None
    best_text: str | None = None
    best_field: str | None = None
    for field in LAST_EVENT_TIME_FIELDS:
        parsed = _parse_time(mapped.get(field))
        if parsed is None:
            continue
        parsed_at, text = parsed
        # Field order is the tie-break, so an equal timestamp does not replace.
        if best_at is None or parsed_at > best_at:
            best_at = parsed_at
            best_text = text
            best_field = field
    return best_text, best_field


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
