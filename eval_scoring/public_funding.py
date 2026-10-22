"""Offline Kraken Futures public funding for Official Fake-Fill scoring.

This module does not open a ledger, place an order, or fetch rates. A
separate helper may write a cache. The scorer reads only that cache.

Source label: EXTERNAL_PUBLIC_FUNDING_V1. The amounts are derived from a
public historical-rate file. They are not ledger-recorded funding.

Locked public URL (v3, hyphenated). v4 hyphenated and v4 unhyphenated
respond as well; the cache records the URL that was actually fetched.

    https://futures.kraken.com/derivatives/api/v3/historical-funding-rates?symbol=SYMBOL

Semantics, checked against Kraken's contract-spec pages and a public
PF_XBTUSD payload on 2026-10-22:

- ``fundingRate`` is absolute USD a 1-contract short receives for one full
  hour. A positive rate means longs pay shorts. A negative rate reverses that.
- ``relativeFundingRate`` is the absolute rate divided by spot at calculation
  time. It is stored for audit and is not multiplied by notional.
- Each ``timestamp`` is the start of the hour the rate applies to.
  The application window is ``[timestamp, timestamp + 1h)``.
- Overlap with a held leg is ``[entry fill_time_utc, exit fill_time_utc)``.
  Kraken realizes funding at the hour end or when the position changes, so a
  partial hour closed before the clock-hour settlement still counts, prorated.
- The next stamp is not used as the period length. A missing clock hour is a
  missing settlement. It is not filled with a neighbour and it is not zero.
- ``contractSize`` comes from the public instruments payload and is stored on
  the cache. PF_XBTUSD was 1 on 2026-10-22 (base BTC, quote USD). Ledger
  ``quantity`` is multiplied by that recorded size. The scorer does not look
  up a size at score time.

Payout for one overlapping hour:

    short = quantity * contract_size * fundingRate * overlap_hours
    long  = -short
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

SCHEMA = "EXTERNAL_PUBLIC_FUNDING_V1"
SOURCE_URL_TEMPLATE = (
    "https://futures.kraken.com/derivatives/api/v3/historical-funding-rates?symbol={symbol}"
)
INSTRUMENTS_URL = "https://futures.kraken.com/derivatives/api/v3/instruments"
CONVENTION = (
    "absolute_fundingRate_usd_per_contract_per_hour; "
    "positive rate is received by a short and paid by a long; "
    "pnl = short_sign * quantity * contract_size * fundingRate * overlap_hours; "
    "period is [timestamp, timestamp+1h); "
    "hold is [entry_fill_time_utc, exit_fill_time_utc); "
    "relativeFundingRate is audit-only and is not multiplied by notional; "
    "a clock hour without its own rate makes the whole leg MISSING"
)
HOUR = timedelta(hours=1)


class FundingCacheError(Exception):
    """The cache is not a usable EXTERNAL_PUBLIC_FUNDING_V1 file."""


@dataclass(frozen=True)
class FundingBook:
    """Verified public-rate cache. Rates are keyed by period start."""

    schema: str
    symbol: str
    source_url: str
    fetched_at: str
    contract_size: Decimal
    contract_size_source: str
    convention: str
    rates_sha256: str
    rates: Mapping[datetime, Decimal]
    relative_rates: Mapping[datetime, Decimal]


@dataclass(frozen=True)
class FundingLeg:
    """Funding for one held leg. ``amount`` is None when any hour is missing."""

    status: str
    amount: Decimal | None
    hours: Decimal
    settlements: int
    missing_periods: tuple[str, ...]


def source_url_for(symbol: str) -> str:
    return SOURCE_URL_TEMPLATE.format(symbol=symbol)


def build_funding_cache(
    *,
    symbol: str,
    source_url: str,
    fetched_at: str,
    contract_size: Decimal | str | int,
    rates: Sequence[Mapping[str, Any]],
    contract_size_source: str,
    convention: str = CONVENTION,
) -> dict[str, Any]:
    """Return a cache document whose embedded rates hash matches its rates."""
    if not isinstance(symbol, str) or not symbol.strip():
        raise FundingCacheError("symbol is empty")
    canonical, _parsed = _canonical_rates(rates)
    digest = hashlib.sha256(canonical).hexdigest()
    size = _decimal(contract_size, "contract_size")
    if size <= 0:
        raise FundingCacheError("contract_size must be positive")
    if _parse_time(fetched_at) is None:
        raise FundingCacheError("fetched_at is not an ISO-8601 timestamp")
    if not isinstance(source_url, str) or not source_url.startswith("https://"):
        raise FundingCacheError("source_url must be https")
    return {
        "schema": SCHEMA,
        "symbol": symbol.strip(),
        "source_url": source_url,
        "fetched_at": _format_utc(_parse_time(fetched_at)),
        "contract_size": _dec(size),
        "contract_size_source": contract_size_source,
        "convention": convention,
        "rates_sha256": digest,
        "rates": json.loads(canonical.decode("utf-8")),
    }


def load_funding_cache_bytes(blob: bytes) -> FundingBook:
    """Load a cache and refuse it when the embedded rates hash does not match."""
    try:
        payload = json.loads(blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FundingCacheError("funding cache is not JSON") from exc
    if not isinstance(payload, dict):
        raise FundingCacheError("funding cache is not an object")
    if payload.get("schema") != SCHEMA:
        raise FundingCacheError("funding cache schema is not EXTERNAL_PUBLIC_FUNDING_V1")
    symbol = payload.get("symbol")
    source_url = payload.get("source_url")
    fetched_at = payload.get("fetched_at")
    recorded_hash = payload.get("rates_sha256")
    rates = payload.get("rates")
    if not isinstance(symbol, str) or not symbol.strip():
        raise FundingCacheError("funding cache symbol is empty")
    if not isinstance(source_url, str) or not source_url.startswith("https://futures.kraken.com/"):
        raise FundingCacheError("funding cache source_url is not a Kraken Futures https URL")
    if _parse_time(fetched_at) is None:
        raise FundingCacheError("funding cache fetched_at is not an ISO-8601 timestamp")
    if not isinstance(recorded_hash, str) or len(recorded_hash) != 64:
        raise FundingCacheError("funding cache rates_sha256 is absent")
    if not isinstance(rates, list):
        raise FundingCacheError("funding cache rates is not a list")
    canonical, parsed = _canonical_rates(rates)
    digest = hashlib.sha256(canonical).hexdigest()
    if digest != recorded_hash:
        raise FundingCacheError("funding cache rates_sha256 does not match the rates")
    size = _decimal(payload.get("contract_size"), "contract_size")
    if size <= 0:
        raise FundingCacheError("contract_size must be positive")
    source = payload.get("contract_size_source")
    if not isinstance(source, str) or not source.strip():
        raise FundingCacheError("contract_size_source is absent")
    convention = payload.get("convention")
    if not isinstance(convention, str) or not convention.strip():
        raise FundingCacheError("convention is absent")
    return FundingBook(
        schema=SCHEMA,
        symbol=symbol.strip(),
        source_url=source_url,
        fetched_at=_format_utc(_parse_time(fetched_at)),
        contract_size=size,
        contract_size_source=source,
        convention=convention,
        rates_sha256=digest,
        rates=parsed[0],
        relative_rates=parsed[1],
    )


def rates_from_kraken_payload(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Read the public historical-funding ``rates`` list. No network."""
    if payload.get("result") != "success":
        raise FundingCacheError("kraken historical funding result was not success")
    rates = payload.get("rates")
    if not isinstance(rates, list) or not rates:
        raise FundingCacheError("kraken historical funding payload has no rates")
    return list(rates)


