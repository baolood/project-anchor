"""Gate B recording contracts. These tests do not score Official PnL, PF, or DD."""

from __future__ import annotations

import ast
import hashlib
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from eval_recording import boundaries
from eval_recording.c9_sources import PROPOSED_INCIDENT_REGISTER, authoritative_sources
from eval_recording.equity_schema import (
    EQUITY_V2_1_HEADER,
    LEGACY_EQUITY_FILENAME,
    LEGACY_HEADER_10,
    LEGACY_HEADER_6,
    NEW_EQUITY_FILENAME,
    EquitySchemaError,
    LegacyEquityImmutable,
    genesis_row,
    header_line,
    parse_equity_csv,
    reject_legacy_header,
    render_equity_csv,
)
from eval_recording.funding_ingest import (
    CANDIDATE_ABSOLUTE,
    CANDIDATE_RELATIVE,
    DATA_MISSING,
    DATA_NO_INTERVAL,
    DATA_PARTIAL,
    DATA_PRESENT,
    NET_EX_FUNDING,
    NET_INCL_FUNDING,
    OFFICIAL_SIGN_LOCK,
    OFFICIAL_SYMBOL,
    ZERO_FILL_MISSING,
    FundingRatePoint,
    ZeroFillForbidden,
    assess_funding_window,
    public_historical_funding_request,
    resolve_recorded_net,
)
from eval_recording.mark_rule import (
    HONESTY_NOT_TICK_LOW,
    MARK_KIND_BAR,
    MARK_KIND_FILL,
    MARK_KIND_OHLC_PROXY,
    MARK_RULE_C7_V1_TEXT,
    MARK_RULE_ID,
    counts_toward_required_mark,
    missing_fill_marks,
    missing_hourly_marks,
)
from eval_recording.trade_id import (
    RECORDING_SCHEMA_VERSION,
    RecordingOptionalFields,
    TradeIdError,
    apply_trade_id,
    authoritative_trade_id,
    trade_id_from_entry_ledger_event_id,
    trade_id_hash,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = PROJECT_ROOT / "docs" / "ANCHOR_EVAL_RECORDING_INFRA_SPEC_V1.md"


def _between(text: str, begin: str, end: str) -> str:
    start = text.index(begin) + len(begin)
    stop = text.index(end, start)
    return text[start:stop].strip()


def _open_row() -> dict[str, str]:
    row = genesis_row(
        timestamp_utc="2026-01-01T00:00:00Z",
        net_liquidation_equity="10000",
        cash_reserve="10000",
    )
    row.update(
        {
            "observation_id": "obs-open",
            "trade_id": "tr_le-000007",
            "position": "LONG",
            "equity_at_open": "10000",
            "mark_kind": MARK_KIND_FILL,
            "net_liquidation_equity": "10000",
        }
    )
    return row


class BoundariesTest(unittest.TestCase):
    def test_gate_b_is_not_on_the_formal_scoring_chain(self):
        self.assertEqual(boundaries.FORMAL_SCORING_CHAIN, "NOT_ON_FORMAL_SCORING_CHAIN")
        self.assertEqual(boundaries.T0_FROZEN, "NO")
        self.assertEqual(boundaries.OFFICIAL_PNL_SCORED, "NO")
        self.assertEqual(boundaries.OFFICIAL_PF_SCORED, "NO")
        self.assertEqual(boundaries.OFFICIAL_DD_SCORED, "NO")
        self.assertEqual(boundaries.PASS_LINE_THRESHOLDS_CHANGED, "NO")
        self.assertEqual(boundaries.LEGACY_OFFICIAL_LEDGER_MODIFIED, "NO")
        self.assertEqual(boundaries.PRODUCTION_DEPLOY, "NO")
        self.assertEqual(boundaries.LIVE_TRADING, "NO")
        self.assertEqual(boundaries.FOUNDER_EXECUTE_REQUIRED_FOR_WIRE_UP, "YES")
        self.assertEqual(boundaries.EDITS_AFFL_V2_TYPES, "NO")
        with self.assertRaises(boundaries.FormalScoreRefused):
            boundaries.refuse_formal_score("Official PnL")

    def test_c6_policy_keeps_trade_id_optional_and_additive(self):
        policy = boundaries.c6_additive_field_policy()
        self.assertEqual(policy["trade_id_if_c6_touches_same_struct"], "OPTIONAL_ADDITIVE")
        self.assertEqual(policy["version_gate"], RECORDING_SCHEMA_VERSION)
        self.assertIn("preset_stop_price", policy["c6_owns_fields"])
        self.assertNotIn("preset_stop_price", RecordingOptionalFields.__dataclass_fields__)

    def test_runtime_trees_do_not_import_the_scaffold(self):
        roots = [
            PROJECT_ROOT / "local_box",
            PROJECT_ROOT / "anchor-backend",
            PROJECT_ROOT / "scripts",
            PROJECT_ROOT / "risk_engine",
            PROJECT_ROOT / "shared",
        ]
        for root in roots:
            for path in root.rglob("*"):
                if path.suffix not in {".py", ".sh"} or not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                self.assertNotIn("eval_recording", text, msg=str(path))

    def test_package_does_not_import_network_or_affl_writer(self):
        package = PROJECT_ROOT / "eval_recording"
        for path in package.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module.split(".")[0]]
                else:
                    continue
                for name in names:
                    self.assertNotIn(
                        name,
                        {"requests", "urllib", "http", "socket", "local_box", "affl_v2"},
                    )


