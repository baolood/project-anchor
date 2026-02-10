"""
Action execution protocol: input command dict, output ActionOutput.
Unified for all command types (NOOP/FAIL/FLAKY) and future pipeline (validate → execute → postprocess).
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypedDict


class ActionOutput(TypedDict, total=False):
    ok: bool
    result: Optional[Dict[str, Any]]
    error: Optional[Any]  # dict | str | None


class Action(ABC):
    """Pluggable handler for a domain command type. run() must not raise."""

    name: str = ""

    @abstractmethod
    def run(self, command: Dict[str, Any]) -> ActionOutput:
        """
        Execute the action. Must not raise.
        Returns: {"ok": bool, "result": dict|None, "error": dict|str|None}
        """
        pass
