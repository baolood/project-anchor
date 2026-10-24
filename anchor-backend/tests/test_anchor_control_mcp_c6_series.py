"""Compact read-only C6 series block on get_ledger_summary."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from app.mcp.c6_series import C6_SERIES_DIR_ENV, read_c6_series
from app.mcp.commands import CommandResult
from app.mcp.tools import TOOL_NAMES, ToolContext, call_tool


EQUITY_HEADER = (
    "schema_version,timestamp_utc,observation_id,position,realized_pnl,unrealized_pnl,"
    "net_liquidation_equity,drawdown,exposure,cash_reserve,active_notional,mark_rule_id,sample_class"
)
SECRET = "SECRETPRICE999"


def _row(when: str, observation: str) -> str:
    return (
        f"equity_v2_1,{when},{observation},FLAT,0,0,10000,0,0,10000,0,UNBOUND,NON_SCORING"
    )


def _write_series(root: Path) -> None:
    out = root / "out"
    marks = root / "marks"
    out.mkdir(parents=True)
    marks.mkdir()
    equity = "\n".join(
        [
            EQUITY_HEADER,
            _row("2026-10-24T01:13:00Z", "LEDGER_GENESIS"),
            _row("2026-10-24T02:13:00Z", "c6-20261024T021300Z"),
            "",
        ]
    )
    (out / "anchor_fake_fill_equity_v2_1_official.csv").write_text(equity, encoding="utf-8")
    (marks / "pf_xbtusd_marks.jsonl").write_text(
        json.dumps({"markPrice": SECRET, "status": "RECORDED"}) + "\n",
        encoding="utf-8",
    )
    (root / "funding-cache-should-not-be-here.json").write_text(
        json.dumps({"rates": [{"fundingRate": SECRET}]}) + "\n",
        encoding="utf-8",
    )


def _context(root: Path, env: dict[str, str]) -> ToolContext:
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    return ToolContext(
        reports_dir=reports,
        repo_root=root,
        env=env,
        run_command=lambda argv, timeout: CommandResult(True, 0, "", ""),
        kill_switch=lambda: {"enabled": False, "source": "redis", "state": "CLOSED", "reason": "redis_read"},
        clock=lambda: "2026-10-24T02:20:00Z",
    )


class C6SeriesReaderTest(unittest.TestCase):
    def test_unset_env_is_unavailable_and_compact(self) -> None:
        block = read_c6_series({})
        self.assertFalse(block["available"])
        self.assertEqual(block["reason"], "c6_series_dir_unset")
        self.assertEqual(block["rows"], 0)
        self.assertIsNone(block["last_row_time"])
        self.assertIsNone(block["position_state"])
        self.assertIsNone(block["scoring_status"])
        self.assertTrue(block["read_only"])
        self.assertLess(len(json.dumps(block)), 400)

    def test_series_summary_is_compact_and_omits_prices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            series = Path(tmp) / "var" / "lib" / "anchor-passline" / "affl-v2-official-ledger-c6"
            _write_series(series)
            env = {C6_SERIES_DIR_ENV: str(series)}
            block = read_c6_series(env)
            self.assertEqual(
                block,
                {
                    "available": True,
                    "rows": 2,
                    "last_row_time": "2026-10-24T02:13:00Z",
                    "position_state": "FLAT",
                    "scoring_status": "NON_SCORING",
                    "read_only": True,
                },
            )
            encoded = json.dumps(block)
            self.assertLess(len(encoded), 400)
            self.assertNotIn(SECRET, encoded)
            self.assertNotIn("markPrice", encoded)
            self.assertNotIn("fundingRate", encoded)

            ctx = _context(Path(tmp), env)
            payload = call_tool("get_ledger_summary", {}, ctx)
            self.assertEqual(payload["c6_series"], block)
            blob = json.dumps(payload)
            self.assertNotIn(SECRET, blob)
            self.assertLess(len(json.dumps(payload["c6_series"])), 400)
            self.assertLess(len(blob), 2600)
            self.assertEqual(len(TOOL_NAMES), 9)

    def test_line_a_paths_are_rejected_unread(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in (
                "affl-v2-official-ledger",
                "anchor-official-ledger",
                "anchor-official-ledger-20261010",
                "affl-v2-official-ledger-c6-extra",
            ):
                series = root / name
                _write_series(series)
                equity = series / "out" / "anchor_fake_fill_equity_v2_1_official.csv"
                equity.write_text(equity.read_text(encoding="utf-8") + f"secret,{SECRET}\n", encoding="utf-8")
                block = read_c6_series({C6_SERIES_DIR_ENV: str(series)})
                self.assertFalse(block["available"], name)
                self.assertEqual(block["reason"], "c6_series_dir_rejected", name)
                self.assertNotIn(SECRET, json.dumps(block))

            private = root / "var" / "lib" / "private" / "affl-v2-official-ledger-c6"
            _write_series(private)
            private_block = read_c6_series({C6_SERIES_DIR_ENV: str(private)})
            self.assertFalse(private_block["available"])
            self.assertEqual(private_block["reason"], "c6_series_dir_rejected")

            allowed = root / "var" / "lib" / "anchor-passline" / "affl-v2-official-ledger-c6"
            _write_series(allowed)
            allowed_block = read_c6_series({C6_SERIES_DIR_ENV: str(allowed)})
            self.assertTrue(allowed_block["available"])
            self.assertEqual(allowed_block["position_state"], "FLAT")
            self.assertEqual(allowed_block["scoring_status"], "NON_SCORING")

    def test_symlink_equity_is_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            series = root / "series"
            secret = root / "secret.csv"
            secret.write_text(f"markPrice,{SECRET}\n", encoding="utf-8")
            out = series / "out"
            out.mkdir(parents=True)
            link = out / "anchor_fake_fill_equity_v2_1_official.csv"
            link.symlink_to(secret)
            block = read_c6_series({C6_SERIES_DIR_ENV: str(series)})
            self.assertFalse(block["available"])
            self.assertNotIn(SECRET, json.dumps(block))

    def test_relative_and_sensitive_dirs_are_rejected(self) -> None:
        self.assertEqual(read_c6_series({C6_SERIES_DIR_ENV: "var/lib/anchor-passline"})["reason"], "c6_series_dir_rejected")
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.mkdir()
            block = read_c6_series({C6_SERIES_DIR_ENV: str(env_path)})
            self.assertEqual(block["reason"], "c6_series_dir_rejected")
            self.assertFalse(block["available"])


if __name__ == "__main__":
    unittest.main()
