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
from datetime import datetime, timedelta, timezone

from app.mcp.inventory import LEDGER_MIRROR_DIR
from app.mcp.ledger_run_index import BOUNDARY_NAME, boundaries_from_commits, parse_committed_runs
from app.mcp.official_ledger import (
    ALLOWLISTED_LEDGER_DIRS,
    LEDGER_DIR_ENV,
    LEDGER_NAME_RE,
    MIRROR_STALE_AFTER_SEC,
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


def _out(root: Path) -> Path:
    """Mirror files live in the allowlisted directory itself."""
    root.mkdir(parents=True, exist_ok=True)
    return root


def _seal(directory: Path, copied_at: str | None = None) -> None:
    if not directory.is_dir():
        return
    stamp = copied_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file() or not LEDGER_NAME_RE.fullmatch(path.name):
            continue
        blob = path.read_bytes()
        digest = hashlib.sha256(blob).hexdigest()
        (directory / f"{path.name}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
        meta = {"source_mtime": stamp, "source_size": len(blob), "copied_at": stamp}
        (directory / f"{path.name}.meta.json").write_text(json.dumps(meta) + "\n", encoding="utf-8")


def _read_mirror(ledger: Path, **kwargs: object):
    copied_at = kwargs.get("copied_at")
    _seal(ledger, copied_at if isinstance(copied_at, str) else None)
    return read_official_ledger(
        {LEDGER_DIR_ENV: str(kwargs.get("env_dir", ledger))},
        allowlist=kwargs.get("allowlist") if isinstance(kwargs.get("allowlist"), tuple) else (str(ledger),),
        now=kwargs.get("now") if isinstance(kwargs.get("now"), datetime) else None,
    )


def _event(event_id: str, event_hash: str, event_type: str = "GENESIS", pnl: str = "0") -> dict:
    return {
        "event_id": event_id,
        "event_time": "2026-10-10T00:00:00Z",
        "event_type": event_type,
        "event_hash": event_hash,
        "realized_pnl_cum": pnl,
    }


class OfficialLedgerSummaryTests(unittest.TestCase):
    def test_allowlist_is_the_mirror_directory_only(self) -> None:
        self.assertEqual(ALLOWLISTED_LEDGER_DIRS, ("/var/lib/anchor-ledger-mirror",))
        self.assertEqual(LEDGER_MIRROR_DIR, ALLOWLISTED_LEDGER_DIRS[0])
        self.assertNotIn("/var/lib/private/anchor-official-ledger-20261010", ALLOWLISTED_LEDGER_DIRS)
        self.assertEqual(MIRROR_STALE_AFTER_SEC, 90 * 60)

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
            path = _out(ledger) / LEDGER_NAME
            path.write_text(text, encoding="utf-8")
            before = path.read_bytes()
            digest = hashlib.sha256(before).hexdigest()
            mode = path.stat().st_mode
            summary = _read_mirror(ledger)
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
            self.assertEqual(summary["last_event_time_field"], "event_time")
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
            (_out(ledger) / LEDGER_NAME).write_text(
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
            (_out(ledger) / later).write_text(
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
            summary = _read_mirror(ledger)
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
            (_out(ledger) / name).write_text(body, encoding="utf-8")
            summary = _read_mirror(ledger)
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
            (_out(ledger) / name).write_text(body, encoding="utf-8")
            summary = _read_mirror(ledger)
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
            (_out(ledger) / LEDGER_NAME).write_text(
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
            (_out(ledger) / LEDGER_NAME).write_text(
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
            _seal(ledger)
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
            (_out(ledger) / LEDGER_NAME).write_text(
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
            (_out(ledger) / LEDGER_NAME).write_text(
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
            (_out(ledger) / "anchor_fake_fill_ledger_v2_official_link.jsonl").symlink_to(outside)
            (_out(ledger) / "notes.jsonl").write_text(
                _jsonl({"event_id": "evt-notes", "event_hash": "d" * 64, "event_type": "GENESIS"}),
                encoding="utf-8",
            )
            (_out(ledger) / "anchor_fake_fill_ledger_v2_official.json").write_text(
                _jsonl({"event_id": "evt-json", "event_hash": "e" * 64, "event_type": "GENESIS"}),
                encoding="utf-8",
            )
            summary = _read_mirror(ledger)
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
            (_out(ledger) / LEDGER_NAME).write_text(
                _jsonl({"event_id": "evt-1", "event_hash": HASH_A, "event_type": "GENESIS"}),
                encoding="utf-8",
            )
            _seal(ledger)
            with mock.patch("app.mcp.official_ledger.os.listdir", side_effect=PermissionError):
                summary = read_official_ledger({LEDGER_DIR_ENV: str(ledger)}, allowlist=(str(ledger),))
            self.assertFalse(summary["available"])
            self.assertEqual(summary["reason"], "ledger_unreadable")
            self.assertNotIn("hash_chain_head", summary)
            self.assertNotIn(HASH_A, json.dumps(summary))

    def test_oversize_ledger_does_not_report_a_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            (_out(ledger) / LEDGER_NAME).write_text(
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
                summary = _read_mirror(ledger)
            self.assertFalse(summary["available"])
            self.assertEqual(summary["reason"], "ledger_too_large")
            self.assertNotIn("hash_chain_head", summary)
            self.assertNotIn(HASH_A, json.dumps(summary))

    def test_opens_are_read_only_and_do_not_follow_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            (_out(ledger) / LEDGER_NAME).write_text(
                _jsonl({"event_id": "evt-1", "event_hash": HASH_A, "event_type": "GENESIS"}),
                encoding="utf-8",
            )
            flags_seen: list[int] = []
            real_open = os.open

            def spy(path: str | os.PathLike[str], flags: int, *args: int, **kwargs: int) -> int:
                flags_seen.append(flags)
                return real_open(path, flags, *args, **kwargs)

            with mock.patch("app.mcp.official_ledger.os.open", side_effect=spy):
                summary = _read_mirror(ledger)
            self.assertTrue(summary["available"])
            self.assertTrue(flags_seen)
            for flags in flags_seen:
                self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY)
                self.assertTrue(flags & os.O_NOFOLLOW)

    def test_live_out_ignores_snapshots_and_does_not_recurse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            (_out(ledger) / LEDGER_NAME).write_text(
                _jsonl(_event("evt-live", HASH_A, pnl="1.5")),
                encoding="utf-8",
            )
            nested = _out(ledger) / "nested"
            nested.mkdir()
            (nested / LEDGER_NAME).write_text(
                _jsonl(_event("evt-nested", "e" * 64, pnl="8")),
                encoding="utf-8",
            )
            baseline = ledger / "baseline"
            baseline.mkdir()
            (baseline / LEDGER_NAME).write_text(
                _jsonl(_event("evt-baseline", "b" * 64, pnl="2")),
                encoding="utf-8",
            )
            before = ledger / "runs" / "sample-run" / "before"
            before.mkdir(parents=True)
            (before / LEDGER_NAME).write_text(
                _jsonl(_event("evt-before", "c" * 64, pnl="3")),
                encoding="utf-8",
            )
            opened: list[str] = []
            real_open = os.open

            def spy(path: str | os.PathLike[str], flags: int, *args: int, **kwargs: int) -> int:
                opened.append(os.fspath(path))
                return real_open(path, flags, *args, **kwargs)

            with mock.patch("app.mcp.official_ledger.os.open", side_effect=spy):
                summary = _read_mirror(ledger)
            blob = json.dumps(summary)
            self.assertTrue(summary["available"])
            self.assertEqual(summary["counts"]["events"], 1)
            self.assertEqual(summary["last_event_id"], "evt-live")
            self.assertEqual(summary["hash_chain_head"], HASH_A)
            self.assertEqual(summary["realized_pnl_cum"], "1.5")
            self.assertEqual(summary["source"], LEDGER_NAME)
            for marker in ("evt-baseline", "evt-before", "evt-top", "evt-nested"):
                self.assertNotIn(marker, blob)
            self.assertTrue(opened)
            for path in opened:
                self.assertNotIn("/baseline/", path)
                self.assertNotIn("/runs/", path)
                self.assertNotIn("/nested/", path)

    def test_symlinked_root_reads_live_out_and_ignores_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            real = base / "private"
            real.mkdir()
            public = base / "var-lib"
            public.symlink_to(real, target_is_directory=True)
            (_out(real) / LEDGER_NAME).write_text(
                _jsonl(_event("evt-live", HASH_A, pnl="4.5")),
                encoding="utf-8",
            )
            (real / "baseline").mkdir()
            (real / "baseline" / LEDGER_NAME).write_text(
                _jsonl(_event("evt-baseline", "b" * 64)),
                encoding="utf-8",
            )
            before = real / "runs" / "sample-run" / "before"
            before.mkdir(parents=True)
            (before / LEDGER_NAME).write_text(
                _jsonl(_event("evt-before", "c" * 64)),
                encoding="utf-8",
            )
            summary = _read_mirror(real, env_dir=public, allowlist=(str(public),))
            blob = json.dumps(summary)
            self.assertTrue(summary["available"])
            self.assertEqual(summary["last_event_id"], "evt-live")
            self.assertEqual(summary["hash_chain_head"], HASH_A)
            self.assertEqual(summary["realized_pnl_cum"], "4.5")
            self.assertNotIn("evt-baseline", blob)
            self.assertNotIn("evt-before", blob)
            self.assertNotIn(str(real), blob)
            self.assertNotIn(str(public), blob)

    def test_sha256_mismatch_does_not_report_a_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            (_out(ledger) / LEDGER_NAME).write_text(
                _jsonl(_event("evt-1", HASH_A, pnl="1")),
                encoding="utf-8",
            )
            _seal(ledger)
            (ledger / f"{LEDGER_NAME}.sha256").write_text(f"{'ab' * 32}  {LEDGER_NAME}\n", encoding="ascii")
            summary = read_official_ledger({LEDGER_DIR_ENV: str(ledger)}, allowlist=(str(ledger),))
            self.assertFalse(summary["available"])
            self.assertEqual(summary["reason"], "ledger_mirror_hash_mismatch")
            self.assertNotIn("hash_chain_head", summary)
            self.assertNotIn(HASH_A, json.dumps(summary))

    def test_stale_mirror_is_flagged_after_90_minutes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            (_out(ledger) / LEDGER_NAME).write_text(
                _jsonl(_event("evt-1", HASH_A, pnl="1")),
                encoding="utf-8",
            )
            now = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)
            fresh = (now - timedelta(minutes=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
            stale = (now - timedelta(minutes=90, seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
            fresh_summary = _read_mirror(ledger, copied_at=fresh, now=now)
            self.assertTrue(fresh_summary["available"])
            self.assertFalse(fresh_summary["mirror_stale"])
            self.assertEqual(fresh_summary["mirror_age_sec"], 90 * 60)
            self.assertEqual(fresh_summary["mirror_copied_at"], fresh)
            self.assertEqual(fresh_summary["last_event_id"], "evt-1")
            stale_summary = _read_mirror(ledger, copied_at=stale, now=now)
            self.assertTrue(stale_summary["available"])
            self.assertTrue(stale_summary["mirror_stale"])
            self.assertEqual(stale_summary["mirror_age_sec"], 90 * 60 + 1)
            self.assertEqual(stale_summary["mirror_stale_after_sec"], 90 * 60)
            self.assertEqual(stale_summary["hash_chain_head"], HASH_A)

    def test_missing_sha256_does_not_report_a_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            (_out(ledger) / LEDGER_NAME).write_text(
                _jsonl(_event("evt-1", HASH_A, pnl="1")),
                encoding="utf-8",
            )
            summary = read_official_ledger({LEDGER_DIR_ENV: str(ledger)}, allowlist=(str(ledger),))
            self.assertFalse(summary["available"])
            self.assertEqual(summary["reason"], "ledger_mirror_hash_missing")
            self.assertNotIn("hash_chain_head", summary)
            self.assertNotIn("mirror_sha256_ok", summary)

    def test_sha256_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            (_out(ledger) / LEDGER_NAME).write_text(
                _jsonl(_event("evt-1", HASH_A, pnl="1")),
                encoding="utf-8",
            )
            _seal(ledger)
            sidecar = ledger / f"{LEDGER_NAME}.sha256"
            sidecar.unlink()
            sidecar.symlink_to(ledger / LEDGER_NAME)
            summary = read_official_ledger({LEDGER_DIR_ENV: str(ledger)}, allowlist=(str(ledger),))
            self.assertFalse(summary["available"])
            self.assertEqual(summary["reason"], "ledger_mirror_hash_rejected")
            self.assertNotIn("hash_chain_head", summary)

    def test_missing_meta_flags_stale_without_hiding_the_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            (_out(ledger) / LEDGER_NAME).write_text(
                _jsonl(_event("evt-1", HASH_A, pnl="1")),
                encoding="utf-8",
            )
            _seal(ledger)
            meta_path = ledger / f"{LEDGER_NAME}.meta.json"
            meta_path.unlink()
            summary = read_official_ledger({LEDGER_DIR_ENV: str(ledger)}, allowlist=(str(ledger),))
            self.assertTrue(summary["available"])
            self.assertTrue(summary["mirror_stale"])
            self.assertIsNone(summary["mirror_copied_at"])
            self.assertIsNone(summary["mirror_age_sec"])
            self.assertTrue(summary["mirror_sha256_ok"])
            self.assertEqual(summary["hash_chain_head"], HASH_A)
            meta_path.write_text(
                json.dumps(
                    {
                        "source_mtime": "not-a-time",
                        "source_size": 1,
                        "copied_at": "2026-10-12T00:00:00Z",
                    }
                ),
                encoding="utf-8",
            )
            checked = datetime(2026, 10, 12, 0, 1, tzinfo=timezone.utc)
            sized = read_official_ledger(
                {LEDGER_DIR_ENV: str(ledger)},
                allowlist=(str(ledger),),
                now=checked,
            )
            self.assertTrue(sized["available"])
            self.assertTrue(sized["mirror_stale"])
            self.assertIsNone(sized["mirror_source_mtime"])
            self.assertEqual(sized["mirror_source_size"], 1)
            self.assertNotIn("not-a-time", json.dumps(sized))

    def test_live_row_names_map_id_hash_and_latest_time(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            earlier = {
                "ledger_event_id": "evt-100",
                "event_type": "GENESIS",
                "prev_hash": "0" * 64,
                "row_hash": HASH_A,
                "signal_candle_open_utc": "2026-10-12T00:00:00Z",
                "signal_available_at": "2026-10-12T00:01:00Z",
                "fill_time_utc": "2026-10-12T12:00:00Z",
                "realized_pnl_cum": "0",
                "net_pnl": "0",
                "order_id": ORDER_MARKER,
            }
            last = {
                "ledger_event_id": "evt-101",
                "event_type": "NET_PNL",
                "prev_hash": HASH_A,
                "row_hash": HASH_B,
                "signal_candle_open_utc": "2026-10-12T00:00:00Z",
                "signal_available_at": "2026-10-12T00:05:00+00:00",
                "fill_time_utc": "2026-10-12T00:04:30.250000Z",
                "realized_pnl_cum": "1.25",
                "net_pnl": "0.25",
                "client_order_id": CLIENT_MARKER,
            }
            (_out(ledger) / LEDGER_NAME).write_text(_jsonl(earlier, last), encoding="utf-8")
            summary = _read_mirror(ledger)
            blob = json.dumps(summary)
            self.assertTrue(summary["available"])
            self.assertEqual(summary["counts"]["events"], 2)
            self.assertEqual(summary["counts"]["by_type"], {"GENESIS": 1, "NET_PNL": 1})
            self.assertEqual(summary["last_event_id"], "evt-101")
            self.assertEqual(summary["hash_chain_head"], HASH_B)
            self.assertEqual(summary["realized_pnl_cum"], "1.25")
            self.assertEqual(summary["last_event_time"], "2026-10-12T00:05:00+00:00")
            self.assertEqual(summary["last_event_time_field"], "signal_available_at")
            self.assertNotIn(ORDER_MARKER, blob)
            self.assertNotIn(CLIENT_MARKER, blob)
            self.assertNotIn("order_id", blob)

    def test_last_row_time_uses_fill_when_it_is_latest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            row = {
                "ledger_event_id": "evt-102",
                "event_type": "NET_PNL",
                "row_hash": HASH_A,
                "signal_available_at": "not-a-time",
                "signal_candle_open_utc": "2026-10-12 00:00:00",
                "fill_time_utc": "2026-10-12T01:00:00Z",
                "realized_pnl_cum": "2",
            }
            (_out(ledger) / LEDGER_NAME).write_text(_jsonl(row), encoding="utf-8")
            summary = _read_mirror(ledger)
            self.assertEqual(summary["last_event_id"], "evt-102")
            self.assertEqual(summary["hash_chain_head"], HASH_A)
            self.assertEqual(summary["last_event_time"], "2026-10-12T01:00:00Z")
            self.assertEqual(summary["last_event_time_field"], "fill_time_utc")

    def test_equal_times_prefer_signal_available_at(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            row = {
                "ledger_event_id": "evt-103",
                "row_hash": HASH_A,
                "event_type": "GENESIS",
                "signal_candle_open_utc": "2026-10-12T00:05:00Z",
                "fill_time_utc": "2026-10-12T00:05:00+00:00",
                "signal_available_at": "2026-10-12T00:05:00Z",
            }
            (_out(ledger) / LEDGER_NAME).write_text(_jsonl(row), encoding="utf-8")
            summary = _read_mirror(ledger)
            self.assertEqual(summary["last_event_time"], "2026-10-12T00:05:00Z")
            self.assertEqual(summary["last_event_time_field"], "signal_available_at")

    def test_only_candle_open_is_named(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            row = {
                "ledger_event_id": "evt-104",
                "row_hash": HASH_B,
                "event_type": "GENESIS",
                "signal_candle_open_utc": "2026-10-12T00:15:00Z",
            }
            (_out(ledger) / LEDGER_NAME).write_text(_jsonl(row), encoding="utf-8")
            summary = _read_mirror(ledger)
            self.assertEqual(summary["last_event_time"], "2026-10-12T00:15:00Z")
            self.assertEqual(summary["last_event_time_field"], "signal_candle_open_utc")

    def test_csv_header_uses_live_field_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            name = "anchor_fake_fill_ledger_v2_official.csv"
            body = "\n".join(
                [
                    "ledger_event_id,event_type,row_hash,signal_candle_open_utc,fill_time_utc,signal_available_at,realized_pnl_cum",
                    f"evt-105,NET_PNL,{HASH_A},2026-10-12T00:00:00Z,2026-10-12T00:02:00Z,2026-10-12T00:01:00Z,3.5",
                ]
            )
            (_out(ledger) / name).write_text(body, encoding="utf-8")
            summary = _read_mirror(ledger)
            self.assertEqual(summary["last_event_id"], "evt-105")
            self.assertEqual(summary["hash_chain_head"], HASH_A)
            self.assertEqual(summary["realized_pnl_cum"], "3.5")
            self.assertEqual(summary["last_event_time"], "2026-10-12T00:02:00Z")
            self.assertEqual(summary["last_event_time_field"], "fill_time_utc")
            self.assertEqual(summary["counts"]["header_row_mismatches"], 0)


OBS_A = "obs-pending-a"
OBS_B = "obs-pending-b"
HASH_C = "c" * 64
HASH_D = "d" * 64
HASH_E = "e" * 64
FILL_OPEN = "2026-10-12T11:00:00Z"
SIGNAL_AT = "2026-10-12T10:05:00Z"
CANDLE_OPEN = "2026-10-12T10:00:00Z"
WHEN = datetime(2026, 10, 12, 15, 0, tzinfo=timezone.utc)


def _committed(at: str, run_seq: int, ledger_events: int) -> str:
    """Host events.jsonl committed line: run_seq and cumulative ledger_events."""
    item = {
        "at": at,
        "commits": ledger_events,
        "event": "committed",
        "ledger_events": ledger_events,
        "run_seq": run_seq,
        "source_lines": ledger_events,
    }
    return json.dumps(item, sort_keys=True)


def _pending_row(event_id: str, event_hash: str, observation: str, **extra: object) -> dict:
    row = {
        "ledger_event_id": event_id,
        "row_hash": event_hash,
        "event_type": "PENDING_NEXT_BAR",
        "observation_id": observation,
        "signal_available_at": SIGNAL_AT,
        "signal_candle_open_utc": CANDLE_OPEN,
        "order_id": ORDER_MARKER,
        "event_time": "2026-10-12T13:00:00Z",
    }
    row.update(extra)
    return row


def _resolve_row(event_id: str, event_hash: str, observation: str, fill_time: str | None = FILL_OPEN) -> dict:
    row = {
        "ledger_event_id": event_id,
        "row_hash": event_hash,
        "event_type": "OPEN",
        "signal_available_at": SIGNAL_AT,
        "signal_candle_open_utc": CANDLE_OPEN,
        "realized_pnl_cum": "0",
        "order_id": ORDER_MARKER,
        "observation_id": observation,
    }
    if fill_time is not None:
        row["fill_time_utc"] = fill_time
    return row


def _write_boundaries(directory: Path, events_text: str) -> None:
    boundaries = boundaries_from_commits(parse_committed_runs(events_text))
    if not boundaries:
        raise AssertionError("fixture events.jsonl is not a usable run index")
    blob = "".join(json.dumps(item, sort_keys=True) + "\n" for item in boundaries).encode("utf-8")
    (directory / BOUNDARY_NAME).write_bytes(blob)
    digest = hashlib.sha256(blob).hexdigest()
    (directory / f"{BOUNDARY_NAME}.sha256").write_text(f"{digest}  {BOUNDARY_NAME}\n", encoding="ascii")


class PendingObservationReadTests(unittest.TestCase):
    def test_run_commit_time_collapses_repeated_pending_rows(self) -> None:
        events = "\n".join(
            [
                _committed("2026-10-12T10:10:01.250000+00:00", 1, 2),
                _committed("2026-10-12T10:20:01+00:00", 2, 4),
                _committed("2026-10-12T12:10:01+00:00", 3, 5),
            ]
        ) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            rows = [
                _pending_row("le-0001", HASH_A, OBS_A),
                _pending_row("le-0002", HASH_B, OBS_A),
                _pending_row("le-0003", HASH_C, OBS_A),
                _pending_row("le-0004", HASH_D, OBS_A),
                _resolve_row("le-0005", HASH_E, OBS_A),
            ]
            path = _out(ledger) / LEDGER_NAME
            path.write_text(_jsonl(*rows), encoding="utf-8")
            before = path.read_bytes()
            _write_boundaries(ledger, events)
            summary = _read_mirror(ledger, now=WHEN)
            blob = json.dumps(summary)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(
                summary["pending_observations"],
                {
                    "raw_rows": 4,
                    "observations": 1,
                    "runs_waited": 2,
                    "PRE_INDEX": 0,
                    "BAR_NOT_YET_CLOSED": 1,
                    "DATA_GAP": 0,
                    "IN_FLIGHT": 0,
                },
            )
            self.assertEqual(summary["counts"]["by_type"]["PENDING_NEXT_BAR"], 4)
            self.assertEqual(summary["counts"]["events"], 5)
            self.assertEqual(summary["hash_chain_head"], HASH_E)
            self.assertNotIn(OBS_A, blob)
            self.assertNotIn(ORDER_MARKER, blob)
            self.assertNotIn("run-000001", blob)

    def test_commit_at_or_after_bar_close_is_a_data_gap(self) -> None:
        for committed in ("2026-10-12T12:00:00Z", "2026-10-12T12:10:00Z"):
            with self.subTest(committed=committed):
                events = _committed(committed, 1, 1) + "\n" + _committed("2026-10-12T12:20:00Z", 2, 2) + "\n"
                with tempfile.TemporaryDirectory() as tmp:
                    ledger = Path(tmp)
                    rows = [
                        _pending_row("le-0001", HASH_A, OBS_A),
                        _resolve_row("le-0002", HASH_B, OBS_A),
                    ]
                    (_out(ledger) / LEDGER_NAME).write_text(_jsonl(*rows), encoding="utf-8")
                    _write_boundaries(ledger, events)
                    summary = _read_mirror(ledger, now=WHEN)
                    self.assertEqual(summary["pending_observations"]["DATA_GAP"], 1)
                    self.assertEqual(summary["pending_observations"]["BAR_NOT_YET_CLOSED"], 0)
                    self.assertEqual(summary["pending_observations"]["IN_FLIGHT"], 0)

    def test_unresolved_bar_still_open_is_in_flight(self) -> None:
        events = _committed("2026-10-12T10:10:01+00:00", 1, 1) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            (_out(ledger) / LEDGER_NAME).write_text(
                _jsonl(_pending_row("le-0001", HASH_A, OBS_A)),
                encoding="utf-8",
            )
            _write_boundaries(ledger, events)
            early = _read_mirror(ledger, now=datetime(2026, 10, 12, 11, 30, tzinfo=timezone.utc))
            closed = _read_mirror(ledger, now=datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc))
            self.assertEqual(early["pending_observations"]["IN_FLIGHT"], 1)
            self.assertEqual(early["pending_observations"]["DATA_GAP"], 0)
            self.assertEqual(closed["pending_observations"]["IN_FLIGHT"], 0)
            self.assertEqual(closed["pending_observations"]["DATA_GAP"], 1)

    def test_pending_row_past_the_last_commit_is_not_given_a_write_time(self) -> None:
        events = _committed("2026-10-12T10:10:01+00:00", 1, 1) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            rows = [
                _pending_row("le-0001", HASH_A, OBS_A),
                _pending_row("le-0002", HASH_B, OBS_A),
            ]
            path = _out(ledger) / LEDGER_NAME
            path.write_text(_jsonl(*rows), encoding="utf-8")
            before = path.read_bytes()
            _write_boundaries(ledger, events)
            summary = _read_mirror(ledger, now=datetime(2026, 10, 12, 11, 30, tzinfo=timezone.utc))
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(summary["counts"]["by_type"]["PENDING_NEXT_BAR"], 2)
            self.assertEqual(summary["counts"]["events"], 2)
            self.assertEqual(
                summary["pending_observations"],
                {"raw_rows": 2, "observations": 1, "runs_waited": 2},
            )
            self.assertNotIn("IN_FLIGHT", summary["pending_observations"])
            self.assertNotIn("PRE_INDEX", summary["pending_observations"])

    def test_missing_run_boundaries_reports_counts_without_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            rows = [
                _pending_row("le-0001", HASH_A, OBS_A),
                _pending_row("le-0002", HASH_B, OBS_A),
                _pending_row("le-0003", HASH_C, OBS_B),
            ]
            (_out(ledger) / LEDGER_NAME).write_text(_jsonl(*rows), encoding="utf-8")
            summary = _read_mirror(ledger, now=WHEN)
            self.assertEqual(
                summary["pending_observations"],
                {"raw_rows": 3, "observations": 2, "runs_waited": 3},
            )
            self.assertNotIn("BAR_NOT_YET_CLOSED", summary["pending_observations"])
            self.assertNotIn("DATA_GAP", summary["pending_observations"])
            self.assertNotIn("IN_FLIGHT", summary["pending_observations"])

    def test_resolving_row_before_the_pending_does_not_count(self) -> None:
        events = "\n".join(
            [_committed("2026-10-12T09:10:01+00:00", 1, 1), _committed("2026-10-12T10:10:01+00:00", 2, 2)]
        ) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            rows = [
                _resolve_row("le-0001", HASH_A, OBS_A),
                _pending_row("le-0002", HASH_B, OBS_A),
            ]
            (_out(ledger) / LEDGER_NAME).write_text(_jsonl(*rows), encoding="utf-8")
            _write_boundaries(ledger, events)
            summary = _read_mirror(ledger, now=datetime(2026, 10, 12, 11, 30, tzinfo=timezone.utc))
            self.assertEqual(summary["pending_observations"]["IN_FLIGHT"], 1)
            self.assertEqual(summary["pending_observations"]["BAR_NOT_YET_CLOSED"], 0)

    def test_ledger_without_pending_rows_reports_zero_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)
            (_out(ledger) / LEDGER_NAME).write_text(_jsonl(_event("evt-1", HASH_A)), encoding="utf-8")
            summary = _read_mirror(ledger)
            self.assertEqual(
                summary["pending_observations"],
                {
                    "raw_rows": 0,
                    "observations": 0,
                    "runs_waited": 0,
                    "PRE_INDEX": 0,
                    "BAR_NOT_YET_CLOSED": 0,
                    "DATA_GAP": 0,
                    "IN_FLIGHT": 0,
                },
            )