class TradeIdTest(unittest.TestCase):
    def test_scheme_is_prefix_plus_entry_ledger_event_id(self):
        self.assertEqual(trade_id_from_entry_ledger_event_id("le-000007"), "tr_le-000007")
        with self.assertRaises(TradeIdError):
            trade_id_from_entry_ledger_event_id("tr_le-000007")
        with self.assertRaises(TradeIdError):
            trade_id_from_entry_ledger_event_id(" le-000007")

    def test_reverse_mints_a_new_leg_only_after_the_exit_copies_the_old_one(self):
        event_id, held = apply_trade_id(
            event_type="OPEN",
            ledger_event_id="le-000007",
            held_trade_id=None,
        )
        self.assertEqual((event_id, held), ("tr_le-000007", "tr_le-000007"))
        exit_id, held = apply_trade_id(
            event_type="REVERSE_EXIT",
            ledger_event_id="le-000008",
            held_trade_id=held,
        )
        self.assertEqual(exit_id, "tr_le-000007")
        self.assertIsNone(held)
        next_id, held = apply_trade_id(
            event_type="REVERSE_ENTRY",
            ledger_event_id="le-000009",
            held_trade_id=held,
        )
        self.assertEqual((next_id, held), ("tr_le-000009", "tr_le-000009"))
        with self.assertRaises(TradeIdError):
            apply_trade_id(
                event_type="REVERSE_ENTRY",
                ledger_event_id="le-000010",
                held_trade_id=held,
            )

    def test_version_gate_ignores_trade_id_on_older_records(self):
        record = {"trade_id": "tr_le-000007", "observation_id": "obs-9"}
        self.assertIsNone(
            authoritative_trade_id(record, recording_schema_version="recording_v0")
        )
        self.assertEqual(
            authoritative_trade_id(record, recording_schema_version=RECORDING_SCHEMA_VERSION),
            "tr_le-000007",
        )
        fields = RecordingOptionalFields(trade_id="tr_le-000007")
        self.assertEqual(fields.recording_schema_version, RECORDING_SCHEMA_VERSION)
        digest = trade_id_hash("genesis-1", "le-000007")
        self.assertEqual(digest, hashlib.sha256(b"genesis-1|le-000007").hexdigest())


