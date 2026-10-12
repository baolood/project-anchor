"""Official V2 fill rule and pending-row policy.

``resolve_fill_bar`` is the current fill rule: the fill is the first 1h bar
that opens after ``signal_available_at``. Live signals are published at
minute :05, so that bar opens on the following hour. The fill price is that
bar's open, and only after the bar has closed. Nothing in this module
rewrites or deletes an existing ledger line.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


PENDING_NEXT_BAR = "PENDING_NEXT_BAR"
BAR_NOT_YET_CLOSED = "BAR_NOT_YET_CLOSED"
DATA_GAP = "DATA_GAP"
FILL_BAR = timedelta(hours=1)
POLICY_ENV = "ANCHOR_OFFICIAL_LEDGER_PENDING_POLICY_EFFECTIVE_AT"
CANDLE_FETCH_UNIT = "anchor-candle-fetch.service"
LEDGER_UNIT = "anchor-official-ledger.service"
GENESIS_PREV = "0" * 64


class LedgerWriteError(Exception):
    """The observation was not appended. Existing ledger bytes stay as they were."""


def render_ledger_after_candle_drop_in() -> str:
    """Order the ledger oneshot after candle fetch. No permission settings."""
    return f"""[Unit]
After={CANDLE_FETCH_UNIT}
"""


def render_candle_success_drop_in() -> str:
    """Start the ledger oneshot when candle fetch completes successfully."""
    return f"""[Unit]
OnSuccess={LEDGER_UNIT}
"""


def render_pending_policy_drop_in(effective_at: str) -> str:
    """Record the explicit instant at which the one-pending policy starts."""
    text = effective_at.strip()
    parse_time(text)
    return f"""[Service]
