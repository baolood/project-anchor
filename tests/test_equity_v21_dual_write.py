"""Equity v2.1 dual-write. Default off. Legacy CSV and Line A stay untouched."""

from __future__ import annotations

import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from eval_recording.equity_v21_dual_write import (
    EQUITY_V21_COLUMNS,
    HEADER_COLUMN_COUNT,
    LEGACY_EQUITY_FILENAME,
    MARK_RULE_BOUND,
    MARK_RULE_UNBOUND,
    NEW_EQUITY_FILENAME,
    SAMPLE_CLASS_NON_SCORING,
    SCHEMA_VERSION,
    EquityDualWriteError,
    LegacyEquityImmutable,
    SealedLedgerWriteRefused,
    assert_csv_column_equality,
    dual_write_enabled,
    genesis_row,
    header_line,
    record_equity_v21,
)


def _genesis() -> dict[str, str]:
    return genesis_row(
        timestamp_utc="2026-04-20T00:00:00Z",
        net_liquidation_equity="10000",
        cash_reserve="10000",
        sample_class=SAMPLE_CLASS_NON_SCORING,
    )


def _row() -> dict[str, str]:
    return {
        "schema_version": SCHEMA_VERSION,
        "timestamp_utc": "2026-04-20T02:00:00Z",
        "observation_id": "obs-1",
        "position": "LONG",
        "realized_pnl": "0",
        "unrealized_pnl": "1",
        "net_liquidation_equity": "10001",
        "drawdown": "0",
        "exposure": "1",
        "cash_reserve": "9000",
        "active_notional": "1000",
        "mark_rule_id": MARK_RULE_BOUND,
        "sample_class": SAMPLE_CLASS_NON_SCORING,
    }


