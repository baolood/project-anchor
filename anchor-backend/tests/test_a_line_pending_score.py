"""Read-side A-line pending score and the shadow OnSuccess example."""

from __future__ import annotations

import unittest
from pathlib import Path

from app.mcp.a_line_score import score_a_line
from app.mcp.tools import tool_definitions


DOCS = Path(__file__).resolve().parents[1] / "docs"
DROP_IN = (
    DOCS
    / "systemd"
    / "project-anchor-jev-forward-shadow-v2.service.d"
    / "start-official-ledger.conf.example"
)
SHADOW_DOC = DOCS / "ANCHOR_OFFICIAL_LEDGER_AFTER_SHADOW_V1.md"
OBS = "obs-score-1"
FILL_OPEN = "2026-10-12T11:00:00Z"


def _row(event_type: str, **fields: object) -> dict:
    row: dict = {"event_type": event_type, "observation_id": OBS}
    row.update(fields)
    return row


class ALinePendingScoreTests(unittest.TestCase):
    def test_score_matches_the_collapsed_ledger_counts(self) -> None:
        rows = [
            _row("PENDING_NEXT_BAR", ledger_event_id="le-1", event_time="2026-10-12T10:10:00Z"),
            _row("PENDING_NEXT_BAR", ledger_event_id="le-2", event_time="2026-10-12T10:20:00Z"),
            _row("PENDING_NEXT_BAR", ledger_event_id="le-3", event_time="2026-10-12T10:30:00Z"),
            _row("PENDING_NEXT_BAR", ledger_event_id="le-4", event_time="2026-10-12T11:10:00Z"),
            _row("OPEN", ledger_event_id="le-5", event_time="2026-10-12T12:10:00Z", fill_time_utc=FILL_OPEN),
            _row(
                "PENDING_NEXT_BAR",
                observation_id="obs-score-2",
                event_time="2026-10-12T12:00:00Z",
                recorded_at="2026-10-12T12:00:00Z",
            ),
        ]
        scored = score_a_line(rows)
        self.assertEqual(scored["kind"], "a_line_pending_score")
        self.assertTrue(scored["read_only"])
        self.assertFalse(scored["ledger_modified"])
        self.assertEqual(
            scored["pending_observations"],
            {"raw_rows": 5, "observations": 2, "BAR_NOT_YET_CLOSED": 1, "DATA_GAP": 1},
        )
        self.assertNotIn(OBS, str(scored))

    def test_tool_description_names_both_pending_classes(self) -> None:
        description = next(item["description"] for item in tool_definitions() if item["name"] == "get_ledger_summary")
        self.assertIn("BAR_NOT_YET_CLOSED", description)
        self.assertIn("DATA_GAP", description)


class ShadowLedgerDropInTests(unittest.TestCase):
    def test_example_is_only_the_onsuccess_line(self) -> None:
        text = DROP_IN.read_text(encoding="utf-8")
        self.assertEqual(text, "[Unit]\nOnSuccess=anchor-official-ledger.service\n")
        for forbidden in ("StateDirectory=", "DynamicUser=", "chmod", "setfacl", "User="):
            self.assertNotIn(forbidden, text)

    def test_doc_states_the_runner_evidence_and_the_timer_overlap(self) -> None:
        text = SHADOW_DOC.read_text(encoding="utf-8")
        self.assertIn("Type=oneshot", text)
        self.assertIn("minute :10", text)
        self.assertIn("ProtectiveRiskBook.on_signal", text)
        self.assertIn("cloud_official_once.py", text)
        self.assertIn("not a line from `cloud_official_once.py`", text)
        self.assertIn("does not `chmod` or `setfacl`", text)