class FundingIngestTest(unittest.TestCase):
    def test_public_plan_does_not_execute_and_names_pf_xbtusd(self):
        plan = public_historical_funding_request()
        self.assertEqual(plan["execute"], "NO")
        self.assertEqual(plan["auth"], "NONE")
        self.assertEqual(plan["private_api"], "NO")
        self.assertEqual(plan["query"], {"symbol": OFFICIAL_SYMBOL})
        self.assertIn("historicalfundingrates", plan["url"])
        self.assertEqual(plan["zero_fill_missing"], ZERO_FILL_MISSING)
        self.assertEqual(plan["cache_write_in_this_package"], "NO")
        self.assertEqual(OFFICIAL_SIGN_LOCK, "NO")

    def test_missing_partial_and_present_never_zero_fill(self):
        fixture = json.loads(
            (PROJECT_ROOT / "eval_recording/fixtures/pf_xbtusd_funding_rate_row.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(fixture["use_as_official_pnl"], "NO")
        points = tuple(FundingRatePoint.from_public_row(row) for row in fixture["rows"])
        expected = ("2026-01-01T04:00:00Z", "2026-01-01T08:00:00Z")
        window = dict(
            entry_time_utc="2026-01-01T00:00:00Z",
            exit_time_utc="2026-01-01T08:00:00Z",
            side="SHORT",
            quantity_contracts=Decimal("2"),
            position_notional=Decimal("100"),
        )
        missing = assess_funding_window(expected_timestamps=expected, points=(), **window)
        self.assertEqual(missing["FUNDING_DATA_STATUS"], DATA_MISSING)
        self.assertEqual(missing["NET_PNL_STATUS"], NET_EX_FUNDING)
        self.assertIsNone(missing["funding_pnl"])
        self.assertIsNone(missing["candidates"])
        self.assertFalse(missing["zero_filled"])

        partial = assess_funding_window(
            expected_timestamps=expected,
            points=points[:1],
            **window,
        )
        self.assertEqual(partial["FUNDING_DATA_STATUS"], DATA_PARTIAL)
        self.assertIsNone(partial["funding_pnl"])
        self.assertIsNone(partial["NET_PNL_INCL_FUNDING"])

        present = assess_funding_window(expected_timestamps=expected, points=points, **window)
        self.assertEqual(present["FUNDING_DATA_STATUS"], DATA_PRESENT)
        self.assertEqual(present["NET_PNL_STATUS"], NET_EX_FUNDING)
        self.assertIsNone(present["selected_for_net_pnl"])
        self.assertIsNone(present["funding_pnl"])
        self.assertEqual(present["candidates"][CANDIDATE_ABSOLUTE], "0.50")
        self.assertEqual(present["candidates"][CANDIDATE_RELATIVE], "-0.100")
        self.assertTrue(present["not_a_score"])
        self.assertEqual(present["formal_scoring_chain"], "NOT_ON_FORMAL_SCORING_CHAIN")

        empty = assess_funding_window(expected_timestamps=(), points=points, **window)
        self.assertEqual(empty["FUNDING_DATA_STATUS"], DATA_NO_INTERVAL)
        self.assertIsNone(empty["funding_pnl"])

    def test_retrieved_zero_is_present_and_a_gap_cannot_be_passed_as_zero(self):
        zero = FundingRatePoint.from_public_row(
            {
                "timestamp": "2026-01-01T04:00:00Z",
                "fundingRate": "0",
                "relativeFundingRate": "0",
            }
        )
        self.assertTrue(zero.is_retrieved())
        present = assess_funding_window(
            expected_timestamps=("2026-01-01T04:00:00Z",),
            points=(zero,),
            entry_time_utc="2026-01-01T00:00:00Z",
            exit_time_utc="2026-01-01T04:00:00Z",
            side="LONG",
            quantity_contracts=Decimal("1"),
            position_notional=Decimal("1"),
        )
        self.assertEqual(present["FUNDING_DATA_STATUS"], DATA_PRESENT)
        self.assertEqual(present["candidates"][CANDIDATE_ABSOLUTE], "0")
        self.assertIsNone(present["funding_pnl"])

        incomplete = FundingRatePoint.from_public_row(
            {"timestamp": "2026-01-01T04:00:00Z", "fundingRate": None, "relativeFundingRate": "0"}
        )
        self.assertFalse(incomplete.is_retrieved())
        with self.assertRaises(ZeroFillForbidden):
            resolve_recorded_net(
                ex_funding=Decimal("10"),
                funding_pnl=Decimal("0"),
                data_status=DATA_PARTIAL,
                sign_lock="YES",
            )
        with self.assertRaises(ZeroFillForbidden):
            resolve_recorded_net(
                ex_funding=Decimal("10"),
                funding_pnl=Decimal("0"),
                data_status=DATA_PRESENT,
                sign_lock=OFFICIAL_SIGN_LOCK,
            )

    def test_present_path_adds_funding_only_when_the_caller_locks_the_sign(self):
        recorded = resolve_recorded_net(
            ex_funding=Decimal("10"),
            funding_pnl=Decimal("1.5"),
            data_status=DATA_PRESENT,
            sign_lock="YES",
        )
        self.assertEqual(recorded["NET_PNL_STATUS"], NET_INCL_FUNDING)
        self.assertEqual(recorded["NET_PNL_EX_FUNDING"], "10")
        self.assertEqual(recorded["NET_PNL_INCL_FUNDING"], "11.5")
        self.assertEqual(recorded["funding_pnl"], "1.5")
        self.assertTrue(recorded["not_a_score"])
        self.assertEqual(recorded["formal_scoring_chain"], "NOT_ON_FORMAL_SCORING_CHAIN")
        self.assertEqual(OFFICIAL_SIGN_LOCK, "NO")


class EquitySchemaTest(unittest.TestCase):
    def test_header_includes_equity_at_open_and_rejects_legacy_widths(self):
        self.assertIn("equity_at_open", EQUITY_V2_1_HEADER)
        self.assertEqual(len(EQUITY_V2_1_HEADER), 17)
        self.assertNotEqual(EQUITY_V2_1_HEADER, LEGACY_HEADER_6)
        self.assertNotEqual(EQUITY_V2_1_HEADER, LEGACY_HEADER_10)
        with self.assertRaises(LegacyEquityImmutable):
            reject_legacy_header(list(LEGACY_HEADER_6))
        with self.assertRaises(LegacyEquityImmutable):
            reject_legacy_header(list(LEGACY_HEADER_10))
        schema = json.loads(
            (
                PROJECT_ROOT
                / "eval_recording/schemas/anchor_fake_fill_equity_v2_1_official.SCHEMA.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(tuple(schema["header"]), EQUITY_V2_1_HEADER)
        self.assertEqual(
            schema["header_sha256"],
            hashlib.sha256(header_line().encode("utf-8")).hexdigest(),
        )
        self.assertIn(LEGACY_EQUITY_FILENAME, schema["legacy_do_not_rewrite"])

    def test_writer_refuses_legacy_name_and_official_tree(self):
        row = genesis_row(
            timestamp_utc="2026-01-01T00:00:00Z",
            net_liquidation_equity="10000",
            cash_reserve="9900",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(LegacyEquityImmutable):
                render_equity_csv(rows=[row], dest=root / LEGACY_EQUITY_FILENAME)
            official = root / "affl-v2-official-ledger" / "out"
            with self.assertRaises(LegacyEquityImmutable):
                render_equity_csv(rows=[row], dest=official / NEW_EQUITY_FILENAME)
            dest = root / NEW_EQUITY_FILENAME
            render_equity_csv(rows=[row, _open_row()], dest=dest)
            parsed = parse_equity_csv(dest.read_text(encoding="utf-8"))
        self.assertEqual(parsed[0]["observation_id"], "LEDGER_GENESIS")
        self.assertEqual(parsed[0]["equity_at_open"], "")
        self.assertEqual(parsed[1]["equity_at_open"], "10000")
        self.assertEqual(parsed[1]["trade_id"], "tr_le-000007")
        self.assertEqual(len(dest_header(parsed)), 17)

    def test_ohlc_proxy_must_say_not_tick_low(self):
        row = _open_row()
        row["mark_kind"] = MARK_KIND_OHLC_PROXY
        row["mark_honesty_label"] = "RECORDED_MARK"
        with self.assertRaises(EquitySchemaError):
            parse_ready(row)
        row["mark_honesty_label"] = HONESTY_NOT_TICK_LOW
        parse_ready(row)
        row["trade_id"] = ""
        row["equity_at_open"] = ""
        with self.assertRaises(EquitySchemaError):
            parse_ready(row)


def dest_header(rows: list[dict[str, str]]) -> tuple[str, ...]:
    return tuple(rows[0].keys())


def parse_ready(row: dict[str, str]) -> None:
    from eval_recording.equity_schema import validate_equity_row

    validate_equity_row(row)


class MarkRuleTest(unittest.TestCase):
    def test_hourly_and_fill_gaps_ignore_the_ohlc_proxy(self):
        self.assertTrue(counts_toward_required_mark(MARK_KIND_BAR))
        self.assertTrue(counts_toward_required_mark(MARK_KIND_FILL))
        self.assertFalse(counts_toward_required_mark(MARK_KIND_OHLC_PROXY))
        missing = missing_hourly_marks(
            required_bar_open_utc=("2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"),
            marked_bar_open_utc=("2026-01-01T00:00:00Z",),
        )
        self.assertEqual(missing, ["2026-01-01T01:00:00Z"])
        self.assertEqual(
            missing_fill_marks(
                fill_event_ids=("le-000007", "le-000008"),
                marked_fill_event_ids=("le-000007",),
            ),
            ["le-000008"],
        )
        self.assertIn("at least 1 equity sample per completed 1h bar", MARK_RULE_C7_V1_TEXT)
        self.assertIn("NOT_TICK_LOW", MARK_RULE_C7_V1_TEXT)
        self.assertIn(MARK_RULE_ID, MARK_RULE_C7_V1_TEXT)


class C9SourcesTest(unittest.TestCase):
    def test_sources_are_paths_outside_the_trade_ledger(self):
        sources = authoritative_sources()
        categories = {item.category for item in sources}
        self.assertEqual(categories, {"audit", "kill_switch", "deploy", "authorization"})
        for item in sources:
            self.assertFalse(item.in_trade_ledger)
            self.assertFalse(item.path.startswith("http"))
            if item.present_in_this_repo:
                self.assertTrue((PROJECT_ROOT / item.path).is_file(), msg=item.path)
        proposed = [item for item in sources if item.proposed_register]
        self.assertEqual(len(proposed), 1)
        self.assertEqual(proposed[0].path, PROPOSED_INCIDENT_REGISTER)
        self.assertFalse((PROJECT_ROOT / PROPOSED_INCIDENT_REGISTER).exists())
        self.assertFalse((PROJECT_ROOT / "affl-v2-official-ledger").exists())


class SpecLockTest(unittest.TestCase):
    def test_spec_matches_the_code_contracts(self):
        text = SPEC_PATH.read_text(encoding="utf-8")
        self.assertEqual(_between(text, "<!-- MARK_RULE_C7_V1_BEGIN -->", "<!-- MARK_RULE_C7_V1_END -->"), MARK_RULE_C7_V1_TEXT)
        self.assertEqual(
            _between(text, "<!-- EQUITY_V2_1_HEADER_BEGIN -->", "<!-- EQUITY_V2_1_HEADER_END -->"),
            header_line(),
        )
        self.assertIn("NOT_ON_FORMAL_SCORING_CHAIN", text)
        self.assertIn("historicalfundingrates", text)
        self.assertIn("PF_XBTUSD", text)
        self.assertIn("EX_FUNDING", text)
        self.assertIn("stored as `0`", text)
        self.assertIn(NEW_EQUITY_FILENAME, text)
        self.assertIn("equity_at_open", text)
        self.assertIn("tr_", text)
        self.assertIn("separate branch", text)
        for item in authoritative_sources():
            self.assertIn(item.path, text)
        self.assertIn("does **not** freeze T0", text)
        self.assertIn("does **not** change PASS LINE C1–C10 thresholds", text)


if __name__ == "__main__":
    unittest.main()
