import os
from typing import Dict, Any

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
