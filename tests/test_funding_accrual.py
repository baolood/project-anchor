"""PF_XBTUSD accrual fixtures. Live writer funding_pnl stays off."""

from __future__ import annotations

import ast
import io
import json
import math
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from eval_recording.funding.accrual import AccrualResult, accrue, rates_map_from_records
from eval_recording.funding.fetch_pf_xbtusd_funding import detect_gaps, main
from eval_recording.funding.recording import (
    LIVE_FUNDING_INGEST_ENABLED,
    recording_funding_fields,
    writer_funding_record,
)

FIX = Path(__file__).resolve().parents[1] / "eval_recording" / "funding" / "fixtures"


def _parse(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


class AccrualFixtureTest(unittest.TestCase):
    def test_present_12h_contiguous(self) -> None:
        doc = json.loads((FIX / "accrual_present_12h.json").read_text(encoding="utf-8"))
        rates = rates_map_from_records(doc["rates"])
        first = doc["rates"][0]["timestamp"]
        last = doc["rates"][-1]["timestamp"]
        entry = (_parse(first) - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        notional = 10000.0
        result = accrue(
            side="LONG",
            position_notional_usd=notional,
            entry_time_utc=entry,
            exit_time_utc=last,
            rates_by_ts=rates,
        )
        self.assertEqual(result.status, "PRESENT")
        self.assertEqual(result.n_expected, 12)
        self.assertEqual(result.n_present, 12)
        self.assertIsNotNone(result.funding_pnl)
        expected_pnl = -sum(
            float(item["relativeFundingRate"]) * notional for item in doc["rates"]
        )
        self.assertTrue(math.isclose(result.funding_pnl, expected_pnl, rel_tol=1e-12, abs_tol=1e-9))
        short = accrue(
            side="SHORT",
            position_notional_usd=notional,
            entry_time_utc=entry,
            exit_time_utc=last,
            rates_by_ts=rates,
        )
        self.assertEqual(short.status, "PRESENT")
        self.assertTrue(
            math.isclose(short.funding_pnl, -expected_pnl, rel_tol=1e-12, abs_tol=1e-9)
        )

    def test_partial_never_zero_fill(self) -> None:
        doc = json.loads(
            (FIX / "accrual_partial_gap_synthetic.json").read_text(encoding="utf-8")
        )
        rates = rates_map_from_records(doc["rates_available"])
        hold = doc["hold"]
        result = accrue(
            side=hold["side"],
            position_notional_usd=hold["position_notional_usd"],
            entry_time_utc=hold["entry_time_utc"],
            exit_time_utc=hold["exit_time_utc"],
            rates_by_ts=rates,
        )
        self.assertEqual(result.status, doc["expected_status"])
        self.assertEqual(result.status, "PARTIAL")
        self.assertIsNone(result.funding_pnl)
        self.assertIn("2026-01-15T03:00:00Z", result.missing_timestamps)
        self.assertNotIn("2026-01-15T03:00:00Z", rates)

    def test_missing_empty(self) -> None:
        doc = json.loads((FIX / "accrual_missing_empty.json").read_text(encoding="utf-8"))
        hold = doc["hold"]
        result = accrue(
            side=hold["side"],
            position_notional_usd=hold["position_notional_usd"],
            entry_time_utc=hold["entry_time_utc"],
            exit_time_utc=hold["exit_time_utc"],
            rates_by_ts={},
        )
        self.assertEqual(result.status, "MISSING")
        self.assertIsNone(result.funding_pnl)
        self.assertGreater(result.n_expected, 0)
        self.assertEqual(result.n_present, 0)

    def test_retrieved_zero_is_present_on_the_candidate_only(self) -> None:
        result = accrue(
            side="LONG",
            position_notional_usd=10000.0,
            entry_time_utc="2026-01-15T00:30:00Z",
            exit_time_utc="2026-01-15T01:00:00Z",
            rates_by_ts={"2026-01-15T01:00:00Z": 0.0},
        )
        self.assertEqual(result.status, "PRESENT")
        self.assertTrue(math.isclose(result.funding_pnl, 0.0, abs_tol=1e-12))
        record = writer_funding_record(result, net_pnl_ex_funding=4.0)
        self.assertEqual(record["FUNDING_DATA_STATUS"], "PRESENT")
        self.assertIsNone(record["funding_pnl"])
        self.assertEqual(record["NET_PNL_STATUS"], "EX_FUNDING")
        self.assertEqual(record["NET_PNL_EX_FUNDING"], 4.0)
        self.assertIsNone(record["NET_PNL_INCL_FUNDING"])
        self.assertEqual(record["live_funding_ingest"], "OFF")
        self.assertTrue(math.isclose(record["diagnostic_relative_funding_pnl"], 0.0, abs_tol=1e-12))


class WriterFundingOffTest(unittest.TestCase):
    def test_live_ingest_constant_stays_off(self) -> None:
        self.assertFalse(LIVE_FUNDING_INGEST_ENABLED)
        doc = json.loads((FIX / "accrual_present_12h.json").read_text(encoding="utf-8"))
        rates = rates_map_from_records(doc["rates"])
        first = doc["rates"][0]["timestamp"]
        last = doc["rates"][-1]["timestamp"]
        entry = (_parse(first) - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        record = recording_funding_fields(
            side="LONG",
            position_notional_usd=10000.0,
            entry_time_utc=entry,
            exit_time_utc=last,
            rates_by_ts=rates,
            net_pnl_ex_funding=1.5,
        )
        self.assertEqual(record["FUNDING_DATA_STATUS"], "PRESENT")
        self.assertIsNone(record["funding_pnl"])
        self.assertEqual(record["NET_PNL_STATUS"], "EX_FUNDING")
        self.assertIsNone(record["NET_PNL_INCL_FUNDING"])
        self.assertEqual(record["selected_for_scoring"], "NO")
        self.assertEqual(record["official_sign_lock"], "NO")
        self.assertTrue(record["not_a_score"])
        self.assertIsNotNone(record["diagnostic_relative_funding_pnl"])

    def test_partial_writer_record_has_null_amount(self) -> None:
        doc = json.loads(
            (FIX / "accrual_partial_gap_synthetic.json").read_text(encoding="utf-8")
        )
        record = recording_funding_fields(
            side=doc["hold"]["side"],
            position_notional_usd=doc["hold"]["position_notional_usd"],
            entry_time_utc=doc["hold"]["entry_time_utc"],
            exit_time_utc=doc["hold"]["exit_time_utc"],
            rates_by_ts=rates_map_from_records(doc["rates_available"]),
        )
        self.assertEqual(record["FUNDING_DATA_STATUS"], "PARTIAL")
        self.assertIsNone(record["funding_pnl"])
        self.assertIsNone(record["diagnostic_relative_funding_pnl"])
        self.assertIn("2026-01-15T03:00:00Z", record["missing_timestamps"])

    def test_turning_the_ingest_constant_on_still_refuses(self) -> None:
        result = AccrualResult(
            status="PRESENT",
            funding_pnl=1.0,
            n_expected=1,
            n_present=1,
            missing_timestamps=(),
            used_timestamps=("2026-01-15T01:00:00Z",),
        )
        with mock.patch(
            "eval_recording.funding.recording.LIVE_FUNDING_INGEST_ENABLED",
            True,
        ):
            with self.assertRaises(RuntimeError):
                writer_funding_record(result)

    def test_recording_modules_do_not_import_the_network_or_the_scorer(self) -> None:
        root = Path(__file__).resolve().parents[1] / "eval_recording"
        for name in ("__init__.py", "equity_v21_dual_write.py"):
            self._assert_offline(root / name)
        self._assert_offline(root / "funding" / "__init__.py")
        self._assert_offline(root / "funding" / "accrual.py")
        self._assert_offline(root / "funding" / "recording.py")

    def _assert_offline(self, path: Path) -> None:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            else:
                continue
            for name in names:
                self.assertNotIn(name, {"urllib", "requests", "http", "socket", "eval_scoring"})


class FetchGapTest(unittest.TestCase):
    def test_detect_gaps_lists_missing_hours_without_a_zero_rate(self) -> None:
        gaps = detect_gaps(
            [
                {"timestamp": "2026-01-15T01:00:00Z"},
                {"timestamp": "2026-01-15T02:00:00Z"},
                {"timestamp": "2026-01-15T04:00:00Z"},
            ]
        )
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["missing_timestamps"], ["2026-01-15T03:00:00Z"])
        self.assertNotIn("relativeFundingRate", gaps[0])

    def test_public_fetch_writes_gap_records_and_not_zero_rates(self) -> None:
        body = json.dumps(
            {
                "result": "success",
                "serverTime": "2026-01-15T04:00:00.00Z",
                "rates": [
                    {
                        "timestamp": "2026-01-15T01:00:00Z",
                        "fundingRate": 1.0,
                        "relativeFundingRate": 1e-5,
                    },
                    {
                        "timestamp": "2026-01-15T02:00:00Z",
                        "fundingRate": -2.0,
                        "relativeFundingRate": -2e-5,
                    },
                    {
                        "timestamp": "2026-01-15T04:00:00Z",
                        "fundingRate": 1.5,
                        "relativeFundingRate": 1.5e-5,
                    },
                ],
            }
        ).encode("utf-8")

        class _Response:
            status = 200

            def read(self) -> bytes:
                return body

            def __enter__(self) -> "_Response":
                return self

            def __exit__(self, *args: object) -> bool:
                return False

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            with mock.patch(
                "eval_recording.funding.fetch_pf_xbtusd_funding.urllib.request.urlopen",
                return_value=_Response(),
            ):
                with mock.patch(
                    "sys.argv",
                    ["fetch_pf_xbtusd_funding.py", "--out-dir", str(out)],
                ):
                    with redirect_stdout(io.StringIO()):
                        self.assertEqual(main(), 0)
            cache = (out / "cache" / "PF_XBTUSD_historicalfundingrates.jsonl").read_text(
                encoding="utf-8"
            )
            rows = [json.loads(line) for line in cache.splitlines() if line]
            rate_stamps = [row["timestamp"] for row in rows if row["record_type"] == "RATE"]
            gaps = [row for row in rows if row["record_type"] == "GAP"]
            self.assertEqual(
                rate_stamps,
                [
                    "2026-01-15T01:00:00Z",
                    "2026-01-15T02:00:00Z",
                    "2026-01-15T04:00:00Z",
                ],
            )
            self.assertEqual(gaps[0]["missing_timestamps"], ["2026-01-15T03:00:00Z"])
            self.assertNotIn("2026-01-15T03:00:00Z", rate_stamps)
            self.assertTrue(all(row.get("relativeFundingRate") != 0 for row in rows if row["record_type"] == "RATE"))
            summary = json.loads(
                (out / "cache" / "PF_XBTUSD_gaps_summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(summary["zero_fill_policy"], "FORBIDDEN")
            self.assertEqual(summary["n_missing_hours"], 1)


if __name__ == "__main__":
    unittest.main()
