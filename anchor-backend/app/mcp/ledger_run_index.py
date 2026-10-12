"""Join Official V2 pending rows to the ledger run that appended them.

Live ledger rows have no write-time field. The append time is the ``at``
value on a committed line in ``events.jsonl``, matched to
``runs/run-NNNNNN/before/`` by run number.

``simulation/d5/original/cloud-package/cloud_loop.py`` ``event()`` writes
``events.jsonl`` as one JSON object per line (``sort_keys=True``) with
``at``, ``event``, and the extra fields. A finished generation calls
``event(root, "committed", round_index=..., round_id=..., next_due=...,
status=...)``. The host ledger root uses ``runs/run-NNNNNN`` (six digits)
and keeps the pre-run ledger under ``before/``. This module does not write
either tree.
"""

from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence


EVENTS_NAME = "events.jsonl"
BOUNDARY_NAME = "run-boundaries.jsonl"
RUN_DIR_RE = re.compile(r"^run-(?P<index>\d{6})$")
PENDING_EVENT = "PENDING_NEXT_BAR"
MAX_RUN_INDEX = 999999


def parse_committed_runs(text: str) -> list[dict[str, Any]]:
    """Return committed runs from an ``events.jsonl`` body, earliest line first.

    A line counts only when ``event`` is ``committed`` and ``at`` is a string.
    The run number is ``run_index`` when that key is present, otherwise
    ``round_index``. The first committed line for a number wins.
    """
    found: dict[int, str] = {}
    order: list[int] = []
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
        index = _run_index(obj)
        at = obj.get("at")
        if index is None or not isinstance(at, str) or not at.strip():
            continue
        if index not in found:
            found[index] = at.strip()
            order.append(index)
    return [
        {"run_index": index, "run": f"run-{index:06d}", "committed_at": found[index]}
        for index in order
    ]


def last_event_id_from_snapshot(blob: bytes) -> tuple[bool, str | None]:
    """Return ``(ok, ledger_event_id)`` from the last line of a before-snapshot.

    An empty snapshot is ``(True, None)``. A tail that is not one JSON object
    is ``(False, None)``.
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
    for key in ("ledger_event_id", "event_id"):
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return True, value.strip()
    return False, None


def build_boundaries(
    commits: Sequence[Mapping[str, Any]],
    tails: Mapping[str, str | None],
) -> list[dict[str, Any]]:
    """Keep committed runs whose ``run-NNNNNN`` directory had a readable before-snapshot."""
    boundaries: list[dict[str, Any]] = []
    for commit in commits:
        name = commit.get("run")
        if not isinstance(name, str) or name not in tails:
            continue
        index = commit.get("run_index")
        at = commit.get("committed_at")
        if type(index) is not int or not isinstance(at, str):
            continue
        boundaries.append(
            {
                "run": name,
                "run_index": index,
                "committed_at": at,
                "last_ledger_event_id_before": tails[name],
            }
        )
    boundaries.sort(key=lambda item: item["run_index"])
    return boundaries


def write_times_for_rows(
    rows: Sequence[Mapping[str, Any]],
    boundaries: Sequence[Mapping[str, Any]],
) -> dict[str, tuple[str, str]] | None:
    """Map each pending row's event id to ``(committed_at, run)``.

    ``None`` means a pending row cannot be placed in a run, so the caller
    must not label ``BAR_NOT_YET_CLOSED`` or ``DATA_GAP``.
    """
    if not boundaries:
        return None if _has_pending(rows) else {}
    ids: list[str | None] = []
    for row in rows:
        ids.append(_event_id(row))
    spans: list[tuple[int, int, Mapping[str, Any]]] = []
    ordered = sorted(boundaries, key=lambda item: int(item["run_index"]))
    for index, boundary in enumerate(ordered):
        start = _before_index(ids, boundary.get("last_ledger_event_id_before"))
        if start is None:
            return None
        if index + 1 < len(ordered):
            end = _before_index(ids, ordered[index + 1].get("last_ledger_event_id_before"))
            if end is None:
                return None
        else:
            end = len(ids) - 1
        if end < start:
            return None
        spans.append((start, end, boundary))
    writes: dict[str, tuple[str, str]] = {}
    for index, row in enumerate(rows):
        if row.get("event_type") != PENDING_EVENT:
            continue
        event_id = ids[index]
        if event_id is None:
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


def _run_index(obj: Mapping[str, Any]) -> int | None:
    if "run_index" in obj:
        value = obj.get("run_index")
    else:
        value = obj.get("round_index")
    if type(value) is not int or isinstance(value, bool):
        return None
    if value < 0 or value > MAX_RUN_INDEX:
        return None
    return value


def _event_id(row: Mapping[str, Any]) -> str | None:
    value = row.get("event_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _before_index(ids: Sequence[str | None], before: Any) -> int | None:
    if before is None:
        return -1
    if not isinstance(before, str):
        return None
    try:
        return list(ids).index(before)
    except ValueError:
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
