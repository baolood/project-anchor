"""Equity v2.1 dual-write helpers. Default off. Legacy CSV is not a write target.

New file: ``anchor_fake_fill_equity_v2_1_official.csv`` (13 columns).
Every row, including genesis, uses that same header. The legacy file
``anchor_fake_fill_equity_v2_official.csv`` is never opened for write.
Paths inside ``affl-v2-official-ledger`` are refused.

Enable only by passing ``enabled=True`` or by setting
``AFFL_EQUITY_V21_DUAL_WRITE=1`` / argv ``--equity-v21-dual-write``.
Unset means off, and off does not create the new file.
"""

from __future__ import annotations

import csv
import io
import os
from collections.abc import Mapping, Sequence
from pathlib import Path

SCHEMA_VERSION = "equity_v2_1"
NEW_EQUITY_FILENAME = "anchor_fake_fill_equity_v2_1_official.csv"
LEGACY_EQUITY_FILENAME = "anchor_fake_fill_equity_v2_official.csv"
LEGACY_HEADER_TAG = "LEGACY_HEADER_MISMATCH"
SEALED_LEDGER_DIRNAME = "affl-v2-official-ledger"
ENV_FLAG = "AFFL_EQUITY_V21_DUAL_WRITE"
CLI_FLAG = "--equity-v21-dual-write"
GENESIS_OBSERVATION_ID = "LEDGER_GENESIS"
MARK_RULE_BOUND = "MARK_RULE_C7_V1"
MARK_RULE_UNBOUND = "UNBOUND"
SAMPLE_CLASS_NON_SCORING = "NON_SCORING"

EQUITY_V21_COLUMNS: tuple[str, ...] = (
    "schema_version",
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
    "mark_rule_id",
    "sample_class",
)
HEADER_COLUMN_COUNT = len(EQUITY_V21_COLUMNS)

POSITIONS = frozenset({"FLAT", "LONG", "SHORT"})
MARK_RULE_IDS = frozenset({"", MARK_RULE_UNBOUND, MARK_RULE_BOUND})


class EquityDualWriteError(ValueError):
    """The v2.1 file would be born or extended incorrectly."""


class LegacyEquityImmutable(EquityDualWriteError):
    """The legacy Official equity CSV is not a v2.1 write target."""


class SealedLedgerWriteRefused(EquityDualWriteError):
    """Line A / sealed Official ledger tree is not a write target."""


def header_line() -> str:
    return ",".join(EQUITY_V21_COLUMNS)


def dual_write_enabled(
    *,
    enabled: bool | None = None,
    environ: Mapping[str, str] | None = None,
    argv: Sequence[str] | None = None,
) -> bool:
    """Return whether a caller asked for the new file.

    An explicit ``enabled`` value wins. Otherwise the CLI flag or
    ``AFFL_EQUITY_V21_DUAL_WRITE=1`` turns it on. Any other env value,
    including unset, stays off. This function does not read ``sys.argv``.
    """
    if enabled is not None:
        return enabled
    if argv is not None and CLI_FLAG in argv:
        return True
    env = os.environ if environ is None else environ
    return env.get(ENV_FLAG, "0").strip() == "1"


def _hits_sealed(path: Path) -> bool:
    if SEALED_LEDGER_DIRNAME in path.parts:
        return True
    try:
        resolved = path.resolve()
    except OSError:
        return False
    return SEALED_LEDGER_DIRNAME in resolved.parts


def assert_v21_destination(path: Path) -> None:
    """Refuse the legacy filename and any path under sealed Line A."""
    if path.name == LEGACY_EQUITY_FILENAME:
        raise LegacyEquityImmutable(
            f"{LEGACY_EQUITY_FILENAME} stays immutable ({LEGACY_HEADER_TAG})"
        )
    if path.name != NEW_EQUITY_FILENAME:
        raise EquityDualWriteError(
            f"v2.1 writes must use {NEW_EQUITY_FILENAME}"
        )
    try:
        if path.exists() and path.resolve().name == LEGACY_EQUITY_FILENAME:
            raise LegacyEquityImmutable(
                "refusing to write through a path that resolves to the legacy equity CSV"
            )
    except OSError as exc:
        raise EquityDualWriteError("could not resolve the equity destination") from exc
    if _hits_sealed(path):
        raise SealedLedgerWriteRefused(
            "refusing to write inside affl-v2-official-ledger"
        )


def genesis_row(
    *,
    timestamp_utc: str,
    net_liquidation_equity: str,
    cash_reserve: str,
    sample_class: str,
    mark_rule_id: str = MARK_RULE_UNBOUND,
) -> dict[str, str]:
    """13-column genesis. ``mark_rule_id`` defaults to explicit ``UNBOUND``."""
    row = {column: "" for column in EQUITY_V21_COLUMNS}
    row.update(
        {
            "schema_version": SCHEMA_VERSION,
            "timestamp_utc": timestamp_utc,
            "observation_id": GENESIS_OBSERVATION_ID,
            "position": "FLAT",
            "realized_pnl": "0",
            "unrealized_pnl": "0",
            "net_liquidation_equity": net_liquidation_equity,
            "drawdown": "0",
            "exposure": "0",
            "cash_reserve": cash_reserve,
            "active_notional": "0",
            "mark_rule_id": mark_rule_id,
            "sample_class": sample_class,
        }
    )
    return _normalize_row(row)