def contract_size_from_instruments(payload: Mapping[str, Any], symbol: str) -> Decimal:
    """Read ``contractSize`` for one symbol from the public instruments payload."""
    if payload.get("result") != "success":
        raise FundingCacheError("kraken instruments result was not success")
    instruments = payload.get("instruments")
    if not isinstance(instruments, list):
        raise FundingCacheError("kraken instruments payload has no instruments list")
    for item in instruments:
        if isinstance(item, Mapping) and item.get("symbol") == symbol:
            return _decimal(item.get("contractSize"), "contractSize")
    raise FundingCacheError(f"symbol {symbol} is not in the instruments payload")


def leg_funding(
    book: FundingBook,
    *,
    entry_at: datetime,
    exit_at: datetime,
    quantity: Decimal,
    short_receives_positive: bool,
) -> FundingLeg:
    """Funding cashflow for one leg.

    ``short_receives_positive`` is True for a short. Any clock hour that
    overlaps the hold and has no rate makes the whole leg MISSING. No partial
    sum is returned in that case.
    """
    if entry_at.tzinfo is None or exit_at.tzinfo is None:
        raise FundingCacheError("fill times must be timezone-aware")
    entry_at = entry_at.astimezone(timezone.utc)
    exit_at = exit_at.astimezone(timezone.utc)
    if quantity <= 0:
        raise FundingCacheError("quantity must be positive")
    if exit_at <= entry_at:
        return FundingLeg("PRESENT", Decimal(0), Decimal(0), 0, ())

    missing: list[str] = []
    hours_total = Decimal(0)
    amount = Decimal(0)
    settlements = 0
    cursor = entry_at.replace(minute=0, second=0, microsecond=0)
    while cursor < exit_at:
        period_end = cursor + HOUR
        overlap_start = entry_at if entry_at > cursor else cursor
        overlap_end = exit_at if exit_at < period_end else period_end
        if overlap_end > overlap_start:
            overlap_hours = _hours(overlap_end - overlap_start)
            rate = book.rates.get(cursor)
            if rate is None:
                missing.append(_format_utc(cursor))
            else:
                piece = quantity * book.contract_size * rate * overlap_hours
                if not short_receives_positive:
                    piece = -piece
                amount += piece
                hours_total += overlap_hours
                settlements += 1
        cursor = period_end
    if missing:
        return FundingLeg("MISSING", None, Decimal(0), 0, tuple(missing))
    return FundingLeg("PRESENT", amount, hours_total, settlements, ())


