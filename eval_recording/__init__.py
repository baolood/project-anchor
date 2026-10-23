"""Evaluation recording helpers for a later series. Not a scorer.

DEPLOY=NO. Importing this package does not write an equity file, does not
fetch funding, and does not freeze PASS LINE.

Equity v2.1 dual-write stays off unless a caller passes the flag or sets
``AFFL_EQUITY_V21_DUAL_WRITE=1``. The on-disk file is 13 columns.
``equity_schema.project_scoring_view`` builds the 17-field scoring view in
memory and does not write it. Live funding ingest stays off with no
environment switch. Line A and the legacy equity CSV are not write targets.
"""

PRODUCTION_DEPLOY = "NO"
LIVE_TRADING = "NO"
FORMAL_SCORING_CHAIN = "NOT_ON_FORMAL_SCORING_CHAIN"
EQUITY_V21_DUAL_WRITE_DEFAULT = "OFF"
LIVE_FUNDING_INGEST = "OFF"
PASS_LINE_FREEZE_BY_THIS_PACKAGE = "NO"
LINE_A_REWRITE = "NO"
LEGACY_EQUITY_REWRITE = "NO"

__all__ = [
    "EQUITY_V21_DUAL_WRITE_DEFAULT",
    "FORMAL_SCORING_CHAIN",
    "LEGACY_EQUITY_REWRITE",
    "LINE_A_REWRITE",
    "LIVE_FUNDING_INGEST",
    "LIVE_TRADING",
    "PASS_LINE_FREEZE_BY_THIS_PACKAGE",
    "PRODUCTION_DEPLOY",
]
