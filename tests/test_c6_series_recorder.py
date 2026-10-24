"""C6 series recorder. Temp-dir only. DEPLOY=NO. Does not touch Line A."""

from __future__ import annotations

import contextlib
import csv
import io
import json
import stat
import unittest
from pathlib import Path

from ops.passline.c6_series_recorder import SeriesRootRefused, main, run_series


ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE = ROOT / "governance" / "ANCHOR_C9_GOVERNANCE_REGISTER.jsonl"
FREEZE = ROOT / "docs" / "PROJECT_ANCHOR_PASS_LINE_V1_1_FREEZE_RECORD.md"
LEGACY_NAME = "anchor_fake_fill_equity_v2_official.csv"
INVENTED_MARK = "999999.123"
T0 = "2026-10-24T01:13:00Z"
T1 = "2026-10-24T02:13:00Z"


def _mark_ok() -> dict:
    return {"status": "RECORDED", "markPrice": "67000.5"}


def _funding_ok() -> dict:
    return {
        "result": "success",
        "rates": [
            {
                "timestamp": "2026-10-24T00:00:00Z",
                "fundingRate": 0.01,
                "relativeFundingRate": 0.0001,
            },
            {
                "timestamp": "2026-10-24T02:00:00Z",
                "fundingRate": -0.02,
                "relativeFundingRate": -0.0002,
            },
            {
                "timestamp": "2026-10-24T03:00:00Z",
                "fundingRate": None,
                "relativeFundingRate": 0.0003,
            },
        ],
    }


def _boom() -> dict:
    raise OSError("fetch failed")


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _funding_pnl_values(root: Path) -> list[object]:
    found: list[object] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in {".json", ".jsonl"}:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict) and "funding_pnl" in payload:
                found.append(payload["funding_pnl"])
    return found


