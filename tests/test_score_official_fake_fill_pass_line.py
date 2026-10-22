"""Unit tests for the offline Official Fake-Fill pass-line scorer."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from eval_scoring.line_a_pass_line import FROZEN_T0, ScoringRefusal, score_ledger_file, score_rows
from eval_scoring.official_v2_row_hash import (
    GENESIS_PREV_HASH,
    GOVERNANCE_GENESIS_PREV_HASH,
    seal_chain,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCORER = PROJECT_ROOT / "scripts" / "score_official_fake_fill_pass_line.py"
C9_TEMPLATE = PROJECT_ROOT / "docs" / "templates" / "ANCHOR_C9_GOVERNANCE_REGISTER_TEMPLATE.jsonl"
T0 = "2026-01-01T00:00:00Z"
T_SCORE = "2026-04-01T00:00:00Z"
CST = timezone(timedelta(hours=8))


def _chain(rows: list[dict]) -> list[dict]:
    prepared: list[dict] = []
    for index, row in enumerate(rows, start=1):
        item = dict(row)
        item["ledger_event_id"] = f"le-{index:06d}"
        prepared.append(item)
    return seal_chain(prepared, GENESIS_PREV_HASH)


def _attest(**overrides: object) -> dict:
    row: dict = {
        "record_type": "ATTEST_COVERAGE",
        "id": "gov-000001",
        "time_utc": "2026-04-01T00:00:00Z",
        "criterion": "C9",
        "rule": "C9",
        "description": "test coverage attestation",
        "recorder": "founder-test",
        "window_start": "2025-01-01T00:00:00Z",
        "window_end": "2027-01-01T00:00:00Z",
        "founder_signed": True,
    }
    row.update(overrides)
    return row


def _open(at: str, *, signal: str | None = None, equity: str = "10000") -> dict:
    opened = datetime.fromisoformat(at.replace("Z", "+00:00"))
    signal_at = signal or (opened - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "event_type": "OPEN",
        "fill_time_utc": at,
        "signal_available_at": signal_at,
        "signal_candle_open_utc": signal_at,
        "side": "LONG",
        "quantity": "1",
        "effective_price": "100",
        "signal_price": "1",
        "reference_price": "1",
        "fee_paid": "1",
        "slippage_cost": "1",
        "net_liquidation_equity": equity,
        "drawdown": "0.99",
        "realized_pnl_cum": "999999",
        "preset_stop_price": "99",
        "equity_at_open": "10000",
        "risk_amount": "50",
        "FUNDING_DATA_STATUS": "MISSING",
        "funding_pnl": None,
    }


def _exit(at: str, *, trade_net: str, gross: str, price: str, funding: str | None = "0") -> dict:
    """`trade_net` is the round-trip net before funding. Exit NET excludes entry costs of 2."""
    exit_net = str(Decimal(trade_net) + Decimal(2))
    return {
        "event_type": "FLAT_EXIT",
        "fill_time_utc": at,
        "signal_available_at": at,
        "signal_candle_open_utc": at,
        "side": "LONG",
        "quantity": "1",
        "effective_price": price,
        "signal_price": "1",
        "fee_paid": "1",
        "slippage_cost": "1",
        "gross_pnl": gross,
        "NET_PNL_EX_FUNDING": exit_net,
        "net_liquidation_equity": "10000",
        "drawdown": "0.99",
        "realized_pnl_cum": "999999",
        "FUNDING_DATA_STATUS": "PRESENT" if funding is not None else "MISSING",
        "funding_pnl": funding,
    }


def _mark(at: str, equity: str = "10000") -> dict:
    return {
        "event_type": "EQUITY_MARK",
        "mark_rule_id": "MARK_RULE_C7_V1",
        "mark_kind": "BAR_1H",
        "mark_honesty_label": "RECORDED_MARK",
        "mark_time_utc": at,
        "signal_available_at": at,
        "net_liquidation_equity": equity,
    }


def _midnight_cst(day: datetime) -> str:
    midnight = datetime(day.year, day.month, day.day, tzinfo=CST)
    return midnight.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _passing_rows() -> list[dict]:
    rows: list[dict] = [
        _open("2025-12-01T00:00:00Z"),
        _exit("2025-12-01T01:00:00Z", trade_net="4", gross="8", price="108"),
        _open("2026-01-02T00:00:00Z", signal="2025-12-31T00:00:00Z"),
        _exit("2026-01-02T02:00:00Z", trade_net="4", gross="8", price="108"),
        {
            "event_type": "MISSING_CANDLE",
            "reason_code": "MISSING_CANDLE",
            "signal_available_at": "2026-01-01T03:00:00Z",
        },
        {
            "event_type": "NO_FILL",
            "fill_status": "NO_FILL",
            "signal_available_at": "2026-01-01T04:00:00Z",
        },
        {
            "event_type": "PENDING_NEXT_BAR",
            "signal_available_at": "2026-01-01T05:00:00Z",
        },
        _mark(T0),
        _mark("2026-01-01T02:00:00Z", "9900"),
        # The 9900 row above is a real C7 mark and would fail the 2% day rule
        # if it were the day low under a 10000 open. Keep the dip off the C7 rule.
    ]
    rows[-1]["mark_rule_id"] = "NOT_A_C7_MARK"
    rows[-1]["event_type"] = "FLAT_MARK"
    rows[-1]["mark_kind"] = "FLAT_MARK"
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 4, 1, tzinfo=timezone.utc)
    day = start.astimezone(CST).date() + timedelta(days=1)
    last = end.astimezone(CST).date()
    while day <= last:
        rows.append(_mark(_midnight_cst(datetime(day.year, day.month, day.day))))
        day += timedelta(days=1)
    rows.append(_mark("2026-03-31T00:00:00Z", "10050"))
    for index in range(50):
        entry_at = start + timedelta(days=index + 1)
        exit_at = entry_at + timedelta(hours=1)
        winner = index % 2 == 0
        rows.append(_open(entry_at.strftime("%Y-%m-%dT%H:%M:%SZ")))
        rows.append(
            _exit(
                exit_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                trade_net="4" if winner else "-2",
                gross="8" if winner else "2",
                price="108" if winner else "102",
                funding="0",
            )
        )
    return _chain(rows)


def _governance() -> list[dict]:
    return seal_chain([_attest()], GOVERNANCE_GENESIS_PREV_HASH)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


class PassLineScorerTest(unittest.TestCase):
    def test_synthetic_line_scores_recorded_fields_without_rewriting_thresholds(self) -> None:
        report = score_rows(
            _passing_rows(),
            t0=T0,
            t_score=T_SCORE,
            governance_rows=_governance(),
            random_seed="freeze-seed-v1",
        )
        criteria = report["criteria"]
        self.assertEqual(criteria["C1"]["status"], "PASS")
        self.assertEqual(criteria["C1"]["value"], 90)
        self.assertEqual(criteria["C2"]["status"], "PASS")
        self.assertEqual(criteria["C2"]["value"], 50)
        self.assertEqual(criteria["C3"]["status"], "PASS")
        self.assertEqual(criteria["C3"]["value"], "50")
        self.assertEqual(criteria["C4"]["status"], "PASS")
        self.assertEqual(criteria["C4"]["value"], "2")
        self.assertEqual(criteria["C5"]["status"], "PASS")
        self.assertEqual(criteria["C6"]["status"], "NOT_APPLICABLE")
        self.assertEqual(criteria["C6"]["reason"], "LINE_B_ONLY")
        self.assertEqual(criteria["C7"]["status"], "NOT_APPLICABLE")
        self.assertEqual(criteria["C7"]["reason"], "LINE_B_ONLY")
        self.assertEqual(report["line"], "A")
        self.assertEqual(report["overall_scope"], "LINE_A_RESEARCH_BASELINE")
        self.assertFalse(report["pilot_eligible"])
        self.assertEqual(report["pilot_eligible_reason"], "LINE_A_PASS_IS_NOT_REAL_MONEY_ELIGIBILITY")
        line_b = score_rows(
            _passing_rows(),
            t0=T0,
            t_score=T_SCORE,
            governance_rows=_governance(),
            random_seed="freeze-seed-v1",
            line="B",
        )
        self.assertEqual(line_b["criteria"]["C6"]["status"], "PASS")
        self.assertEqual(line_b["criteria"]["C7"]["status"], "PASS")
        self.assertEqual(line_b["line"], "B")
        self.assertEqual(line_b["overall"], "PASS")
        self.assertTrue(line_b["pilot_eligible"])
        self.assertEqual(line_b["pilot_eligible_reason"], "LINE_B_PASSED_INCLUDING_C6_C7")
        self.assertEqual(line_b["live_trading"], "NO-GO")
        self.assertTrue(line_b["frozen"])
        self.assertEqual(line_b["frozen_t0"], FROZEN_T0)
        self.assertEqual(report["research_baseline"], "PASS")
        self.assertEqual(report["overall"], "PASS")
        self.assertEqual(criteria["C8"]["status"], "PASS")
        self.assertEqual(criteria["C9"]["status"], "PASS")
        self.assertEqual(criteria["C9"]["value"]["UNAUTHORIZED_PRIVILEGE"], 0)
        self.assertEqual(criteria["C10"]["structural_status"], "PASS")
        self.assertEqual(criteria["C10"]["status"], "PASS")
        self.assertEqual(criteria["C10"]["payload_digest_status"], "PASS")
        self.assertEqual(criteria["C10"]["value"], "RECOMPUTED_LINK_OK")
        self.assertEqual(criteria["R0_RANDOM_DIRECTION"]["status"], "PASS")
        self.assertFalse(report["thresholds_changed"])
        self.assertEqual(report["live_trading"], "NO-GO")
        self.assertFalse(report["line_a_rewritten"])
        self.assertFalse(report["funding_zero_filled"])
        self.assertFalse(report["fill_latency_seconds"]["used_as_fill"])
        self.assertGreater(report["counts_by_type"]["MISSING_CANDLE"], 0)
        self.assertGreater(report["counts_by_type"]["PENDING_NEXT_BAR"], 0)
        self.assertGreater(report["counts_by_type"]["NO_FILL"], 0)
        self.assertEqual(report["pairing"]["excluded_from_window"]["pre_t0"], 1)
        self.assertEqual(report["pairing"]["excluded_from_window"]["signal_pre_t0"], 1)
        self.assertTrue(all(trade["quantity"] == "1" for trade in report["closed_trades"]))
        self.assertNotEqual(criteria["C3"]["value"], "999999")
        self.assertLess(Decimal(criteria["C5"]["value"]), Decimal("0.08"))

    def test_short_window_few_trades_and_exact_profit_factor_fail(self) -> None:
        rows = _chain(
            [
                _open("2026-01-02T00:00:00Z"),
                _exit("2026-01-02T01:00:00Z", trade_net="11", gross="15", price="115", funding="0"),
                _open("2026-01-03T00:00:00Z"),
                _exit("2026-01-03T01:00:00Z", trade_net="-10", gross="-6", price="94", funding="0"),
            ]
        )
        report = score_rows(rows, t0=T0, t_score="2026-01-15T00:00:00Z", governance_rows=_governance())
        self.assertEqual(report["criteria"]["C1"]["status"], "FAIL")
        self.assertEqual(report["criteria"]["C2"]["status"], "FAIL")
        self.assertEqual(report["criteria"]["C4"]["value"], "1.1")
        self.assertEqual(report["criteria"]["C4"]["status"], "FAIL")

    def test_missing_funding_stays_missing_and_entry_costs_are_subtracted(self) -> None:
        rows = _chain(
            [
                _open("2026-01-02T00:00:00Z"),
                _exit("2026-01-02T01:00:00Z", trade_net="6", gross="10", price="110", funding=None),
            ]
        )
        rows[0]["fee_paid"] = "1.5"
        rows[0]["slippage_cost"] = "0.5"
        rows[1]["fee_paid"] = "1.5"
        rows[1]["slippage_cost"] = "0.5"
        rows[1]["NET_PNL_EX_FUNDING"] = "8"
        rows[1]["gross_pnl"] = "10"
        report = score_rows(rows, t0=T0, t_score=T_SCORE, governance_rows=_governance())
        self.assertEqual(report["criteria"]["C3"]["status"], "NOT_SCORABLE")
        self.assertEqual(report["criteria"]["C3"]["reason"], "NOT_SCORABLE_ON_LINE_A")
        diagnostic = report["criteria"]["C3"]["diagnostic_ex_funding"]
        self.assertEqual(diagnostic["funding"], "MISSING")
        self.assertEqual(diagnostic["net_pnl_ex_funding"], "6")
        self.assertEqual(report["closed_trades"][0]["funding_pnl"], "MISSING")
        self.assertEqual(report["closed_trades"][0]["official_net"], "MISSING")
        self.assertNotEqual(report["closed_trades"][0]["net_ex_funding"], "0")
        self.assertNotEqual(report["closed_trades"][0]["net_ex_funding"], "8")

    def test_present_zero_funding_is_a_real_zero(self) -> None:
        rows = _chain(
            [
                _open("2026-01-02T00:00:00Z"),
                _exit("2026-01-02T01:00:00Z", trade_net="4", gross="8", price="108", funding="0"),
            ]
        )
        report = score_rows(rows, t0=T0, t_score=T_SCORE)
        self.assertEqual(report["closed_trades"][0]["funding_status"], "PRESENT")
        self.assertEqual(report["closed_trades"][0]["funding_pnl"], "0")
        self.assertEqual(report["closed_trades"][0]["official_net"], "4")

    def test_missing_stop_is_not_back_calculated_from_pnl(self) -> None:
        rows = _chain(
            [
                _open("2026-01-02T00:00:00Z"),
                _exit("2026-01-02T01:00:00Z", trade_net="-50", gross="-46", price="54", funding="0"),
            ]
        )
        for key in ("preset_stop_price", "equity_at_open", "risk_amount"):
            del rows[0][key]
        rows[0]["net_liquidation_equity"] = "10000"
        report = score_rows(rows, t0=T0, t_score=T_SCORE)
        c6 = report["criteria"]["C6"]
        self.assertEqual(c6["status"], "NOT_APPLICABLE")
        self.assertEqual(c6["reason"], "LINE_B_ONLY")
        self.assertIsNone(c6["value"])
        line_b = score_rows(rows, t0=T0, t_score=T_SCORE, line="B")
        self.assertEqual(line_b["criteria"]["C6"]["status"], "NOT_SCORABLE")
        self.assertEqual(line_b["criteria"]["C6"]["reason"], "EX_ANTE_FIELDS_MISSING")
        self.assertIsNone(line_b["criteria"]["C6"]["value"])

    def test_recorded_risk_above_cap_fails(self) -> None:
        rows = _chain(
            [
                _open("2026-01-02T00:00:00Z"),
                _exit("2026-01-02T01:00:00Z", trade_net="4", gross="8", price="108", funding="0"),
            ]
        )
        rows[0]["risk_amount"] = "51"
        line_a = score_rows(rows, t0=T0, t_score=T_SCORE)
        self.assertEqual(line_a["criteria"]["C6"]["status"], "NOT_APPLICABLE")
        report = score_rows(rows, t0=T0, t_score=T_SCORE, line="B")
        self.assertEqual(report["criteria"]["C6"]["status"], "FAIL")
        self.assertEqual(report["criteria"]["C6"]["reason"], "RISK_PCT_ABOVE_0_5_PERCENT")

    def test_inconsistent_exit_net_and_gross_are_not_averaged(self) -> None:
        rows = _chain(
            [
                _open("2026-01-02T00:00:00Z"),
                _exit("2026-01-02T01:00:00Z", trade_net="6", gross="10", price="110", funding="0"),
            ]
        )
        rows[0]["fee_paid"] = "1.5"
        rows[0]["slippage_cost"] = "0.5"
        rows[1]["fee_paid"] = "1.5"
        rows[1]["slippage_cost"] = "0.5"
        rows[1]["gross_pnl"] = "10"
        rows[1]["NET_PNL_EX_FUNDING"] = "6"
        report = score_rows(rows, t0=T0, t_score=T_SCORE)
        self.assertEqual(report["criteria"]["C3"]["reason"], "NET_AND_GROSS_INCONSISTENT")
        self.assertEqual(report["closed_trades"][0]["official_net"], "MISSING")

    def test_drawdown_above_eight_percent_fails_from_equity_not_stored_column(self) -> None:
        rows = _chain(
            [
                _mark(T0, "100"),
                {
                    "event_type": "FLAT_MARK",
                    "signal_available_at": "2026-01-01T02:00:00Z",
                    "net_liquidation_equity": "90",
                    "drawdown": "0",
                },
            ]
        )
        report = score_rows(rows, t0=T0, t_score=T_SCORE)
        self.assertEqual(report["criteria"]["C5"]["status"], "FAIL")
        self.assertEqual(report["criteria"]["C5"]["value"], "0.1")

    def test_flat_marks_without_c7_rule_do_not_score_daily_loss(self) -> None:
        rows = _chain(
            [
                {
                    "event_type": "FLAT_MARK",
                    "signal_available_at": T0,
                    "net_liquidation_equity": "10000",
                },
                {
                    "event_type": "FLAT_MARK",
                    "signal_available_at": "2026-01-01T06:00:00Z",
                    "net_liquidation_equity": "1",
                },
            ]
        )
        report = score_rows(rows, t0=T0, t_score="2026-01-02T00:00:00Z")
        self.assertEqual(report["criteria"]["C7"]["status"], "NOT_APPLICABLE")
        self.assertEqual(report["criteria"]["C7"]["reason"], "LINE_B_ONLY")
        self.assertIsNone(report["criteria"]["C7"]["value"])
        line_b = score_rows(rows, t0=T0, t_score="2026-01-02T00:00:00Z", line="B")
        self.assertEqual(line_b["criteria"]["C7"]["status"], "NOT_SCORABLE")
        self.assertEqual(line_b["criteria"]["C7"]["reason"], "MARK_RULE_C7_V1_ABSENT")
        self.assertIsNone(line_b["criteria"]["C7"]["value"])

    def test_daily_loss_above_two_percent_fails_when_marks_exist(self) -> None:
        rows = _chain([_mark(T0, "10000"), _mark("2026-01-01T06:00:00Z", "9700")])
        line_a = score_rows(rows, t0=T0, t_score="2026-01-01T12:00:00Z")
        self.assertEqual(line_a["criteria"]["C7"]["status"], "NOT_APPLICABLE")
        report = score_rows(rows, t0=T0, t_score="2026-01-01T12:00:00Z", line="B")
        self.assertEqual(report["criteria"]["C7"]["status"], "FAIL")
        self.assertEqual(report["criteria"]["C7"]["reason"], "DAILY_LOSS_ABOVE_2_PERCENT")

    def test_concentration_above_25_percent_fails(self) -> None:
        rows = []
        start = datetime(2026, 1, 2, tzinfo=timezone.utc)
        nets = ("10", "10", "10", "100")
        for index, trade_net in enumerate(nets):
            entry = start + timedelta(days=index)
            gross = str(Decimal(trade_net) + Decimal(4))
            rows.append(_open(entry.strftime("%Y-%m-%dT%H:%M:%SZ")))
            rows.append(
                _exit(
                    (entry + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    trade_net=trade_net,
                    gross=gross,
                    price="100",
                    funding="0",
                )
            )
        report = score_rows(_chain(rows), t0=T0, t_score=T_SCORE)
        self.assertEqual(report["criteria"]["C8"]["status"], "FAIL")

    def test_absent_governance_register_is_not_zero_incidents(self) -> None:
        report = score_rows(_chain([_mark(T0)]), t0=T0, t_score=T_SCORE, governance_rows=None)
        self.assertEqual(report["criteria"]["C9"]["status"], "NOT_SCORABLE")
        self.assertEqual(report["criteria"]["C9"]["reason"], "GOVERNANCE_REGISTER_ABSENT")
        self.assertIsNone(report["criteria"]["C9"]["value"])

    def test_empty_governance_file_is_not_zero_incidents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "copy.jsonl"
            governance = root / "governance.jsonl"
            _write_jsonl(ledger, _chain([_mark(T0)]))
            governance.write_text("", encoding="utf-8")
            report = score_ledger_file(ledger, t0=T0, t_score=T_SCORE, governance_path=governance)
        self.assertEqual(report["criteria"]["C9"]["status"], "NOT_SCORABLE")
        self.assertEqual(report["criteria"]["C9"]["reason"], "EMPTY_GOVERNANCE_REGISTER")

    def test_governance_breach_fails(self) -> None:
        rows = seal_chain(
            [
                _attest(),
                {
                    "record_type": "BREACH",
                    "id": "gov-000002",
                    "time_utc": "2026-02-01T00:00:00Z",
                    "criterion": "LEDGER_TAMPER",
                    "rule": "LEDGER_TAMPER",
                    "description": "a sealed breach inside the window",
                    "recorder": "founder-test",
                },
            ],
            GOVERNANCE_GENESIS_PREV_HASH,
        )
        report = score_rows(_chain([_mark(T0)]), t0=T0, t_score=T_SCORE, governance_rows=rows)
        self.assertEqual(report["criteria"]["C9"]["status"], "FAIL")
        self.assertEqual(report["criteria"]["C9"]["reason"], "GOVERNANCE_BREACH_PRESENT")
        self.assertEqual(report["criteria"]["C9"]["value"]["LEDGER_TAMPER"], 1)

    def test_hash_break_duplicate_and_id_gap_fail_structural_integrity(self) -> None:
        broken = _chain([_mark(T0), _mark("2026-01-02T00:00:00Z")])
        broken[1]["prev_hash"] = "not-the-previous-hash"
        self.assertEqual(score_rows(broken)["criteria"]["C10"]["reason"], "HASH_CHAIN_BREAK")
        duplicated = _chain([_mark(T0), _mark("2026-01-02T00:00:00Z")])
        duplicated[1]["ledger_event_id"] = duplicated[0]["ledger_event_id"]
        duplicated = seal_chain(duplicated, GENESIS_PREV_HASH)
        self.assertEqual(score_rows(duplicated)["criteria"]["C10"]["reason"], "DUPLICATE_LEDGER_EVENT_ID")
        gapped = _chain([_mark(T0), _mark("2026-01-02T00:00:00Z")])
        gapped[1]["ledger_event_id"] = "le-000004"
        gapped = seal_chain(gapped, GENESIS_PREV_HASH)
        self.assertEqual(score_rows(gapped)["criteria"]["C10"]["reason"], "LEDGER_EVENT_ID_GAP")

    def test_unparsed_row_fails_integrity_and_blocks_trade_count(self) -> None:
        blob_rows = _chain([_open("2026-01-02T00:00:00Z"), _exit("2026-01-02T01:00:00Z", trade_net="4", gross="8", price="108")])
        report = score_rows(blob_rows, unparsed=1, t0=T0, t_score=T_SCORE)
        self.assertEqual(report["criteria"]["C10"]["reason"], "UNPARSED_ROWS")
        self.assertEqual(report["criteria"]["C2"]["reason"], "PAIRING_NOT_FAIR")

    def test_negative_gross_does_not_beat_random_direction(self) -> None:
        rows = _chain(
            [
                _open("2026-01-02T00:00:00Z"),
                _exit("2026-01-02T01:00:00Z", trade_net="-14", gross="-10", price="90", funding="0"),
            ]
        )
        report = score_rows(rows, t0=T0, t_score=T_SCORE, random_seed="freeze-seed-v1")
        self.assertEqual(report["criteria"]["R0_RANDOM_DIRECTION"]["status"], "FAIL")

    def test_signal_price_is_not_used_as_the_fill(self) -> None:
        rows = _chain(
            [
                _open("2026-01-02T00:00:00Z"),
                _exit("2026-01-02T01:00:00Z", trade_net="4", gross="8", price="108", funding="0"),
            ]
        )
        del rows[1]["gross_pnl"]
        rows[0]["signal_price"] = "1000000"
        rows[1]["signal_price"] = "1"
        report = score_rows(rows, t0=T0, t_score=T_SCORE)
        self.assertEqual(report["criteria"]["R0_RANDOM_DIRECTION"]["diagnostic_ex_funding"]["anchor_gross"], "8")

    def test_reverse_pairs_as_two_legs_and_gap_rows_stay(self) -> None:
        rows = [
            _open("2026-01-02T00:00:00Z"),
            _exit("2026-01-02T01:00:00Z", trade_net="4", gross="8", price="108", funding="0"),
        ]
        rows[1]["event_type"] = "REVERSE_EXIT"
        second = _open("2026-01-02T02:00:00Z")
        second["event_type"] = "REVERSE_ENTRY"
        second["side"] = "SHORT"
        rows.append(second)
        flat = _exit("2026-01-02T03:00:00Z", trade_net="4", gross="8", price="92", funding="0")
        rows.append(flat)
        rows.extend(
            {
                "event_type": "MISSING_CANDLE",
                "reason_code": "MISSING_CANDLE",
                "signal_available_at": "2026-01-03T00:00:00Z",
            }
            for _ in range(249)
        )
        report = score_rows(_chain(rows), t0=T0, t_score=T_SCORE)
        self.assertEqual(report["pairing"]["closed"], 2)
        self.assertEqual(report["counts_by_type"]["MISSING_CANDLE"], 249)
        self.assertEqual(report["rows_retained"], 4 + 249)
        self.assertEqual(report["closed_trades"][1]["entry_type"], "REVERSE_ENTRY")

    def test_without_t0_post_freeze_criteria_are_not_scorable(self) -> None:
        report = score_rows(_passing_rows())
        for name in ("C1", "C2", "C3", "R0_RANDOM_DIRECTION"):
            self.assertEqual(report["criteria"][name]["status"], "NOT_SCORABLE")
            self.assertEqual(report["criteria"][name]["reason"], "T0_NOT_FROZEN")
        self.assertEqual(report["criteria"]["C6"]["status"], "NOT_APPLICABLE")
        self.assertEqual(report["criteria"]["C6"]["reason"], "LINE_B_ONLY")
        self.assertEqual(report["criteria"]["C7"]["reason"], "LINE_B_ONLY")
        self.assertEqual(report["overall"], "NOT_ELIGIBLE")
        self.assertFalse(report["pilot_eligible"])

    def test_ledger_copy_is_not_modified_and_sealed_paths_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "anchor_fake_fill_ledger_v2_official.jsonl"
            _write_jsonl(ledger, _chain([_mark(T0)]))
            before = hashlib.sha256(ledger.read_bytes()).hexdigest()
            mode = stat.S_IMODE(ledger.stat().st_mode)
            out = root / "report.json"
            completed = subprocess.run(
                [
                    "python3",
                    str(SCORER),
                    "--ledger",
                    str(ledger),
                    "--t0",
                    T0,
                    "--t-score",
                    T_SCORE,
                    "--out",
                    str(out),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(hashlib.sha256(ledger.read_bytes()).hexdigest(), before)
            self.assertEqual(stat.S_IMODE(ledger.stat().st_mode), mode)
            saved = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(saved["input"]["bytes_written"], 0)
            self.assertTrue(saved["input"]["read_only"])

            sealed = root / "affl-v2-official-ledger"
            sealed.mkdir()
            sealed_file = sealed / "copy.jsonl"
            _write_jsonl(sealed_file, _chain([_mark(T0)]))
            refused = subprocess.run(
                ["python3", str(SCORER), "--ledger", str(sealed_file)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(refused.returncode, 2)
            self.assertIn("affl-v2-official-ledger", refused.stderr)

            link = root / "linked.jsonl"
            link.symlink_to(ledger)
            linked = subprocess.run(
                ["python3", str(SCORER), "--ledger", str(link)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(linked.returncode, 2)
            self.assertEqual(os.stat(ledger).st_mtime_ns, ledger.stat().st_mtime_ns)

    def test_direct_refusal_for_private_state_directory_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp) / "var" / "lib" / "private"
            private.mkdir(parents=True)
            ledger = private / "copy.jsonl"
            _write_jsonl(ledger, _chain([_mark(T0)]))
            with self.assertRaises(ScoringRefusal):
                score_ledger_file(ledger)

    def test_payload_tamper_is_row_hash_mismatch(self) -> None:
        rows = _chain([_mark(T0)])
        rows[0]["net_liquidation_equity"] = "1"
        report = score_rows(rows, t0=T0, t_score=T_SCORE)
        self.assertEqual(report["criteria"]["C10"]["status"], "FAIL")
        self.assertEqual(report["criteria"]["C10"]["reason"], "ROW_HASH_MISMATCH")

    def test_first_prev_hash_must_be_genesis(self) -> None:
        rows = _chain([_mark(T0)])
        rows[0]["prev_hash"] = "NOT_GENESIS"
        report = score_rows(rows, t0=T0, t_score=T_SCORE)
        self.assertEqual(report["criteria"]["C10"]["reason"], "HASH_CHAIN_BREAK")

    def test_leading_header_is_skipped_and_not_hashed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "copy.jsonl"
            body = "".join(json.dumps(row) + "\n" for row in _chain([_mark(T0)]))
            ledger.write_text(
                "ledger_event_id,event_type,row_hash,prev_hash\n" + body,
                encoding="utf-8",
            )
            report = score_ledger_file(ledger, t0=T0, t_score=T_SCORE)
        self.assertEqual(report["criteria"]["C10"]["status"], "PASS")
        self.assertEqual(report["criteria"]["C10"]["header_rows_skipped"], 1)
        self.assertEqual(report["criteria"]["C10"]["rows_checked"], 1)

    def test_mid_file_non_json_fails_unparsed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "copy.jsonl"
            rows = _chain([_mark(T0), _mark("2026-01-02T00:00:00Z")])
            ledger.write_text(
                json.dumps(rows[0]) + "\nnot a row\n" + json.dumps(rows[1]) + "\n",
                encoding="utf-8",
            )
            report = score_ledger_file(ledger, t0=T0, t_score=T_SCORE)
        self.assertEqual(report["criteria"]["C10"]["status"], "FAIL")
        self.assertEqual(report["criteria"]["C10"]["reason"], "UNPARSED_ROWS")
        self.assertEqual(report["unparsed"], 1)

    def test_json_object_is_not_treated_as_a_header(self) -> None:
        rows = _chain([_mark(T0)])
        self.assertTrue(json.dumps(rows[0]).startswith("{"))
        report = score_rows(rows, t0=T0, t_score=T_SCORE)
        self.assertEqual(report["criteria"]["C10"]["status"], "PASS")
        self.assertEqual(report["criteria"]["C10"]["header_rows_skipped"], 0)

    def test_governance_payload_tamper_is_not_zero_breaches(self) -> None:
        rows = _governance()
        rows[0]["description"] = "changed after the hash"
        report = score_rows(_chain([_mark(T0)]), t0=T0, t_score=T_SCORE, governance_rows=rows)
        self.assertEqual(report["criteria"]["C9"]["status"], "FAIL")
        self.assertEqual(report["criteria"]["C9"]["reason"], "GOVERNANCE_ROW_HASH_MISMATCH")

    def test_governance_link_break_fails(self) -> None:
        rows = _governance()
        rows[0]["prev_hash"] = "GENESIS"
        report = score_rows(_chain([_mark(T0)]), t0=T0, t_score=T_SCORE, governance_rows=rows)
        self.assertEqual(report["criteria"]["C9"]["status"], "FAIL")
        self.assertEqual(report["criteria"]["C9"]["reason"], "GOVERNANCE_HASH_CHAIN_BREAK")

    def test_string_true_is_not_a_founder_signature(self) -> None:
        rows = seal_chain([_attest(founder_signed="true")], GOVERNANCE_GENESIS_PREV_HASH)
        report = score_rows(_chain([_mark(T0)]), t0=T0, t_score=T_SCORE, governance_rows=rows)
        self.assertEqual(report["criteria"]["C9"]["status"], "NOT_SCORABLE")
        self.assertEqual(report["criteria"]["C9"]["reason"], "GOVERNANCE_COVERAGE_NOT_ATTESTED")

    def test_live_governance_register_starts_empty(self) -> None:
        live = PROJECT_ROOT / "governance" / "ANCHOR_C9_GOVERNANCE_REGISTER.jsonl"
        self.assertTrue(live.is_file())
        self.assertEqual(live.read_bytes(), b"")
        self.assertEqual(FROZEN_T0, "2026-10-22T20:27:21+08:00")
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "copy.jsonl"
            _write_jsonl(ledger, _chain([_mark(T0)]))
            report = score_ledger_file(ledger, t0=T0, t_score=T_SCORE, governance_path=live)
        self.assertEqual(report["criteria"]["C9"]["status"], "NOT_SCORABLE")
        self.assertEqual(report["criteria"]["C9"]["reason"], "EMPTY_GOVERNANCE_REGISTER")
        self.assertTrue(report["frozen"])
        self.assertEqual(report["frozen_t0"], FROZEN_T0)
        self.assertEqual(report["live_trading"], "NO-GO")

    def test_template_register_is_not_a_passing_attestation(self) -> None:
        self.assertTrue(C9_TEMPLATE.is_file())
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "copy.jsonl"
            _write_jsonl(ledger, _chain([_mark(T0)]))
            report = score_ledger_file(ledger, t0=T0, t_score=T_SCORE, governance_path=C9_TEMPLATE)
        self.assertEqual(report["criteria"]["C9"]["status"], "NOT_SCORABLE")
        self.assertEqual(report["criteria"]["C9"]["reason"], "GOVERNANCE_COVERAGE_NOT_ATTESTED")
        self.assertNotEqual(report["criteria"]["C9"]["status"], "PASS")

    def test_breach_fails_without_a_covering_attestation(self) -> None:
        rows = seal_chain(
            [
                {
                    "record_type": "BREACH",
                    "id": "gov-000001",
                    "time_utc": "2026-02-01T00:00:00Z",
                    "criterion": "OTHER",
                    "description": "rule named only in criterion",
                    "recorder": "operator",
                }
            ],
            GOVERNANCE_GENESIS_PREV_HASH,
        )
        report = score_rows(_chain([_mark(T0)]), t0=T0, t_score=T_SCORE, governance_rows=rows)
        self.assertEqual(report["criteria"]["C9"]["status"], "FAIL")
        self.assertEqual(report["criteria"]["C9"]["reason"], "GOVERNANCE_BREACH_PRESENT")
        self.assertEqual(report["criteria"]["C9"]["value"]["OTHER"], 1)


if __name__ == "__main__":
    unittest.main()
