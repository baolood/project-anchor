"""AFFL V2 Gate A protective risk boundary.

DEPLOY is NO. Live trading is NO-GO. This package does not place orders.
"""

from affl_v2.c6_protective_boundary import (
    DEPLOY,
    FEE_BPS,
    FIXED_ADVERSE_STOP_BPS,
    LIVE_TRADING,
    MAX_RISK_PCT,
    SCHEMA_VERSION,
    SIZE_POLICY_ID,
    SLIPPAGE_BPS,
    STOP_RULE_ID,
    STRATEGY_VERSION,
    ProtectiveBoundaryError,
    ProtectiveRiskBook,
    adverse_fill_price,
    frozen_stop_price,
    max_allowed_quantity,
    risk_per_unit,
)

__all__ = [
    "DEPLOY",
    "FEE_BPS",
    "FIXED_ADVERSE_STOP_BPS",
    "LIVE_TRADING",
    "MAX_RISK_PCT",
    "SCHEMA_VERSION",
    "SIZE_POLICY_ID",
    "SLIPPAGE_BPS",
    "STOP_RULE_ID",
    "STRATEGY_VERSION",
    "ProtectiveBoundaryError",
    "ProtectiveRiskBook",
    "adverse_fill_price",
    "frozen_stop_price",
    "max_allowed_quantity",
    "risk_per_unit",
]
