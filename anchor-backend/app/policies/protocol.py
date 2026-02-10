"""
Policy protocol: check(ctx, command_dict) -> PolicyDecision.
Used by runner before running action pipeline; block => mark_failed + POLICY_BLOCK event.
"""
from typing import Any, Dict, Optional, TypedDict


class PolicyDecision(TypedDict, total=False):
    allowed: bool
    code: str
    message: str
    detail: Optional[Dict[str, Any]]


class Policy:
    """Pluggable guardrail. check() must not raise; on exception runner treats as allow."""

    name: str = ""

    async def check(
        self,
        ctx: Any,
        command_dict: Dict[str, Any],
        engine: Any,
    ) -> PolicyDecision:
        """
        Return allowed=True to pass; allowed=False to block this command.
        Must not raise; exceptions are treated as allow by run_policies.
        """
        raise NotImplementedError