def _canonical_rates(
    rates: Sequence[Mapping[str, Any]],
) -> tuple[bytes, tuple[dict[datetime, Decimal], dict[datetime, Decimal]]]:
    rows: list[dict[str, str]] = []
    absolute: dict[datetime, Decimal] = {}
    relative: dict[datetime, Decimal] = {}
    seen: set[str] = set()
    for rate in rates:
        if not isinstance(rate, Mapping):
            raise FundingCacheError("a funding rate is not an object")
        parsed = _parse_time(rate.get("timestamp"))
        if parsed is None:
            raise FundingCacheError("a funding rate timestamp is not ISO-8601")
        stamp = _format_utc(parsed)
        if stamp in seen:
            raise FundingCacheError(f"duplicate funding timestamp {stamp}")
        seen.add(stamp)
        funding_rate = _decimal(rate.get("fundingRate"), "fundingRate")
        item = {"timestamp": stamp, "fundingRate": _dec(funding_rate)}
        relative_raw = rate.get("relativeFundingRate")
        if relative_raw not in (None, ""):
            relative_rate = _decimal(relative_raw, "relativeFundingRate")
            item["relativeFundingRate"] = _dec(relative_rate)
            relative[parsed] = relative_rate
        rows.append(item)
        absolute[parsed] = funding_rate
    rows.sort(key=lambda item: item["timestamp"])
    canonical = json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return canonical, (absolute, relative)


def _hours(delta: timedelta) -> Decimal:
    seconds = Decimal(delta.days) * Decimal(86400) + Decimal(delta.seconds) + (
        Decimal(delta.microseconds) / Decimal(1000000)
    )
    return seconds / Decimal(3600)


def _decimal(value: Any, label: str) -> Decimal:
    if isinstance(value, bool) or value is None or value == "":
        raise FundingCacheError(f"{label} is absent")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise FundingCacheError(f"{label} is not a decimal") from exc
    if not number.is_finite():
        raise FundingCacheError(f"{label} is not finite")
    return number


def _dec(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


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


def _format_utc(value: datetime | None) -> str:
    if value is None:
        raise FundingCacheError("timestamp is absent")
    stamp = value.astimezone(timezone.utc).replace(tzinfo=None)
    text = stamp.isoformat()
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text + "Z"