Environment={POLICY_ENV}={text}
"""


def resolve_fill_bar(signal_available_at: datetime) -> datetime:
    """Return the open time of the first 1h bar that opens after the signal.

    Hour bars open at minute 00. A signal at 10:05 is after the 10:00 open,
    so the fill bar opens at 11:00. The open at exactly ``signal_available_at``
    is not after the signal, so an exact hour moves to the next hour.
    """
    instant = _as_utc(signal_available_at).replace(microsecond=0)
    opened = instant.replace(minute=0, second=0, microsecond=0)
    if opened <= instant:
        opened += FILL_BAR
    return opened


def pending_reason(fill_bar_open: datetime, now: datetime, candle_present: bool) -> str | None:
    """Classify why a fill cannot be recorded, or return None when it can.

    ``BAR_NOT_YET_CLOSED`` means ``fill_bar_open + 1h > now``. The candle
    dataset does not contain that bar until it closes, so its open is not
    read yet. ``DATA_GAP`` means the bar should already be closed and the
    candle is still absent. A present candle is not a reason to fill early.
    """
    if _as_utc(fill_bar_open) + FILL_BAR > _as_utc(now):
        return BAR_NOT_YET_CLOSED
    if not candle_present:
        return DATA_GAP
    return None


def planned_fill(signal: Mapping[str, Any], candles: Sequence[Mapping[str, Any]], now: datetime) -> dict[str, Any]:
    """Apply the current fill rule. This is the replay reference for price and time."""
    available = parse_time(str(signal["signal_available_at"]))
    fill_open = resolve_fill_bar(available)
    candle = _candle_at(candles, fill_open)
    reason = pending_reason(fill_open, now, candle is not None)
    planned: dict[str, Any] = {
        "signal_available_at": _iso(available),
        "fill_time_utc": _iso(fill_open),
        "pending_reason": reason,
    }
    candle_open = signal.get("signal_candle_open_utc")
    if isinstance(candle_open, str) and candle_open.strip():
        planned["signal_candle_open_utc"] = _iso(parse_time(candle_open))
    if reason is None:
        if candle is None:
            raise LedgerWriteError("closed bar has no candle")
        planned["fill_price"] = _open_price(candle)
        planned["event_type"] = _fill_event_type(signal)
    else:
        planned["event_type"] = PENDING_NEXT_BAR
    return planned


def policy_active(now: datetime, effective_at: datetime | None) -> bool:
    """The one-pending policy starts at ``effective_at`` and does not look backward."""
    if effective_at is None:
        return False
    return _as_utc(now) >= _as_utc(effective_at)


def commit_observation(
    ledger_path: str | Path,
    run_log_path: str | Path,
    *,
    signal: Mapping[str, Any],
    candles: Sequence[Mapping[str, Any]],
    now: datetime,
    effective_at: datetime | None,
    attempts: int = 4,
) -> list[dict[str, Any]]:
    """Append the observation. Existing ledger bytes are not rewritten or deleted.

    Before ``effective_at``, each retry appends a ledger row, which is the
    current behavior. At and after ``effective_at``, one observation appends
    at most one ``PENDING_NEXT_BAR`` row. Further retries go to ``run_log_path``.
    Fill price and fill time always come from ``planned_fill``.
    """
    if attempts < 1:
        raise LedgerWriteError("attempts must be at least 1")
    plan = planned_fill(signal, candles, now)
    active = policy_active(now, effective_at)
    if plan["event_type"] != PENDING_NEXT_BAR:
        rows = [_ledger_row(plan, include_reason=False)]
        log_rows: list[dict[str, Any]] = []
    elif active:
        rows = [_ledger_row(plan, include_reason=True)]
        log_rows = [_retry_log(plan, attempt) for attempt in range(2, attempts + 1)]
    else:
        rows = [_ledger_row(plan, include_reason=False) for _ in range(attempts)]
        log_rows = []
    _append_ledger(Path(ledger_path), rows)
    if log_rows:
        _append_log(Path(run_log_path), log_rows)
    return rows


def parse_time(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise LedgerWriteError("timestamp is not valid") from exc
    return _as_utc(parsed)


def _ledger_row(plan: Mapping[str, Any], *, include_reason: bool) -> dict[str, Any]:
    row: dict[str, Any] = {
        "event_type": plan["event_type"],
        "signal_available_at": plan["signal_available_at"],
        "fill_time_utc": plan["fill_time_utc"],
    }
    if "signal_candle_open_utc" in plan:
        row["signal_candle_open_utc"] = plan["signal_candle_open_utc"]
    if plan["event_type"] != PENDING_NEXT_BAR:
        row["fill_price"] = plan["fill_price"]
    elif include_reason:
        row["pending_reason"] = plan["pending_reason"]
    return row


def _retry_log(plan: Mapping[str, Any], attempt: int) -> dict[str, Any]:
    return {
        "attempt": attempt,
        "event_type": PENDING_NEXT_BAR,
        "pending_reason": plan["pending_reason"],
        "signal_available_at": plan["signal_available_at"],
        "fill_time_utc": plan["fill_time_utc"],
        "logged_to": "run_log",
    }


def _append_ledger(path: Path, rows: list[dict[str, Any]]) -> None:
    existing = _read_existing(path)
    previous = _last_hash(existing)
    encoded: list[str] = []
    for index, row in enumerate(rows, start=_line_count(existing) + 1):
        body = dict(row)
        body["ledger_event_id"] = f"le-{index:06d}"
        body["prev_hash"] = previous
        body["row_hash"] = _chain_hash(previous, body)
        previous = body["row_hash"]
        encoded.append(json.dumps(body, sort_keys=True, separators=(",", ":")))
    _append_lines(path, encoded)


def _append_log(path: Path, rows: list[dict[str, Any]]) -> None:
    _append_lines(path, [json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows])


def _append_lines(path: Path, lines: list[str]) -> None:
    if not lines:
        return
    if path.exists() and path.is_symlink():
        raise LedgerWriteError("refusing to append through a symlink")
    payload = ("".join(line + "\n" for line in lines)).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o644)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise LedgerWriteError("ledger path is not a regular file")
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _read_existing(path: Path) -> bytes:
    if not path.exists():
        return b""
    if path.is_symlink() or not path.is_file():
        raise LedgerWriteError("ledger path is not a regular file")
    return path.read_bytes()


def _line_count(existing: bytes) -> int:
    if not existing:
        return 0
    text = existing.decode("utf-8")
    return len([line for line in text.splitlines() if line.strip()])


def _last_hash(existing: bytes) -> str:
    if not existing:
        return GENESIS_PREV
    for line in reversed(existing.decode("utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LedgerWriteError("existing ledger line is not json") from exc
        value = obj.get("row_hash")
        if isinstance(value, str) and value:
            return value
        return GENESIS_PREV
    return GENESIS_PREV


def _chain_hash(previous: str, body: Mapping[str, Any]) -> str:
    material = {key: value for key, value in body.items() if key != "row_hash"}
    payload = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{previous}\n{payload}".encode("utf-8")).hexdigest()


def _candle_at(candles: Sequence[Mapping[str, Any]], fill_open: datetime) -> Mapping[str, Any] | None:
    target = _iso(fill_open)
    for candle in candles:
        opened = candle.get("open_time")
        if not isinstance(opened, str):
            continue
        if _iso(parse_time(opened)) == target:
            return candle
    return None


def _open_price(candle: Mapping[str, Any]) -> str:
    value = candle.get("open")
    if not isinstance(value, str) or not value.strip():
        raise LedgerWriteError("candle open price is missing")
    return value


def _fill_event_type(signal: Mapping[str, Any]) -> str:
    value = signal.get("fill_event_type")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "OPEN"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return _as_utc(value).replace(microsecond=0).isoformat().replace("+00:00", "Z")
