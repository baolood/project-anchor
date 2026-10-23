"""Versioned equity file contract. Legacy 6-column and 10-column files stay untouched."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from eval_recording.mark_rule import (
    HONESTY_NOT_TICK_LOW,
    HONESTY_RECORDED,
    MARK_KIND_GENESIS,
    MARK_KIND_OHLC_PROXY,
    MARK_RULE_ID,
)

SCHEMA_VERSION = "equity_v2_1"
NEW_EQUITY_FILENAME = "anchor_fake_fill_equity_v2_1_official.csv"
SCHEMA_FILENAME = "anchor_fake_fill_equity_v2_1_official.SCHEMA.json"
SAMPLE_CLASS = "FORWARD_LIVE_SHADOW"
GENESIS_OBSERVATION_ID = "LEDGER_GENESIS"

EQUITY_V2_1_HEADER: tuple[str, ...] = (
    "schema_version",
    "timestamp_utc",
    "observation_id",
    "trade_id",
    "position",
    "realized_pnl",
    "unrealized_pnl",
    "net_liquidation_equity",
    "equity_at_open",
    "drawdown",
    "exposure",
    "cash_reserve",
    "active_notional",
    "mark_rule_id",
    "mark_kind",
    "mark_honesty_label",
    "sample_class",
)

# On-disk Official artifact today. Do not rewrite either shape.
LEGACY_EQUITY_FILENAME = "anchor_fake_fill_equity_v2_official.csv"
LEGACY_HEADER_6: tuple[str, ...] = (
    "timestamp_utc",
    "equity",
    "realized_pnl",
    "unrealized_pnl",
    "position",
    "event",
)
LEGACY_HEADER_10: tuple[str, ...] = (
    "timestamp_utc",
    "observation_id",
    "position",
    "realized_pnl",
    "unrealized_pnl",
    "net_liquidation_equity",
    "drawdown",
    "exposure",
    "cash_reserve",
    "active_notional",
)

NUMERIC_COLUMNS = (
    "realized_pnl",
    "unrealized_pnl",
    "net_liquidation_equity",
    "drawdown",
    "exposure",
    "cash_reserve",
    "active_notional",
)
POSITIONS = frozenset({"FLAT", "LONG", "SHORT"})
MARK_KINDS = frozenset({"GENESIS", "BAR_1H", "FILL", "OHLC_ADVERSE_PROXY"})


class LegacyEquityImmutable(ValueError):
    """Raised when a write would touch the legacy Official equity file."""


class EquitySchemaError(ValueError):
    """Raised when a row does not match equity_v2_1."""


def header_line() -> str:
    return ",".join(EQUITY_V2_1_HEADER)


def _path_hits_official_ledger(path: Path) -> bool:
    if "affl-v2-official-ledger" in path.parts:
        return True
    try:
        if path.exists() and "affl-v2-official-ledger" in path.resolve().parts:
            return True
    except OSError:
        return False
    return False


def assert_equity_write_allowed(path: Path) -> None:
    """Allow only the new filename, and never inside the Official ledger tree."""
    if _path_hits_official_ledger(path):
        raise LegacyEquityImmutable("refusing to write inside affl-v2-official-ledger")
    if path.name == LEGACY_EQUITY_FILENAME:
        raise LegacyEquityImmutable("legacy equity CSV stays immutable")
    if path.name != NEW_EQUITY_FILENAME:
        raise EquitySchemaError(
            f"new equity writes must use {NEW_EQUITY_FILENAME}"
        )


def reject_legacy_header(header: list[str] | tuple[str, ...]) -> None:
    as_tuple = tuple(header)
    if as_tuple in {LEGACY_HEADER_6, LEGACY_HEADER_10}:
        raise LegacyEquityImmutable(
            "legacy 6-column and 10-column equity headers are not the v2.1 scoring path"
        )
    if as_tuple != EQUITY_V2_1_HEADER:
        raise EquitySchemaError("equity header does not match equity_v2_1")


def genesis_row(
    *,
    timestamp_utc: str,
    net_liquidation_equity: str,
    cash_reserve: str,
) -> dict[str, str]:
    """Same width as every later row. No 6-column seed.

    Starting equity is copied in by the caller from ledger genesis. This
    helper does not hard-code a figure and does not score the curve.
    """
    row = {column: "" for column in EQUITY_V2_1_HEADER}
    row.update(
        {
            "schema_version": SCHEMA_VERSION,
            "timestamp_utc": timestamp_utc,
            "observation_id": GENESIS_OBSERVATION_ID,
            "trade_id": "",
            "position": "FLAT",
            "realized_pnl": "0",
            "unrealized_pnl": "0",
            "net_liquidation_equity": net_liquidation_equity,
            "equity_at_open": "",
            "drawdown": "0",
            "exposure": "0",
            "cash_reserve": cash_reserve,
            "active_notional": "0",
            "mark_rule_id": MARK_RULE_ID,
            "mark_kind": MARK_KIND_GENESIS,
            "mark_honesty_label": HONESTY_RECORDED,
            "sample_class": SAMPLE_CLASS,
        }
    )
    return row


def validate_equity_row(row: dict[str, str]) -> None:
    missing = [column for column in EQUITY_V2_1_HEADER if column not in row]
    if missing:
        raise EquitySchemaError(f"missing columns: {','.join(missing)}")
    extra = [column for column in row if column not in EQUITY_V2_1_HEADER]
    if extra:
        raise EquitySchemaError(f"unexpected columns: {','.join(extra)}")
    if row["schema_version"] != SCHEMA_VERSION:
        raise EquitySchemaError("schema_version must be equity_v2_1 on every row")
    if row["mark_rule_id"] != MARK_RULE_ID:
        raise EquitySchemaError("mark_rule_id must be MARK_RULE_C7_V1")
    if row["sample_class"] != SAMPLE_CLASS:
        raise EquitySchemaError("sample_class must be FORWARD_LIVE_SHADOW")
    if row["position"] not in POSITIONS:
        raise EquitySchemaError("position must be FLAT, LONG, or SHORT")
    if row["mark_kind"] not in MARK_KINDS:
        raise EquitySchemaError("unknown mark_kind")
    for column in NUMERIC_COLUMNS:
        if row[column] == "":
            raise EquitySchemaError(f"{column} must be present as text")
    if row["mark_kind"] == MARK_KIND_OHLC_PROXY:
        if row["mark_honesty_label"] != HONESTY_NOT_TICK_LOW:
            raise EquitySchemaError("OHLC adverse proxy rows must be labeled NOT_TICK_LOW")
    elif row["mark_honesty_label"] != HONESTY_RECORDED:
        raise EquitySchemaError("recorded marks use mark_honesty_label RECORDED_MARK")
    trade_id = row["trade_id"]
    equity_at_open = row["equity_at_open"]
    if row["mark_kind"] == MARK_KIND_OHLC_PROXY and not trade_id:
        raise EquitySchemaError("OHLC adverse proxy requires an open trade_id")
    if trade_id and equity_at_open == "":
        raise EquitySchemaError("equity_at_open is required when trade_id is set")
    if not trade_id and equity_at_open != "":
        raise EquitySchemaError("equity_at_open is empty when no trade is open")
    if trade_id and not trade_id.startswith("tr_"):
        raise EquitySchemaError("trade_id on an equity row must use the tr_ scheme")
    if row["mark_kind"] == MARK_KIND_GENESIS:
        if row["observation_id"] != GENESIS_OBSERVATION_ID or row["position"] != "FLAT":
            raise EquitySchemaError("genesis row must be FLAT LEDGER_GENESIS")
        if trade_id or equity_at_open:
            raise EquitySchemaError("genesis row has no trade_id and no equity_at_open")


def render_equity_csv(rows: list[dict[str, str]], dest: Path) -> None:
    """Write a new v2.1 file. Refuses the legacy filename and the Official tree."""
    assert_equity_write_allowed(dest)
    for row in rows:
        validate_equity_row(row)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(EQUITY_V2_1_HEADER), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_equity_csv(text: str) -> list[dict[str, str]]:
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise EquitySchemaError("equity CSV is empty") from exc
    reject_legacy_header(header)
    rows: list[dict[str, str]] = []
    for raw in reader:
        if not raw or raw == [""]:
            continue
        if len(raw) != len(EQUITY_V2_1_HEADER):
            raise EquitySchemaError("equity v2.1 rows must stay on the versioned header width")
        row = dict(zip(EQUITY_V2_1_HEADER, raw, strict=True))
        validate_equity_row(row)
        rows.append(row)
    return rows
