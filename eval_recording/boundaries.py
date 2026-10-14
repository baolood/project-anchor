"""Hard boundaries for Gate B. These constants are the scoring-chain gate."""

FOUNDATION_DOC = "docs/ANCHOR_EVAL_RECORDING_INFRA_SPEC_V1.md"
DOC_ID = "ANCHOR_EVAL_RECORDING_INFRA_SPEC_V1"
GATE = "B"

# Parallel to the C6 risk-boundary PR. Not a scorer, not a freeze.
FORMAL_SCORING_CHAIN = "NOT_ON_FORMAL_SCORING_CHAIN"
T0_FROZEN = "NO"
OFFICIAL_PNL_SCORED = "NO"
OFFICIAL_PF_SCORED = "NO"
OFFICIAL_DD_SCORED = "NO"
PASS_LINE_THRESHOLDS_CHANGED = "NO"
LEGACY_OFFICIAL_LEDGER_MODIFIED = "NO"
PRODUCTION_DEPLOY = "NO"
LIVE_TRADING = "NO"
FOUNDER_EXECUTE_REQUIRED_FOR_WIRE_UP = "YES"

# C6 owns writer structs under this tree. Gate B does not edit them.
C6_OWNED_PREFIX = "affl-causal-successor/affl_v2/"
EDITS_AFFL_V2_TYPES = "NO"


class FormalScoreRefused(RuntimeError):
    """Raised when a caller asks this package to score the exam."""


def refuse_formal_score(kind: str) -> None:
    """Stop Official PnL / PF / DD scoring inside Gate B."""
    raise FormalScoreRefused(
        f"{kind} is {FORMAL_SCORING_CHAIN} until the Founder says so"
    )


def c6_additive_field_policy() -> dict[str, object]:
    """How Gate B and the C6 PR share names without sharing a struct edit."""
    return {
        "gate": GATE,
        "edits_affl_v2_types": EDITS_AFFL_V2_TYPES,
        "c6_owned_prefix": C6_OWNED_PREFIX,
        "trade_id_if_c6_touches_same_struct": "OPTIONAL_ADDITIVE",
        "version_gate": "recording_v1",
        "c6_owns_fields": (
            "preset_stop_price",
            "stop_rule_id",
            "risk_amount",
            "risk_pct",
            "HARD_STOP_EXIT",
        ),
        "gate_b_owns": (
            "trade_id scheme",
            "equity_v2_1 header including equity_at_open",
            "funding completeness and PRESENT-only net path",
            "MARK_RULE_C7_V1",
            "C9 authoritative source paths",
        ),
        "equity_at_open": (
            "Gate B column on the versioned equity file. "
            "C6 may copy the same semantic onto an entry event. "
            "That copy must not rewrite the legacy equity CSV or this header."
        ),
    }
