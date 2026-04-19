import os
from typing import Dict, Any
from app.system.risk_state import get_risk_state


## PHASE38_POLICY_LIMITS_FROM_RISK_STATE
async def _policy_limits() -> dict:
    try:
        v = await get_risk_state("policy_limits")
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}

def _lim_num(lims: dict, k: str, default: float):
    try:
        v = lims.get(k, default)
        return float(v)
    except Exception:
        return float(default)


MAX_SINGLE_TRADE_RISK_USD = float(os.getenv("MAX_SINGLE_TRADE_RISK_USD", "100"))


class RiskDecision:
    def __init__(self, allowed: bool, reason: str = ""):
        self.allowed = allowed
        self.reason = reason


class RiskPolicyEngine:

    @staticmethod
    def evaluate_single_trade(payload: Dict[str, Any]) -> RiskDecision:
        """
        payload must contain:
        - notional_usd
        """

        notional = float(payload.get("notional_usd", 0))

        if notional > MAX_SINGLE_TRADE_RISK_USD:
            return RiskDecision(
                allowed=False,
                reason=f"SINGLE_TRADE_RISK_EXCEEDED:{notional}>{MAX_SINGLE_TRADE_RISK_USD}"
            )

        return RiskDecision(allowed=True)