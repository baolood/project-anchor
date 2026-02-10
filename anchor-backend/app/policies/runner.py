"""
Run policy pipeline; first block wins. Exceptions => allow (do not kill command).
"""
from typing import Any, Dict, List, Optional, Tuple

from app.policies.protocol import Policy, PolicyDecision


async def run_policies(
    policies: List[Policy],
    ctx: Any,
    command_dict: Dict[str, Any],
    engine: Any,
) -> Tuple[bool, Optional[PolicyDecision]]:
    """
    Run each policy in order. First allowed=False returns (False, decision).
    Any exception in policy.check => treat as allow (True, None).
    """
    if not policies or engine is None:
        return True, None
    for policy in policies:
        try:
            decision = await policy.check(ctx, command_dict, engine)
        except Exception:
            return True, None
        if not decision.get("allowed", True):
            return False, decision
    return True, None
