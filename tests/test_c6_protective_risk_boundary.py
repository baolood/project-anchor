import inspect
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "affl-causal-successor"))

from affl_v2.c6_protective_boundary import (  # noqa: E402
    DEPLOY,
    FEE_BPS,
    FIXED_ADVERSE_STOP_BPS,
    LIVE_TRADING,
    MAX_RISK_PCT,
    SCHEMA_VERSION,
    SIZE_POLICY_ID,
    SLIPPAGE_BPS,
    STOP_RULE_ID,
    STRATEGY_VERSION,
    ProtectiveBoundaryError,
    ProtectiveRiskBook,
    adverse_fill_price,
    frozen_stop_price,
    max_allowed_quantity,
    risk_per_unit,
)
import affl_v2.c6_protective_boundary as boundary  # noqa: E402


AT = "2026-09-30T00:00:00Z"
REF = Decimal("100")
EQUITY = Decimal("10000")


def _book(equity=EQUITY):
    return ProtectiveRiskBook(equity)


def _open(book, choice="LONG", qty="1", ref=REF, oid="obs-open", at=AT):
    return book.on_signal(
        choice,
        ref,
        Decimal(qty),
        observation_id=oid,
        at=at,
    )


class ProtectiveRiskBoundaryTest(unittest.TestCase):
    def test_version_contract_is_a_new_series(self):
        self.assertEqual(STRATEGY_VERSION, "affl_v2_c6_protective_v1")
        self.assertEqual(SCHEMA_VERSION, "official_ledger_c6_v1")
        self.assertEqual(STOP_RULE_ID, "STOP_RULE_C6_FIXED_ADVERSE_BPS_V1")
        self.assertEqual(SIZE_POLICY_ID, "SIZE_POLICY_C6_SHRINK_TO_MAX_ELSE_REJECT_V1")
        self.assertEqual(FIXED_ADVERSE_STOP_BPS, Decimal("100"))
        self.assertEqual(FEE_BPS, Decimal("5"))
        self.assertEqual(SLIPPAGE_BPS, Decimal("2"))
        self.assertEqual(MAX_RISK_PCT, Decimal("0.005"))
        self.assertEqual(DEPLOY, "NO")
        self.assertEqual(LIVE_TRADING, "NO-GO")

    def test_stop_formula_is_fixed_adverse_bps_from_entry(self):
        long_entry = REF * (Decimal(1) + Decimal("2") / Decimal(10000))
        short_entry = REF * (Decimal(1) - Decimal("2") / Decimal(10000))
        self.assertEqual(adverse_fill_price("LONG", REF), Decimal("100.02"))
        self.assertEqual(adverse_fill_price("SHORT", REF), Decimal("99.98"))
        self.assertEqual(long_entry, Decimal("100.02"))
        self.assertEqual(frozen_stop_price("LONG", long_entry), Decimal("99.0198"))
        self.assertEqual(frozen_stop_price("SHORT", short_entry), short_entry * Decimal("1.01"))
        distance = long_entry - Decimal("99.0198")
        self.assertEqual(distance, Decimal("1.0002"))
        self.assertEqual(distance / long_entry * Decimal(10000), Decimal("100"))

    def test_stop_and_size_functions_do_not_take_outcome_inputs(self):
        stop_params = set(inspect.signature(frozen_stop_price).parameters)
        self.assertEqual(stop_params, {"side", "entry_price"})
        size_params = set(inspect.signature(max_allowed_quantity).parameters)
        self.assertEqual(
            size_params,
            {"entry_price", "preset_stop_price", "reference_price", "equity_at_open"},
        )
        signal_params = set(inspect.signature(ProtectiveRiskBook.on_signal).parameters)
        self.assertNotIn("preset_stop_price", signal_params)
        self.assertNotIn("stop_price", signal_params)
        for name in (
            "calibrate",
            "fit_stop",
            "widen_stop_to_fit",
            "load_official",
            "from_official_ledger",
        ):
            self.assertFalse(hasattr(ProtectiveRiskBook, name))
        forbidden = (
            "profit_factor",
            "maximum_drawdown",
            "max_drawdown",
            "win_rate",
            "expectancy",
            "calibrate",
        )
        for fn in (frozen_stop_price, risk_per_unit, max_allowed_quantity, adverse_fill_price):
            source = inspect.getsource(fn)
            for token in forbidden:
                self.assertNotIn(token, source)

    def test_module_source_has_no_outcome_fitting_hooks(self):
        source = (
            PROJECT_ROOT / "affl-causal-successor" / "affl_v2" / "c6_protective_boundary.py"
        ).read_text(encoding="utf-8")
        for token in (
            "profit_factor",
            "maximum_drawdown",
            "max_drawdown",
            "win_rate",
            "expectancy",
            "calibrate",
            "anchor_fake_fill_ledger",
        ):
            self.assertNotIn(token, source)

    def test_passing_a_stop_or_outcome_into_the_rule_is_rejected(self):
        with self.assertRaises(TypeError):
            frozen_stop_price("LONG", Decimal("100.02"), preset_stop_price=Decimal("90"))
        with self.assertRaises(TypeError):
            frozen_stop_price("LONG", Decimal("100.02"), observed_pnl=Decimal("-3"))
        book = _book()
        with self.assertRaises(TypeError):
            book.on_signal(
                "LONG",
                REF,
                Decimal("1"),
                observation_id="obs",
                at=AT,
                preset_stop_price=Decimal("90"),
            )

    def test_small_candidate_opens_with_ex_ante_fields(self):
        book = _book()
        event = _open(book, qty="1")[0]
        self.assertEqual(event["event_type"], "OPEN")
        self.assertEqual(event["fill_status"], "FILLED")
        self.assertEqual(event["reason_code"], "C6_OPEN")
        self.assertEqual(event["size_action"], "UNCHANGED")
        self.assertEqual(event["quantity"], Decimal("1"))
        self.assertEqual(event["candidate_quantity"], Decimal("1"))
        self.assertEqual(event["entry_price"], Decimal("100.02"))
        self.assertEqual(event["preset_stop_price"], Decimal("99.0198"))
        self.assertEqual(event["stop_distance"], Decimal("1.0002"))
        self.assertEqual(event["equity_at_open"], EQUITY)
        self.assertEqual(event["max_risk_amount"], Decimal("50"))
        self.assertEqual(event["trade_id"], "tr_le-000001")
        self.assertEqual(event["strategy_version"], STRATEGY_VERSION)
        self.assertEqual(event["schema_version"], SCHEMA_VERSION)
        self.assertEqual(event["stop_rule_id"], STOP_RULE_ID)
        self.assertEqual(event["size_policy_id"], SIZE_POLICY_ID)
        self.assertIsNone(event["funding_pnl"])
        self.assertEqual(event["FUNDING_DATA_STATUS"], "MISSING")
        self.assertEqual(event["NET_PNL_STATUS"], "EX_FUNDING")
        per_unit = risk_per_unit(Decimal("100.02"), Decimal("99.0198"), REF)
        self.assertEqual(event["risk_amount"], per_unit * Decimal("1"))
        self.assertEqual(event["risk_pct"], event["risk_amount"] / EQUITY)
        self.assertLessEqual(event["risk_pct"], MAX_RISK_PCT)
        self.assertEqual(book.position.side, "LONG")
        self.assertEqual(book.position.protective_stop_price, event["preset_stop_price"])

    def test_oversized_candidate_shrinks_and_does_not_widen_the_stop(self):
        book = _book()
        event = _open(book, qty="1000")[0]
        entry = Decimal("100.02")
        stop = Decimal("99.0198")
        max_qty, max_risk, per_unit = max_allowed_quantity(entry, stop, REF, EQUITY)
        self.assertGreater(Decimal("1000"), max_qty)
        self.assertEqual(event["size_action"], "SHRINK")
        self.assertEqual(event["quantity"], max_qty)
        self.assertEqual(event["candidate_quantity"], Decimal("1000"))
        self.assertEqual(event["preset_stop_price"], stop)
        self.assertEqual(event["entry_price"], entry)
        self.assertEqual(event["stop_distance"], Decimal("1.0002"))
        self.assertEqual(event["risk_amount"], per_unit * max_qty)
        self.assertLessEqual(event["risk_amount"], max_risk)
        self.assertLessEqual(event["risk_pct"], MAX_RISK_PCT)
        self.assertEqual(book.position.protective_stop_price, stop)
        self.assertEqual((entry - stop) / entry * Decimal(10000), Decimal("100"))
        self.assertEqual(event["preset_stop_price"], frozen_stop_price("LONG", entry))

    def test_short_open_uses_the_short_stop(self):
        book = _book()
        event = _open(book, choice="SHORT", qty="1")[0]
        entry = Decimal("99.98")
        stop = entry * Decimal("1.01")
        self.assertEqual(event["entry_price"], entry)
        self.assertEqual(event["preset_stop_price"], stop)
        self.assertGreater(stop, entry)
        self.assertEqual((stop - entry) / entry * Decimal(10000), Decimal("100"))
        self.assertLessEqual(event["risk_pct"], MAX_RISK_PCT)
        self.assertEqual(event["position_after"], "SHORT")

    def test_dust_equity_rejects_without_a_fill(self):
        book = _book(Decimal("0.00000001"))
        event = _open(book, qty="1")[0]
        self.assertEqual(event["event_type"], "NO_FILL")
        self.assertEqual(event["fill_status"], "NO_FILL")
        self.assertEqual(event["reason_code"], "C6_NO_POSITIVE_SIZE")
        self.assertEqual(event["quantity"], Decimal(0))
        self.assertIsNone(event["trade_id"])
        self.assertEqual(event["preset_stop_price"], Decimal("99.0198"))
        self.assertIsNone(book.position)
        self.assertEqual(len(book.events), 1)

    def test_zero_equity_rejects_without_inventing_a_position(self):
        book = _book(Decimal(0))
        event = _open(book, qty="1")[0]
        self.assertEqual(event["event_type"], "NO_FILL")
        self.assertEqual(event["reason_code"], "C6_NO_POSITIVE_SIZE")
        self.assertIsNone(book.position)

    def test_non_positive_reference_does_not_invent_a_stop(self):
        book = _book()
        event = _open(book, ref=Decimal(0))[0]
        self.assertEqual(event["reason_code"], "C6_INVALID_ENTRY")
        self.assertIsNone(event["preset_stop_price"])
        self.assertIsNone(event["entry_price"])
        self.assertIsNone(book.position)

    def test_open_row_stays_immutable_when_the_caller_mutates_the_copy(self):
        book = _book()
        returned = _open(book, qty="1")[0]
        returned["preset_stop_price"] = Decimal("1")
        returned["risk_pct"] = Decimal("1")
        stored = book.events[0]
        self.assertEqual(stored["preset_stop_price"], Decimal("99.0198"))
        self.assertLessEqual(stored["risk_pct"], MAX_RISK_PCT)

    def test_stop_widen_is_refused_and_tighten_does_not_rewrite_the_open(self):
        book = _book()
        opened = _open(book, qty="1")[0]
        original = opened["preset_stop_price"]
        refused = book.propose_stop_update(
            Decimal("98"),
            observation_id="obs-widen",
            at="2026-09-30T00:01:00Z",
        )
        self.assertEqual(refused["event_type"], "STOP_UPDATE_REJECTED")
        self.assertEqual(refused["reason_code"], "STOP_WIDEN_FORBIDDEN")
        self.assertEqual(book.position.protective_stop_price, original)
        self.assertEqual(book.events[0]["preset_stop_price"], original)
        self.assertEqual(book.events[0]["risk_amount"], opened["risk_amount"])

        tightened = book.propose_stop_update(
            Decimal("99.50"),
            observation_id="obs-tighten",
            at="2026-09-30T00:02:00Z",
        )
        self.assertEqual(tightened["event_type"], "STOP_TIGHTEN")
        self.assertEqual(tightened["protective_stop_price"], Decimal("99.50"))
        self.assertEqual(tightened["preset_stop_price"], original)
        self.assertTrue(tightened["ex_ante_fields_unchanged"])
        self.assertEqual(book.position.protective_stop_price, Decimal("99.50"))
        self.assertEqual(book.position.preset_stop_price, original)
        self.assertEqual(book.events[0]["preset_stop_price"], original)
        self.assertEqual(book.events[0]["risk_pct"], opened["risk_pct"])
        self.assertEqual(book.events[0]["equity_at_open"], EQUITY)

        unchanged = book.propose_stop_update(
            Decimal("99.50"),
            observation_id="obs-same",
            at="2026-09-30T00:03:00Z",
        )
        self.assertIsNone(unchanged)
        self.assertEqual(len(book.events), 3)

    def test_refused_widen_does_not_move_the_hard_stop(self):
        book = _book()
        _open(book, qty="1")
        book.propose_stop_update(Decimal("90"), observation_id="obs-w", at="2026-09-30T00:01:00Z")
        self.assertEqual(book.position.protective_stop_price, Decimal("99.0198"))
        inside = book.on_mark(Decimal("99.50"), observation_id="obs-m1", at="2026-09-30T00:02:00Z")
        self.assertIsNone(inside)
        self.assertIsNotNone(book.position)
        # Touching the frozen stop exits. A stop moved down to 90 would still be open here.
        hit = book.on_mark(Decimal("99.0198"), observation_id="obs-m2", at="2026-09-30T00:03:00Z")
        self.assertEqual(hit["event_type"], "HARD_STOP_EXIT")
        self.assertEqual(hit["reason_code"], "HARD_STOP_TOUCHED")
        self.assertIsNone(book.position)

    def test_hard_stop_exit_long_and_short(self):
        long_book = _book()
        opened = _open(long_book, qty="1")[0]
        quiet = long_book.on_mark(Decimal("99.02"), observation_id="obs-q", at="2026-09-30T00:01:00Z")
        self.assertIsNone(quiet)
        hit = long_book.on_mark(Decimal("99.0198"), observation_id="obs-h", at="2026-09-30T00:02:00Z")
        self.assertEqual(hit["event_type"], "HARD_STOP_EXIT")
        self.assertEqual(hit["trade_id"], opened["trade_id"])
        self.assertEqual(hit["preset_stop_price"], opened["preset_stop_price"])
        self.assertEqual(hit["equity_at_open"], opened["equity_at_open"])
        self.assertEqual(hit["risk_amount"], opened["risk_amount"])
        self.assertEqual(hit["risk_pct"], opened["risk_pct"])
        self.assertEqual(hit["position_after"], "FLAT")
        self.assertEqual(hit["fill_status"], "FILLED")
        self.assertIsNone(long_book.position)
        later = long_book.on_signal(
            "FLAT",
            REF,
            Decimal("1"),
            observation_id="obs-flat-after",
            at="2026-09-30T00:03:00Z",
        )
        self.assertEqual(later, [])

        short_book = _book()
        short_open = _open(short_book, choice="SHORT", qty="1")[0]
        stop = short_open["preset_stop_price"]
        self.assertIsNone(
            short_book.on_mark(stop - Decimal("0.0001"), observation_id="obs-s1", at="2026-09-30T00:01:00Z")
        )
        short_hit = short_book.on_mark(stop, observation_id="obs-s2", at="2026-09-30T00:02:00Z")
        self.assertEqual(short_hit["event_type"], "HARD_STOP_EXIT")
        self.assertEqual(short_hit["trade_id"], short_open["trade_id"])
        self.assertIsNone(short_book.position)

    def test_gap_through_the_stop_does_not_rewrite_the_preset(self):
        book = _book()
        opened = _open(book, qty="1")[0]
        hit = book.on_mark(Decimal("50"), observation_id="obs-gap", at="2026-09-30T00:02:00Z")
        self.assertEqual(hit["event_type"], "HARD_STOP_EXIT")
        self.assertEqual(hit["exit_price"], Decimal("50"))
        self.assertEqual(hit["preset_stop_price"], opened["preset_stop_price"])
        self.assertEqual(book.events[0]["preset_stop_price"], Decimal("99.0198"))

    def test_flat_and_reverse_still_close_on_signal(self):
        flat_book = _book()
        opened = _open(flat_book, qty="1")[0]
        flat = flat_book.on_signal(
            "FLAT",
            Decimal("101"),
            Decimal("1"),
            observation_id="obs-flat",
            at="2026-09-30T00:04:00Z",
        )
        self.assertEqual(len(flat), 1)
        self.assertEqual(flat[0]["event_type"], "FLAT_EXIT")
        self.assertEqual(flat[0]["reason_code"], "FLAT_SIGNAL")
        self.assertEqual(flat[0]["trade_id"], opened["trade_id"])
        self.assertEqual(flat[0]["preset_stop_price"], opened["preset_stop_price"])
        self.assertIsNone(flat_book.position)
        self.assertNotIn("HARD_STOP_EXIT", [row["event_type"] for row in flat_book.events])

        rev_book = _book()
        first = _open(rev_book, qty="1", oid="obs-1")[0]
        events = rev_book.on_signal(
            "SHORT",
            Decimal("101"),
            Decimal("1000"),
            observation_id="obs-rev",
            at="2026-09-30T00:05:00Z",
        )
        self.assertEqual([row["event_type"] for row in events], ["REVERSE_EXIT", "REVERSE_ENTRY"])
        self.assertEqual(events[0]["trade_id"], first["trade_id"])
        self.assertEqual(events[0]["reason_code"], "REVERSE_SIGNAL")
        self.assertNotEqual(events[1]["trade_id"], first["trade_id"])
        self.assertEqual(events[1]["event_type"], "REVERSE_ENTRY")
        self.assertEqual(events[1]["size_action"], "SHRINK")
        self.assertLessEqual(events[1]["risk_pct"], MAX_RISK_PCT)
        self.assertEqual(events[1]["side"], "SHORT")
        self.assertGreater(events[1]["preset_stop_price"], events[1]["entry_price"])
        self.assertEqual(rev_book.position.side, "SHORT")
        self.assertEqual(rev_book.position.trade_id, events[1]["trade_id"])

    def test_same_side_signal_does_not_add_size_or_move_the_stop(self):
        book = _book()
        _open(book, qty="1")
        stop = book.position.protective_stop_price
        extra = book.on_signal(
            "LONG",
            REF,
            Decimal("1000"),
            observation_id="obs-add",
            at="2026-09-30T00:06:00Z",
        )
        self.assertEqual(extra, [])
        self.assertEqual(book.position.quantity, Decimal("1"))
        self.assertEqual(book.position.protective_stop_price, stop)
        self.assertEqual(len(book.events), 1)

    def test_stop_distance_bps_stays_fixed_after_a_protective_exit(self):
        book = _book()
        _open(book, qty="1")
        book.on_mark(Decimal("99.0198"), observation_id="obs-h", at="2026-09-30T00:02:00Z")
        self.assertLess(book.cash, EQUITY)
        second = _open(book, qty="1000", oid="obs-2", at="2026-09-30T00:03:00Z")[0]
        entry = second["entry_price"]
        stop = second["preset_stop_price"]
        self.assertEqual((entry - stop) / entry * Decimal(10000), Decimal("100"))
        self.assertEqual(second["equity_at_open"], book.events[-1]["equity_at_open"])
        self.assertEqual(second["max_risk_amount"], second["equity_at_open"] * MAX_RISK_PCT)
        self.assertLess(second["equity_at_open"], EQUITY)
        self.assertLessEqual(second["risk_pct"], MAX_RISK_PCT)
        self.assertEqual(second["stop_rule_id"], STOP_RULE_ID)

    def test_live_execution_is_refused(self):
        with self.assertRaises(ProtectiveBoundaryError) as raised:
            ProtectiveRiskBook(EQUITY, execution="live")
        self.assertEqual(raised.exception.reason, "LIVE_TRADING_NO_GO")
        book = _book()
        with self.assertRaises(ProtectiveBoundaryError):
            book.on_signal(
                "LONG",
                REF,
                Decimal("1"),
                observation_id="obs",
                at=AT,
                execution="live",
            )
        self.assertEqual(book.events, [])
        self.assertIsNone(book.position)

    def test_hash_chain_and_jsonl_keep_decimal_risk_fields(self):
        book = _book()
        _open(book, qty="1000")
        rows = book.events
        self.assertEqual(rows[0]["prev_hash"], "GENESIS")
        self.assertEqual(len(rows[0]["row_hash"]), 64)
        text = book.to_jsonl()
        self.assertIn('"schema_version":"official_ledger_c6_v1"', text)
        self.assertIn('"strategy_version":"affl_v2_c6_protective_v1"', text)
        self.assertIn('"event_type":"OPEN"', text)
        self.assertIn('"preset_stop_price":"99.0198"', text)
        self.assertNotIn("HARD_STOP_EXIT", text)

    def test_public_position_mutation_cannot_bypass_stop(self):
        book = _book()
        opened = _open(book, qty="1")[0]
        original = opened["preset_stop_price"]
        view = book.position
        with self.assertRaises(AttributeError):
            view.protective_stop_price = Decimal("90")
        with self.assertRaises(AttributeError):
            view.preset_stop_price = Decimal("90")
        with self.assertRaises(AttributeError):
            view.risk_amount = Decimal(0)
        object.__setattr__(view, "protective_stop_price", Decimal("90"))
        object.__setattr__(view, "preset_stop_price", Decimal("90"))
        object.__setattr__(view, "risk_amount", Decimal(0))
        object.__setattr__(view, "risk_pct", Decimal(0))
        self.assertEqual(book.position.protective_stop_price, original)
        self.assertEqual(book.position.preset_stop_price, original)
        self.assertEqual(book.position.risk_amount, opened["risk_amount"])
        self.assertEqual(book.position.risk_pct, opened["risk_pct"])
        with self.assertRaises(AttributeError):
            book.position = None
        self.assertEqual(book.position.side, "LONG")
        hit = book.on_mark(original, observation_id="obs-still-stopped", at="2026-09-30T00:02:00Z")
        self.assertEqual(hit["event_type"], "HARD_STOP_EXIT")
        self.assertEqual(hit["preset_stop_price"], opened["preset_stop_price"])
        self.assertEqual(hit["risk_amount"], opened["risk_amount"])
        self.assertEqual(hit["risk_pct"], opened["risk_pct"])
        self.assertEqual(hit["equity_at_open"], opened["equity_at_open"])
        self.assertIsNone(book.position)

    def test_exit_and_mark_reject_non_finite_or_non_positive_prices(self):
        book = _book()
        _open(book, choice="SHORT", qty="1")
        cash = book.cash
        event_count = len(book.events)
        for bad in (0, -1, "NaN", "Infinity", "-Infinity"):
            with self.assertRaises(ProtectiveBoundaryError):
                book.on_signal(
                    "FLAT",
                    bad,
                    Decimal("1"),
                    observation_id="obs-bad-flat",
                    at="2026-09-30T00:04:00Z",
                )
            self.assertEqual(len(book.events), event_count)
            self.assertEqual(book.cash, cash)
            self.assertEqual(book.position.side, "SHORT")
            self.assertFalse(any(row["fill_status"] == "FILLED" and row["event_type"] != "OPEN" for row in book.events))
        for bad in (0, -1, "NaN", "Infinity", "-Infinity"):
            with self.assertRaises(ProtectiveBoundaryError):
                book.on_mark(bad, observation_id="obs-bad-mark", at="2026-09-30T00:05:00Z")
            self.assertEqual(len(book.events), event_count)
            self.assertEqual(book.cash, cash)
            self.assertEqual(book.position.protective_stop_price, book.events[0]["preset_stop_price"])
        flat = book.on_signal(
            "FLAT",
            Decimal("101"),
            Decimal("1"),
            observation_id="obs-good-flat",
            at="2026-09-30T00:06:00Z",
        )
        self.assertEqual(flat[0]["event_type"], "FLAT_EXIT")
        self.assertEqual(flat[0]["fill_status"], "FILLED")
        self.assertIsNone(book.position)

    def test_unserializable_observation_id_does_not_half_apply(self):
        book = _book()
        cash = book.cash
        with self.assertRaises(TypeError):
            book.on_signal(
                "LONG",
                REF,
                Decimal("1"),
                observation_id=["not-a-string"],
                at=AT,
            )
        self.assertEqual(book.events, [])
        self.assertIsNone(book.position)
        self.assertEqual(book.cash, cash)

        opened = _open(book, qty="1")[0]
        cash = book.cash
        with self.assertRaises(TypeError):
            book.on_signal(
                "FLAT",
                Decimal("101"),
                Decimal("1"),
                observation_id=["not-a-string"],
                at="2026-09-30T00:04:00Z",
            )
        self.assertEqual(len(book.events), 1)
        self.assertEqual(book.events[0]["event_type"], "OPEN")
        self.assertEqual(book.events[0]["trade_id"], opened["trade_id"])
        self.assertEqual(book.position.side, "LONG")
        self.assertEqual(book.position.protective_stop_price, opened["preset_stop_price"])
        self.assertEqual(book.cash, cash)
        flat = book.on_signal(
            "FLAT",
            Decimal("101"),
            Decimal("1"),
            observation_id="obs-flat-after-reject",
            at="2026-09-30T00:05:00Z",
        )
        self.assertEqual(flat[0]["event_type"], "FLAT_EXIT")
        self.assertEqual(flat[0]["trade_id"], opened["trade_id"])
        self.assertEqual(flat[0]["risk_amount"], opened["risk_amount"])
        self.assertIsNone(book.position)


