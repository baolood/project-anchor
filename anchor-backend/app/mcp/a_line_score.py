"""Read-only A-line score over Official V2 ledger rows.

Repeated PENDING_NEXT_BAR rows for one observation count once. Write time
comes from the run index, not from a field on the ledger row. This module
does not open the ledger StateDirectory and does not write a ledger.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from app.mcp.official_ledger import (
    _canon_key,
    pending_observation_summary,
)


def score_a_line(
    rows: Sequence[Mapping[str, Any]],
    *,
    boundaries: Sequence[Mapping[str, Any]] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Score pending observations. `rows` are already-read ledger objects."""
    events: list[dict[str, Any]] = []
    for row in rows:
        mapped: dict[str, Any] = {}
        for key, value in row.items():
            canon = _canon_key(str(key))
            if canon and canon not in mapped:
                mapped[canon] = value
        if mapped:
            events.append(mapped)
    return {
        "kind": "a_line_pending_score",
        "read_only": True,
        "ledger_modified": False,
        "pending_observations": pending_observation_summary(events, boundaries, now),
    }
