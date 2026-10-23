"""Recording adapter for the relative-rate accrual candidate.

Live ``funding_pnl`` stays off. There is no environment variable and no
CLI flag in this module that turns it on. ``FUNDING_DATA_STATUS`` may be
``PRESENT`` only when every expected print was retrieved. Gaps stay
``PARTIAL`` or ``MISSING``, and ``funding_pnl`` on the writer record stays
null in every status.

``NET_PNL_EX_FUNDING`` is passed through when the caller already has it.
This module does not compute Official net and does not import
``eval_scoring``.
"""

from __future__ import annotations

from typing import Mapping, Optional

from eval_recording.funding.accrual import AccrualResult, accrue

LIVE_FUNDING_INGEST_ENABLED = False
OFFICIAL_SIGN_LOCK = "NO"
CANDIDATE_RELATIVE = "RELATIVE_RATE_TIMES_NOTIONAL_LONG_PAYS_WHEN_POSITIVE"
NET_EX_FUNDING = "EX_FUNDING"


def writer_funding_record(
    result: AccrualResult,
    *,
    net_pnl_ex_funding: Optional[float] = None,
) -> dict[str, object]:
    """Fields a later writer may copy. The writer amount stays null."""
    if LIVE_FUNDING_INGEST_ENABLED:
        raise RuntimeError("this package cannot enable live funding ingest")
    if result.status == "PRESENT" and result.funding_pnl is None:
        raise ValueError("PRESENT requires a computed funding amount on the candidate")
    if result.status != "PRESENT" and result.funding_pnl is not None:
        raise ValueError("non-PRESENT candidate must not carry a funding amount")
    return {
        "FUNDING_DATA_STATUS": result.status,
        "funding_pnl": None,
        "NET_PNL_STATUS": NET_EX_FUNDING,
        "NET_PNL_EX_FUNDING": net_pnl_ex_funding,
        "NET_PNL_INCL_FUNDING": None,
        "live_funding_ingest": "OFF",
        "official_sign_lock": OFFICIAL_SIGN_LOCK,
        "selected_for_scoring": "NO",
        "candidate_id": CANDIDATE_RELATIVE,
        "not_a_score": True,
        "diagnostic_relative_funding_pnl": result.funding_pnl,
        "diagnostic_not_for_writer": True,
        "n_expected": result.n_expected,
        "n_present": result.n_present,
        "missing_timestamps": result.missing_timestamps,
    }


def recording_funding_fields(
    *,
    side: str,
    position_notional_usd: float,
    entry_time_utc: str,
    exit_time_utc: str,
    rates_by_ts: Mapping[str, float],
    net_pnl_ex_funding: Optional[float] = None,
) -> dict[str, object]:
    """Run accrual, then return the writer record with live ingest off."""
    result = accrue(
        side=side,
        position_notional_usd=position_notional_usd,
        entry_time_utc=entry_time_utc,
        exit_time_utc=exit_time_utc,
        rates_by_ts=rates_by_ts,
    )
    return writer_funding_record(result, net_pnl_ex_funding=net_pnl_ex_funding)
