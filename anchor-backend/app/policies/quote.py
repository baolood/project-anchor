"""
QUOTE-specific policy: max notional cap. Default POLICY_QUOTE_MAX_NOTIONAL=0 (no limit).
"""
import os
from typing import Any, Dict

from app.policies.protocol import Policy, PolicyDecision


class QuoteNotionalPolicy(Policy):
    """
    For commands of type QUOTE only: block if payload.notional > POLICY_QUOTE_MAX_NOTIONAL.
    Default max=0 means no limit (allow all).
    """

    name = "quote_notional"

    async def check(
        self,
        ctx: Any,
        command_dict: Dict[str, Any],
        engine: Any,
    ) -> PolicyDecision:
        cmd_type = (command_dict.get("type") or "").strip().upper()
        if cmd_type != "QUOTE":
            return {"allowed": True, "code": "OK", "message": "ok", "detail": None}
        max_notional = int(os.environ.get("POLICY_QUOTE_MAX_NOTIONAL", "0"))
        if max_notional <= 0:
            return {"allowed": True, "code": "OK", "message": "ok", "detail": None}
        payload = command_dict.get("payload") or {}
        try:
            notional = float(payload.get("notional", 0))
        except (TypeError, ValueError):
            notional = 0.0
        if notional > max_notional:
            return {
                "allowed": False,
                "code": "QUOTE_NOTIONAL_TOO_LARGE",
                "message": f"notional {notional} exceeds max {max_notional}",
                "detail": {"type": cmd_type, "policy": self.name, "notional": notional, "max": max_notional},
            }
        return {"allowed": True, "code": "OK", "message": "ok", "detail": None}
