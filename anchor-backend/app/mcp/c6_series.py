"""Read-only compact summary of the C6 pass-line series.

``get_ledger_summary`` attaches this block when
``ANCHOR_CONTROL_MCP_C6_SERIES_DIR`` is set. The block is a handful of
tokens: availability, row count, last row time, position, and scoring
status. Mark prices, funding rates, and row bodies are not returned.

The connector truncates near 2.6 KB, so this object stays small on purpose.
Opens are read-only and do not follow symlinks. Line A paths are rejected
and their bytes are not read.
"""

from __future__ import annotations

import csv
import io
import os
import re
import stat
from pathlib import Path
from typing import Any, Mapping

from app.mcp.inventory import LEDGER_MIRROR_DIR, OFFICIAL_LEDGER_DIR, OFFICIAL_LEDGER_DIR_PRIVATE
from app.mcp.sanitize import looks_sensitive_path


C6_SERIES_DIR_ENV = "ANCHOR_CONTROL_MCP_C6_SERIES_DIR"
EQUITY_NAME = "anchor_fake_fill_equity_v2_1_official.csv"
EQUITY_COLUMNS = (
    "schema_version",
    "timestamp_utc",
    "observation_id",
    "position",
    "realized_pnl",
    "unrealized_pnl",
    "net_liquidation_equity",
    "drawdown",
    "exposure",
    "cash_reserve",
    "active_notional",
    "mark_rule_id",
    "sample_class",
)
MAX_EQUITY_BYTES = 4 * 1024 * 1024
_LINE_A_ROOTS = (
    OFFICIAL_LEDGER_DIR,
    OFFICIAL_LEDGER_DIR_PRIVATE,
    LEDGER_MIRROR_DIR,
)
_LINE_A_MARKERS = ("affl-v2-official-ledger", "anchor-official-ledger")
_ALLOWED_C6_COMPONENTS = frozenset({"affl-v2-official-ledger-c6", "anchor-official-ledger-c6"})
_POSITIONS = frozenset({"FLAT", "LONG", "SHORT"})
_TOKEN = re.compile(r"^[A-Za-z0-9_.:-]{1,40}$")
_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


def _block(
    *,
    available: bool,
    rows: int = 0,
    last_row_time: str | None = None,
    position_state: str | None = None,
    scoring_status: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "available": available,
        "rows": rows,
        "last_row_time": last_row_time,
        "position_state": position_state,
        "scoring_status": scoring_status,
        "read_only": True,
    }
    if not available and reason is not None:
        payload["reason"] = reason
    return payload


def _line_a_component(part: str) -> bool:
    if part in _ALLOWED_C6_COMPONENTS:
        return False
    return any(marker in part for marker in _LINE_A_MARKERS)


def _sealed_line_a(path: Path) -> bool:
    text = str(path)
    if "/var/lib/private" in text:
        return True
    if any(_line_a_component(part) for part in path.parts):
        return True
    for root in _LINE_A_ROOTS:
        root_path = Path(root)
        if path == root_path:
            return True
        try:
            path.relative_to(root_path)
        except ValueError:
            continue
        else:
            return True
    return False


def _reject_dir(raw: str) -> str | None:
    if not raw or looks_sensitive_path(raw):
        return "c6_series_dir_rejected"
    candidate = Path(raw)
    if not candidate.is_absolute():
        return "c6_series_dir_rejected"
    try:
        info = os.lstat(candidate)
    except FileNotFoundError:
        return "c6_series_dir_missing"
    except OSError:
        return "c6_series_dir_rejected"
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        return "c6_series_dir_rejected"
    try:
        resolved = candidate.resolve()
    except OSError:
        return "c6_series_dir_rejected"
    if _sealed_line_a(resolved) or _sealed_line_a(candidate):
        return "c6_series_dir_rejected"
    return None


def _read_regular(path: Path, root: Path) -> bytes | None:
    try:
        if path.is_symlink():
            return None
        resolved = path.resolve()
        root_resolved = root.resolve()
        resolved.relative_to(root_resolved)
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
        if info.st_size > MAX_EQUITY_BYTES:
            return None
        chunks: list[bytes] = []
        remaining = MAX_EQUITY_BYTES
        while remaining > 0:
            blob = os.read(fd, min(65536, remaining))
            if not blob:
                break
            chunks.append(blob)
            remaining -= len(blob)
        if remaining == 0 and os.read(fd, 1):
            return None
        return b"".join(chunks)
    finally:
        os.close(fd)


def _token(value: str | None, allowed: frozenset[str] | None = None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if allowed is not None:
        return text if text in allowed else None
    if _TOKEN.fullmatch(text):
        return text
    return None


def _summarize_equity(blob: bytes) -> dict[str, Any]:
    try:
        text = blob.decode("utf-8")
    except UnicodeError:
        return _block(available=False, reason="c6_equity_unreadable")
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        return _block(available=False, reason="c6_equity_header_rejected")
    if tuple(header) != EQUITY_COLUMNS:
        return _block(available=False, reason="c6_equity_header_rejected")
    rows = 0
    last: list[str] | None = None
    for raw in reader:
        if not raw or raw == [""]:
            continue
        if len(raw) != len(EQUITY_COLUMNS):
            return _block(available=False, reason="c6_equity_row_rejected")
        rows += 1
        last = raw
    if last is None:
        return _block(available=True, rows=0)
    record = dict(zip(EQUITY_COLUMNS, last))
    when = record["timestamp_utc"].strip()
    last_row_time = when if _TIME.fullmatch(when) else None
    return _block(
        available=True,
        rows=rows,
        last_row_time=last_row_time,
        position_state=_token(record["position"], _POSITIONS),
        scoring_status=_token(record["sample_class"]),
    )


def read_c6_series(env: Mapping[str, str]) -> dict[str, Any]:
    """Summarize the configured C6 series directory. Never raises."""
    raw = (env.get(C6_SERIES_DIR_ENV) or "").strip()
    if not raw:
        return _block(available=False, reason="c6_series_dir_unset")
    reason = _reject_dir(raw)
    if reason is not None:
        return _block(available=False, reason=reason)
    root = Path(raw)
    equity = root / "out" / EQUITY_NAME
    blob = _read_regular(equity, root)
    if blob is None:
        if not equity.is_file() or equity.is_symlink():
            return _block(available=False, reason="c6_equity_not_found")
        return _block(available=False, reason="c6_equity_unreadable")
    summary = _summarize_equity(blob)
    # The compact block is the whole response contribution. Drop anything
    # that is not one of the fixed keys before it can leave the process.
    allowed = {"available", "rows", "last_row_time", "position_state", "scoring_status", "read_only", "reason"}
    return {key: summary[key] for key in summary if key in allowed}
