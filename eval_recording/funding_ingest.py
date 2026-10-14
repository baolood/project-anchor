"""Public funding completeness. No HTTP client and no zero-fill.

The PRESENT-only incl-funding path is implemented and tested here.
``OFFICIAL_SIGN_LOCK`` stays ``NO``, so this package still records
``EX_FUNDING`` and does not place the series on the formal scoring chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

OFFICIAL_SYMBOL = "PF_XBTUSD"
PUBLIC_ORIGIN = "https://futures.kraken.com"
PUBLIC_PATH = "/derivatives/api/v3/historicalfundingrates"
PUBLIC_DOCS_URL = (
    "https://docs.kraken.com/api-reference/historical-funding-rates/"
    "historical-funding-rates"
)

DATA_MISSING = "MISSING"
DATA_PARTIAL = "PARTIAL"
DATA_PRESENT = "PRESENT"
DATA_NO_INTERVAL = "NO_INTERVAL"

NET_EX_FUNDING = "EX_FUNDING"
NET_INCL_FUNDING = "INCL_FUNDING"

# Candidate formulas exist so a later lock can pick one. Neither is scored.
OFFICIAL_SIGN_LOCK = "NO"
CANDIDATE_ABSOLUTE = "ABSOLUTE_PER_CONTRACT_SHORT_RECEIVES"
CANDIDATE_RELATIVE = "RELATIVE_RATE_TIMES_NOTIONAL_LONG_PAYS_WHEN_POSITIVE"
ZERO_FILL_MISSING = "FORBIDDEN"

# Future append-only cache. This package does not create it.
FUNDING_CACHE_RELATIVE = (
    "affl-v2-official-ledger/funding/PF_XBTUSD_historicalfundingrates.jsonl"
)
CACHE_FIELDS = (
    "fetched_at_utc",
    "symbol",
    "source_url",
    "response_sha256",
    "timestamp",
    "fundingRate",
    "relativeFundingRate",
    "auth",
)


class ZeroFillForbidden(ValueError):
    """Missing funding must stay missing. A retrieved 0 rate is a different case."""


class FundingWindowError(ValueError):
    """Raised when the expected funding grid does not match the hold."""


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def parse_utc(value: str) -> datetime:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise FundingWindowError("funding timestamps must be timezone-aware UTC")
    return parsed.astimezone(timezone.utc)


def _in_hold(timestamp: str, entry_time_utc: str, exit_time_utc: str) -> bool:
    instant = parse_utc(timestamp)
    return parse_utc(entry_time_utc) < instant <= parse_utc(exit_time_utc)


@dataclass(frozen=True)
class FundingRatePoint:
    """One public historical row. ``None`` means the field was not retrieved."""

    timestamp_utc: str
    funding_rate: Decimal | None
    relative_funding_rate: Decimal | None

    @classmethod
    def from_public_row(cls, row: dict[str, object]) -> FundingRatePoint:
        timestamp = row.get("timestamp")
        if not isinstance(timestamp, str) or not timestamp:
            raise FundingWindowError("public funding row needs a timestamp")
        return cls(
            timestamp_utc=timestamp,
            funding_rate=_decimal_or_none(row.get("fundingRate")),
            relative_funding_rate=_decimal_or_none(row.get("relativeFundingRate")),
        )

    def is_retrieved(self) -> bool:
        """Both public fields must be present. A real 0 is retrieved, not missing."""
        return self.funding_rate is not None and self.relative_funding_rate is not None


def public_historical_funding_request(symbol: str = OFFICIAL_SYMBOL) -> dict[str, object]:
    """Describe the future public GET. ``execute`` stays NO in this package."""
    if not symbol or any(char.isspace() for char in symbol):
        raise FundingWindowError("symbol must be a non-empty token")
    return {
        "method": "GET",
        "url": PUBLIC_ORIGIN + PUBLIC_PATH,
        "query": {"symbol": symbol},
        "auth": "NONE",
        "private_api": "NO",
        "execute": "NO",
        "zero_fill_missing": ZERO_FILL_MISSING,
        "docs_url": PUBLIC_DOCS_URL,
        "cache_relative": FUNDING_CACHE_RELATIVE,
        "cache_write_in_this_package": "NO",
        "fields": ("timestamp", "fundingRate", "relativeFundingRate"),
    }


def coverage_status(
    expected_timestamps: tuple[str, ...] | list[str],
    points: tuple[FundingRatePoint, ...] | list[FundingRatePoint],
    *,
    entry_time_utc: str,
    exit_time_utc: str,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    """Classify the hold. Missing slots are never treated as rate 0."""
    if parse_utc(exit_time_utc) <= parse_utc(entry_time_utc):
        raise FundingWindowError("exit must be after entry")
    expected = tuple(expected_timestamps)
    if not expected:
        return DATA_NO_INTERVAL, (), ()
    outside = [item for item in expected if not _in_hold(item, entry_time_utc, exit_time_utc)]
    if outside:
        raise FundingWindowError("expected funding timestamps must fall inside (entry, exit]")
    retrieved = {
        point.timestamp_utc
        for point in points
        if point.is_retrieved() and _in_hold(point.timestamp_utc, entry_time_utc, exit_time_utc)
    }
    missing = tuple(item for item in expected if item not in retrieved)
    covered = tuple(item for item in expected if item in retrieved)
    if not missing:
        return DATA_PRESENT, covered, missing
    if len(missing) == len(expected):
        return DATA_MISSING, covered, missing
    return DATA_PARTIAL, covered, missing


def _candidate_amounts(
    points: tuple[FundingRatePoint, ...],
    *,
    side: str,
    quantity_contracts: Decimal,
    position_notional: Decimal,
) -> dict[str, str]:
    if side not in {"LONG", "SHORT"}:
        raise FundingWindowError("side must be LONG or SHORT")
    absolute = Decimal("0")
    relative = Decimal("0")
    for point in points:
        if point.funding_rate is None or point.relative_funding_rate is None:
            raise ZeroFillForbidden("candidate math refuses a missing rate")
        if side == "SHORT":
            absolute += point.funding_rate * quantity_contracts
            relative += point.relative_funding_rate * position_notional
        else:
            absolute += -point.funding_rate * quantity_contracts
            relative += -point.relative_funding_rate * position_notional
    return {
        CANDIDATE_ABSOLUTE: format(absolute, "f"),
        CANDIDATE_RELATIVE: format(relative, "f"),
    }


def assess_funding_window(
    *,
    expected_timestamps: tuple[str, ...] | list[str],
    points: tuple[FundingRatePoint, ...] | list[FundingRatePoint],
    entry_time_utc: str,
    exit_time_utc: str,
    side: str,
    quantity_contracts: Decimal,
    position_notional: Decimal,
) -> dict[str, object]:
    """Record completeness. The official sign lock stays off, so net stays ex-funding."""
    status, covered, missing = coverage_status(
        expected_timestamps,
        points,
        entry_time_utc=entry_time_utc,
        exit_time_utc=exit_time_utc,
    )
    candidates = None
    if status == DATA_PRESENT:
        used_by_timestamp: dict[str, FundingRatePoint] = {}
        for point in points:
            if point.timestamp_utc in covered and point.is_retrieved():
                used_by_timestamp.setdefault(point.timestamp_utc, point)
        ordered = tuple(used_by_timestamp[timestamp] for timestamp in covered)
        candidates = _candidate_amounts(
            ordered,
            side=side,
            quantity_contracts=quantity_contracts,
            position_notional=position_notional,
        )
    recorded = resolve_recorded_net(
        ex_funding=None,
        funding_pnl=None,
        data_status=status,
        sign_lock=OFFICIAL_SIGN_LOCK,
    )
    return {
        "symbol": OFFICIAL_SYMBOL,
        "FUNDING_DATA_STATUS": status,
        "covered_timestamps": covered,
        "missing_timestamps": missing,
        "sign_lock": OFFICIAL_SIGN_LOCK,
        "selected_for_net_pnl": None,
        "candidates": candidates,
        "zero_filled": False,
        **recorded,
    }


def resolve_recorded_net(
    *,
    ex_funding: Decimal | None,
    funding_pnl: Decimal | None,
    data_status: str,
    sign_lock: str,
) -> dict[str, object]:
    """PRESENT-only incl-funding path.

    A numeric ``funding_pnl`` is refused unless every interval was retrieved
    and the sign convention is locked. This package's official lock is NO,
    and even a locked call is marked ``not_a_score`` because Gate B is not
    the formal scoring chain.
    """
    eligible = data_status == DATA_PRESENT and sign_lock == "YES"
    if not eligible:
        if funding_pnl is not None:
            raise ZeroFillForbidden(
                "refusing to record funding_pnl while data is not PRESENT "
                "or the sign convention is unlocked"
            )
        return {
            "NET_PNL_STATUS": NET_EX_FUNDING,
            "NET_PNL_EX_FUNDING": None if ex_funding is None else format(ex_funding, "f"),
            "NET_PNL_INCL_FUNDING": None,
            "funding_pnl": None,
            "formal_scoring_chain": "NOT_ON_FORMAL_SCORING_CHAIN",
            "not_a_score": True,
        }
    if funding_pnl is None or ex_funding is None:
        raise ZeroFillForbidden(
            "a locked PRESENT window needs both series; missing funding is not zero"
        )
    return {
        "NET_PNL_STATUS": NET_INCL_FUNDING,
        "NET_PNL_EX_FUNDING": format(ex_funding, "f"),
        "NET_PNL_INCL_FUNDING": format(ex_funding + funding_pnl, "f"),
        "funding_pnl": format(funding_pnl, "f"),
        "formal_scoring_chain": "NOT_ON_FORMAL_SCORING_CHAIN",
        "not_a_score": True,
    }