def _normalize_row(row: Mapping[str, str]) -> dict[str, str]:
    missing = [column for column in EQUITY_V21_COLUMNS if column not in row]
    extra = [column for column in row if column not in EQUITY_V21_COLUMNS]
    if missing or extra:
        raise EquityDualWriteError(
            f"row width must be {HEADER_COLUMN_COUNT}; "
            f"missing={missing}; extra={extra}"
        )
    cleaned = {column: str(row[column]) for column in EQUITY_V21_COLUMNS}
    for column, value in cleaned.items():
        if "\n" in value or "\r" in value:
            raise EquityDualWriteError(f"{column} must be a single-line field")
    if cleaned["schema_version"] != SCHEMA_VERSION:
        raise EquityDualWriteError("schema_version must be equity_v2_1 on every row")
    if not cleaned["timestamp_utc"] or not cleaned["observation_id"]:
        raise EquityDualWriteError("timestamp_utc and observation_id are required")
    if cleaned["position"] not in POSITIONS:
        raise EquityDualWriteError("position must be FLAT, LONG, or SHORT")
    if cleaned["mark_rule_id"] not in MARK_RULE_IDS:
        raise EquityDualWriteError(
            "mark_rule_id must be MARK_RULE_C7_V1, UNBOUND, or empty"
        )
    if not cleaned["sample_class"]:
        raise EquityDualWriteError("sample_class is required")
    if cleaned["observation_id"] == GENESIS_OBSERVATION_ID and cleaned["position"] != "FLAT":
        raise EquityDualWriteError("genesis row must be FLAT")
    return cleaned


def assert_csv_column_equality(text: str) -> int:
    """Require header and every body row to share the 13-column v2.1 width."""
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise EquityDualWriteError("equity CSV is empty") from exc
    if tuple(header) != EQUITY_V21_COLUMNS:
        raise EquityDualWriteError(
            f"header width {len(header)} is not the {HEADER_COLUMN_COUNT}-column v2.1 header"
        )
    body = 0
    for raw in reader:
        if not raw or raw == [""]:
            continue
        body += 1
        if len(raw) != HEADER_COLUMN_COUNT:
            raise EquityDualWriteError(
                f"body row {body} has {len(raw)} columns; header has {HEADER_COLUMN_COUNT}"
            )
    if body == 0:
        raise EquityDualWriteError("v2.1 file has a header and no rows")
    return HEADER_COLUMN_COUNT


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(EQUITY_V21_COLUMNS),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    assert_csv_column_equality(path.read_text(encoding="utf-8"))


def _read_checked(path: Path) -> None:
    assert_csv_column_equality(path.read_text(encoding="utf-8"))
    with path.open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle))
    if tuple(header) != EQUITY_V21_COLUMNS:
        raise EquityDualWriteError("refusing to append to a non-v2.1 header")


def record_equity_v21(
    path: Path,
    row: Mapping[str, str],
    *,
    enabled: bool | None = None,
    genesis: Mapping[str, str] | None = None,
    environ: Mapping[str, str] | None = None,
    argv: Sequence[str] | None = None,
) -> dict[str, object]:
    """Append one v2.1 row when the flag is on. Off leaves the disk untouched.

    A missing file is born with the 13-column header and a genesis row of
    the same width. An existing file is append-only. Genesis is not appended
    twice, and the legacy CSV is never opened.
    """
    destination = Path(path)
    assert_v21_destination(destination)
    turned_on = dual_write_enabled(enabled=enabled, environ=environ, argv=argv)
    if not turned_on:
        return {
            "written": False,
            "reason": "DISABLED",
            "path": str(destination),
            "created": False,
        }
    incoming = _normalize_row(row)
    if not destination.exists():
        if genesis is None:
            if incoming["observation_id"] != GENESIS_OBSERVATION_ID:
                raise EquityDualWriteError(
                    "genesis row required to birth the v2.1 file"
                )
            rows = [incoming]
        else:
            first = _normalize_row(genesis)
            if first["observation_id"] != GENESIS_OBSERVATION_ID:
                raise EquityDualWriteError(
                    "genesis observation_id must be LEDGER_GENESIS"
                )
            rows = [first]
            if incoming["observation_id"] != GENESIS_OBSERVATION_ID:
                rows.append(incoming)
        _write_rows(destination, rows)
        return {
            "written": True,
            "reason": "CREATED",
            "path": str(destination),
            "created": True,
            "rows_written": len(rows),
        }
    _read_checked(destination)
    if incoming["observation_id"] == GENESIS_OBSERVATION_ID:
        raise EquityDualWriteError(
            "genesis already written; refusing to append another genesis row"
        )
    existing = destination.read_bytes()
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=list(EQUITY_V21_COLUMNS),
        lineterminator="\n",
    )
    writer.writerow(incoming)
    payload = buffer.getvalue().encode("utf-8")
    with destination.open("ab") as handle:
        if existing and not existing.endswith(b"\n"):
            handle.write(b"\n")
        handle.write(payload)
    assert_csv_column_equality(destination.read_text(encoding="utf-8"))
    return {
        "written": True,
        "reason": "APPENDED",
        "path": str(destination),
        "created": False,
        "rows_written": 1,
    }