class EquityV21DualWriteTest(unittest.TestCase):
    def test_header_and_genesis_share_thirteen_columns(self) -> None:
        self.assertEqual(HEADER_COLUMN_COUNT, 13)
        self.assertEqual(len(EQUITY_V21_COLUMNS), 13)
        self.assertEqual(header_line().split(","), list(EQUITY_V21_COLUMNS))
        genesis = _genesis()
        self.assertEqual(list(genesis), list(EQUITY_V21_COLUMNS))
        self.assertEqual(len(genesis), len(EQUITY_V21_COLUMNS))
        self.assertEqual(genesis["schema_version"], SCHEMA_VERSION)
        self.assertEqual(genesis["mark_rule_id"], MARK_RULE_UNBOUND)
        self.assertNotEqual(genesis["mark_rule_id"], MARK_RULE_BOUND)
        self.assertEqual(genesis["observation_id"], "LEDGER_GENESIS")
        self.assertEqual(genesis["position"], "FLAT")

    def test_default_off_does_not_create_a_file(self) -> None:
        self.assertFalse(dual_write_enabled(environ={}))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / NEW_EQUITY_FILENAME
            result = record_equity_v21(
                path,
                _row(),
                genesis=_genesis(),
                environ={},
            )
            self.assertFalse(result["written"])
            self.assertEqual(result["reason"], "DISABLED")
            self.assertFalse(path.exists())

    def test_explicit_off_beats_env_and_cli(self) -> None:
        self.assertFalse(
            dual_write_enabled(
                enabled=False,
                environ={"AFFL_EQUITY_V21_DUAL_WRITE": "1"},
                argv=["--equity-v21-dual-write"],
            )
        )

    def test_env_and_cli_can_turn_the_helper_on(self) -> None:
        self.assertTrue(dual_write_enabled(environ={"AFFL_EQUITY_V21_DUAL_WRITE": "1"}))
        self.assertTrue(dual_write_enabled(environ={}, argv=["--equity-v21-dual-write"]))
        self.assertFalse(dual_write_enabled(environ={"AFFL_EQUITY_V21_DUAL_WRITE": "true"}))
        with mock.patch.dict(os.environ, {"AFFL_EQUITY_V21_DUAL_WRITE": "1"}):
            self.assertTrue(dual_write_enabled())

    def test_enabled_file_keeps_header_and_body_width_equal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / NEW_EQUITY_FILENAME
            created = record_equity_v21(path, _row(), genesis=_genesis(), enabled=True)
            self.assertTrue(created["created"])
            text = path.read_text(encoding="utf-8")
            self.assertEqual(assert_csv_column_equality(text), 13)
            rows = list(csv.reader(text.splitlines()))
            self.assertEqual(rows[0], list(EQUITY_V21_COLUMNS))
            self.assertEqual(len(rows), 3)
            for body in rows[1:]:
                self.assertEqual(len(body), len(rows[0]))
            self.assertEqual(rows[1][2], "LEDGER_GENESIS")
            before = path.read_text(encoding="utf-8")
            second = dict(_row())
            second["observation_id"] = "obs-2"
            second["timestamp_utc"] = "2026-04-20T03:00:00Z"
            appended = record_equity_v21(path, second, enabled=True)
            self.assertEqual(appended["reason"], "APPENDED")
            after = path.read_text(encoding="utf-8")
            self.assertTrue(after.startswith(before))
            self.assertEqual(assert_csv_column_equality(after), 13)
            self.assertEqual(len(list(csv.reader(after.splitlines()))), 4)

    def test_mismatched_body_is_rejected(self) -> None:
        text = header_line() + "\nequity_v2_1,only,three\n"
        with self.assertRaises(EquityDualWriteError):
            assert_csv_column_equality(text)

    def test_legacy_headers_are_not_the_v21_path(self) -> None:
        legacy_6 = "timestamp_utc,equity,realized_pnl,unrealized_pnl,position,event\n"
        legacy_10 = (
            "timestamp_utc,observation_id,position,realized_pnl,unrealized_pnl,"
            "net_liquidation_equity,drawdown,exposure,cash_reserve,active_notional\n"
        )
        for text in (legacy_6, legacy_10):
            with self.assertRaises(EquityDualWriteError):
                assert_csv_column_equality(text)

    def test_legacy_file_is_not_opened_for_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / LEGACY_EQUITY_FILENAME
            path.write_text("legacy-sentinel\n", encoding="utf-8")
            with self.assertRaises(LegacyEquityImmutable):
                record_equity_v21(path, _row(), genesis=_genesis(), enabled=True)
            self.assertEqual(path.read_text(encoding="utf-8"), "legacy-sentinel\n")

    def test_existing_wrong_width_is_not_rewritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / NEW_EQUITY_FILENAME
            path.write_text(
                "timestamp_utc,equity,realized_pnl,unrealized_pnl,position,event\n"
                "t,1,0,0,FLAT,GENESIS\n",
                encoding="utf-8",
            )
            before = path.read_bytes()
            with self.assertRaises(EquityDualWriteError):
                record_equity_v21(path, _row(), enabled=True)
            self.assertEqual(path.read_bytes(), before)

    def test_sealed_line_a_path_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = (
                Path(tmp)
                / "affl-v2-official-ledger"
                / "out"
                / NEW_EQUITY_FILENAME
            )
            with self.assertRaises(SealedLedgerWriteRefused):
                record_equity_v21(path, _row(), genesis=_genesis(), enabled=True)
            self.assertFalse(path.exists())

    def test_symlink_onto_legacy_file_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / LEGACY_EQUITY_FILENAME
            legacy.write_text("legacy-sentinel\n", encoding="utf-8")
            link = root / NEW_EQUITY_FILENAME
            link.symlink_to(legacy)
            with self.assertRaises(LegacyEquityImmutable):
                record_equity_v21(link, _row(), genesis=_genesis(), enabled=True)
            self.assertEqual(legacy.read_text(encoding="utf-8"), "legacy-sentinel\n")

    def test_second_genesis_is_not_appended(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / NEW_EQUITY_FILENAME
            record_equity_v21(path, _genesis(), enabled=True)
            before = path.read_bytes()
            with self.assertRaises(EquityDualWriteError):
                record_equity_v21(path, _genesis(), enabled=True)
            self.assertEqual(path.read_bytes(), before)

    def test_append_keeps_a_file_that_had_no_trailing_newline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / NEW_EQUITY_FILENAME
            record_equity_v21(path, _genesis(), enabled=True)
            text = path.read_text(encoding="utf-8").rstrip("\n")
            path.write_text(text, encoding="utf-8")
            record_equity_v21(path, _row(), enabled=True)
            after = path.read_text(encoding="utf-8")
            self.assertTrue(after.startswith(text + "\n"))
            self.assertEqual(assert_csv_column_equality(after), 13)

    def test_birth_requires_genesis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / NEW_EQUITY_FILENAME
            with self.assertRaises(EquityDualWriteError):
                record_equity_v21(path, _row(), enabled=True)
            self.assertFalse(path.exists())

    def test_other_filenames_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "equity.csv"
            with self.assertRaises(EquityDualWriteError):
                record_equity_v21(path, _row(), enabled=True)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
