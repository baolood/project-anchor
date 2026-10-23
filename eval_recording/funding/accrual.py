#!/usr/bin/env python3
"""PF_XBTUSD funding accrual helpers (public relativeFundingRate).

Diagnostic candidate only. This is not ``eval_scoring.public_funding`` and
it is not selected for Official C3. The locked scorer uses absolute
``fundingRate`` per contract. Nothing here turns on live ``funding_pnl``.

Sign convention (Kraken Futures perpetual, long pays when relativeFundingRate > 0):
  funding_pnl_usd ≈ -side_sign * position_notional_usd * relativeFundingRate
  where side_sign = +1 for LONG, -1 for SHORT.

Interval inclusion: a funding print at timestamp T accrues if
  entry_time < T <= exit_time
(open interval on entry so the print at exact entry is not double-counted
across adjacent trades; closed on exit so exit-bar funding is included).

NEVER zero-fill: if any expected 1h print in (entry, exit] is absent from
the rate map, status is PARTIAL (or MISSING if none present) and
funding_pnl is None.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Mapping, Optional


def parse_ts(s: str) -> datetime:
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def side_sign(side: str) -> int:
    s = side.strip().upper()
    if s in ("LONG", "BUY", "L"):
        return 1
    if s in ("SHORT", "SELL", "S"):
        return -1
    raise ValueError(f"unknown side: {side!r}")


def expected_funding_timestamps(entry: datetime, exit_: datetime) -> list[datetime]:
    """Hourly funding stamps strictly after entry and <= exit."""
    if exit_ <= entry:
        return []
    # first candidate: ceil to next whole hour after entry
    t = entry.replace(minute=0, second=0, microsecond=0)
    if t <= entry:
        t = t + timedelta(hours=1)
    out: list[datetime] = []
    while t <= exit_:
        out.append(t)
        t = t + timedelta(hours=1)
    return out


@dataclass(frozen=True)
class AccrualResult:
    status: str  # PRESENT | PARTIAL | MISSING
    funding_pnl: Optional[float]
    n_expected: int
    n_present: int
    missing_timestamps: tuple[str, ...]
    used_timestamps: tuple[str, ...]


def accrue(
    *,
    side: str,
    position_notional_usd: float,
    entry_time_utc: str,
    exit_time_utc: str,
    rates_by_ts: Mapping[str, float],
) -> AccrualResult:
    """rates_by_ts maps ISO-Z timestamp -> relativeFundingRate (not fundingRate)."""
    entry = parse_ts(entry_time_utc)
    exit_ = parse_ts(exit_time_utc)
    expected = expected_funding_timestamps(entry, exit_)
    if not expected:
        return AccrualResult(
            status="MISSING",
            funding_pnl=None,
            n_expected=0,
            n_present=0,
            missing_timestamps=(),
            used_timestamps=(),
        )

    missing: list[str] = []
    used: list[str] = []
    pnl = 0.0
    sign = side_sign(side)
    for t in expected:
        key = t.strftime("%Y-%m-%dT%H:%M:%SZ")
        # also accept variants without seconds normalization already Z
        if key not in rates_by_ts:
            missing.append(key)
            continue
        rel = rates_by_ts[key]
        used.append(key)
        pnl += -sign * float(position_notional_usd) * float(rel)

    if not used:
        status = "MISSING"
        funding_pnl: Optional[float] = None
    elif missing:
        status = "PARTIAL"
        funding_pnl = None  # never partial-sum as if complete
    else:
        status = "PRESENT"
        funding_pnl = pnl

    return AccrualResult(
        status=status,
        funding_pnl=funding_pnl,
        n_expected=len(expected),
        n_present=len(used),
        missing_timestamps=tuple(missing),
        used_timestamps=tuple(used),
    )


def rates_map_from_records(records: Iterable[dict]) -> dict[str, float]:
    out: dict[str, float] = {}
    for r in records:
        ts = r["timestamp"]
        if not ts.endswith("Z"):
            ts = parse_ts(ts).strftime("%Y-%m-%dT%H:%M:%SZ")
        out[ts] = float(r["relativeFundingRate"])
    return out
