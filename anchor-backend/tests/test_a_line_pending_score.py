"""Read-side A-line pending score and the same-hour run note."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.mcp.a_line_score import score_a_line
from app.mcp.ledger_run_index import build_boundaries, parse_committed_runs
from app.mcp.tools import tool_definitions


DOCS = Path(__file__).resolve().parents[1] / "docs"
SHADOW_DOC = DOCS / "ANCHOR_OFFICIAL_LEDGER_SAME_HOUR_RUN_V1.md"
DROPPED = (
    DOCS
    / "systemd"
    / "project-anchor-jev-forward-shadow-v2.service.d"
    / "start-official-ledger.conf.example"
)
OBS = "obs-score-1"
FILL_OPEN = "2026-10-12T11:00:00Z"
NOW = datetime(2026, 10, 12, 15, 0, tzinfo=timezone.utc)


def _committed(at: str, round_index: int) -> str:
    item = {
        "at": at,
        "event": "committed",
        "next_due": None,
        "round_id": "ab" * 16,
        "round_index": round_index,
        "status": "waiting",
    }
    return json.dumps(item, sort_keys=True)


def _row(event_type: str, event_id: str, **fields: object) -> dict:
    row: dict = {
        "event_type": event_type,
        "ledger_event_id": event_id,
        "observation_id": OBS,
        "signal_available_at": "2026-10-12T10:05:00Z",
        "signal_candle_open_utc": "2026-10-12T10:00:00Z",
        "event_time": "2026-10-12T13:00:00Z",
    }
    row.update(fields)
    return row


class ALinePendingScoreTests(unittest.TestCase):
    def test_score_uses_committed_run_time_not_the_row_clock(self) -> None:
        events = "\n".join(
            [
                _committed("2026-10-12T10:10:01.250000+00:00", 1),
                _committed("2026-10-12T10:20:01+00:00", 2),
                _committed("2026-10-12T12:00:00Z", 3),
            ]
        ) + "\n"
        boundaries = build_boundaries(
            parse_committed_runs(events),
            {"run-000001": None, "run-000002": "le-4", "run-000003": "le-5"},
        )
        rows = [
            _row("PENDING_NEXT_BAR", "le-1"),
            _row("PENDING_NEXT_BAR", "le-2"),
            _row("PENDING_NEXT_BAR", "le-3"),
            _row("PENDING_NEXT_BAR", "le-4"),
            _row("OPEN", "le-5", fill_time_utc=FILL_OPEN),
            _row("PENDING_NEXT_BAR", "le-6", observation_id="obs-score-2"),
        ]
        scored = score_a_line(rows, boundaries=boundaries, now=NOW)
        self.assertEqual(scored["kind"], "a_line_pending_score")
        self.assertTrue(scored["read_only"])
        self.assertFalse(scored["ledger_modified"])
        self.assertEqual(
            scored["pending_observations"],
            {
                "raw_rows": 5,
                "observations": 2,
                "runs_waited": 2,
                "BAR_NOT_YET_CLOSED": 1,
                "DATA_GAP": 1,
                "IN_FLIGHT": 0,
            },
        )
        self.assertNotIn(OBS, str(scored))

    def test_score_without_a_run_index_has_no_labels(self) -> None:
        scored = score_a_line([_row("PENDING_NEXT_BAR", "le-1")], now=NOW)
        self.assertEqual(
            scored["pending_observations"],
            {"raw_rows": 1, "observations": 1, "runs_waited": 1},
        )

    def test_tool_description_names_in_flight_and_the_unlabeled_counts(self) -> None:
        description = next(item["description"] for item in tool_definitions() if item["name"] == "get_ledger_summary")
        self.assertIn("IN_FLIGHT", description)
        self.assertIn("runs_waited", description)
        self.assertIn("BAR_NOT_YET_CLOSED", description)


class SameHourRunDocTests(unittest.TestCase):
    def test_shadow_onsuccess_example_is_gone(self) -> None:
        self.assertFalse(DROPPED.exists())

    def test_doc_states_the_duplicate_pending_row_and_blocked_file(self) -> None:
        text = SHADOW_DOC.read_text(encoding="utf-8")
        self.assertIn("PENDING_NEXT_BAR", text)
        self.assertIn("not a no-op", text)
        self.assertIn("BLOCKED.json", text)
        self.assertIn("cloud_loop.py", text)
        self.assertIn('event(root, "committed"', text)
        self.assertIn("runs/run-NNNNNN", text)
        self.assertIn("IN_FLIGHT", text)
        self.assertIn("Do not `chmod` or `setfacl`", text)
        self.assertIn("Do not add `OnSuccess=anchor-official-ledger.service`", text)
