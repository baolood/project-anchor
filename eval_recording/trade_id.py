"""Stable open-to-close trade id. Optional, version-gated, not a C6 risk field."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

RECORDING_SCHEMA_VERSION = "recording_v1"
TRADE_ID_PREFIX = "tr_"

ENTRY_EVENT_TYPES = frozenset({"OPEN", "REVERSE_ENTRY"})
EXIT_EVENT_TYPES = frozenset({"FLAT_EXIT", "REVERSE_EXIT"})


class TradeIdError(ValueError):
    """Raised when a trade id would be ambiguous or invented."""


def trade_id_from_entry_ledger_event_id(entry_ledger_event_id: str) -> str:
    """Mint ``tr_`` + the entry event's own ``ledger_event_id``.

    The id is not the observation id and not a row index. Exit events copy
    this value; they do not mint another one.
    """
    if not isinstance(entry_ledger_event_id, str):
        raise TradeIdError("entry ledger_event_id must be a string")
    cleaned = entry_ledger_event_id.strip()
    if not cleaned or cleaned != entry_ledger_event_id:
        raise TradeIdError("entry ledger_event_id must be a non-empty exact token")
    if cleaned.startswith(TRADE_ID_PREFIX):
        raise TradeIdError("refusing to stack the tr_ prefix")
    if any(char.isspace() for char in cleaned):
        raise TradeIdError("entry ledger_event_id must not contain whitespace")
    return TRADE_ID_PREFIX + cleaned


def trade_id_hash(ledger_genesis_id: str, entry_ledger_event_id: str) -> str:
    """Optional cross-host checksum. The trade id itself stays the ``tr_`` form."""
    if not ledger_genesis_id or not entry_ledger_event_id:
        raise TradeIdError("hash inputs must be non-empty")
    material = f"{ledger_genesis_id}|{entry_ledger_event_id}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RecordingOptionalFields:
    """Additive fields a future writer may attach. Default-off for older schemas.

    This is not ``affl_v2`` ``LedgerEvent`` and not the C6 stop struct.
    If the C6 PR adds ``trade_id`` onto a shared struct, keep it optional
    and honor it only when ``recording_schema_version`` is ``recording_v1``.
    """

    recording_schema_version: str = RECORDING_SCHEMA_VERSION
    trade_id: str | None = None
    trade_id_hash: str | None = None

    def __post_init__(self) -> None:
        if self.recording_schema_version != RECORDING_SCHEMA_VERSION:
            raise TradeIdError(
                "recording fields require the recording_v1 version gate"
            )
        if self.trade_id is not None and not self.trade_id.startswith(TRADE_ID_PREFIX):
            raise TradeIdError("trade_id must use the tr_ scheme")


def authoritative_trade_id(
    record: dict[str, object],
    *,
    recording_schema_version: str | None,
) -> str | None:
    """Return a trade id only behind the version gate.

    Older schema versions ignore a stray ``trade_id`` so a later additive
    field cannot re-pair an already recorded exam window by itself.
    """
    if recording_schema_version != RECORDING_SCHEMA_VERSION:
        return None
    value = record.get("trade_id")
    if value is None or value == "":
        return None
    if not isinstance(value, str) or not value.startswith(TRADE_ID_PREFIX):
        raise TradeIdError("recording_v1 trade_id must use the tr_ scheme")
    return value


def apply_trade_id(
    *,
    event_type: str,
    ledger_event_id: str,
    held_trade_id: str | None,
) -> tuple[str | None, str | None]:
    """Assign the event trade id and the id still held after the event.

    Returns ``(event_trade_id, next_held_trade_id)``.
    OPEN and REVERSE_ENTRY mint. FLAT_EXIT and REVERSE_EXIT copy.
    REVERSE_ENTRY is legal only after the previous leg has been cleared.
    """
    if event_type in ENTRY_EVENT_TYPES:
        if held_trade_id is not None:
            raise TradeIdError(
                f"{event_type} requires the previous leg to be closed first"
            )
        minted = trade_id_from_entry_ledger_event_id(ledger_event_id)
        return minted, minted
    if event_type in EXIT_EVENT_TYPES:
        if not held_trade_id:
            raise TradeIdError("exit cannot mint a trade id and none is held")
        return held_trade_id, None
    return None, held_trade_id
