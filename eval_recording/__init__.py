"""Gate B evaluation recording contracts.

This package is scaffolding for ANCHOR_EVAL_RECORDING_INFRA_SPEC_V1.
It is not on the formal scoring chain, and it does not write Official
ledger files. Wire-up into the Official writer waits on Founder EXECUTE.

See docs/ANCHOR_EVAL_RECORDING_INFRA_SPEC_V1.md.
"""

from eval_recording.boundaries import (
    FORMAL_SCORING_CHAIN,
    FOUNDATION_DOC,
    LIVE_TRADING,
    PASS_LINE_THRESHOLDS_CHANGED,
    PRODUCTION_DEPLOY,
    T0_FROZEN,
)

__all__ = [
    "FORMAL_SCORING_CHAIN",
    "FOUNDATION_DOC",
    "LIVE_TRADING",
    "PASS_LINE_THRESHOLDS_CHANGED",
    "PRODUCTION_DEPLOY",
    "T0_FROZEN",
]
