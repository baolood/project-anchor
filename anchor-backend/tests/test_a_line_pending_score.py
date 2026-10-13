"""Read-side A-line pending score and the same-hour run note."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.mcp.a_line_score import score_a_line
from app.mcp.ledger_run_index import boundaries_from_commits, parse_committed_runs
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


HOST_COMMITTED = (
    '{"at":"2026-10-12T23:10:01.432083+00:00","commits":366,'
    '"event":"committed","ledger_events":1015,"run_seq":70,"source_lines":370}'
)


def _committed(at: str, run_seq: int, ledger_events: int) -> str:
    item = {
        "at": at,
        "commits": ledger_events,
        "event": "committed",
        "ledger_events": ledger_events,
        "run_seq": run_seq,
        "source_lines": ledger_events,
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
    def test_host_committed_line_uses_run_seq_and_needs_a_predecessor(self) -> None:
        parsed = parse_committed_runs(HOST_COMMITTED + "\n")
        self.assertEqual(
            parsed,
            [
                {
                    "run_seq": 70,
                    "run": "run-000070",
                    "committed_at": "2026-10-12T23:10:01.432083+00:00",
                    "ledger_events": 1015,
                }
            ],
        )
        self.assertIsNone(boundaries_from_commits(parsed))
        self.assertEqual(json.loads(HOST_COMMITTED)["commits"], 366)
        self.assertEqual(json.loads(HOST_COMMITTED)["source_lines"], 370)

    def test_round_index_is_not_a_run_number(self) -> None:
        line = json.dumps(
            {
                "at": "2026-10-12T10:10:01+00:00",
                "event": "committed",
                "round_index": 1,
                "run_index": 1,
            },
            sort_keys=True,
        )
        self.assertEqual(parse_committed_runs(line + "\n"), [])

    def test_a_gap_in_run_seq_is_not_an_index(self) -> None:
        events = "\n".join(
            [
                _committed("2026-10-12T10:10:01+00:00", 1, 1),
                _committed("2026-10-12T12:10:01+00:00", 3, 3),
            ]
        )
        self.assertIsNone(boundaries_from_commits(parse_committed_runs(events + "\n")))

    def test_score_uses_committed_run_time_not_the_row_clock(self) -> None:
        events = "\n".join(
            [
                _committed("2026-10-12T10:10:01.250000+00:00", 1, 4),
                _committed("2026-10-12T10:20:01+00:00", 2, 5),
                _committed("2026-10-12T12:00:00Z", 3, 6),
            ]
        ) + "\n"
        boundaries = boundaries_from_commits(parse_committed_runs(events))
        self.assertIsNotNone(boundaries)
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

    def test_score_without_run_boundaries_has_no_labels(self) -> None:
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
        self.assertIn("run_seq", text)
        self.assertIn('"ledger_events":1015', text)
        self.assertIn(
            "runs/run-NNNNNN/before/affl-v2-official-ledger/out/anchor_fake_fill_ledger_v2_official.jsonl",
            text,
        )
        self.assertIn("IN_FLIGHT", text)
        self.assertIn("BAR_NOT_YET_CLOSED", text)
        self.assertIn("signal_available_at", text)
        self.assertNotIn("round_index", text)
        self.assertNotIn("cloud_loop.py", text)
        self.assertIn("Do not `chmod` or `setfacl`", text)
        self.assertIn("Do not add `OnSuccess=anchor-official-ledger.service`", text)