class C6SeriesRecorderTest(unittest.TestCase):
    def setUp(self) -> None:
        self._governance = GOVERNANCE.read_bytes()
        self._freeze = FREEZE.read_bytes()

    def tearDown(self) -> None:
        self.assertEqual(GOVERNANCE.read_bytes(), self._governance)
        self.assertEqual(FREEZE.read_bytes(), self._freeze)

    def test_genesis_created_then_appended(self) -> None:
        with self._temp() as root:
            legacy = root / LEGACY_NAME
            legacy.write_text("legacy-sentinel\n", encoding="utf-8")
            sealed = root / "affl-v2-official-ledger" / "sealed.txt"
            sealed.parent.mkdir()
            sealed.write_text("line-a\n", encoding="utf-8")
            first = run_series(root, now=T0, fetch_mark=_mark_ok, fetch_funding=_funding_ok)
            second = run_series(root, now=T1, fetch_mark=_mark_ok, fetch_funding=_funding_ok)
            self.assertEqual(first["equity_reason"], "CREATED")
            self.assertEqual(second["equity_reason"], "APPENDED")
            self.assertEqual(first["scoring_status"], "NON_SCORING")
            self.assertEqual(first["position_state"], "FLAT")
            self.assertIsNone(first["funding_pnl"])
            self.assertIsNone(second["funding_pnl"])
            self.assertFalse(first["funding_zero_filled"])
            self.assertEqual(first["open_legs"], "NO_OPEN_LEGS")
            self.assertEqual(first["events"], "EMPTY")
            self.assertEqual(second["events"], "EMPTY")
            self.assertEqual(first["events_writer"], "NO_C6_WRITER")
            self.assertEqual(first["governance"], "DEPLOY_RECORDED")
            self.assertEqual(second["governance"], "DEPLOY_PRESENT")

            series = root / "affl-v2-official-ledger-c6"
            equity = series / "out" / "anchor_fake_fill_equity_v2_1_official.csv"
            with equity.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["observation_id"], "LEDGER_GENESIS")
            self.assertEqual(rows[0]["position"], "FLAT")
            self.assertEqual(rows[0]["net_liquidation_equity"], "10000")
            self.assertEqual(rows[0]["mark_rule_id"], "UNBOUND")
            self.assertEqual(rows[0]["sample_class"], "NON_SCORING")
            self.assertEqual(rows[1]["position"], "FLAT")
            self.assertEqual(rows[1]["sample_class"], "NON_SCORING")
            self.assertNotEqual(rows[1]["observation_id"], "LEDGER_GENESIS")
            events = (series / "out" / "c6_events.jsonl").read_bytes()
            self.assertEqual(events, b"")
            self.assertEqual(legacy.read_text(encoding="utf-8"), "legacy-sentinel\n")
            self.assertEqual(sealed.read_text(encoding="utf-8"), "line-a\n")
            deploy = _load_jsonl(series / "governance" / "C9_SERIES_REGISTER.jsonl")
            self.assertEqual(len(deploy), 1)
            self.assertEqual(deploy[0]["record_type"], "DEPLOY")
            self.assertIsNone(deploy[0]["funding_pnl"])
            self.assertTrue(deploy[0]["not_a_c9_attestation"])
            for value in _funding_pnl_values(root):
                self.assertIsNone(value)

    def test_mark_missing_is_not_invented(self) -> None:
        with self._temp() as root:
            result = run_series(root, now=T0, fetch_mark=_boom, fetch_funding=_funding_ok)
            self.assertEqual(result["mark_status"], "MARK_MISSING")
            self.assertIsNone(result["funding_pnl"])
            marks = _load_jsonl(
                root / "affl-v2-official-ledger-c6" / "marks" / "pf_xbtusd_marks.jsonl"
            )
            self.assertEqual(len(marks), 1)
            self.assertEqual(marks[0]["status"], "MARK_MISSING")
            self.assertIsNone(marks[0]["markPrice"])
            self.assertFalse(marks[0]["invented"])
            self.assertIsNone(marks[0]["funding_pnl"])
            tree = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*") if path.is_file())
            self.assertNotIn(INVENTED_MARK, tree)

    def test_funding_gap_is_not_zero_filled(self) -> None:
        with self._temp() as root:
            run_series(root, now=T0, fetch_mark=_mark_ok, fetch_funding=_funding_ok)
            cache = root / "funding-cache" / "PF_XBTUSD_historicalfundingrates.jsonl"
            rows = _load_jsonl(cache)
            rates = [row for row in rows if row["record_type"] == "RATE"]
            gaps = [row for row in rows if row["record_type"] == "GAP"]
            stamps = {row["timestamp"] for row in rates}
            self.assertEqual(stamps, {"2026-10-24T00:00:00Z", "2026-10-24T02:00:00Z"})
            self.assertNotIn("2026-10-24T01:00:00Z", stamps)
            self.assertNotIn("2026-10-24T03:00:00Z", stamps)
            self.assertTrue(gaps)
            missing = set(gaps[0]["missing_timestamps"])
            self.assertIn("2026-10-24T01:00:00Z", missing)
            self.assertIn("2026-10-24T03:00:00Z", missing)
            for row in rates:
                self.assertNotEqual(row["fundingRate"], "0")
                self.assertNotEqual(row["fundingRate"], 0)
            text = cache.read_text(encoding="utf-8")
            self.assertNotIn('"fundingRate":0', text)
            self.assertNotIn('"fundingRate":"0"', text)
            for value in _funding_pnl_values(root):
                self.assertIsNone(value)

    def test_funding_fetch_failure_leaves_the_cache_and_does_not_invent_zeros(self) -> None:
        with self._temp() as root:
            run_series(root, now=T0, fetch_mark=_mark_ok, fetch_funding=_funding_ok)
            cache = root / "funding-cache" / "PF_XBTUSD_historicalfundingrates.jsonl"
            before = cache.read_bytes()
            result = run_series(root, now=T1, fetch_mark=_mark_ok, fetch_funding=_boom)
            self.assertIsNone(result["funding_pnl"])
            self.assertFalse(result["funding_zero_filled"])
            self.assertEqual(cache.read_bytes(), before)
            self.assertNotIn(b'"fundingRate":0', before)
            fail = root / "funding-cache" / "PF_XBTUSD_last_fetch_fail.json"
            self.assertFalse(fail.exists())

    def test_fresh_funding_failure_writes_a_fail_record_without_a_zero_rate(self) -> None:
        with self._temp() as root:
            result = run_series(root, now=T0, fetch_mark=_boom, fetch_funding=_boom)
            self.assertEqual(result["mark_status"], "MARK_MISSING")
            self.assertIsNone(result["funding_pnl"])
            cache = root / "funding-cache" / "PF_XBTUSD_historicalfundingrates.jsonl"
            self.assertFalse(cache.exists())
            fail = json.loads((root / "funding-cache" / "PF_XBTUSD_last_fetch_fail.json").read_text(encoding="utf-8"))
            self.assertEqual(fail["record_type"], "FETCH_FAIL")
            self.assertEqual(fail["policy"], "NEVER_ZERO_FILL")
            self.assertIsNone(fail["funding_pnl"])
            self.assertNotIn("fundingRate", fail)
            self.assertNotIn("rates", fail)

    def test_line_a_roots_are_refused_before_write(self) -> None:
        with self._temp() as root:
            for name in (
                "affl-v2-official-ledger",
                "anchor-official-ledger",
                "anchor-official-ledger-20261010",
            ):
                target = root / name
                target.mkdir()
                with self.assertRaises(SeriesRootRefused):
                    run_series(target, now=T0, fetch_mark=_boom, fetch_funding=_boom)
                self.assertEqual(list(target.iterdir()), [])
            with contextlib.redirect_stderr(io.StringIO()):
                code = main(["--root", str(root / "affl-v2-official-ledger")])
            self.assertEqual(code, 2)

    def test_templates_match_the_host_wire(self) -> None:
        service = (ROOT / "docs" / "templates" / "anchor-official-ledger-c6.service").read_text(encoding="utf-8")
        timer = (ROOT / "docs" / "templates" / "anchor-official-ledger-c6.timer").read_text(encoding="utf-8")
        drop_in = (
            ROOT / "docs" / "templates" / "anchor-control-mcp.service.d" / "30-c6-series.conf"
        ).read_text(encoding="utf-8")
        rollback = (ROOT / "docs" / "templates" / "ROLLBACK_HOST_WIRE.sh").read_text(encoding="utf-8")
        self.assertIn("User=anchor-c6", service)
        self.assertIn("Group=anchor-mcp", service)
        self.assertIn("/opt/anchor-passline-host/bin/c6_series_recorder.py", service)
        self.assertIn("PYTHONPATH=/opt/project-anchor-passline", service)
        self.assertIn("InaccessiblePaths=/var/lib/private", service)
        self.assertIn("DEPLOY=NO", service)
        self.assertIn("OnCalendar=*-*-* *:13:00 UTC", timer)
        self.assertIn("ReadOnlyPaths=/var/lib/anchor-passline", drop_in)
        self.assertIn(
            "ANCHOR_CONTROL_MCP_C6_SERIES_DIR=/var/lib/anchor-passline/affl-v2-official-ledger-c6",
            drop_in,
        )
        service_units = drop_in.split("ANCHOR_CONTROL_MCP_SERVICE_UNITS=", 1)[1].splitlines()[0]
        timer_units = drop_in.split("ANCHOR_CONTROL_MCP_TIMER_UNITS=", 1)[1].splitlines()[0]
        self.assertLessEqual(len(service_units.split(",")), 8)
        self.assertLessEqual(len(timer_units.split(",")), 8)
        self.assertIn("anchor-official-ledger-c6.service", service_units)
        self.assertIn("anchor-official-ledger-c6.timer", timer_units)
        self.assertIn("rm -f /etc/systemd/system/anchor-official-ledger-c6.service", rollback)
        self.assertIn("rm -f /etc/systemd/system/anchor-control-mcp.service.d/30-c6-series.conf", rollback)
        self.assertNotIn("rm -rf /var/lib/private", rollback)
        self.assertNotIn("rm -f /etc/systemd/system/anchor-official-ledger.service\n", rollback)
        self.assertIn("SERIES_DATA_REMOVED=NO", rollback)
        self.assertIn("LINE_A_TOUCHED=NO", rollback)
        mode = stat.S_IMODE((ROOT / "docs" / "templates" / "ROLLBACK_HOST_WIRE.sh").stat().st_mode)
        self.assertTrue(mode & stat.S_IXUSR)

    def _temp(self):
        return tempfile_cm(self)


class _Temp:
    def __init__(self) -> None:
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()

    def __enter__(self) -> Path:
        return Path(self._tmp.name)

    def __exit__(self, exc_type, exc, tb) -> None:
        self._tmp.cleanup()


def tempfile_cm(_test: unittest.TestCase) -> _Temp:
    return _Temp()


if __name__ == "__main__":
    unittest.main()
