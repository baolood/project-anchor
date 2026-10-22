"""Synthetic public-funding cache tests. No network and no ledger write."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from eval_scoring.line_a_pass_line import ScoringRefusal, score_ledger_file, score_rows
from eval_scoring.public_funding import (
    SCHEMA,
    FundingCacheError,
    build_funding_cache,
    contract_size_from_instruments,
    leg_funding,
    load_funding_cache_bytes,
    rates_from_kraken_payload,
)
from tests.test_score_official_fake_fill_pass_line import T0, T_SCORE, _chain, _exit, _governance, _open


def _book(rates: list[dict], *, symbol: str = "PF_XBTUSD", contract_size: str = "1"):
    document = build_funding_cache(
        symbol=symbol,
        source_url=f"https://futures.kraken.com/derivatives/api/v3/historical-funding-rates?symbol={symbol}",
        fetched_at="2026-10-22T12:00:00Z",
        contract_size=contract_size,
        rates=rates,
        contract_size_source="https://futures.kraken.com/derivatives/api/v3/instruments",
    )
    return load_funding_cache_bytes(json.dumps(document).encode("utf-8")), document


def _at(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


class PublicFundingMathTest(unittest.TestCase):
    def test_sign_uses_absolute_rate_not_relative_notional(self) -> None:
        book, _document = _book(
            [
                {
                    "timestamp": "2026-01-02T00:00:00Z",
                    "fundingRate": "10",
                    "relativeFundingRate": "0.9",
                }
            ]
        )
        short = leg_funding(
            book,
            entry_at=_at("2026-01-02T00:00:00Z"),
            exit_at=_at("2026-01-02T01:00:00Z"),
            quantity=Decimal("2"),
            short_receives_positive=True,
        )
        long = leg_funding(
            book,
            entry_at=_at("2026-01-02T00:00:00Z"),
            exit_at=_at("2026-01-02T01:00:00Z"),
            quantity=Decimal("2"),
            short_receives_positive=False,
        )
        self.assertEqual(short.status, "PRESENT")
        self.assertEqual(short.amount, Decimal("20"))
        self.assertEqual(long.amount, Decimal("-20"))
        self.assertNotEqual(short.amount, Decimal("2") * Decimal("100") * Decimal("0.9"))

    def test_negative_rate_pays_the_short(self) -> None:
        book, _document = _book([{"timestamp": "2026-01-02T00:00:00Z", "fundingRate": "-3"}])
        long = leg_funding(
            book,
            entry_at=_at("2026-01-02T00:00:00Z"),
            exit_at=_at("2026-01-02T01:00:00Z"),
            quantity=Decimal("1"),
            short_receives_positive=False,
        )
        short = leg_funding(
            book,
            entry_at=_at("2026-01-02T00:00:00Z"),
            exit_at=_at("2026-01-02T01:00:00Z"),
            quantity=Decimal("1"),
            short_receives_positive=True,
        )
        self.assertEqual(long.amount, Decimal("3"))
        self.assertEqual(short.amount, Decimal("-3"))

    def test_partial_window_is_prorated_and_stops_at_the_exit(self) -> None:
        book, _document = _book(
            [
                {"timestamp": "2026-01-02T00:00:00Z", "fundingRate": "10"},
                {"timestamp": "2026-01-02T01:00:00Z", "fundingRate": "4"},
                {"timestamp": "2026-01-02T02:00:00Z", "fundingRate": "100"},
            ],
            contract_size="1",
        )
        leg = leg_funding(
            book,
            entry_at=_at("2026-01-02T00:30:00Z"),
            exit_at=_at("2026-01-02T02:00:00Z"),
            quantity=Decimal("2"),
            short_receives_positive=True,
        )
        self.assertEqual(leg.status, "PRESENT")
        self.assertEqual(leg.settlements, 2)
        self.assertEqual(leg.hours, Decimal("1.5"))
        self.assertEqual(leg.amount, Decimal("18"))
        doubled, _document = _book(
            [
                {"timestamp": "2026-01-02T00:00:00Z", "fundingRate": "10"},
                {"timestamp": "2026-01-02T01:00:00Z", "fundingRate": "4"},
                {"timestamp": "2026-01-02T02:00:00Z", "fundingRate": "100"},
            ],
            contract_size="2",
        )
        doubled_leg = leg_funding(
            doubled,
            entry_at=_at("2026-01-02T00:30:00Z"),
            exit_at=_at("2026-01-02T02:00:00Z"),
            quantity=Decimal("2"),
            short_receives_positive=True,
        )
        self.assertEqual(doubled_leg.amount, Decimal("36"))

    def test_missing_hour_is_missing_for_the_whole_leg(self) -> None:
        book, _document = _book(
            [
                {"timestamp": "2026-01-02T00:00:00Z", "fundingRate": "10"},
                {"timestamp": "2026-01-02T02:00:00Z", "fundingRate": "4"},
            ]
        )
        leg = leg_funding(
            book,
            entry_at=_at("2026-01-02T00:30:00Z"),
            exit_at=_at("2026-01-02T02:30:00Z"),
            quantity=Decimal("2"),
            short_receives_positive=True,
        )
        self.assertEqual(leg.status, "MISSING")
        self.assertIsNone(leg.amount)
        self.assertEqual(leg.missing_periods, ("2026-01-02T01:00:00Z",))
        self.assertNotEqual(leg.amount, Decimal("14"))

    def test_recorded_zero_rate_is_a_real_zero(self) -> None:
        book, _document = _book([{"timestamp": "2026-01-02T00:00:00Z", "fundingRate": "0"}])
        leg = leg_funding(
            book,
            entry_at=_at("2026-01-02T00:00:00Z"),
            exit_at=_at("2026-01-02T01:00:00Z"),
            quantity=Decimal("1"),
            short_receives_positive=True,
        )
        self.assertEqual(leg.status, "PRESENT")
        self.assertEqual(leg.amount, Decimal("0"))

    def test_hash_mismatch_and_duplicate_timestamp_are_refused(self) -> None:
        _book_ok, document = _book([{"timestamp": "2026-01-02T00:00:00Z", "fundingRate": "1"}])
        document["rates"][0]["fundingRate"] = "2"
        with self.assertRaises(FundingCacheError):
            load_funding_cache_bytes(json.dumps(document).encode("utf-8"))
        with self.assertRaises(FundingCacheError):
            build_funding_cache(
                symbol="PF_XBTUSD",
                source_url="https://futures.kraken.com/derivatives/api/v3/historical-funding-rates?symbol=PF_XBTUSD",
                fetched_at="2026-10-22T12:00:00Z",
                contract_size="1",
                rates=[
                    {"timestamp": "2026-01-02T00:00:00Z", "fundingRate": "1"},
                    {"timestamp": "2026-01-02T00:00:00.000Z", "fundingRate": "2"},
                ],
                contract_size_source="https://futures.kraken.com/derivatives/api/v3/instruments",
            )

    def test_kraken_payload_parser_keeps_decimal_text(self) -> None:
        payload = json.loads(
            '{"result":"success","rates":[{"timestamp":"2026-01-02T00:00:00Z","fundingRate":1.25,"relativeFundingRate":0.00000125}]}',
            parse_float=Decimal,
        )
        rates = rates_from_kraken_payload(payload)
        self.assertEqual(rates[0]["fundingRate"], Decimal("1.25"))
        size = contract_size_from_instruments(
            {"result": "success", "instruments": [{"symbol": "PF_XBTUSD", "contractSize": 1}]},
            "PF_XBTUSD",
        )
        self.assertEqual(size, Decimal("1"))


class PublicFundingScorerTest(unittest.TestCase):
    def _rows(self, *, funding: str | None, side: str = "LONG", market: str | None = None) -> list[dict]:
        opened = _open("2026-01-02T00:00:00Z")
        opened["side"] = side
        closed = _exit("2026-01-02T01:00:00Z", trade_net="6", gross="10", price="110", funding=funding)
        closed["side"] = side
        if market is not None:
            opened["market"] = market
            closed["market"] = market
        return _chain([opened, closed])

    def test_external_funding_makes_c3_c4_c8_and_r0_scorable(self) -> None:
        # Four one-hour legs on consecutive days, each fully inside its 00:00 rate.
        rows = []
        rates = []
        nets = ("10", "10", "10", "10")
        for index, trade_net in enumerate(nets):
            day = 2 + index
            opened = _open(f"2026-01-0{day}T00:00:00Z")
            opened["market"] = "PF_XBTUSD"
            opened["FUNDING_DATA_STATUS"] = "MISSING"
            opened["funding_pnl"] = None
            closed = _exit(
                f"2026-01-0{day}T01:00:00Z",
                trade_net=trade_net,
                gross=str(Decimal(trade_net) + Decimal(4)),
                price="100",
                funding=None,
            )
            closed["market"] = "PF_XBTUSD"
            rows.extend([opened, closed])
            rates.append({"timestamp": f"2026-01-0{day}T00:00:00Z", "fundingRate": "0"})
        book, document = _book(rates)
        report = score_rows(
            _chain(rows),
            t0=T0,
            t_score=T_SCORE,
            governance_rows=_governance(),
            funding_book=book,
        )
        self.assertEqual(report["funding"]["label"], SCHEMA)
        self.assertTrue(report["funding"]["derived"])
        self.assertFalse(report["funding"]["zero_filled"])
        self.assertEqual(report["funding"]["cache"]["rates_sha256"], document["rates_sha256"])
        self.assertEqual(report["closed_trades"][0]["funding_source"], SCHEMA)
        self.assertEqual(report["closed_trades"][0]["funding_pnl"], "0")
        self.assertEqual(report["closed_trades"][0]["official_net"], "10")
        for name in ("C3", "C4", "C8", "R0_RANDOM_DIRECTION"):
            self.assertEqual(report["criteria"][name]["status"], "PASS", name)
        self.assertFalse(report["pilot_eligible"])
        self.assertNotIn("C10", report["blocking_criteria"])
        self.assertIn("C2", report["blocking_criteria"])
        self.assertNotIn("C6", report["blocking_criteria"])
        self.assertNotIn("C7", report["blocking_criteria"])

    def test_long_pays_positive_public_rate_and_entry_costs_stay_subtracted(self) -> None:
        book, _document = _book(
            [{"timestamp": "2026-01-02T00:00:00Z", "fundingRate": "1.5", "relativeFundingRate": "0.5"}]
        )
        report = score_rows(self._rows(funding=None, market="PF_XBTUSD"), t0=T0, t_score=T_SCORE, funding_book=book)
        trade = report["closed_trades"][0]
        self.assertEqual(trade["funding_source"], SCHEMA)
        self.assertEqual(trade["funding_pnl"], "-1.5")
        self.assertEqual(trade["net_ex_funding"], "6")
        self.assertEqual(trade["official_net"], "4.5")
        self.assertEqual(report["criteria"]["C3"]["status"], "PASS")
        self.assertEqual(report["criteria"]["C3"]["value"], "4.5")

    def test_missing_settlement_blocks_without_a_partial_sum(self) -> None:
        book, _document = _book([{"timestamp": "2026-01-02T00:00:00Z", "fundingRate": "10"}])
        opened = _open("2026-01-02T00:30:00Z")
        opened["market"] = "PF_XBTUSD"
        closed = _exit("2026-01-02T02:00:00Z", trade_net="6", gross="10", price="110", funding=None)
        closed["market"] = "PF_XBTUSD"
        report = score_rows(_chain([opened, closed]), t0=T0, t_score=T_SCORE, funding_book=book)
        self.assertEqual(report["criteria"]["C3"]["status"], "NOT_SCORABLE")
        self.assertEqual(report["criteria"]["C3"]["reason"], "NOT_SCORABLE_ON_LINE_A")
        self.assertEqual(report["criteria"]["C4"]["status"], "NOT_SCORABLE")
        self.assertEqual(report["criteria"]["C8"]["status"], "NOT_SCORABLE")
        self.assertEqual(report["criteria"]["R0_RANDOM_DIRECTION"]["status"], "NOT_SCORABLE")
        self.assertEqual(report["closed_trades"][0]["funding_pnl"], "MISSING")
        self.assertNotEqual(report["closed_trades"][0]["funding_pnl"], "0")
        self.assertFalse(report["funding_zero_filled"])

    def test_ledger_present_disagreement_is_not_averaged(self) -> None:
        book, _document = _book([{"timestamp": "2026-01-02T00:00:00Z", "fundingRate": "2"}])
        rows = self._rows(funding="-2", market="PF_XBTUSD")
        agreed = score_rows(rows, t0=T0, t_score=T_SCORE, funding_book=book)
        self.assertEqual(agreed["closed_trades"][0]["funding_source"], "LEDGER_RECORDED")
        self.assertEqual(agreed["closed_trades"][0]["funding_pnl"], "-2")
        rows[1]["funding_pnl"] = "1"
        report = score_rows(rows, t0=T0, t_score=T_SCORE, funding_book=book)
        self.assertEqual(report["criteria"]["C3"]["reason"], "FUNDING_LEDGER_EXTERNAL_DISAGREE")
        self.assertEqual(report["closed_trades"][0]["official_net"], "MISSING")
        self.assertNotEqual(report["closed_trades"][0]["funding_pnl"], "-0.5")

    def test_other_instrument_is_not_scored_with_this_cache(self) -> None:
        book, _document = _book([{"timestamp": "2026-01-02T00:00:00Z", "fundingRate": "2"}])
        report = score_rows(
            self._rows(funding=None, market="PF_ETHUSD"),
            t0=T0,
            t_score=T_SCORE,
            funding_book=book,
        )
        self.assertEqual(report["criteria"]["C3"]["reason"], "FUNDING_INSTRUMENT_MISMATCH")
        self.assertEqual(report["closed_trades"][0]["funding_pnl"], "MISSING")

    def test_absent_market_is_labeled_when_the_cache_symbol_is_used(self) -> None:
        book, _document = _book([{"timestamp": "2026-01-02T00:00:00Z", "fundingRate": "0"}])
        report = score_rows(self._rows(funding=None), t0=T0, t_score=T_SCORE, funding_book=book)
        self.assertEqual(report["funding"]["instrument_sources"], ["CACHE_SYMBOL_LEDGER_MARKET_ABSENT"])
        self.assertEqual(report["closed_trades"][0]["funding_source"], SCHEMA)
        self.assertEqual(report["closed_trades"][0]["funding_pnl"], "0")

    def test_bad_cache_file_is_refused_and_ledger_bytes_stay_put(self) -> None:
        import tempfile
        from pathlib import Path

        book, document = _book([{"timestamp": "2026-01-02T00:00:00Z", "fundingRate": "0"}])
        del book
        document["rates"][0]["fundingRate"] = "9"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "copy.jsonl"
            cache = root / "funding.json"
            ledger.write_text("{}\n", encoding="utf-8")
            before = ledger.read_bytes()
            cache.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(ScoringRefusal):
                score_ledger_file(ledger, funding_cache=cache)
            self.assertEqual(ledger.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
