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
    C7_NOT_READY,
    EQUITY_V2_1_HEADER,
    EQUITY_V2_1_SCORING_VIEW,
    LEGACY_EQUITY_FILENAME,
    LEGACY_HEADER_10,
    LEGACY_HEADER_6,
    NEW_EQUITY_FILENAME,
    SCORING_SAMPLE_CLASS,
    VIEW_ID,
    EquitySchemaError,
    LegacyEquityImmutable,
    accepts_scoring_sample,
    header_line,
    parse_equity_csv,
    project_scoring_view,
    reject_legacy_header,
    render_equity_csv,
    scoring_view_header_line,
)
from eval_recording.equity_v21_dual_write import (
    EQUITY_V21_COLUMNS,
    MARK_RULE_BOUND,
    MARK_RULE_UNBOUND,
    SAMPLE_CLASS_NON_SCORING,
    genesis_row,
    record_equity_v21,
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
    HONESTY_RECORDED,
    MARK_KIND_BAR,
    MARK_KIND_FILL,
    MARK_KIND_GENESIS,
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


def _disk_row(
    *,
    timestamp_utc: str,
    observation_id: str,
    position: str,
    mark_rule_id: str,
    sample_class: str,
    net_liquidation_equity: str = "10000",
) -> dict[str, str]:
    return {
        "schema_version": "equity_v2_1",
        "timestamp_utc": timestamp_utc,
        "observation_id": observation_id,
        "position": position,
        "realized_pnl": "0",
        "unrealized_pnl": "0",
        "net_liquidation_equity": net_liquidation_equity,
        "drawdown": "0",
        "exposure": "0" if position == "FLAT" else "1",
        "cash_reserve": "10000",
        "active_notional": "0" if position == "FLAT" else "1000",
        "mark_rule_id": mark_rule_id,
        "sample_class": sample_class,
    }


def _c6_fixture_events() -> list[dict[str, object]]:
    payload = json.loads(
        (PROJECT_ROOT / "eval_recording/fixtures/c6_open_ex_ante.json").read_text(
            encoding="utf-8"
        )
    )
    events = payload["events"]
    assert isinstance(events, list)
    return events


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
        # The manual public-funding fetch from the recording package is the
        # one module that imports urllib. Gate B modules stay offline.
        manual_public_fetch = (package / "funding" / "fetch_pf_xbtusd_funding.py").resolve()
        self.assertTrue(manual_public_fetch.is_file())
        for path in package.rglob("*.py"):
            if path.resolve() == manual_public_fetch:
                continue
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
    def test_reader_accepts_only_the_thirteen_column_header(self):
        self.assertEqual(EQUITY_V2_1_HEADER, EQUITY_V21_COLUMNS)
        self.assertEqual(len(EQUITY_V2_1_HEADER), 13)
        self.assertEqual(len(EQUITY_V2_1_SCORING_VIEW), 17)
        self.assertIn("equity_at_open", EQUITY_V2_1_SCORING_VIEW)
        self.assertNotIn("equity_at_open", EQUITY_V2_1_HEADER)
        self.assertNotIn("trade_id", EQUITY_V2_1_HEADER)
        self.assertNotEqual(EQUITY_V2_1_HEADER, LEGACY_HEADER_6)
        self.assertNotEqual(EQUITY_V2_1_HEADER, LEGACY_HEADER_10)
        self.assertNotEqual(EQUITY_V2_1_SCORING_VIEW, EQUITY_V2_1_HEADER)
        with self.assertRaises(LegacyEquityImmutable):
            reject_legacy_header(list(LEGACY_HEADER_6))
        with self.assertRaises(LegacyEquityImmutable):
            reject_legacy_header(list(LEGACY_HEADER_10))
        with self.assertRaises(LegacyEquityImmutable):
            parse_equity_csv(",".join(LEGACY_HEADER_6) + "\n")
        with self.assertRaises(LegacyEquityImmutable):
            parse_equity_csv(",".join(LEGACY_HEADER_10) + "\n")
        seventeen = ",".join(EQUITY_V2_1_SCORING_VIEW) + "\n"
        with self.assertRaises(EquitySchemaError):
            parse_equity_csv(seventeen)
        schema = json.loads(
            (
                PROJECT_ROOT
                / "eval_recording/schemas/anchor_fake_fill_equity_v2_1_official.SCHEMA.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(tuple(schema["header"]), EQUITY_V2_1_HEADER)
        self.assertEqual(schema["scoring_view"]["view_id"], VIEW_ID)
        self.assertFalse(schema["scoring_view"]["written"])
        self.assertEqual(tuple(schema["scoring_view"]["columns"]), EQUITY_V2_1_SCORING_VIEW)
        self.assertEqual(
            schema["header_sha256"],
            hashlib.sha256(header_line().encode("utf-8")).hexdigest(),
        )
        self.assertIn(LEGACY_EQUITY_FILENAME, schema["legacy_do_not_rewrite"])
        self.assertIn("C6 OPEN", schema["scoring_view"]["derivation"]["trade_id"])
        self.assertIn("C7_NOT_READY", schema["scoring_view"]["derivation"]["mark_rule_id"])

    def test_seventeen_column_writer_does_not_create_a_file(self):
        row = genesis_row(
            timestamp_utc="2026-04-20T00:00:00Z",
            net_liquidation_equity="10000",
            cash_reserve="10000",
            sample_class=SAMPLE_CLASS_NON_SCORING,
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            targets = (
                root / LEGACY_EQUITY_FILENAME,
                root / "affl-v2-official-ledger" / "out" / NEW_EQUITY_FILENAME,
                root / NEW_EQUITY_FILENAME,
                root / "equity_v2_1_view.csv",
            )
            for dest in targets:
                with self.assertRaises(EquitySchemaError):
                    render_equity_csv(rows=[row], dest=dest)
                self.assertFalse(dest.exists(), msg=str(dest))

    def test_writer_file_reads_back_and_view_joins_the_open_fixture(self):
        genesis = genesis_row(
            timestamp_utc="2026-04-20T00:00:00Z",
            net_liquidation_equity="10000",
            cash_reserve="10000",
            sample_class=SAMPLE_CLASS_NON_SCORING,
        )
        opened = _disk_row(
            timestamp_utc="2026-04-20T01:00:00Z",
            observation_id="obs-open",
            position="LONG",
            mark_rule_id=MARK_RULE_BOUND,
            sample_class=SCORING_SAMPLE_CLASS,
        )
        bar = _disk_row(
            timestamp_utc="2026-04-20T02:00:00Z",
            observation_id="obs-bar",
            position="LONG",
            mark_rule_id=MARK_RULE_BOUND,
            sample_class=SCORING_SAMPLE_CLASS,
            net_liquidation_equity="10040",
        )
        flat = _disk_row(
            timestamp_utc="2026-04-20T03:00:00Z",
            observation_id="obs-exit",
            position="FLAT",
            mark_rule_id="",
            sample_class=SCORING_SAMPLE_CLASS,
            net_liquidation_equity="10020",
        )
        after_exit = _disk_row(
            timestamp_utc="2026-04-20T04:00:00Z",
            observation_id="obs-after",
            position="LONG",
            mark_rule_id=MARK_RULE_UNBOUND,
            sample_class=SAMPLE_CLASS_NON_SCORING,
        )
        written = (genesis, opened, bar, flat, after_exit)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / NEW_EQUITY_FILENAME
            record_equity_v21(path, opened, genesis=genesis, enabled=True)
            for extra in (bar, flat, after_exit):
                record_equity_v21(path, extra, enabled=True)
            parsed = parse_equity_csv(path.read_text(encoding="utf-8"))
        self.assertEqual(parsed, list(written))
        for row in parsed:
            self.assertEqual(list(row), list(EQUITY_V21_COLUMNS))
            self.assertNotIn("trade_id", row)
            self.assertNotIn("equity_at_open", row)
        events = _c6_fixture_events()
        self.assertEqual(events[0]["event_type"], "OPEN")
        self.assertEqual(events[0]["trade_id"], "tr_le-000007")
        self.assertEqual(events[0]["equity_at_open"], "10000")
        view = project_scoring_view(parsed, events)
        self.assertEqual([tuple(row) for row in view], [EQUITY_V2_1_SCORING_VIEW] * len(view))

        genesis_view, open_view, bar_view, flat_view, after_view = view
        self.assertEqual(genesis_view["mark_kind"], MARK_KIND_GENESIS)
        self.assertEqual(genesis_view["trade_id"], "")
        self.assertEqual(genesis_view["equity_at_open"], "")
        self.assertEqual(genesis_view["mark_rule_id"], C7_NOT_READY)
        self.assertNotEqual(genesis_view["mark_rule_id"], MARK_RULE_ID)
        self.assertEqual(genesis["mark_rule_id"], MARK_RULE_UNBOUND)

        self.assertEqual(open_view["mark_kind"], MARK_KIND_FILL)
        self.assertEqual(open_view["trade_id"], "tr_le-000007")
        self.assertEqual(open_view["equity_at_open"], "10000")
        self.assertEqual(open_view["mark_rule_id"], MARK_RULE_ID)
        self.assertEqual(open_view["mark_honesty_label"], HONESTY_RECORDED)
        self.assertTrue(accepts_scoring_sample(open_view))

        self.assertEqual(bar_view["mark_kind"], MARK_KIND_BAR)
        self.assertEqual(bar_view["trade_id"], "tr_le-000007")
        self.assertEqual(bar_view["equity_at_open"], "10000")
        self.assertEqual(bar_view["mark_honesty_label"], HONESTY_RECORDED)

        self.assertEqual(flat_view["position"], "FLAT")
        self.assertEqual(flat_view["mark_kind"], MARK_KIND_FILL)
        self.assertEqual(flat_view["trade_id"], "")
        self.assertEqual(flat_view["equity_at_open"], "")
        self.assertEqual(flat_view["mark_rule_id"], C7_NOT_READY)

        self.assertEqual(after_view["trade_id"], "")
        self.assertEqual(after_view["equity_at_open"], "")
        self.assertEqual(after_view["mark_kind"], MARK_KIND_BAR)
        self.assertEqual(after_view["mark_rule_id"], C7_NOT_READY)
        self.assertFalse(accepts_scoring_sample(after_view))
        self.assertFalse(accepts_scoring_sample(genesis_view))
        for row in view:
            self.assertEqual(row["mark_honesty_label"], HONESTY_RECORDED)
            self.assertNotEqual(row["mark_kind"], MARK_KIND_OHLC_PROXY)

    def test_reverse_entry_replaces_the_closed_leg_and_flat_stays_empty(self):
        events = [
            {
                "event_type": "OPEN",
                "observation_id": "obs-first",
                "at": "2026-04-20T01:00:00Z",
                "trade_id": "tr_le-000001",
                "equity_at_open": "10000",
            },
            {
                "event_type": "REVERSE_EXIT",
                "observation_id": "obs-rev-exit",
                "at": "2026-04-20T02:00:00Z",
                "trade_id": "tr_le-000001",
                "equity_at_open": "10000",
            },
            {
                "event_type": "REVERSE_ENTRY",
                "observation_id": "obs-rev-entry",
                "at": "2026-04-20T02:00:00Z",
                "trade_id": "tr_le-000009",
                "equity_at_open": Decimal("10050"),
            },
            {
                "event_type": "HARD_STOP_EXIT",
                "observation_id": "obs-stop",
                "at": "2026-04-20T04:00:00Z",
                "trade_id": "tr_le-000009",
                "equity_at_open": "10050",
            },
        ]
        rows = [
            _disk_row(
                timestamp_utc="2026-04-20T01:30:00Z",
                observation_id="obs-mid",
                position="LONG",
                mark_rule_id=MARK_RULE_BOUND,
                sample_class=SCORING_SAMPLE_CLASS,
            ),
            _disk_row(
                timestamp_utc="2026-04-20T02:00:00Z",
                observation_id="obs-rev-entry",
                position="SHORT",
                mark_rule_id=MARK_RULE_BOUND,
                sample_class=SCORING_SAMPLE_CLASS,
                net_liquidation_equity="10050",
            ),
            _disk_row(
                timestamp_utc="2026-04-20T02:00:00Z",
                observation_id="obs-flat-same-time",
                position="FLAT",
                mark_rule_id=MARK_RULE_BOUND,
                sample_class=SCORING_SAMPLE_CLASS,
            ),
            _disk_row(
                timestamp_utc="2026-04-20T05:00:00Z",
                observation_id="obs-later",
                position="LONG",
                mark_rule_id=MARK_RULE_BOUND,
                sample_class=SCORING_SAMPLE_CLASS,
            ),
        ]
        first, second, flat, later = project_scoring_view(rows, events)
        self.assertEqual(first["trade_id"], "tr_le-000001")
        self.assertEqual(first["equity_at_open"], "10000")
        self.assertEqual(first["mark_kind"], MARK_KIND_BAR)
        self.assertEqual(second["trade_id"], "tr_le-000009")
        self.assertEqual(second["equity_at_open"], "10050")
        self.assertEqual(second["mark_kind"], MARK_KIND_FILL)
        self.assertEqual(flat["trade_id"], "")
        self.assertEqual(flat["equity_at_open"], "")
        self.assertEqual(later["trade_id"], "")
        self.assertEqual(later["equity_at_open"], "")


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
        self.assertEqual(
            _between(
                text,
                "<!-- EQUITY_V2_1_SCORING_VIEW_BEGIN -->",
                "<!-- EQUITY_V2_1_SCORING_VIEW_END -->",
            ),
            scoring_view_header_line(),
        )
        self.assertIn(VIEW_ID, text)
        self.assertIn(C7_NOT_READY, text)
        self.assertIn("not a file header", text)
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
