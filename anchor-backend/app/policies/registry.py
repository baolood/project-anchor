"""
Registry of policies. init_policies() is idempotent; get_policies() for runner.
"""
from typing import List

from app.policies.builtins import CooldownAfterFailPolicy, IdempotencyPolicy, RateLimitPolicy
from app.policies.protocol import Policy

POLICIES: List[Policy] = []
_INIT_DONE = False


def register(policy: Policy) -> None:
    if policy and getattr(policy, "name", None):
        POLICIES.append(policy)


def get_policies() -> List[Policy]:
    return list(POLICIES)


def init_policies() -> None:
    """Register built-in policies. Idempotent."""
    global _INIT_DONE
    if _INIT_DONE:
        return
    register(IdempotencyPolicy())
    register(RateLimitPolicy())
    register(CooldownAfterFailPolicy())
    _INIT_DONE = True
