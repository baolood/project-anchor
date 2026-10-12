"""Official V2 ledger reads stay allowlisted, read-only, and CSV-tolerant."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.mcp.commands import CommandResult
from app.mcp.inventory import OFFICIAL_LEDGER_DIR, OFFICIAL_LEDGER_DIR_PRIVATE
from app.mcp.official_ledger import (
    ALLOWLISTED_LEDGER_DIRS,
    LEDGER_DIR_ENV,
    NET_PNL_NOTE,
    read_official_ledger,
)
from app.mcp.status import collect_ledger
from app.mcp.tools import ToolContext, call_tool, tool_definitions


HASH_A = "a" * 64
HASH_B = "b" * 64
ORDER_MARKER = "synthetic-order-should-not-echo"
CLIENT_MARKER = "synthetic-client-should-not-echo"
LEDGER_NAME = "anchor_fake_fill_ledger_v2_official.jsonl"


def _context(root: Path, env: dict[str, str]) -> ToolContext:
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    return ToolContext(
        reports_dir=reports,
        repo_root=root,
        env=env,
        run_command=lambda argv, timeout: CommandResult(False, 1, "", ""),
        kill_switch=lambda: {"enabled": False, "source": "redis", "state": "CLOSED", "reason": "redis_read"},
        clock=lambda: "2026-10-12T00:00:00Z",
    )


def _jsonl(*records: dict) -> str:
    return "".join(json.dumps(record) + "\n" for record in records)


class OfficialLedgerSummaryTests(unittest.TestCase):
    def test_allowlist_is_the_two_official_directories(self) -> None:
        self.assertEqual(
            ALLOWLISTED_LEDGER_DIRS,
            (
                "/var/lib/anchor-official-ledger-20261010",
                "/var/lib/private/anchor-official-ledger-20261010",
            ),
        )
        self.assertEqual(OFFICIAL_LEDGER_DIR, ALLOWLISTED_LEDGER_DIRS[0])
        self.assertEqual(OFFICIAL_LEDGER_DIR_PRIVATE, ALLOWLISTED_LEDGER_DIRS[1])

    def test_jsonl_summary_counts_head_and_pnl_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            text = _jsonl(
                {
                    "event_id": "evt-1",
                    "event_time": "2026-10-10T00:00:00Z",
                    "event_type": "GENESIS",
                    "prev_hash": "0",
                    "event_hash": HASH_A,
                    "realized_pnl_cum": "0",
                    "order_id": ORDER_MARKER,
                    "client_order_id": CLIENT_MARKER,
                },
                {
                    "event_id": "evt-2",
                    "event_time": "2026-10-10T00:02:00Z",
                    "event_type": "NET_PNL",
                    "prev_hash": HASH_A,
                    "event_hash": HASH_B,
                    "realized_pnl_cum": 3.25,
                    "net_pnl": "3.25",
                },
            )
            text += "not-json\n"
            path = ledger / LEDGER_NAME
            path.write_text(text, encoding="utf-8")
            before = path.read_bytes()
            digest = hashlib.sha256(before).hexdigest()
            mode = path.stat().st_mode
            summary = read_official_ledger(
                {LEDGER_DIR_ENV: str(ledger)},
                allowlist=(str(ledger),),
            )
            blob = json.dumps(summary)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
            self.assertEqual(path.stat().st_mode, mode)
            self.assertTrue(summary["available"])
            self.assertEqual(summary["kind"], "official_fake_fill_v2")
            self.assertEqual(summary["source"], LEDGER_NAME)
            self.assertNotIn(str(ledger), blob)
            self.assertTrue(summary["read_only"])
            self.assertEqual(summary["fill_status"], "OFFICIAL_V2")
            self.assertEqual(summary["counts"]["events"], 2)
            self.assertEqual(summary["counts"]["by_type"], {"GENESIS": 1, "NET_PNL": 1})
            self.assertEqual(summary["counts"]["header_row_mismatches"], 0)
            self.assertEqual(summary["counts"]["unparsed"], 1)
            self.assertEqual(summary["last_event_id"], "evt-2")
            self.assertEqual(summary["last_event_time"], "2026-10-10T00:02:00Z")
            self.assertEqual(summary["hash_chain_head"], HASH_B)
            self.assertEqual(summary["realized_pnl_cum"], "3.25")
            self.assertEqual(summary["net_pnl_note"], NET_PNL_NOTE)
            self.assertIn("exclude entry costs", summary["net_pnl_note"])
            self.assertNotIn(ORDER_MARKER, blob)
            self.assertNotIn(CLIENT_MARKER, blob)
            self.assertNotIn("order_id", blob)

    def test_later_file_supplies_the_hash_chain_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            (ledger / LEDGER_NAME).write_text(
                _jsonl(
                    {
                        "event_id": "evt-1",
                        "event_time": "2026-10-10T00:00:00Z",
                        "event_type": "GENESIS",
                        "event_hash": HASH_A,
                        "realized_pnl_cum": "0",
                    }
                ),
                encoding="utf-8",
            )
            later = "anchor_fake_fill_ledger_v2_official_b.jsonl"
            (ledger / later).write_text(
                _jsonl(
                    {
                        "event_id": "evt-2",
                        "event_time": "2026-10-10T00:03:00Z",
                        "event_type": "NET_PNL",
                        "event_hash": HASH_B,
                        "realized_pnl_cum": "4",
                    }
                ),
                encoding="utf-8",
            )
            summary = read_official_ledger({LEDGER_DIR_ENV: str(ledger)}, allowlist=(str(ledger),))
            self.assertEqual(summary["counts"]["events"], 2)
            self.assertEqual(summary["source"], later)
            self.assertEqual(summary["last_event_id"], "evt-2")
            self.assertEqual(summary["hash_chain_head"], HASH_B)
            self.assertEqual(summary["realized_pnl_cum"], "4")

    def test_csv_header_row_mismatch_uses_row_width(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            name = "anchor_fake_fill_ledger_v2_official.csv"
            # Header inserted net_pnl in the middle. The historical row still has
            # six columns, with realized_pnl_cum last. Zipping onto the header
            # would park the hash in realized_pnl_cum.
            body = "\n".join(
                [
                    "event_id,event_time,event_type,net_pnl,prev_hash,event_hash,realized_pnl_cum",
                    f"evt-1,2026-10-10T00:00:00Z,GENESIS,prev0,{HASH_A},1.5",
                    "odd,row",
                    "",
                ]
            )
            (ledger / name).write_text(body, encoding="utf-8")
            summary = read_official_ledger({LEDGER_DIR_ENV: str(ledger)}, allowlist=(str(ledger),))
            self.assertTrue(summary["available"])
            self.assertEqual(summary["counts"]["events"], 1)
            self.assertEqual(summary["counts"]["header_row_mismatches"], 2)
            self.assertEqual(summary["counts"]["unparsed"], 1)
            self.assertEqual(summary["counts"]["by_type"], {"GENESIS": 1})
            self.assertEqual(summary["last_event_id"], "evt-1")
            self.assertEqual(summary["hash_chain_head"], HASH_A)
            self.assertEqual(summary["realized_pnl_cum"], "1.5")
            self.assertNotEqual(summary["realized_pnl_cum"], HASH_A)

    def test_matching_csv_row_uses_header_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            name = "anchor_fake_fill_ledger_v2_official.csv"
            body = "\n".join(
                [
                    "event_id,event_time,event_type,net_pnl,prev_hash,event_hash,realized_pnl_cum",
                    f"evt-1,2026-10-10T00:00:00Z,GENESIS,prev0,{HASH_A},1.5",
                    f"evt-2,2026-10-10T00:01:00Z,NET_PNL,0.25,prev1,{HASH_B},1.25",
                ]
            )
            (ledger / name).write_text(body, encoding="utf-8")
            summary = read_official_ledger({LEDGER_DIR_ENV: str(ledger)}, allowlist=(str(ledger),))
            self.assertEqual(summary["counts"]["header_row_mismatches"], 1)
            self.assertEqual(summary["counts"]["events"], 2)
            self.assertEqual(summary["last_event_id"], "evt-2")
            self.assertEqual(summary["hash_chain_head"], HASH_B)
            self.assertEqual(summary["realized_pnl_cum"], "1.25")
            self.assertEqual(summary["counts"]["by_type"]["NET_PNL"], 1)

    def test_unset_env_keeps_report_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "reports"
            reports.mkdir()
            (reports / "official_fake_fill_ledger.json").write_text(
                json.dumps({"fake_transport_external_status": "FILLED", "result": "PASS"}),
                encoding="utf-8",
            )
            ledger = root / "v2"
            ledger.mkdir()
            (ledger / LEDGER_NAME).write_text(
                _jsonl({"event_id": "evt-1", "event_hash": HASH_A, "event_type": "GENESIS"}),
                encoding="utf-8",
            )
            summary = collect_ledger(reports, {}, ledger_allowlist=(str(ledger),))
            self.assertEqual(summary["kind"], "official_fake_fill")
            self.assertEqual(summary["fill_status"], "FILLED")
            self.assertNotIn(HASH_A, json.dumps(summary))

    def test_set_env_does_not_fall_back_to_report_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "reports"
            reports.mkdir()
            (reports / "official_fake_fill_ledger.json").write_text(
                json.dumps({"fake_transport_external_status": "FILLED", "result": "PASS"}),
                encoding="utf-8",
            )
            ledger = root / "v2"
            ledger.mkdir()
            (ledger / LEDGER_NAME).write_text(
                _jsonl(
                    {
                        "event_id": "evt-1",
                        "event_time": "2026-10-10T00:00:00Z",
                        "event_type": "GENESIS",
                        "event_hash": HASH_A,
                        "realized_pnl_cum": "0",
                    }
                ),
                encoding="utf-8",
            )
            summary = collect_ledger(
                reports,
                {LEDGER_DIR_ENV: str(ledger)},
                ledger_allowlist=(str(ledger),),
            )
            blob = json.dumps(summary)
            self.assertEqual(summary["kind"], "official_fake_fill_v2")
            self.assertEqual(summary["hash_chain_head"], HASH_A)
            self.assertNotIn("FILLED", blob)

    def test_tool_path_rejects_a_directory_outside_the_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = _context(root, {LEDGER_DIR_ENV: str(root / "v2")})
            (ctx.reports_dir / "official_fake_fill_ledger.json").write_text(
                json.dumps({"fake_transport_external_status": "FILLED"}),
                encoding="utf-8",
            )
            ledger = root / "v2"
            ledger.mkdir()
            (ledger / LEDGER_NAME).write_text(
                _jsonl({"event_id": "evt-1", "event_hash": HASH_A, "event_type": "GENESIS"}),
                encoding="utf-8",
            )
            payload = call_tool("get_ledger_summary", {}, ctx)
            health = call_tool("run_readonly_healthcheck", {}, ctx)
            blob = json.dumps({"payload": payload, "health": health})
            self.assertFalse(payload["available"])
            self.assertEqual(payload["reason"], "ledger_dir_not_allowlisted")
            self.assertEqual(payload["kind"], "official_fake_fill_v2")
            self.assertNotIn("FILLED", blob)
            self.assertNotIn(HASH_A, blob)
            ledger_check = next(item for item in health["checks"] if item["name"] == "ledger")
            self.assertEqual(ledger_check["result"], "DEGRADED")
            self.assertEqual(ledger_check["detail"], "ledger_dir_not_allowlisted")
            schema = next(item for item in tool_definitions() if item["name"] == "get_ledger_summary")
            self.assertEqual(schema["inputSchema"]["properties"], {})
            with self.assertRaises(ValueError):
                call_tool("get_ledger_summary", {"ledger_dir": str(ledger)}, ctx)

    def test_relative_sensitive_child_and_missing_paths_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            nested = ledger / "nested"
            nested.mkdir()
            missing = ledger / "missing-ledger"
            self.assertEqual(
                read_official_ledger(
                    {LEDGER_DIR_ENV: "var/lib/anchor-official-ledger-20261010"},
                    allowlist=(str(ledger),),
                )["reason"],
                "ledger_dir_rejected",
            )
            self.assertEqual(
                read_official_ledger(
                    {LEDGER_DIR_ENV: str(ledger / ".env")},
                    allowlist=(str(ledger),),
                )["reason"],
                "ledger_dir_rejected",
            )
            self.assertEqual(
                read_official_ledger({LEDGER_DIR_ENV: str(nested)}, allowlist=(str(ledger),))["reason"],
                "ledger_dir_not_allowlisted",
            )
            self.assertEqual(
                read_official_ledger({LEDGER_DIR_ENV: str(missing)}, allowlist=(str(missing),))["reason"],
                "ledger_dir_missing",
            )

    def test_symlink_and_non_matching_names_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "ledger"
            ledger.mkdir()
            outside = root / "outside.jsonl"
            outside.write_text(
                _jsonl(
                    {
                        "event_id": "evt-leaked",
                        "event_hash": "c" * 64,
                        "event_type": "GENESIS",
                        "order_id": ORDER_MARKER,
                    }
                ),
                encoding="utf-8",
            )
            (ledger / LEDGER_NAME).write_text(
                _jsonl(
                    {
                        "event_id": "evt-1",
                        "event_time": "2026-10-10T00:00:00Z",
                        "event_type": "GENESIS",
                        "event_hash": HASH_A,
                        "realized_pnl_cum": "0",
                    }
                ),
                encoding="utf-8",
            )
            (ledger / "anchor_fake_fill_ledger_v2_official_link.jsonl").symlink_to(outside)
            (ledger / "notes.jsonl").write_text(
                _jsonl({"event_id": "evt-notes", "event_hash": "d" * 64, "event_type": "GENESIS"}),
                encoding="utf-8",
            )
            (ledger / "anchor_fake_fill_ledger_v2_official.json").write_text(
                _jsonl({"event_id": "evt-json", "event_hash": "e" * 64, "event_type": "GENESIS"}),
                encoding="utf-8",
            )
            summary = read_official_ledger({LEDGER_DIR_ENV: str(ledger)}, allowlist=(str(ledger),))
            blob = json.dumps(summary)
            self.assertEqual(summary["counts"]["events"], 1)
            self.assertEqual(summary["last_event_id"], "evt-1")
            self.assertEqual(summary["hash_chain_head"], HASH_A)
            self.assertNotIn("evt-leaked", blob)
            self.assertNotIn("evt-notes", blob)
            self.assertNotIn("evt-json", blob)
            self.assertNotIn(ORDER_MARKER, blob)

    def test_permission_error_is_unreadable_without_a_partial_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            (ledger / LEDGER_NAME).write_text(
                _jsonl({"event_id": "evt-1", "event_hash": HASH_A, "event_type": "GENESIS"}),
                encoding="utf-8",
            )
            with mock.patch("app.mcp.official_ledger.os.listdir", side_effect=PermissionError):
                summary = read_official_ledger({LEDGER_DIR_ENV: str(ledger)}, allowlist=(str(ledger),))
            self.assertFalse(summary["available"])
            self.assertEqual(summary["reason"], "ledger_unreadable")
            self.assertNotIn("hash_chain_head", summary)
            self.assertNotIn(HASH_A, json.dumps(summary))

    def test_oversize_ledger_does_not_report_a_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            (ledger / LEDGER_NAME).write_text(
                _jsonl(
                    {
                        "event_id": "evt-1",
                        "event_hash": HASH_A,
                        "event_type": "GENESIS",
                        "realized_pnl_cum": "9",
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch("app.mcp.official_ledger.MAX_LEDGER_BYTES", 8):
                summary = read_official_ledger({LEDGER_DIR_ENV: str(ledger)}, allowlist=(str(ledger),))
            self.assertFalse(summary["available"])
            self.assertEqual(summary["reason"], "ledger_too_large")
            self.assertNotIn("hash_chain_head", summary)
            self.assertNotIn(HASH_A, json.dumps(summary))

    def test_opens_are_read_only_and_do_not_follow_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            (ledger / LEDGER_NAME).write_text(
                _jsonl({"event_id": "evt-1", "event_hash": HASH_A, "event_type": "GENESIS"}),
                encoding="utf-8",
            )
            flags_seen: list[int] = []
            real_open = os.open

            def spy(path: str | os.PathLike[str], flags: int, *args: int, **kwargs: int) -> int:
                flags_seen.append(flags)
                return real_open(path, flags, *args, **kwargs)

            with mock.patch("app.mcp.official_ledger.os.open", side_effect=spy):
                summary = read_official_ledger({LEDGER_DIR_ENV: str(ledger)}, allowlist=(str(ledger),))
            self.assertTrue(summary["available"])
            self.assertTrue(flags_seen)
            for flags in flags_seen:
                self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY)
                self.assertTrue(flags & os.O_NOFOLLOW)
