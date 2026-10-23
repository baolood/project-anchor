"""Bounds for this recording package. No scoring hook, no Line A write, no freeze."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

import eval_recording
from eval_recording.funding.recording import LIVE_FUNDING_INGEST_ENABLED

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_TREES = (
    "local_box",
    "anchor-backend",
    "scripts",
    "risk_engine",
    "shared",
    "eval_scoring",
)


class RecordingBoundsTest(unittest.TestCase):
    def test_package_flags_stay_off(self) -> None:
        self.assertEqual(eval_recording.PRODUCTION_DEPLOY, "NO")
        self.assertEqual(eval_recording.LIVE_TRADING, "NO")
        self.assertEqual(
            eval_recording.FORMAL_SCORING_CHAIN,
            "NOT_ON_FORMAL_SCORING_CHAIN",
        )
        self.assertEqual(eval_recording.EQUITY_V21_DUAL_WRITE_DEFAULT, "OFF")
        self.assertEqual(eval_recording.LIVE_FUNDING_INGEST, "OFF")
        self.assertEqual(eval_recording.PASS_LINE_FREEZE_BY_THIS_PACKAGE, "NO")
        self.assertEqual(eval_recording.LINE_A_REWRITE, "NO")
        self.assertEqual(eval_recording.LEGACY_EQUITY_REWRITE, "NO")
        self.assertFalse(LIVE_FUNDING_INGEST_ENABLED)

    def test_runtime_trees_do_not_import_the_scaffold(self) -> None:
        for name in RUNTIME_TREES:
            root = ROOT / name
            for path in root.rglob("*"):
                if path.suffix not in {".py", ".sh"} or not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                self.assertNotIn("eval_recording", text, msg=str(path))
                self.assertNotIn("AFFL_EQUITY_V21_DUAL_WRITE", text, msg=str(path))
                self.assertNotIn("C9_INCIDENT_REGISTER", text, msg=str(path))

    def test_package_init_does_not_import_the_fetch_script(self) -> None:
        for relative in (
            "eval_recording/__init__.py",
            "eval_recording/equity_v21_dual_write.py",
            "eval_recording/funding/__init__.py",
            "eval_recording/funding/accrual.py",
            "eval_recording/funding/recording.py",
        ):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn("fetch_pf_xbtusd_funding", node.module)
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertNotIn("fetch_pf_xbtusd_funding", alias.name)

    def test_c9_template_is_empty_and_not_the_scoring_register(self) -> None:
        template = ROOT / "docs" / "pass-line" / "templates" / "C9_INCIDENT_REGISTER.jsonl"
        self.assertTrue(template.is_file())
        self.assertEqual(template.read_text(encoding="utf-8"), "")
        live = ROOT / "governance" / "ANCHOR_C9_GOVERNANCE_REGISTER.jsonl"
        self.assertEqual(live.read_text(encoding="utf-8"), "")
        for path in (ROOT / "eval_scoring").rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            self.assertNotIn("docs/pass-line", text, msg=str(path))

    def test_gap_summary_does_not_zero_fill(self) -> None:
        summary = (
            ROOT
            / "eval_recording"
            / "funding"
            / "cache"
            / "PF_XBTUSD_gaps_summary.json"
        )
        text = summary.read_text(encoding="utf-8")
        self.assertIn("never coerce to 0", text)
        self.assertIn('"n_missing_hours": 8', text)
        self.assertNotIn("relativeFundingRate", text)


if __name__ == "__main__":
    unittest.main()
