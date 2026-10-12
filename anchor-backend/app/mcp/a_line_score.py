"""Read-only A-line score over Official V2 ledger rows.

Repeated PENDING_NEXT_BAR rows for one observation count once. This module
does not open the ledger StateDirectory and does not write a ledger.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from app.mcp.official_ledger import (
    _canon_key,
    classify_pending_observations,
)


def score_a_line(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
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
        "pending_observations": classify_pending_observations(events),
    }
