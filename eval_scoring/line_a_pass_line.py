"""Score Official Fake-Fill ledger rows against pass line V1.1 (final draft).

The scorer is read-only. It does not fill missing funding, stops, or risk
with zeros, and it does not rewrite Line A rows under a later rule.

Numeric gates C1–C8 and C9's zero-incident bar are the V1 R2 thresholds.
They are not refit to a ledger outcome.

C6 and C7 are Line B criteria. On Line A they are NOT_APPLICABLE and do not
enter the research baseline. A Line A research PASS is not Pilot eligibility.

Public funding, when a verified cache is supplied, is labeled
EXTERNAL_PUBLIC_FUNDING_V1. It is derived. It is not a ledger write.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from eval_scoring.official_v2_row_hash import (
    ENGINE_BUNDLE,
    ENGINE_PY_R22_SHA256,
    ENGINE_PY_SHA256,
    ENGINE_SOURCE,
    GENESIS_PREV_HASH,
    GENESIS_SOURCE,
    GOVERNANCE_GENESIS_PREV_HASH,
    verify_hash_chain,
)
from eval_scoring.public_funding import SCHEMA as FUNDING_SCHEMA
from eval_scoring.public_funding import FundingBook, FundingCacheError, leg_funding, load_funding_cache_bytes

PASS_LINE_ID = "ANCHOR_OFFICIAL_PASS_LINE_V1_1_FINAL_DRAFT"
FROZEN_T0 = "2026-10-22T20:27:21+08:00"
GOVERNANCE_REGISTER_PATH = (
    Path(__file__).resolve().parents[1] / "governance" / "ANCHOR_C9_GOVERNANCE_REGISTER.jsonl"
)
RESEARCH_CRITERIA = (
    "C1",
    "C2",
    "C3",
    "C4",
    "C5",
    "C8",
    "C9",
    "C10",
    "R0_RANDOM_DIRECTION",
)
PILOT_CRITERIA = (
    "C1",
    "C2",
    "C3",
    "C4",
    "C5",
    "C6",
    "C7",
    "C8",
    "C9",
    "C10",
    "R0_RANDOM_DIRECTION",
)
LINE_B_MARKERS = frozenset({"official_ledger_c6_v1", "affl_v2_c6_protective_v1"})
LINE_A_MARKERS = frozenset({"official_fake_fill_v2"})
INSTRUMENT_KEYS = ("market", "symbol", "instrument", "product_id")
WINDOW_DAYS_MIN = 90
CLOSED_TRADES_MIN = 50
PF_MIN = Decimal("1.10")
MAX_DRAWDOWN = Decimal("0.08")
MAX_RISK_PCT = Decimal("0.005")
MAX_DAILY_LOSS = Decimal("0.02")
MAX_CONCENTRATION = Decimal("0.25")
MONEY_TOLERANCE = Decimal("0.00000001")
RANDOM_SIMS = 1000
CST = ZoneInfo("Asia/Shanghai")

OPEN_TYPES = frozenset({"OPEN", "REVERSE_ENTRY"})
EXIT_TYPES = frozenset({"FLAT_EXIT", "REVERSE_EXIT", "HARD_STOP_EXIT"})
FILL_TYPES = OPEN_TYPES | EXIT_TYPES
C7_MARK_KINDS = frozenset({"BAR_1H", "FILL", "GENESIS"})
INCIDENT_CLASSES = (
    "UNAUTHORIZED_PRIVILEGE",
    "UNAUTHORIZED_LIVE_ORDER",
    "LEDGER_TAMPER",
    "RISK_GATE_BYPASS",
)
FORBIDDEN_PATH_MARKERS = (
    "affl-v2-official-ledger",
    "anchor-official-ledger",
    "/var/lib/private",
)

MISSING = "MISSING"


class ScoringRefusal(Exception):
    """The input path is not a ledger copy this program may read."""


@dataclass(frozen=True)
class ClosedTrade:
    entry: Mapping[str, Any]
    exit: Mapping[str, Any]
    entry_index: int
    exit_index: int


def score_ledger_file(
    path: Path | str,
    *,
    t0: str | None = None,
    t_score: str | None = None,
    governance_path: Path | str | None = None,
    random_seed: str | None = None,
    funding_cache: Path | str | None = None,
    line: str | None = None,
) -> dict[str, Any]:
    """Read one regular-file JSONL copy and return a score report."""
    ledger_path = Path(path)
    blob = _read_only_bytes(ledger_path)
    rows, unparsed, header_rows_skipped = _parse_jsonl(blob)
    governance: list[dict[str, Any]] | None = None
    if governance_path is not None:
        governance_blob = _read_only_bytes(Path(governance_path))
        governance, governance_unparsed, _governance_header = _parse_jsonl(governance_blob)
        if governance_unparsed:
            raise ScoringRefusal("governance file has unparsed rows")
    book: FundingBook | None = None
    cache_blob: bytes | None = None
    cache_name: str | None = None
    if funding_cache is not None:
        cache_path = Path(funding_cache)
        cache_blob = _read_only_bytes(cache_path)
        cache_name = cache_path.name
        try:
            book = load_funding_book(cache_blob)
        except FundingCacheError as exc:
            raise ScoringRefusal(str(exc)) from exc
    report = score_rows(
        rows,
        unparsed=unparsed,
        t0=t0,
        t_score=t_score,
        governance_rows=governance,
        random_seed=random_seed,
        funding_book=book,
        line=line,
        header_rows_skipped=header_rows_skipped,
    )
    report["input"] = {
        "sha256": hashlib.sha256(blob).hexdigest(),
        "bytes": len(blob),
        "basename": ledger_path.name,
        "read_only": True,
        "bytes_written": 0,
    }
    if cache_blob is not None:
        report["funding"]["cache_file"] = {
            "sha256": hashlib.sha256(cache_blob).hexdigest(),
            "bytes": len(cache_blob),
            "basename": cache_name,
            "read_only": True,
            "bytes_written": 0,
        }
    return report


def load_funding_book(blob: bytes) -> FundingBook:
    """Verify an EXTERNAL_PUBLIC_FUNDING_V1 cache. Does not fetch."""
    return load_funding_cache_bytes(blob)


def score_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    unparsed: int = 0,
    t0: str | None = None,
    t_score: str | None = None,
    governance_rows: Sequence[Mapping[str, Any]] | None = None,
    random_seed: str | None = None,
    funding_book: FundingBook | None = None,
    line: str | None = None,
    header_rows_skipped: int = 0,
) -> dict[str, Any]:
    """Score already-parsed ledger objects. `rows` are not mutated."""
    if t0 is None:
        t0 = FROZEN_T0
    parsed_t0 = _parse_time(t0) if t0 else None
    parsed_score = _parse_time(t_score) if t_score else None
    if t0 and parsed_t0 is None:
        raise ScoringRefusal("t0 is not an ISO-8601 timestamp")
    if t_score and parsed_score is None:
        raise ScoringRefusal("t_score is not an ISO-8601 timestamp")
    if parsed_t0 is not None and parsed_score is not None and parsed_score < parsed_t0:
        raise ScoringRefusal("t_score is earlier than t0")
    resolved_line = _resolve_line(rows, line)

    counts: dict[str, int] = {}
    for row in rows:
        label = row.get("event_type")
        key = label.strip() if isinstance(label, str) and label.strip() else "UNKNOWN"
        counts[key] = counts.get(key, 0) + 1

    paired, integrity_errors, open_unclosed = _pair(rows)
    window_ready = parsed_t0 is not None and parsed_score is not None
    selected, excluded = _select_window(paired, parsed_t0, parsed_score)
    file_instruments = _file_instruments(rows)
    economics = [
        _economics(trade, funding_book, file_instruments) for trade in selected
    ]

    criteria: dict[str, Any] = {}
    criteria["C1"] = _score_c1(parsed_t0, parsed_score, window_ready, t0, t_score)
    criteria["C2"] = _score_c2(selected, integrity_errors, unparsed, window_ready)
    criteria["C3"] = _score_c3(economics, window_ready, integrity_errors, unparsed)
    criteria["C4"] = _score_c4(economics, criteria["C3"], window_ready, integrity_errors, unparsed)
    criteria["C5"] = _score_c5(rows, parsed_t0, parsed_score, window_ready)
    criteria["C6"] = _score_c6(selected, window_ready, integrity_errors, unparsed, resolved_line)
    criteria["C7"] = _score_c7(rows, parsed_t0, parsed_score, window_ready, resolved_line)
    criteria["C8"] = _score_c8(economics, window_ready, integrity_errors, unparsed)
    criteria["C9"] = _score_c9(governance_rows, parsed_t0, parsed_score, window_ready)
    criteria["C10"] = _score_c10(rows, unparsed, header_rows_skipped)
    criteria["R0_RANDOM_DIRECTION"] = _score_r0(
        economics, window_ready, integrity_errors, unparsed, random_seed
    )

    research_status, research_reason, research_blocking = _rollup(criteria, RESEARCH_CRITERIA)
    pilot_status, pilot_reason, pilot_blocking = _rollup(criteria, PILOT_CRITERIA)
    if resolved_line == "A":
        overall = research_status
        overall_reason = research_reason
        blocking = research_blocking
        overall_scope = "LINE_A_RESEARCH_BASELINE"
        pilot_eligible = False
        pilot_eligible_reason = "LINE_A_PASS_IS_NOT_REAL_MONEY_ELIGIBILITY"
    else:
        overall = pilot_status
        overall_reason = pilot_reason
        blocking = pilot_blocking
        overall_scope = "LINE_B_PILOT"
        pilot_eligible = pilot_status == "PASS"
        pilot_eligible_reason = (
            "LINE_B_PASSED_INCLUDING_C6_C7" if pilot_eligible else "LINE_B_NOT_ELIGIBLE"
        )

    return {
        "program": "score_official_fake_fill_pass_line",
        "pass_line_id": PASS_LINE_ID,
        "frozen": True,
        "frozen_t0": FROZEN_T0,
        "thresholds_changed": False,
        "live_trading": "NO-GO",
        "line": resolved_line,
        "line_a_rewritten": False,
        "rows_retained": len(rows),
        "unparsed": unparsed,
        "counts_by_type": counts,
        "pairing": {
            "closed": len(paired),
            "open_unclosed": open_unclosed,
            "integrity_errors": integrity_errors,
            "excluded_from_window": excluded,
        },
        "t0": t0,
        "t_score": t_score,
        "funding_zero_filled": False,
        "funding": _funding_report(funding_book, economics, file_instruments),
        "program_latency_used_as_fill": False,
        "fill_latency_seconds": _latency_report(paired),
        "criteria": criteria,
        "closed_trades": [_trade_public(trade, econ) for trade, econ in zip(selected, economics)],
        "research_baseline": research_status,
        "research_baseline_reason": research_reason,
        "pilot_eligible": pilot_eligible,
        "pilot_eligible_reason": pilot_eligible_reason,
        "overall": overall,
        "overall_reason": overall_reason,
        "overall_scope": overall_scope,
        "blocking_criteria": blocking,
    }


def _score_c1(t0: datetime | None, t_score: datetime | None, ready: bool, raw_t0: str | None, raw_score: str | None) -> dict[str, Any]:
    base = _criterion("C1", "elapsed_floor_days", f">= {WINDOW_DAYS_MIN}")
    if not ready:
        return _not_scorable(base, "T0_NOT_FROZEN" if not raw_t0 or not raw_score else "T0_NOT_FROZEN")
    assert t0 is not None and t_score is not None
    elapsed = Decimal(int((t_score - t0).total_seconds()))
    window_days = int(elapsed // Decimal(86400))
    base["value"] = window_days
    base["method"] = "floor((T_score - T0) / 86400); a partial day does not round up"
    if window_days >= WINDOW_DAYS_MIN:
        return _pass(base)
    return _fail(base, "WINDOW_SHORTER_THAN_90_DAYS")


def _score_c2(
    selected: Sequence[ClosedTrade],
    integrity_errors: Sequence[str],
    unparsed: int,
    ready: bool,
) -> dict[str, Any]:
    base = _criterion("C2", "n_closed_fully_post_T0", f">= {CLOSED_TRADES_MIN}")
    if not ready:
        return _not_scorable(base, "T0_NOT_FROZEN")
    if unparsed or integrity_errors:
        return _not_scorable(base, "PAIRING_NOT_FAIR")
    base["value"] = len(selected)
    base["method"] = (
        "File order pairs OPEN/REVERSE_ENTRY with the next FLAT_EXIT, "
        "REVERSE_EXIT, or HARD_STOP_EXIT. A trade counts only when signal "
        "(if recorded), entry fill_time_utc, and exit fill_time_utc are all >= T0 "
        "and the exit is <= T_score."
    )
    if len(selected) >= CLOSED_TRADES_MIN:
        return _pass(base)
    return _fail(base, "CLOSED_TRADE_COUNT_BELOW_50")


def _score_c3(
    economics: Sequence[Mapping[str, Any]],
    ready: bool,
    integrity_errors: Sequence[str],
    unparsed: int,
) -> dict[str, Any]:
    base = _criterion("C3", "net_pnl_after_fee_funding_slippage", "> 0")
    if not ready:
        return _not_scorable(base, "T0_NOT_FROZEN")
    if unparsed or integrity_errors:
        return _not_scorable(base, "PAIRING_NOT_FAIR")
    if not economics:
        return _not_scorable(base, "NO_POST_T0_CLOSED_TRADES")
    blocked = _first_cost_block(economics)
    if blocked is not None:
        base["diagnostic_ex_funding"] = _ex_funding_diagnostic(economics)
        return _not_scorable(base, blocked)
    total = sum((item["net_incl_funding"] for item in economics), Decimal(0))
    base["value"] = _dec(total)
    base["method"] = (
        "Per trade: exit NET_PNL_EX_FUNDING minus entry fee_paid minus entry "
        "slippage_cost, plus funding only when that funding is PRESENT. "
        "Ledger PRESENT funding is used when it agrees with the public cache. "
        "A cache amount is used only when the ledger status is MISSING, and it is "
        "labeled EXTERNAL_PUBLIC_FUNDING_V1. A missing settlement stays MISSING."
    )
    if total > 0:
        return _pass(base)
    return _fail(base, "NET_PNL_NOT_POSITIVE")


def _score_c4(
    economics: Sequence[Mapping[str, Any]],
    c3: Mapping[str, Any],
    ready: bool,
    integrity_errors: Sequence[str],
    unparsed: int,
) -> dict[str, Any]:
    base = _criterion("C4", "profit_factor", f"> {PF_MIN}")
    if not ready:
        return _not_scorable(base, "T0_NOT_FROZEN")
    if unparsed or integrity_errors:
        return _not_scorable(base, "PAIRING_NOT_FAIR")
    if c3["status"] != "PASS" and c3["reason"] != "NET_PNL_NOT_POSITIVE":
        return _not_scorable(base, "C3_NET_UNAVAILABLE")
    positives = [item["net_incl_funding"] for item in economics if item["net_incl_funding"] > 0]
    negatives = [item["net_incl_funding"] for item in economics if item["net_incl_funding"] < 0]
    gross_pos = sum(positives, Decimal(0))
    gross_neg = sum(negatives, Decimal(0))
    base["method"] = (
        "PF = sum(positive official net) / abs(sum(negative official net)) "
        "on the same post-T0 set as C3. No losing trade and C3 PASS is the V1 special case."
    )
    if gross_pos == 0:
        base["value"] = _dec(Decimal(0))
        return _fail(base, "NO_POSITIVE_NET")
    if gross_neg == 0:
        base["value"] = "UNDEFINED_NO_LOSSES"
        if c3["status"] == "PASS":
            return _pass(base, reason="NO_LOSS_SPECIAL_CASE")
        return _fail(base, "NO_LOSS_WITHOUT_C3_PASS")
    pf = gross_pos / abs(gross_neg)
    base["value"] = _dec(pf)
    if pf > PF_MIN:
        return _pass(base)
    return _fail(base, "PROFIT_FACTOR_AT_OR_BELOW_1_10")


def _score_c5(
    rows: Sequence[Mapping[str, Any]],
    t0: datetime | None,
    t_score: datetime | None,
    ready: bool,
) -> dict[str, Any]:
    base = _criterion("C5", "max_drawdown", f"<= {MAX_DRAWDOWN}")
    if not ready:
        return _not_scorable(base, "T0_NOT_FROZEN")
    assert t0 is not None and t_score is not None
    points = _equity_points(rows, t0, t_score)
    base["method"] = (
        "Peak-to-trough on recorded net_liquidation_equity. Fills use fill_time_utc. "
        "Other rows use signal_available_at. The stored drawdown column is not the metric. "
        "This is the recorded event curve, not a tick path."
    )
    base["points"] = len(points)
    if len(points) < 2:
        return _not_scorable(base, "EQUITY_PATH_INSUFFICIENT")
    peak = points[0][1]
    max_dd = Decimal(0)
    if peak <= 0:
        return _not_scorable(base, "NON_POSITIVE_EQUITY_PEAK")
    for _, equity in points:
        if equity > peak:
            peak = equity
        if peak <= 0:
            return _not_scorable(base, "NON_POSITIVE_EQUITY_PEAK")
        drawdown = (peak - equity) / peak
        if drawdown > max_dd:
            max_dd = drawdown
    base["value"] = _dec(max_dd)
    if max_dd <= MAX_DRAWDOWN:
        return _pass(base)
    return _fail(base, "MAX_DRAWDOWN_ABOVE_8_PERCENT")


def _score_c6(
    selected: Sequence[ClosedTrade],
    ready: bool,
    integrity_errors: Sequence[str],
    unparsed: int,
    line: str,
) -> dict[str, Any]:
    base = _criterion("C6", "ex_ante_risk_pct", f"<= {MAX_RISK_PCT}")
    base["applies_to"] = "LINE_B"
    base["method"] = (
        "Line B only. risk_pct is the recorded risk_amount / recorded equity_at_open "
        "on the entry row. preset_stop_price must be present. Outcome PnL is not a stop. "
        "OPEN.net_liquidation_equity is not equity_at_open. "
        "Line A is NOT_APPLICABLE and is not a research-baseline block."
    )
    if line == "A":
        return _not_applicable(base, "LINE_B_ONLY")
    if not ready:
        return _not_scorable(base, "T0_NOT_FROZEN")
    if unparsed or integrity_errors:
        return _not_scorable(base, "PAIRING_NOT_FAIR")
    if not selected:
        return _not_scorable(base, "NO_POST_T0_CLOSED_TRADES")
    worst: Decimal | None = None
    for trade in selected:
        stop = trade.entry.get("preset_stop_price")
        equity = _money(trade.entry, "equity_at_open")
        risk = _money(trade.entry, "risk_amount")
        if stop is None or stop == "" or equity is None or risk is None or equity <= 0:
            return _not_scorable(base, "EX_ANTE_FIELDS_MISSING")
        risk_pct = risk / equity
        if worst is None or risk_pct > worst:
            worst = risk_pct
        if risk_pct > MAX_RISK_PCT:
            base["value"] = _dec(risk_pct)
            return _fail(base, "RISK_PCT_ABOVE_0_5_PERCENT")
    base["value"] = _dec(worst if worst is not None else Decimal(0))
    return _pass(base)


def _score_c7(
    rows: Sequence[Mapping[str, Any]],
    t0: datetime | None,
    t_score: datetime | None,
    ready: bool,
    line: str,
) -> dict[str, Any]:
    base = _criterion("C7", "max_cst_daily_loss", f"<= {MAX_DAILY_LOSS}")
    base["applies_to"] = "LINE_B"
    base["method"] = (
        "Line B only. Same-day (day_open - day_low) / day_open. "
        "The T0 calendar day uses equity at T0. "
        "Later CST days use a MARK_RULE_C7_V1 mark at 00:00 Asia/Shanghai. "
        "day_low is the minimum of BAR_1H and FILL marks. OHLC_ADVERSE_PROXY is excluded. "
        "FLAT_MARK rows without that rule are not a day low. "
        "Line A is NOT_APPLICABLE and is not a research-baseline block."
    )
    if line == "A":
        return _not_applicable(base, "LINE_B_ONLY")
    if not ready:
        return _not_scorable(base, "T0_NOT_FROZEN")
    assert t0 is not None and t_score is not None
    marks = [_c7_mark(row) for row in rows]
    marks = [item for item in marks if item is not None]
    if not marks:
        return _not_scorable(base, "MARK_RULE_C7_V1_ABSENT")
    worst: Decimal | None = None
    day = t0.astimezone(CST).date()
    last_day = t_score.astimezone(CST).date()
    while day <= last_day:
        day_start = datetime(day.year, day.month, day.day, tzinfo=CST)
        next_start = day_start + timedelta(days=1)
        window_start = t0 if day == t0.astimezone(CST).date() else day_start
        window_end = t_score if day == last_day else next_start
        if day == t0.astimezone(CST).date():
            opening = _equity_at_exact(marks, t0)
            if opening is None:
                return _not_scorable(base, "T0_EQUITY_MARK_MISSING")
        else:
            opening = _equity_at_exact(marks, day_start)
            if opening is None:
                return _not_scorable(base, "CST_MIDNIGHT_MARK_MISSING")
        in_day = [equity for at, equity in marks if window_start <= at <= window_end]
        if not in_day:
            return _not_scorable(base, "DAY_LOW_MARK_MISSING")
        if opening <= 0:
            return _not_scorable(base, "NON_POSITIVE_DAY_OPEN")
        daily_loss = (opening - min(in_day)) / opening
        if worst is None or daily_loss > worst:
            worst = daily_loss
        day = day + timedelta(days=1)
    assert worst is not None
    base["value"] = _dec(worst)
    if worst <= MAX_DAILY_LOSS:
        return _pass(base)
    return _fail(base, "DAILY_LOSS_ABOVE_2_PERCENT")


def _score_c8(
    economics: Sequence[Mapping[str, Any]],
    ready: bool,
    integrity_errors: Sequence[str],
    unparsed: int,
) -> dict[str, Any]:
    base = _criterion("C8", "best_trade_share_of_positive_net", f"<= {MAX_CONCENTRATION}")
    if not ready:
        return _not_scorable(base, "T0_NOT_FROZEN")
    if unparsed or integrity_errors:
        return _not_scorable(base, "PAIRING_NOT_FAIR")
    blocked = _first_cost_block(economics)
    if blocked is not None:
        return _not_scorable(base, blocked)
    if not economics:
        return _not_scorable(base, "NO_POST_T0_CLOSED_TRADES")
    pool = sum((max(Decimal(0), item["net_incl_funding"]) for item in economics), Decimal(0))
    base["method"] = "max winning official net / sum of positive official nets on the post-T0 set"
    if pool <= 0:
        return _fail(base, "POSITIVE_NET_POOL_EMPTY")
    best = max(item["net_incl_funding"] for item in economics)
    share = best / pool if best > 0 else Decimal(0)
    base["value"] = _dec(share)
    if share <= MAX_CONCENTRATION:
        return _pass(base)
    return _fail(base, "CONCENTRATION_ABOVE_25_PERCENT")


def _score_c9(
    governance_rows: Sequence[Mapping[str, Any]] | None,
    t0: datetime | None,
    t_score: datetime | None,
    ready: bool,
) -> dict[str, Any]:
    base = _criterion("C9", "governance_incidents", "0/0/0/0")
    base["method"] = (
        "Counts come from a separate append-only governance JSONL, not from trade rows. "
        "Each row is BREACH or ATTEST_COVERAGE and is hashed with the Official V2 recipe "
        "and genesis GOVERNANCE_GENESIS. An absent or empty register is not zero. "
        "PASS needs zero BREACH rows inside the window and one Founder ATTEST_COVERAGE "
        "whose window covers [T0, T_score]."
    )
    base["hash_genesis"] = GOVERNANCE_GENESIS_PREV_HASH
    if not ready:
        return _not_scorable(base, "T0_NOT_FROZEN")
    if governance_rows is None:
        return _not_scorable(base, "GOVERNANCE_REGISTER_ABSENT")
    if len(governance_rows) == 0:
        return _not_scorable(base, "EMPTY_GOVERNANCE_REGISTER")
    assert t0 is not None and t_score is not None
    chain_ok, chain_detail = verify_hash_chain(
        [dict(row) for row in governance_rows],
        genesis=GOVERNANCE_GENESIS_PREV_HASH,
    )
    if not chain_ok:
        base["detail"] = chain_detail
        if chain_detail.startswith("prev_hash"):
            return _fail(base, "GOVERNANCE_HASH_CHAIN_BREAK")
        return _fail(base, "GOVERNANCE_ROW_HASH_MISMATCH")
    seen_ids: set[str] = set()
    numbers: list[int] = []
    counts = {name: 0 for name in INCIDENT_CLASSES}
    other_breaches = 0
    covered = False
    for row in governance_rows:
        record_type = row.get("record_type")
        if record_type not in {"BREACH", "ATTEST_COVERAGE"}:
            return _not_scorable(base, "GOVERNANCE_ROW_UNREADABLE")
        event_id = row.get("id")
        if not isinstance(event_id, str) or not event_id.strip():
            return _not_scorable(base, "GOVERNANCE_ROW_UNREADABLE")
        if event_id in seen_ids:
            return _fail(base, "GOVERNANCE_DUPLICATE_ID")
        seen_ids.add(event_id)
        number = _governance_number(event_id)
        if number is None:
            return _not_scorable(base, "GOVERNANCE_ID_UNPATTERNED")
        numbers.append(number)
        at = _parse_time(row.get("time_utc"))
        description = row.get("description")
        recorder = row.get("recorder")
        if at is None or not isinstance(description, str) or not description.strip():
            return _not_scorable(base, "GOVERNANCE_ROW_UNREADABLE")
        if not isinstance(recorder, str) or not recorder.strip():
            return _not_scorable(base, "GOVERNANCE_ROW_UNREADABLE")
        if record_type == "ATTEST_COVERAGE":
            start = _parse_time(row.get("window_start"))
            end = _parse_time(row.get("window_end"))
            if row.get("founder_signed") is True and start is not None and end is not None:
                if start <= t0 and end >= t_score:
                    covered = True
            continue
        rule = _governance_rule(row)
        if rule is None:
            return _not_scorable(base, "GOVERNANCE_ROW_UNREADABLE")
        if t0 <= at <= t_score:
            if rule in counts:
                counts[rule] += 1
            else:
                other_breaches += 1
    if not numbers or numbers[0] != 1:
        return _fail(base, "GOVERNANCE_ID_GAP")
    for previous_number, number in zip(numbers, numbers[1:]):
        if number != previous_number + 1:
            return _fail(base, "GOVERNANCE_ID_GAP")
    base["value"] = {**counts, "OTHER": other_breaches}
    if any(value > 0 for value in counts.values()) or other_breaches:
        return _fail(base, "GOVERNANCE_BREACH_PRESENT")
    if not covered:
        return _not_scorable(base, "GOVERNANCE_COVERAGE_NOT_ATTESTED")
    return _pass(base)


def _governance_rule(row: Mapping[str, Any]) -> str | None:
    criterion = row.get("criterion")
    rule = row.get("rule")
    texts = [value.strip() for value in (criterion, rule) if isinstance(value, str) and value.strip()]
    if not texts:
        return None
    if any(value != texts[0] for value in texts):
        return None
    return texts[0]


def _governance_number(event_id: str) -> int | None:
    if not event_id.startswith("gov-") or not event_id[4:].isdigit():
        return None
    return int(event_id[4:])


def _score_c10(
    rows: Sequence[Mapping[str, Any]],
    unparsed: int,
    header_rows_skipped: int = 0,
) -> dict[str, Any]:
    base = _criterion("C10", "recomputed_ledger_integrity", "recomputed, linked, unique, contiguous, parsed")
    base["method"] = (
        "Vendored Official V2 recipe: SHA-256 of canonical JSON of every field "
        "except row_hash, with prev_hash set to the chain previous. "
        "The first event row's prev_hash must be GENESIS. "
        "ledger_event_id values are unique and le-N ids step by 1. "
        "A single leading non-JSON header line is skipped and is not hashed. "
        "Unparsed lines fail. Re-check the vendored recipe if the writer changes."
    )
    base["header_rows_skipped"] = header_rows_skipped
    base["hash_recipe"] = {
        "source": ENGINE_SOURCE,
        "bundle": ENGINE_BUNDLE,
        "engine_sha256": ENGINE_PY_SHA256,
        "r22_engine_sha256": ENGINE_PY_R22_SHA256,
        "genesis_prev_hash": GENESIS_PREV_HASH,
        "genesis_source": GENESIS_SOURCE,
        "evidence": "2026-10-10 ledger copy, 808/808 row_hash match, 0 link breaks, recomputed 2026-10-22",
    }
    if unparsed:
        base["structural_status"] = "FAIL"
        return _fail(base, "UNPARSED_ROWS")
    if not rows:
        base["structural_status"] = "NOT_SCORABLE"
        return _not_scorable(base, "EMPTY_LEDGER")
    chain_ok, chain_detail = verify_hash_chain([dict(row) for row in rows])
    if not chain_ok:
        base["structural_status"] = "FAIL"
        base["detail"] = chain_detail
        if chain_detail.startswith("prev_hash"):
            return _fail(base, "HASH_CHAIN_BREAK")
        return _fail(base, "ROW_HASH_MISMATCH")
    seen: set[str] = set()
    numbers: list[int] = []
    for row in rows:
        event_id = row.get("ledger_event_id")
        if not isinstance(event_id, str) or not event_id.strip():
            base["structural_status"] = "FAIL"
            return _fail(base, "MISSING_LEDGER_EVENT_ID")
        if event_id in seen:
            base["structural_status"] = "FAIL"
            return _fail(base, "DUPLICATE_LEDGER_EVENT_ID")
        seen.add(event_id)
        number = _ledger_number(event_id)
        if number is None:
            base["structural_status"] = "FAIL"
            return _fail(base, "LEDGER_EVENT_ID_NOT_CONTIGUOUS")
        numbers.append(number)
    if not numbers or numbers[0] != 1:
        base["structural_status"] = "FAIL"
        return _fail(base, "LEDGER_EVENT_ID_GAP")
    for previous_number, number in zip(numbers, numbers[1:]):
        if number != previous_number + 1:
            base["structural_status"] = "FAIL"
            return _fail(base, "LEDGER_EVENT_ID_GAP")
    base["structural_status"] = "PASS"
    base["payload_digest_status"] = "PASS"
    base["id_steps_contiguous"] = True
    base["rows_checked"] = len(rows)
    base["value"] = "RECOMPUTED_LINK_OK"
    return _pass(base)


def _score_r0(
    economics: Sequence[Mapping[str, Any]],
    ready: bool,
    integrity_errors: Sequence[str],
    unparsed: int,
    random_seed: str | None,
) -> dict[str, Any]:
    base = _criterion(
        "R0_RANDOM_DIRECTION",
        "anchor_official_net_vs_expected_random_direction",
        "anchor net > expected random-direction net",
    )
    base["method"] = (
        "Same entry fill, exit fill, quantity, and recorded fee plus slippage. "
        "A fair coin's expected gross is 0, so the expected random-direction net is "
        "minus the same costs. Anchor beats that null when summed gross is positive. "
        "signal_price and reference_price are not fill prices. "
        "The comparison uses the official net, which includes funding only when PRESENT."
    )
    base["seeded_comparison"] = "NOT_FROZEN" if not random_seed else "REPORTED"
    if not ready:
        return _not_scorable(base, "T0_NOT_FROZEN")
    if unparsed or integrity_errors:
        return _not_scorable(base, "PAIRING_NOT_FAIR")
    if not economics:
        return _not_scorable(base, "NO_POST_T0_CLOSED_TRADES")
    blocked = _first_cost_block(economics)
    diagnostic = _random_diagnostic(economics, random_seed)
    base["diagnostic_ex_funding"] = diagnostic
    if blocked is not None:
        return _not_scorable(base, blocked)
    if any(item["gross"] is None or item["costs"] is None for item in economics):
        return _not_scorable(base, "GROSS_NOT_DERIVABLE")
    gross = sum((item["gross"] for item in economics), Decimal(0))
    costs = sum((item["costs"] for item in economics), Decimal(0))
    anchor_net = sum((item["net_incl_funding"] for item in economics), Decimal(0))
    expected_random = -costs
    base["value"] = {
        "anchor_net": _dec(anchor_net),
        "anchor_gross": _dec(gross),
        "expected_random_net": _dec(expected_random),
    }
    beats = anchor_net > expected_random
    if random_seed:
        median = _seeded_median(economics, random_seed, official=True)
        base["value"]["seeded_median_net"] = _dec(median)
        beats = beats and anchor_net > median
    if beats:
        return _pass(base)
    return _fail(base, "DOES_NOT_BEAT_RANDOM_DIRECTION")


def _random_diagnostic(economics: Sequence[Mapping[str, Any]], random_seed: str | None) -> dict[str, Any]:
    """Ex-funding null. This object is not a C3 score."""
    usable = [item for item in economics if item["net_ex_funding"] is not None and item["gross"] is not None and item["costs"] is not None]
    if len(usable) != len(economics) or not economics:
        return {"not_a_score": True, "status": MISSING}
    gross = sum((item["gross"] for item in usable), Decimal(0))
    costs = sum((item["costs"] for item in usable), Decimal(0))
    anchor = sum((item["net_ex_funding"] for item in usable), Decimal(0))
    payload: dict[str, Any] = {
        "not_a_score": True,
        "funding": MISSING if any(item["funding_status"] != "PRESENT" for item in economics) else "PRESENT",
        "anchor_net_ex_funding": _dec(anchor),
        "anchor_gross": _dec(gross),
        "expected_random_net": _dec(-costs),
        "beats_expected_random_direction": anchor > -costs,
    }
    if random_seed and usable:
        payload["seeded_median_net_ex_funding"] = _dec(_seeded_median(usable, random_seed, official=False))
    return payload


def _seeded_median(economics: Sequence[Mapping[str, Any]], seed: str, *, official: bool) -> Decimal:
    nets: list[Decimal] = []
    for sim in range(RANDOM_SIMS):
        total = Decimal(0)
        for item in economics:
            trade_key = item["trade_key"]
            digest = hashlib.sha256(f"{seed}|{sim}|{trade_key}".encode("utf-8")).digest()
            same_side = digest[0] % 2 == 0
            gross = item["gross"] if same_side else -item["gross"]
            funding = Decimal(0)
            if official and item["funding_status"] == "PRESENT":
                funding = item["funding_pnl"] if same_side else -item["funding_pnl"]
            total += gross - item["costs"] + funding
        nets.append(total)
    nets.sort()
    mid = len(nets) // 2
    if len(nets) % 2:
        return nets[mid]
    return (nets[mid - 1] + nets[mid]) / 2


def _economics(
    trade: ClosedTrade,
    book: FundingBook | None,
    file_instruments: frozenset[str],
) -> dict[str, Any]:
    entry_fee = _money(trade.entry, "fee_paid")
    entry_slip = _money(trade.entry, "slippage_cost")
    exit_fee = _money(trade.exit, "fee_paid")
    exit_slip = _money(trade.exit, "slippage_cost")
    nets_disagree = _nets_disagree(trade.exit)
    exit_net = None if nets_disagree else _exit_net_ex_funding(trade.exit)
    exit_gross = _money(trade.exit, "gross_pnl")
    costs_complete = None not in (entry_fee, entry_slip, exit_fee, exit_slip)
    net_ex: Decimal | None = None
    inconsistent = nets_disagree
    if not inconsistent and exit_net is not None and entry_fee is not None and entry_slip is not None:
        net_ex = exit_net - entry_fee - entry_slip
    elif not inconsistent and exit_gross is not None and costs_complete:
        net_ex = exit_gross - entry_fee - entry_slip - exit_fee - exit_slip
    if net_ex is not None and exit_gross is not None and costs_complete:
        reconstructed = exit_gross - entry_fee - entry_slip - exit_fee - exit_slip
        if abs(reconstructed - net_ex) > MONEY_TOLERANCE:
            inconsistent = True
            net_ex = None
    resolved = _resolve_funding(trade, book, file_instruments)
    funding_status = resolved["funding_status"]
    funding_pnl = resolved["funding_pnl"]
    net_incl: Decimal | None = None
    if net_ex is not None and funding_status == "PRESENT" and funding_pnl is not None:
        net_incl = net_ex + funding_pnl
    gross = exit_gross
    gross_source = "exit.gross_pnl" if exit_gross is not None else None
    if gross is None and net_ex is not None and costs_complete:
        gross = net_ex + entry_fee + entry_slip + exit_fee + exit_slip
        gross_source = "net_ex_funding_plus_recorded_costs"
    if gross is None:
        price_gross = _gross_from_fills(trade)
        if price_gross is not None:
            gross = price_gross
            gross_source = "effective_price_quantity_side"
    costs = None
    if costs_complete:
        costs = entry_fee + entry_slip + exit_fee + exit_slip
    elif gross is not None and net_ex is not None:
        costs = gross - net_ex
    entry_id = str(trade.entry.get("ledger_event_id") or trade.entry_index)
    return {
        "trade_key": entry_id,
        "entry_id": entry_id,
        "exit_id": trade.exit.get("ledger_event_id"),
        "net_ex_funding": net_ex,
        "net_incl_funding": net_incl,
        "funding_status": funding_status,
        "funding_pnl": funding_pnl,
        "funding_source": resolved["funding_source"],
        "funding_detail": resolved["funding_detail"],
        "gross": gross,
        "gross_source": gross_source,
        "costs": costs,
        "inconsistent": inconsistent,
        "costs_missing": not costs_complete or net_ex is None and not inconsistent,
    }


def _nets_disagree(exit_row: Mapping[str, Any]) -> bool:
    keys = [key for key in ("NET_PNL_EX_FUNDING", "net_pnl") if key in exit_row]
    if len(keys) < 2:
        return False
    values = [_money(exit_row, key) for key in keys]
    return any(value is None for value in values) or values[0] != values[1]


def _exit_net_ex_funding(exit_row: Mapping[str, Any]) -> Decimal | None:
    """Return the exit-leg net, which excludes entry costs.

    Two names for the same figure must agree. A disagreement is not averaged.
    """
    keys = [key for key in ("NET_PNL_EX_FUNDING", "net_pnl") if key in exit_row]
    if not keys:
        return None
    values = [_money(exit_row, key) for key in keys]
    if any(value is None for value in values):
        return None
    if any(value != values[0] for value in values):
        return None
    return values[0]


def _funding(exit_row: Mapping[str, Any]) -> tuple[str, Decimal | None]:
    status = exit_row.get("FUNDING_DATA_STATUS")
    amount = _money(exit_row, "funding_pnl")
    if status == "PRESENT" and amount is not None:
        return "PRESENT", amount
    if status in {"PARTIAL", "NO_INTERVAL"}:
        return str(status), None
    return "MISSING", None


def _resolve_funding(
    trade: ClosedTrade,
    book: FundingBook | None,
    file_instruments: frozenset[str],
) -> dict[str, Any]:
    """Combine ledger funding with an optional public cache.

    Ledger PRESENT wins when it agrees with the cache. Disagreement is not
    averaged. Ledger MISSING may be replaced by a complete public window.
    A missing hour inside the hold stays MISSING for the whole leg.
    """
    ledger_status, ledger_amount = _funding(trade.exit)
    if book is None:
        return {
            "funding_status": ledger_status,
            "funding_pnl": ledger_amount,
            "funding_source": "LEDGER_RECORDED" if ledger_status == "PRESENT" else None,
            "funding_detail": {"external": "NO_CACHE"},
        }
    instrument_status, instrument_label = _instrument_status(trade, book, file_instruments)
    if instrument_status != "OK":
        if ledger_status == "PRESENT":
            return {
                "funding_status": "PRESENT",
                "funding_pnl": ledger_amount,
                "funding_source": "LEDGER_RECORDED",
                "funding_detail": {
                    "external": "NOT_APPLIED",
                    "reason": instrument_status,
                    "instrument_source": instrument_label,
                },
            }
        return {
            "funding_status": instrument_status,
            "funding_pnl": None,
            "funding_source": None,
            "funding_detail": {
                "external": "NOT_APPLIED",
                "reason": instrument_status,
                "instrument_source": instrument_label,
            },
        }
    external = _external_leg(trade, book)
    detail = {
        "instrument_source": instrument_label,
        "cache_symbol": book.symbol,
        "external_status": external["status"],
        "settlements": external["settlements"],
        "missing_settlements": external["missing_settlements"],
        "hours": _dec(external["hours"]) if external["status"] == "PRESENT" else MISSING,
    }
    if ledger_status == "PRESENT" and ledger_amount is not None:
        if external["status"] == "PRESENT" and external["amount"] is not None:
            if abs(external["amount"] - ledger_amount) > MONEY_TOLERANCE:
                return {
                    "funding_status": "LEDGER_EXTERNAL_DISAGREE",
                    "funding_pnl": None,
                    "funding_source": None,
                    "funding_detail": {
                        **detail,
                        "ledger_funding_pnl": _dec(ledger_amount),
                        "external_funding_pnl": _dec(external["amount"]),
                    },
                }
        return {
            "funding_status": "PRESENT",
            "funding_pnl": ledger_amount,
            "funding_source": "LEDGER_RECORDED",
            "funding_detail": detail,
        }
    if ledger_status in {"PARTIAL", "NO_INTERVAL"}:
        return {
            "funding_status": ledger_status,
            "funding_pnl": None,
            "funding_source": None,
            "funding_detail": {**detail, "external": "NOT_APPLIED_OVER_LEDGER_PARTIAL"},
        }
    if external["status"] == "PRESENT" and external["amount"] is not None:
        return {
            "funding_status": "PRESENT",
            "funding_pnl": external["amount"],
            "funding_source": FUNDING_SCHEMA,
            "funding_detail": detail,
        }
    return {
        "funding_status": "MISSING",
        "funding_pnl": None,
        "funding_source": None,
        "funding_detail": detail,
    }


def _external_leg(trade: ClosedTrade, book: FundingBook) -> dict[str, Any]:
    entry_at = _parse_time(trade.entry.get("fill_time_utc"))
    exit_at = _parse_time(trade.exit.get("fill_time_utc"))
    quantity = _money(trade.entry, "quantity")
    exit_quantity = _money(trade.exit, "quantity") if "quantity" in trade.exit else quantity
    side = _side_sign(trade.entry)
    empty = {
        "status": "MISSING",
        "amount": None,
        "hours": Decimal(0),
        "settlements": 0,
        "missing_settlements": 0,
    }
    if entry_at is None or exit_at is None or side is None:
        return empty
    if quantity is None or quantity <= 0:
        return empty
    if exit_quantity is not None and abs(exit_quantity - quantity) > MONEY_TOLERANCE:
        return empty
    # Long pays a positive rate, so the short-receives flag is the opposite of the price sign.
    leg = leg_funding(
        book,
        entry_at=entry_at,
        exit_at=exit_at,
        quantity=quantity,
        short_receives_positive=side < 0,
    )
    return {
        "status": leg.status,
        "amount": leg.amount,
        "hours": leg.hours,
        "settlements": leg.settlements,
        "missing_settlements": len(leg.missing_periods),
    }


def _gross_from_fills(trade: ClosedTrade) -> Decimal | None:
    entry_px = _money(trade.entry, "effective_price")
    exit_px = _money(trade.exit, "effective_price")
    quantity = _money(trade.entry, "quantity")
    sign = _side_sign(trade.entry)
    if None in (entry_px, exit_px, quantity, sign):
        return None
    assert entry_px is not None and exit_px is not None and quantity is not None and sign is not None
    return sign * (exit_px - entry_px) * quantity


def _first_cost_block(economics: Sequence[Mapping[str, Any]]) -> str | None:
    if any(item["inconsistent"] for item in economics):
        return "NET_AND_GROSS_INCONSISTENT"
    for item in economics:
        status = item["funding_status"]
        if status == "PRESENT":
            continue
        if status == "LEDGER_EXTERNAL_DISAGREE":
            return "FUNDING_LEDGER_EXTERNAL_DISAGREE"
        if status == "INSTRUMENT_MISMATCH":
            return "FUNDING_INSTRUMENT_MISMATCH"
        if status == "MULTIPLE_INSTRUMENTS":
            return "FUNDING_MULTIPLE_INSTRUMENTS"
        return "NOT_SCORABLE_ON_LINE_A"
    if any(item["net_incl_funding"] is None for item in economics):
        return "COSTS_MISSING"
    return None


def _ex_funding_diagnostic(economics: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if any(item["net_ex_funding"] is None for item in economics):
        return {"not_a_score": True, "net_pnl_ex_funding": MISSING}
    total = sum((item["net_ex_funding"] for item in economics), Decimal(0))
    return {
        "not_a_score": True,
        "net_pnl_ex_funding": _dec(total),
        "funding": MISSING,
    }


def _select_window(
    trades: Sequence[ClosedTrade],
    t0: datetime | None,
    t_score: datetime | None,
) -> tuple[list[ClosedTrade], dict[str, int]]:
    if t0 is None or t_score is None:
        return [], {"window": "T0_NOT_FROZEN", "closed_seen": len(trades)}
    selected: list[ClosedTrade] = []
    excluded = {"pre_t0": 0, "signal_pre_t0": 0, "after_score": 0, "time_missing": 0}
    for trade in trades:
        entry_at = _parse_time(trade.entry.get("fill_time_utc"))
        exit_at = _parse_time(trade.exit.get("fill_time_utc"))
        signal_at = _parse_time(trade.entry.get("signal_available_at")) if "signal_available_at" in trade.entry else None
        if entry_at is None or exit_at is None:
            excluded["time_missing"] += 1
            continue
        if entry_at < t0 or exit_at < t0:
            excluded["pre_t0"] += 1
            continue
        if "signal_available_at" in trade.entry and (signal_at is None or signal_at < t0):
            excluded["signal_pre_t0"] += 1
            continue
        if entry_at > t_score or exit_at > t_score:
            excluded["after_score"] += 1
            continue
        selected.append(trade)
    return selected, excluded


def _latency_report(trades: Sequence[ClosedTrade]) -> dict[str, Any]:
    samples: list[int] = []
    for trade in trades:
        signal = _parse_time(trade.entry.get("signal_available_at"))
        fill = _parse_time(trade.entry.get("fill_time_utc"))
        if signal is None or fill is None:
            continue
        samples.append(int((fill - signal).total_seconds()))
    samples.sort()
    median = None
    if samples:
        mid = len(samples) // 2
        median = samples[mid] if len(samples) % 2 else (samples[mid - 1] + samples[mid]) // 2
    return {
        "not_a_fill_price": True,
        "used_as_fill": False,
        "n": len(samples),
        "median_seconds": median,
    }


def _pair(rows: Sequence[Mapping[str, Any]]) -> tuple[list[ClosedTrade], list[str], int]:
    open_trade: tuple[Mapping[str, Any], int] | None = None
    closed: list[ClosedTrade] = []
    errors: list[str] = []
    for index, row in enumerate(rows):
        event_type = row.get("event_type")
        if event_type in OPEN_TYPES:
            if open_trade is not None:
                errors.append(f"OPEN_WHILE_OPEN:{index}")
                continue
            open_trade = (row, index)
            continue
        if event_type in EXIT_TYPES:
            if open_trade is None:
                errors.append(f"EXIT_WHILE_FLAT:{index}")
                continue
            entry, entry_index = open_trade
            entry_at = _parse_time(entry.get("fill_time_utc"))
            exit_at = _parse_time(row.get("fill_time_utc"))
            if entry_at is not None and exit_at is not None and exit_at < entry_at:
                errors.append(f"EXIT_BEFORE_ENTRY:{index}")
            closed.append(ClosedTrade(entry, row, entry_index, index))
            open_trade = None
    return closed, errors, 0 if open_trade is None else 1


def _equity_points(
    rows: Sequence[Mapping[str, Any]],
    t0: datetime,
    t_score: datetime,
) -> list[tuple[datetime, Decimal]]:
    points: list[tuple[int, datetime, Decimal]] = []
    for index, row in enumerate(rows):
        equity = _money(row, "net_liquidation_equity")
        if equity is None:
            continue
        event_type = row.get("event_type")
        if event_type in FILL_TYPES:
            at = _parse_time(row.get("fill_time_utc"))
        else:
            at = _parse_time(row.get("signal_available_at"))
        if at is None or at < t0 or at > t_score:
            continue
        points.append((index, at, equity))
    points.sort(key=lambda item: (item[1], item[0]))
    return [(at, equity) for _, at, equity in points]


def _c7_mark(row: Mapping[str, Any]) -> tuple[datetime, Decimal] | None:
    if row.get("mark_rule_id") != "MARK_RULE_C7_V1":
        return None
    if row.get("mark_kind") not in C7_MARK_KINDS:
        return None
    if row.get("mark_honesty_label") == "NOT_TICK_LOW":
        return None
    equity = _money(row, "net_liquidation_equity")
    at = _parse_time(row.get("mark_time_utc") or row.get("fill_time_utc") or row.get("signal_available_at"))
    if equity is None or at is None:
        return None
    return at, equity


def _equity_at_exact(marks: Sequence[tuple[datetime, Decimal]], at: datetime) -> Decimal | None:
    for mark_at, equity in marks:
        if mark_at == at:
            return equity
    return None


def _trade_public(trade: ClosedTrade, econ: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "entry_id": econ["entry_id"],
        "exit_id": econ["exit_id"],
        "entry_type": trade.entry.get("event_type"),
        "exit_type": trade.exit.get("event_type"),
        "net_ex_funding": _dec(econ["net_ex_funding"]) if econ["net_ex_funding"] is not None else MISSING,
        "funding_status": econ["funding_status"],
        "funding_pnl": _dec(econ["funding_pnl"]) if econ["funding_pnl"] is not None else MISSING,
        "funding_source": econ["funding_source"],
        "official_net": _dec(econ["net_incl_funding"]) if econ["net_incl_funding"] is not None else MISSING,
        "quantity": trade.entry.get("quantity"),
    }


def _criterion(name: str, metric: str, threshold: str) -> dict[str, Any]:
    return {
        "id": name,
        "metric": metric,
        "threshold": threshold,
        "threshold_source": "PASS_LINE_V1_R2",
        "status": None,
        "reason": None,
        "value": None,
    }


def _pass(base: dict[str, Any], reason: str = "THRESHOLD_MET") -> dict[str, Any]:
    base["status"] = "PASS"
    base["reason"] = reason
    return base


def _fail(base: dict[str, Any], reason: str) -> dict[str, Any]:
    base["status"] = "FAIL"
    base["reason"] = reason
    return base


def _not_scorable(base: dict[str, Any], reason: str) -> dict[str, Any]:
    base["status"] = "NOT_SCORABLE"
    base["reason"] = reason
    return base


def _not_applicable(base: dict[str, Any], reason: str) -> dict[str, Any]:
    base["status"] = "NOT_APPLICABLE"
    base["reason"] = reason
    return base


def _rollup(
    criteria: Mapping[str, Mapping[str, Any]],
    names: Sequence[str],
) -> tuple[str, str, list[str]]:
    blocking = [name for name in names if criteria[name]["status"] != "PASS"]
    if any(criteria[name]["status"] == "FAIL" for name in names):
        return "FAIL", "SCORABLE_CRITERION_FAILED", blocking
    if blocking:
        return "NOT_ELIGIBLE", "CRITERION_NOT_SCORABLE", blocking
    return "PASS", "ALL_CRITERIA_PASS", []


def _resolve_line(rows: Sequence[Mapping[str, Any]], requested: str | None) -> str:
    if requested is not None:
        label = requested.strip().upper()
        if label not in {"A", "B"}:
            raise ScoringRefusal("line must be A or B")
        return label
    seen: set[str] = set()
    for row in rows:
        for key in ("schema", "ledger_schema", "kind", "strategy_version"):
            value = row.get(key)
            if not isinstance(value, str):
                continue
            text = value.strip()
            if text in LINE_B_MARKERS:
                seen.add("B")
            elif text in LINE_A_MARKERS:
                seen.add("A")
    if seen == {"B"}:
        return "B"
    if seen == {"A", "B"}:
        raise ScoringRefusal("ledger copy mixes Line A and Line B schema markers")
    return "A"


def _file_instruments(rows: Sequence[Mapping[str, Any]]) -> frozenset[str]:
    found: set[str] = set()
    for row in rows:
        instrument = _row_instrument(row)
        if instrument and instrument != "CONFLICT":
            found.add(instrument)
    return frozenset(found)


def _row_instrument(row: Mapping[str, Any]) -> str | None:
    values: list[str] = []
    for key in INSTRUMENT_KEYS:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
    unique = set(values)
    if not unique:
        return None
    if len(unique) > 1:
        return "CONFLICT"
    return next(iter(unique))


def _instrument_status(
    trade: ClosedTrade,
    book: FundingBook,
    file_instruments: frozenset[str],
) -> tuple[str, str]:
    entry_instrument = _row_instrument(trade.entry)
    exit_instrument = _row_instrument(trade.exit)
    if entry_instrument == "CONFLICT" or exit_instrument == "CONFLICT":
        return "INSTRUMENT_MISMATCH", "ROW_FIELDS_DISAGREE"
    if entry_instrument and exit_instrument and entry_instrument != exit_instrument:
        return "INSTRUMENT_MISMATCH", "ENTRY_EXIT_DISAGREE"
    instrument = entry_instrument or exit_instrument
    if instrument is None:
        if len(file_instruments) > 1:
            return "MULTIPLE_INSTRUMENTS", "LEDGER_MARKET_ABSENT_FILE_HAS_MANY"
        if len(file_instruments) == 1:
            instrument = next(iter(file_instruments))
            if instrument != book.symbol:
                return "INSTRUMENT_MISMATCH", "FILE_INSTRUMENT_DIFFERS_FROM_CACHE"
            return "OK", "LEDGER_MARKET_ABSENT_FILE_HAS_ONE_INSTRUMENT"
        return "OK", "CACHE_SYMBOL_LEDGER_MARKET_ABSENT"
    if instrument != book.symbol:
        return "INSTRUMENT_MISMATCH", "LEDGER_ROW"
    return "OK", "LEDGER_ROW"


def _funding_report(
    book: FundingBook | None,
    economics: Sequence[Mapping[str, Any]],
    file_instruments: frozenset[str],
) -> dict[str, Any]:
    labels = sorted(
        {
            str(item["funding_detail"].get("instrument_source"))
            for item in economics
            if isinstance(item.get("funding_detail"), Mapping)
            and item["funding_detail"].get("instrument_source")
        }
    )
    sources = sorted({item["funding_source"] for item in economics if item.get("funding_source")})
    report: dict[str, Any] = {
        "zero_filled": False,
        "derived": book is not None,
        "ledger_recorded": "LEDGER_RECORDED" in sources,
        "sources_used": sources,
        "ledger_instruments": sorted(file_instruments),
        "instrument_sources": labels,
    }
    if book is None:
        report["label"] = None
        report["cache"] = None
        return report
    report["label"] = FUNDING_SCHEMA
    report["cache"] = {
        "schema": book.schema,
        "symbol": book.symbol,
        "source_url": book.source_url,
        "fetched_at": book.fetched_at,
        "contract_size": _dec(book.contract_size),
        "contract_size_source": book.contract_size_source,
        "convention": book.convention,
        "rates_sha256": book.rates_sha256,
        "rate_count": len(book.rates),
        "derived": True,
        "ledger_recorded": False,
    }
    return report


def _read_only_bytes(path: Path) -> bytes:
    refusal = _forbidden(path)
    if refusal is not None:
        raise ScoringRefusal(refusal)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ScoringRefusal(f"unreadable:{exc.errno}") from exc
    try:
        info = os.fstat(fd)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise ScoringRefusal("not a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _forbidden(path: Path) -> str | None:
    try:
        text = str(path.resolve())
    except OSError:
        text = str(path)
    for marker in FORBIDDEN_PATH_MARKERS:
        if marker in text:
            return f"refusing sealed ledger path containing {marker}"
    return None


_HEADER_CELLS = frozenset(
    {"ledger_event_id", "event_type", "row_hash", "prev_hash", "event_id", "event_hash"}
)


def _is_leading_header(line: str) -> bool:
    """A comma-separated label line, not a JSON event.

    The equity CSV's ``header_row_mismatches`` counter is a different thing:
    the read-only summary counts CSV body rows whose width differs from the
    CSV header. This scorer does not read that CSV. On the JSONL copy, only
    one leading header line is skipped. It is not hashed, and the first event
    row must still chain from GENESIS.
    """
    if line.startswith("{"):
        return False
    cells = [cell.strip().casefold() for cell in line.split(",")]
    return any(cell in _HEADER_CELLS for cell in cells)


def _parse_jsonl(blob: bytes) -> tuple[list[dict[str, Any]], int, int]:
    rows: list[dict[str, Any]] = []
    unparsed = 0
    header_rows_skipped = 0
    seen_data = False
    for line in blob.decode("utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not seen_data and header_rows_skipped == 0 and _is_leading_header(stripped):
            header_rows_skipped += 1
            continue
        seen_data = True
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            unparsed += 1
            continue
        if not isinstance(obj, dict):
            unparsed += 1
            continue
        rows.append(obj)
    return rows, unparsed, header_rows_skipped


def _money(event: Mapping[str, Any], key: str) -> Decimal | None:
    if key not in event:
        return None
    value = event[key]
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite():
        return None
    return number


def _first_money(event: Mapping[str, Any], keys: Sequence[str]) -> Decimal | None:
    present = [key for key in keys if key in event]
    if not present:
        return None
    if len(present) > 1:
        values = [_money(event, key) for key in present]
        if any(value is None for value in values):
            return None
        if any(value != values[0] for value in values):
            return None
    return _money(event, present[0])


def _side_sign(event: Mapping[str, Any]) -> Decimal | None:
    side = event.get("side")
    if not isinstance(side, str):
        return None
    label = side.strip().upper()
    if label in {"LONG", "BUY"}:
        return Decimal(1)
    if label in {"SHORT", "SELL"}:
        return Decimal(-1)
    return None


def _ledger_number(event_id: str) -> int | None:
    if not event_id.startswith("le-") or not event_id[3:].isdigit():
        return None
    return int(event_id[3:])


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _dec(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