class ProtectiveCommitBoundaryRegressionTest(unittest.TestCase):
    @staticmethod
    def snapshot(book):
        return (
            book.cash, book.realized_pnl_cum, book.position,
            book.events, book._seq, book._prev_hash,
        )

    @staticmethod
    def operation(kind):
        book = _book()
        if kind not in ("open", "reject"):
            _open(book)
        if kind == "open":
            call = lambda **meta: book.on_signal("LONG", REF, "1", **meta)
        elif kind == "reject":
            call = lambda **meta: book.on_signal("LONG", REF, "0", **meta)
        elif kind == "close":
            call = lambda **meta: book.on_signal("FLAT", "101", "1", **meta)
        elif kind == "mark":
            call = lambda **meta: book.on_mark("99.0198", **meta)
        elif kind == "tighten":
            call = lambda **meta: book.propose_stop_update("99.5", **meta)
        elif kind == "widen":
            call = lambda **meta: book.propose_stop_update("98", **meta)
        else:
            raise AssertionError(kind)
        return book, call

    def test_metadata_requires_immutable_plain_strings(self):
        for kind in ("open", "reject", "close", "mark", "tighten", "widen"):
            for field in ("observation_id", "at"):
                for value in ({"id": "mutable"}, [], None, 1, False, Decimal("1")):
                    with self.subTest(kind=kind, field=field, value=value):
                        book, call = self.operation(kind)
                        before = self.snapshot(book)
                        meta = {"observation_id": "next", "at": AT, field: value}
                        with self.assertRaises(TypeError):
                            call(**meta)
                        self.assertEqual(self.snapshot(book), before)

    def test_metadata_rejects_blank_strings_without_mutation(self):
        for field in ("observation_id", "at"):
            for value in ("", " ", "\t"):
                with self.subTest(field=field, value=value):
                    book, call = self.operation("open")
                    before = self.snapshot(book)
                    with self.assertRaises(ProtectiveBoundaryError):
                        call(**{"observation_id": "next", "at": AT, field: value})
                    self.assertEqual(self.snapshot(book), before)

    def test_hash_failure_preserves_state_sequence_and_chain(self):
        for kind in ("open", "reject", "close", "mark", "tighten", "widen"):
            with self.subTest(kind=kind):
                book, call = self.operation(kind)
                before = self.snapshot(book)
                with patch.object(boundary, "row_hash", side_effect=RuntimeError("hash fault")):
                    with self.assertRaises(RuntimeError):
                        call(observation_id="next", at=AT)
                self.assertEqual(self.snapshot(book), before)

    def test_copy_failure_is_before_any_commit(self):
        original_copy = boundary.deepcopy
        for kind in ("open", "reject", "close", "mark", "tighten", "widen"):
            for fail_on in (1, 2):
                with self.subTest(kind=kind, fail_on=fail_on):
                    book, call = self.operation(kind)
                    before = self.snapshot(book)
                    calls = 0

                    def fail_copy(value):
                        nonlocal calls
                        calls += 1
                        if calls == fail_on:
                            raise MemoryError("copy fault")
                        return original_copy(value)

                    with patch.object(boundary, "deepcopy", side_effect=fail_copy):
                        with self.assertRaises(MemoryError):
                            call(observation_id="next", at=AT)
                    self.assertEqual(self.snapshot(book), before)

    def test_append_failure_rolls_back_state_sequence_and_chain(self):
        class AppendThenFail(list):
            def append(self, value):
                super().append(value)
                raise RuntimeError("append fault")

        for kind in ("open", "reject", "close", "mark", "tighten", "widen"):
            with self.subTest(kind=kind):
                book, call = self.operation(kind)
                before = self.snapshot(book)
                book._events = AppendThenFail(book._events)
                with self.assertRaises(RuntimeError):
                    call(observation_id="next", at=AT)
                # Disable the injected container fault before the readback;
                # preserve its contents so missing/extra rows still fail.
                book._events = list(book._events)
                self.assertEqual(self.snapshot(book), before)

    def test_successful_commits_keep_detached_rows_and_valid_hashes(self):
        book = _book()
        first = _open(book)[0]
        first["observation_id"] = "caller-mutated"
        book.propose_stop_update("99.5", observation_id="tighten", at=AT)
        book.on_mark("99.5", observation_id="stop", at=AT)
        previous = boundary.GENESIS_HASH
        for event in book.events:
            self.assertEqual(event["prev_hash"], previous)
            self.assertEqual(event["row_hash"], boundary.row_hash(event))
            previous = event["row_hash"]
        self.assertEqual(book.events[0]["observation_id"], "obs-open")
        self.assertIsNone(book.position)


if __name__ == "__main__":
    unittest.main()
