"""
Registry of domain command actions. Worker looks up by command type and calls action.run().
init_actions() is idempotent: repeated calls do not duplicate or overwrite with different instances.
"""
from typing import Any, Dict, Optional

from app.actions.protocol import Action
from app.actions.noop import NoopAction
from app.actions.fail import FailAction
from app.actions.flaky import FlakyAction
from app.actions.quote import QuoteAction

ACTIONS: Dict[str, Action] = {}
_INIT_DONE = False


def register(action: Action) -> None:
    if action.name:
        ACTIONS[action.name.upper()] = action


def get_action(cmd_type: str) -> Optional[Action]:
    if not cmd_type:
        return None
    return ACTIONS.get((cmd_type or "").strip().upper())


def init_actions() -> None:
    """Register NOOP / FAIL / FLAKY. Idempotent: safe to call multiple times."""
    global _INIT_DONE
    if _INIT_DONE:
        return
    register(NoopAction())
    register(FailAction())
    register(FlakyAction())
    register(QuoteAction())
    _INIT_DONE = True
