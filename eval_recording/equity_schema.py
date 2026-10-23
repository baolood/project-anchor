"""Equity v2.1 reader and in-memory scoring view.

The on-disk file is the 13-column header from
``eval_recording.equity_v21_dual_write``. ``trade_id``, ``equity_at_open``,
``mark_kind``, and ``mark_honesty_label`` are projected by
``project_scoring_view`` and are never written under
``anchor_fake_fill_equity_v2_1_official.csv`` or ``schema_version``
``equity_v2_1``.

DEPLOY=NO. This module does not import ``affl_v2`` and does not score.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from eval_recording.equity_v21_dual_write import (
    EQUITY_V21_COLUMNS,
    GENESIS_OBSERVATION_ID,
    LEGACY_EQUITY_FILENAME,
    MARK_RULE_BOUND,
    MARK_RULE_IDS,
    MARK_RULE_UNBOUND,
    NEW_EQUITY_FILENAME,
    POSITIONS,
    SCHEMA_VERSION,
)
from eval_recording.equity_v21_dual_write import (
    header_line as _on_disk_header_line,
)
from eval_recording.mark_rule import HONESTY_RECORDED, MARK_KIND_BAR, MARK_KIND_FILL, MARK_KIND_GENESIS

# Same object as the writer columns. The reader accepts only this header.
EQUITY_V2_1_ON_DISK_HEADER = EQUITY_V21_COLUMNS
EQUITY_V2_1_HEADER = EQUITY_V21_COLUMNS

VIEW_ID = "equity_v2_1_view"
C7_NOT_READY = "C7_NOT_READY"
SCORING_SAMPLE_CLASS = "FORWARD_LIVE_SHADOW"

EQUITY_V2_1_SCORING_VIEW: tuple[str, ...] = (
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

ENTRY_EVENT_TYPES = frozenset({"OPEN", "REVERSE_ENTRY"})
EXIT_EVENT_TYPES = frozenset({"FLAT_EXIT", "REVERSE_EXIT", "HARD_STOP_EXIT"})
VIEW_MARK_KINDS = frozenset({MARK_KIND_GENESIS, MARK_KIND_BAR, MARK_KIND_FILL})


class LegacyEquityImmutable(ValueError):
    """Raised when a reader is pointed at a legacy Official equity header."""


class EquitySchemaError(ValueError):
    """Raised when a row is not the on-disk equity_v2_1 shape, or a view cannot be built."""


def header_line() -> str:
    """Comma-separated on-disk header. This is not the scoring view."""
    return _on_disk_header_line()


def scoring_view_header_line() -> str:
    """Comma-separated view fields. Not a file header."""
    return ",".join(EQUITY_V2_1_SCORING_VIEW)


def reject_legacy_header(header: list[str] | tuple[str, ...]) -> None:
    """Refuse the legacy 6-column and 10-column Official equity headers."""
    as_tuple = tuple(header)
    if as_tuple in {LEGACY_HEADER_6, LEGACY_HEADER_10}:
        raise LegacyEquityImmutable(
            "legacy 6-column and 10-column equity headers are not the v2.1 scoring path "
            f"({LEGACY_EQUITY_FILENAME} stays immutable)"
        )


def _validate_on_disk_row(row: Mapping[str, str]) -> None:
    missing = [column for column in EQUITY_V21_COLUMNS if column not in row]
    extra = [column for column in row if column not in EQUITY_V21_COLUMNS]
    if missing or extra:
        raise EquitySchemaError(
            f"on-disk row must have exactly the {len(EQUITY_V21_COLUMNS)} v2.1 columns; "
            f"missing={missing}; extra={extra}"
        )
    if row["schema_version"] != SCHEMA_VERSION:
        raise EquitySchemaError("schema_version must be equity_v2_1 on every row")
    if not row["timestamp_utc"] or not row["observation_id"]:
        raise EquitySchemaError("timestamp_utc and observation_id are required")
    if row["position"] not in POSITIONS:
        raise EquitySchemaError("position must be FLAT, LONG, or SHORT")
    if row["mark_rule_id"] not in MARK_RULE_IDS:
        raise EquitySchemaError(
            "mark_rule_id must be MARK_RULE_C7_V1, UNBOUND, or empty"
        )
    if not row["sample_class"]:
        raise EquitySchemaError("sample_class is required")
    if row["observation_id"] == GENESIS_OBSERVATION_ID and row["position"] != "FLAT":
        raise EquitySchemaError("genesis row must be FLAT")
    for column in EQUITY_V21_COLUMNS:
        value = row[column]
        if not isinstance(value, str) or "\n" in value or "\r" in value:
            raise EquitySchemaError(f"{column} must be a single-line string")


def parse_equity_csv(text: str) -> list[dict[str, str]]:
    """Read an on-disk equity_v2_1 file. Only the 13-column header is accepted."""
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise EquitySchemaError("equity CSV is empty") from exc
    reject_legacy_header(header)
    if tuple(header) == EQUITY_V2_1_SCORING_VIEW:
        raise EquitySchemaError(
            "the 17-column scoring view is not an on-disk equity_v2_1 file"
        )
    if tuple(header) != EQUITY_V21_COLUMNS:
        raise EquitySchemaError(
            "equity_v2_1 reader accepts only the 13-column on-disk header"
        )
    rows: list[dict[str, str]] = []
    for raw in reader:
        if not raw or raw == [""]:
            continue
        if len(raw) != len(EQUITY_V21_COLUMNS):
            raise EquitySchemaError(
                "equity v2.1 rows must stay on the 13-column header width"
            )
        row = dict(zip(EQUITY_V21_COLUMNS, raw, strict=True))
        _validate_on_disk_row(row)
        rows.append(row)
    return rows


def render_equity_csv(rows: Sequence[Mapping[str, str]], dest: Path) -> None:
    """Retired 17-column writer.

    The scoring view is memory-only. Calling this does not create ``dest``.
    Tests use the refusal to lock that the view is not a write target.
    """
    del rows
    raise EquitySchemaError(
        "equity_v2_1_view is not a write target "
        f"(refusing {Path(dest).name}; on-disk file remains {NEW_EQUITY_FILENAME} "
        f"with {len(EQUITY_V21_COLUMNS)} columns)"
    )


def accepts_scoring_sample(row: Mapping[str, str]) -> bool:
    """Scoring filter for the view. Only ``FORWARD_LIVE_SHADOW`` passes.

    ``C7_NOT_READY`` is a separate mark-rule signal. This predicate does not
    turn an unbound row into a bound one.
    """
    return row.get("sample_class") == SCORING_SAMPLE_CLASS


def _parse_utc(value: str) -> datetime:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise EquitySchemaError(f"unparseable UTC timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise EquitySchemaError("timestamps must be timezone-aware UTC")
    return parsed.astimezone(timezone.utc)


def _event_time(event: Mapping[str, object]) -> datetime:
    for key in ("fill_time_utc", "at", "timestamp_utc"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return _parse_utc(value)
    raise EquitySchemaError("C6 entry or exit is missing fill_time_utc or at")


def _decimal_text(value: Decimal) -> str:
    """Match the C6 JSON text form without importing ``affl_v2``."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


