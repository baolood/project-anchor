"""Read-only MF4 MCP tools. No network. Responses stay within 2.5 KB."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.mcp.commands import CommandResult
from app.mcp.mf4_eval import MF4_DIR_ENV, cap_tool_payload
from app.mcp.tools import ToolContext, call_tool


SECRET = "manual-snapshot-secret-value"
NOW = "2026-10-22T10:00:00Z"
MAX_BYTES = 2560


def _context(root: Path, env: dict[str, str]) -> ToolContext:
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    return ToolContext(
        reports_dir=reports,
        repo_root=root,
        env=env,
        run_command=lambda argv, timeout: CommandResult(True, 0, "", ""),
        kill_switch=lambda: {"enabled": False, "source": "redis", "state": "CLOSED", "reason": "redis_read"},
        clock=lambda: NOW,
    )


def _account() -> dict:
    return {
        "balance": "10120.42",
        "daily_ref_balance": "10120.42",
        "daily_ref_at": "2026-10-22T00:30:00Z",
        "floor": 9400,
        "target": 11000,
        "position": {
            "side": "long",
            "size": "0.176",
            "entry": "84499.5",
            "sl": "83633.1",
            "tp": "87812.6",
        },
        "snapshot_at": "2026-10-22T09:00:00Z",
    }


def _status(reason: str = "no_signal") -> dict:
    return {
        "state": "LONG",
        "pos": {"side": "long", "size": 0.176, "entry": 84499.5, "sl": 83633.1, "tp": 87812.6},
        "trend": "up",
        "long_trigger_gt": 85000,
        "short_trigger_lt": 82000,
        "last_4h_close": {"at_sh": "2026-10-22T12:00:00+08:00", "close": 84499.5},
        "last_signal": {
            "type": "OPEN",
            "side": "long",
            "price": 84499.5,
            "at_sh": "2026-10-22T08:03:00+08:00",
        },
        "price": {"last": 84499.5, "at": "2026-10-22T09:59:30Z"},
        "shadow_equity": 10000,
        "webhook": {"enabled": False, "last_ok_at_sh": None, "outbox_n": 0},
        "compare": {"consecutive_matches": 1, "last_diff_at": None},
        "reason": reason,
    }


def _encoded(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


class Mf4McpTests(unittest.TestCase):
    def test_unset_dir_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _context(Path(tmp), {})
            status = call_tool("get_mf4_status", {}, ctx)
            state = call_tool("get_eval_state", {}, ctx)
        self.assertFalse(status["available"])
        self.assertEqual(status["reason"], "mf4_dir_unset")
        self.assertFalse(state["available"])
        self.assertEqual(state["reason"], "mf4_dir_unset")
        self.assertEqual(state["source"], "manual-snapshot")
        self.assertLessEqual(len(_encoded(status)), MAX_BYTES)
        self.assertLessEqual(len(_encoded(state)), MAX_BYTES)

    def test_trade_snapshot_is_manual_and_compact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mf4 = root / "var" / "lib" / "anchor-mf4-watcher"
            mf4.mkdir(parents=True)
            (mf4 / "status.json").write_text(json.dumps(_status()), encoding="utf-8")
            (mf4 / "eval_account.json").write_text(json.dumps(_account()), encoding="utf-8")
            (mf4 / "notes.txt").write_text(SECRET, encoding="utf-8")
            ctx = _context(root, {MF4_DIR_ENV: str(mf4)})
            status = call_tool("get_mf4_status", {}, ctx)
            state = call_tool("get_eval_state", {}, ctx)
        self.assertTrue(status["available"])
        self.assertEqual(status["state"], "LONG")
        self.assertEqual(status["long_trigger_gt"], 85000)
        self.assertEqual(status["price"]["fresh"], True)
        self.assertLess(status["price"]["age_s"], 120)
        self.assertFalse(status["webhook"]["enabled"])
        self.assertEqual(status["compare"]["consecutive_matches"], 1)
        self.assertTrue(state["available"])
        self.assertEqual(state["source"], "manual-snapshot")
        self.assertEqual(state["daily_line"], 9816.81)
        self.assertEqual(state["floor"], 9400)
        self.assertEqual(state["worst_case_at_sl"], -182.0)
        self.assertEqual(state["guard_verdict"], "ok")
        self.assertEqual(state["position"]["size"], 0.176)
        for payload in (status, state):
            encoded = _encoded(payload)
            self.assertLessEqual(len(encoded), MAX_BYTES)
            self.assertNotIn(SECRET, encoded.decode("utf-8"))
            self.assertNotIn("http://", encoded.decode("utf-8"))

    def test_large_reason_stays_under_the_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mf4 = root / "mf4"
            mf4.mkdir()
            (mf4 / "status.json").write_text(json.dumps(_status("x" * 50000)), encoding="utf-8")
            ctx = _context(root, {MF4_DIR_ENV: str(mf4)})
            status = call_tool("get_mf4_status", {}, ctx)
        self.assertTrue(status["available"])
        self.assertLessEqual(len(status["reason"]), 160)
        self.assertLessEqual(len(_encoded(status)), MAX_BYTES)
        capped = cap_tool_payload(
            "get_mf4_status",
            {"available": True, "read_only": True, "reason": "y" * 4000},
            datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc),
        )
        self.assertLessEqual(len(json.dumps(capped).encode("utf-8")), MAX_BYTES)

    def test_stale_snapshot_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mf4 = root / "mf4"
            mf4.mkdir()
            account = _account()
            account["snapshot_at"] = "2026-10-20T09:00:00Z"
            (mf4 / "eval_account.json").write_text(json.dumps(account), encoding="utf-8")
            (mf4 / "status.json").write_text(json.dumps(_status()), encoding="utf-8")
            ctx = _context(root, {MF4_DIR_ENV: str(mf4)})
            state = call_tool("get_eval_state", {}, ctx)
        self.assertTrue(state["available"])
        self.assertEqual(state["source"], "manual-snapshot")
        self.assertEqual(state["guard_verdict"], "unknown")

    def test_line_a_and_sensitive_paths_are_rejected_unread(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in (
                "affl-v2-official-ledger",
                "anchor-official-ledger",
                "anchor-official-ledger-20261010",
            ):
                series = root / name
                series.mkdir()
                (series / "eval_account.json").write_text(json.dumps({**_account(), "note": SECRET}), encoding="utf-8")
                ctx = _context(root, {MF4_DIR_ENV: str(series)})
                state = call_tool("get_eval_state", {}, ctx)
                self.assertFalse(state["available"], name)
                self.assertEqual(state["reason"], "mf4_dir_rejected", name)
                self.assertNotIn(SECRET, _encoded(state).decode("utf-8"))
            private = root / "var" / "lib" / "private" / "anchor-mf4-watcher"
            private.mkdir(parents=True)
            (private / "eval_account.json").write_text(SECRET, encoding="utf-8")
            private_state = call_tool("get_eval_state", {}, _context(root, {MF4_DIR_ENV: str(private)}))
            self.assertEqual(private_state["reason"], "mf4_dir_rejected")
            self.assertNotIn(SECRET, _encoded(private_state).decode("utf-8"))
            env_dir = root / ".env"
            env_dir.mkdir()
            rejected = call_tool("get_mf4_status", {}, _context(root, {MF4_DIR_ENV: str(env_dir)}))
            self.assertEqual(rejected["reason"], "mf4_dir_rejected")
            relative = call_tool("get_mf4_status", {}, _context(root, {MF4_DIR_ENV: "var/lib/anchor-mf4-watcher"}))
            self.assertEqual(relative["reason"], "mf4_dir_rejected")

    def test_symlink_status_is_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mf4 = root / "mf4"
            mf4.mkdir()
            secret = root / "secret.json"
            secret.write_text(json.dumps({"reason": SECRET, "state": "LONG"}), encoding="utf-8")
            (mf4 / "status.json").symlink_to(secret)
            status = call_tool("get_mf4_status", {}, _context(root, {MF4_DIR_ENV: str(mf4)}))
        self.assertFalse(status["available"])
        self.assertNotIn(SECRET, _encoded(status).decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
