"""Join Official V2 pending rows to the ledger run that appended them.

Live ledger rows have no write-time field. The append time is the ``at``
value on a committed line in ``<ledger root>/events.jsonl``. A host line is::

    {"at":"2026-10-12T23:10:01.432083+00:00","commits":366,"event":"committed","ledger_events":1015,"run_seq":70,"source_lines":370}

``ledger_events`` is the cumulative ledger-row count after that run. Run N
owns ledger lines ``(ledger_events of run N-1, ledger_events of run N]``.
Run 1 owns ``(0, ledger_events]``. ``run_seq`` is the run number. This
module does not write the ledger and does not invent rows.
"""

from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence


EVENTS_NAME = "events.jsonl"
BOUNDARY_NAME = "run-boundaries.jsonl"
RUN_DIR_RE = re.compile(r"^run-(?P<seq>\d{6})$")
PENDING_EVENT = "PENDING_NEXT_BAR"
MAX_RUN_SEQ = 999999
_ID_KEYS = ("ledger_event_id", "event_id")


def parse_committed_runs(text: str) -> list[dict[str, Any]]:
    """Return committed runs from an ``events.jsonl`` body, in file order.

    A line counts only when ``event`` is ``committed``, ``at`` is a
    non-empty string, ``run_seq`` is an int, and ``ledger_events`` is an
    int. ``run_index`` and ``round_index`` are not read.
    """
    found: list[dict[str, Any]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict) or obj.get("event") != "committed":
            continue
        seq = _whole_number(obj.get("run_seq"))
        events = _whole_number(obj.get("ledger_events"))
        at = obj.get("at")
        if seq is None or events is None or not isinstance(at, str) or not at.strip():
            continue
        if seq < 1 or seq > MAX_RUN_SEQ:
            continue
        found.append(
            {
                "run_seq": seq,
                "run": f"run-{seq:06d}",
                "committed_at": at.strip(),
                "ledger_events": events,
            }
        )
    return found


def boundaries_from_commits(commits: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]] | None:
    """Return line spans, or None when the committed lines are not a usable index.

    A usable index is ``run_seq`` 1..N with no gaps or duplicates, and
    ``ledger_events`` never decreases. Run 1 starts at 0. A file whose first
    committed ``run_seq`` is not 1 cannot name ``ledger_events`` of run 0.
    """
    if not commits:
        return []
    boundaries: list[dict[str, Any]] = []
    previous_seq = 0
    previous_events = 0
    for commit in commits:
        seq = commit.get("run_seq")
        end = commit.get("ledger_events")
        at = commit.get("committed_at")
        run = commit.get("run")
        if type(seq) is not int or type(end) is not int or not isinstance(at, str) or not isinstance(run, str):
            return None
        if seq != previous_seq + 1 or seq > MAX_RUN_SEQ or run != f"run-{seq:06d}":
            return None
        if end < previous_events:
            return None
        boundaries.append(
            {
                "run": run,
                "run_seq": seq,
                "committed_at": at,
                "ledger_events_before": previous_events,
                "ledger_events": end,
            }
        )
        previous_seq = seq
        previous_events = end
    return boundaries


def last_event_id_from_snapshot(blob: bytes) -> tuple[bool, str | None]:
    """Return ``(ok, ledger_event_id)`` from the last line of a before-snapshot.

    An empty snapshot is ``(True, None)``. A tail that is not one JSON object,
    or an object with no id, is ``(False, None)``.
    """
    if not blob.strip():
        return True, None
    lines = blob.splitlines()
    if not lines:
        return True, None
    try:
        obj = json.loads(lines[-1].decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return False, None
    if not isinstance(obj, dict):
        return False, None
    event_id = _row_event_id(obj)
    if event_id is None:
        return False, None
    return True, event_id


def ledger_line_ids(blob: bytes) -> list[str | None] | None:
    """Return one id per non-empty JSON object line, in order.

    ``None`` as the list means a non-empty line is not one JSON object, so
    the caller must not treat the file as a line index. A row with no id is
    an entry of ``None`` inside the list.
    """
    try:
        text = blob.decode("utf-8-sig")
    except UnicodeError:
        return None
    ids: list[str | None] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            return None
        if not isinstance(obj, dict):
            return None
        ids.append(_row_event_id(obj))
    return ids


def snapshot_matches(expected_last_id: str | None, blob: bytes) -> bool:
    """A before-snapshot matches when its last id is the previous run's last id."""
    ok, found = last_event_id_from_snapshot(blob)
    return ok and found == expected_last_id


def write_times_for_rows(
    rows: Sequence[Mapping[str, Any]],
    boundaries: Sequence[Mapping[str, Any]],
) -> dict[str, tuple[str, str]] | None:
    """Map each pending row's event id to ``(committed_at, run)``.

    Line numbers are 1-based positions in ``rows``. Run N owns
    ``(ledger_events_before, ledger_events]``. ``None`` means a pending row
    cannot be placed, so the caller must not label it.
    """
    if not boundaries:
        return None if _has_pending(rows) else {}
    spans: list[tuple[int, int, Mapping[str, Any]]] = []
    previous_end = 0
    previous_seq = 0
    for boundary in boundaries:
        start = boundary.get("ledger_events_before")
        end = boundary.get("ledger_events")
        seq = boundary.get("run_seq")
        if type(start) is not int or type(end) is not int or type(seq) is not int:
            return None
        if seq != previous_seq + 1 or start != previous_end or end < start:
            return None
        spans.append((start, end, boundary))
        previous_end = end
        previous_seq = seq
    writes: dict[str, tuple[str, str]] = {}
    for index, row in enumerate(rows, start=1):
        if row.get("event_type") != PENDING_EVENT:
            continue
        event_id = _event_id(row)
        if event_id is None or event_id in writes:
            return None
        owner = _span_owner(spans, index)
        if owner is None:
            return None
        at = owner.get("committed_at")
        run = owner.get("run")
        if not isinstance(at, str) or not isinstance(run, str):
            return None
        writes[event_id] = (at, run)
    return writes


def _whole_number(value: Any) -> int | None:
    if type(value) is not int:
        return None
    return value


def _row_event_id(obj: Mapping[str, Any]) -> str | None:
    for key in _ID_KEYS:
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _event_id(row: Mapping[str, Any]) -> str | None:
    value = row.get("event_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _span_owner(
    spans: Sequence[tuple[int, int, Mapping[str, Any]]],
    index: int,
) -> Mapping[str, Any] | None:
    for start, end, boundary in spans:
        if start < index <= end:
            return boundary
    return None


def _has_pending(rows: Sequence[Mapping[str, Any]]) -> bool:
    return any(row.get("event_type") == PENDING_EVENT for row in rows)