def _ex_ante_text(value: object, field: str) -> str:
    if value is None:
        return ""
    if isinstance(value, bool) or isinstance(value, float):
        raise EquitySchemaError(f"C6 {field} must be text or Decimal, not {type(value).__name__}")
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if not isinstance(value, str):
        raise EquitySchemaError(f"C6 {field} must be text or Decimal")
    if "\n" in value or "\r" in value:
        raise EquitySchemaError(f"C6 {field} must be a single-line field")
    return value


def _legs_from_events(
    events: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Open legs in event order. An exit closes the matching ``trade_id``."""
    legs: list[dict[str, object]] = []
    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            raise EquitySchemaError("c6_events items must be mappings")
        event_type = event.get("event_type")
        if event_type in ENTRY_EVENT_TYPES:
            trade_id = _ex_ante_text(event.get("trade_id"), "trade_id")
            equity_at_open = _ex_ante_text(event.get("equity_at_open"), "equity_at_open")
            if not trade_id:
                raise EquitySchemaError(
                    f"{event_type} is missing the ex-ante trade_id"
                )
            if not trade_id.startswith("tr_"):
                raise EquitySchemaError("C6 trade_id must use the tr_ scheme")
            if equity_at_open == "":
                raise EquitySchemaError(
                    f"{event_type} is missing the ex-ante equity_at_open"
                )
            legs.append(
                {
                    "trade_id": trade_id,
                    "equity_at_open": equity_at_open,
                    "entry_time": _event_time(event),
                    "exit_time": None,
                    "order": index,
                }
            )
        elif event_type in EXIT_EVENT_TYPES:
            trade_id = _ex_ante_text(event.get("trade_id"), "trade_id")
            exit_time = _event_time(event)
            for leg in reversed(legs):
                if leg["exit_time"] is None and leg["trade_id"] == trade_id:
                    leg["exit_time"] = exit_time
                    break
    return legs


def _fill_observation_ids(events: Sequence[Mapping[str, object]]) -> set[str]:
    found: set[str] = set()
    for event in events:
        if not isinstance(event, Mapping):
            raise EquitySchemaError("c6_events items must be mappings")
        if event.get("event_type") not in ENTRY_EVENT_TYPES | EXIT_EVENT_TYPES:
            continue
        observation_id = event.get("observation_id")
        if isinstance(observation_id, str) and observation_id:
            found.add(observation_id)
    return found


def _open_leg_at(
    legs: Sequence[Mapping[str, object]],
    row_time: datetime,
) -> Mapping[str, object] | None:
    active = [
        leg
        for leg in legs
        if leg["entry_time"] <= row_time
        and (leg["exit_time"] is None or row_time < leg["exit_time"])
    ]
    if not active:
        return None
    return max(active, key=lambda leg: (leg["entry_time"], leg["order"]))


def _view_mark_rule_id(raw: str) -> str:
    if raw == "" or raw == MARK_RULE_UNBOUND:
        return C7_NOT_READY
    if raw == MARK_RULE_BOUND:
        return raw
    raise EquitySchemaError("mark_rule_id must be MARK_RULE_C7_V1, UNBOUND, or empty")


def _mark_kind(observation_id: str, fill_ids: set[str]) -> str:
    if observation_id == GENESIS_OBSERVATION_ID:
        return MARK_KIND_GENESIS
    if observation_id in fill_ids:
        return MARK_KIND_FILL
    return MARK_KIND_BAR


def _validate_view_row(row: Mapping[str, str]) -> None:
    if tuple(row) != EQUITY_V2_1_SCORING_VIEW:
        raise EquitySchemaError("scoring view row lost the equity_v2_1_view key order")
    if row["mark_honesty_label"] != HONESTY_RECORDED:
        raise EquitySchemaError("equity_v2_1 view marks are RECORDED_MARK")
    if row["mark_kind"] not in VIEW_MARK_KINDS:
        raise EquitySchemaError("equity_v2_1 view does not emit OHLC proxy rows")
    trade_id = row["trade_id"]
    equity_at_open = row["equity_at_open"]
    if (trade_id == "") != (equity_at_open == ""):
        raise EquitySchemaError("trade_id and equity_at_open are set together")
    if trade_id and not trade_id.startswith("tr_"):
        raise EquitySchemaError("view trade_id must use the tr_ scheme")
    if row["position"] == "FLAT" and (trade_id or equity_at_open):
        raise EquitySchemaError("FLAT rows have empty trade_id and equity_at_open")
    if row["mark_kind"] == MARK_KIND_GENESIS:
        if row["observation_id"] != GENESIS_OBSERVATION_ID or row["position"] != "FLAT":
            raise EquitySchemaError("genesis view row must be FLAT LEDGER_GENESIS")
        if trade_id or equity_at_open:
            raise EquitySchemaError("genesis view row has no trade fields")
    if row["mark_rule_id"] == MARK_RULE_UNBOUND:
        raise EquitySchemaError("UNBOUND is shown as C7_NOT_READY in the view")
    if row["mark_rule_id"] not in {C7_NOT_READY, MARK_RULE_BOUND}:
        raise EquitySchemaError("view mark_rule_id must be MARK_RULE_C7_V1 or C7_NOT_READY")


def project_scoring_view(
    rows13: Sequence[Mapping[str, str]],
    c6_events: Sequence[Mapping[str, object]],
) -> list[dict[str, str]]:
    """Project 13-column rows into the 17-field ``equity_v2_1_view``.

    ``trade_id`` and ``equity_at_open`` come from C6 ``OPEN`` / ``REVERSE_ENTRY``
    ex-ante fields. The open leg is the latest entry that has no matching exit
    at the row timestamp. Both fields are empty when ``position`` is ``FLAT``.

    ``mark_kind`` is ``GENESIS`` for ``LEDGER_GENESIS``, ``FILL`` when the
    observation id is an entry or exit observation, and ``BAR_1H`` otherwise.
    ``mark_honesty_label`` is always ``RECORDED_MARK``. ``UNBOUND`` and empty
    ``mark_rule_id`` values are shown as ``C7_NOT_READY`` and are not relabeled
    ``MARK_RULE_C7_V1``. ``sample_class`` is copied unchanged.
    """
    events = list(c6_events)
    legs = _legs_from_events(events)
    fill_ids = _fill_observation_ids(events)
    projected: list[dict[str, str]] = []
    for source in rows13:
        _validate_on_disk_row(source)
        row_time = _parse_utc(source["timestamp_utc"])
        if source["position"] == "FLAT":
            trade_id = ""
            equity_at_open = ""
        else:
            leg = _open_leg_at(legs, row_time)
            if leg is None:
                trade_id = ""
                equity_at_open = ""
            else:
                trade_id = str(leg["trade_id"])
                equity_at_open = str(leg["equity_at_open"])
        view = {
            "schema_version": source["schema_version"],
            "timestamp_utc": source["timestamp_utc"],
            "observation_id": source["observation_id"],
            "trade_id": trade_id,
            "position": source["position"],
            "realized_pnl": source["realized_pnl"],
            "unrealized_pnl": source["unrealized_pnl"],
            "net_liquidation_equity": source["net_liquidation_equity"],
            "equity_at_open": equity_at_open,
            "drawdown": source["drawdown"],
            "exposure": source["exposure"],
            "cash_reserve": source["cash_reserve"],
            "active_notional": source["active_notional"],
            "mark_rule_id": _view_mark_rule_id(source["mark_rule_id"]),
            "mark_kind": _mark_kind(source["observation_id"], fill_ids),
            "mark_honesty_label": HONESTY_RECORDED,
            "sample_class": source["sample_class"],
        }
        _validate_view_row(view)
        projected.append(view)
    return projected
