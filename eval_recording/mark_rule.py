"""MARK_RULE_C7_V1 text and cadence checks. This module does not score drawdown."""

from __future__ import annotations

from collections.abc import Iterable

MARK_RULE_ID = "MARK_RULE_C7_V1"
MARK_KIND_GENESIS = "GENESIS"
MARK_KIND_BAR = "BAR_1H"
MARK_KIND_FILL = "FILL"
MARK_KIND_OHLC_PROXY = "OHLC_ADVERSE_PROXY"
HONESTY_RECORDED = "RECORDED_MARK"
HONESTY_NOT_TICK_LOW = "NOT_TICK_LOW"

FILL_EVENT_TYPES = ("OPEN", "FLAT_EXIT", "REVERSE_EXIT", "REVERSE_ENTRY")

MARK_RULE_C7_V1_TEXT = (
    "MARK_RULE_C7_V1 (honest sampling). For Official equity used in C5/C7: "
    "(1) Required marks: at least 1 equity sample per completed 1h bar while "
    "the Official account is open or flat-after-genesis, and one mark at each "
    "Official fill (OPEN, FLAT_EXIT, REVERSE_EXIT, REVERSE_ENTRY). "
    "(2) Primary day_low is the minimum of recorded Official equity marks on "
    "that CST day. T0 and partial-day rules stay as already written in the "
    "pass line; this rule does not change them. "
    "(3) Optional conservative intrabar proxy, labeled: if the Founder enables "
    "it, for each 1h bar while a position is open, also emit a mark using that "
    "bar's OHLC adverse extreme (LONG uses the bar low, SHORT uses the bar high) "
    "converted with the same unrealized formula. Those rows use "
    "mark_kind=OHLC_ADVERSE_PROXY and mark_honesty_label=NOT_TICK_LOW, and they "
    "are not tick-low and not an exchange mark-price low. "
    "(4) Forbidden claim: calling an OHLC adverse extreme or a 1h close the "
    "true intraday tick minimum. "
    "(5) Until this rule is implemented and equity v2.1 is the scoring path, "
    "C7 stays CONDITIONAL. This text is not on the formal scoring chain until "
    "the Founder says so."
)


def counts_toward_required_mark(mark_kind: str) -> bool:
    """OHLC adverse rows are extra labeled proxies. They do not fill the quota."""
    return mark_kind in {MARK_KIND_BAR, MARK_KIND_FILL}


def missing_hourly_marks(
    *,
    required_bar_open_utc: Iterable[str],
    marked_bar_open_utc: Iterable[str],
) -> list[str]:
    """Bars with no required mark. Order follows ``required_bar_open_utc``."""
    marked = set(marked_bar_open_utc)
    return [bar for bar in required_bar_open_utc if bar not in marked]


def missing_fill_marks(
    *,
    fill_event_ids: Iterable[str],
    marked_fill_event_ids: Iterable[str],
) -> list[str]:
    marked = set(marked_fill_event_ids)
    return [fill_id for fill_id in fill_event_ids if fill_id not in marked]
