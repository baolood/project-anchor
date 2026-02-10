"""
Action execution protocol: input command dict, output ActionOutput.
Unified for all command types (NOOP/FAIL/FLAKY) and pipeline (validate → execute → postprocess).
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypedDict


class ActionOutput(TypedDict, total=False):
    ok: bool
    result: Optional[Dict[str, Any]]
    error: Optional[Any]  # dict | str | None


class Action(ABC):
    """Pluggable handler for a domain command type. run() must not raise."""

    name: str = ""
    steps: Optional[List[Any]] = None  # custom pipeline steps; None = use default [Validate, Execute, Postprocess]

    def run_core(self, command: Dict[str, Any]) -> ActionOutput:
        """Core business logic. Default delegates to run(); override for pipeline ExecuteStep."""
        return self.run(command)

    @abstractmethod
    def run(self, command: Dict[str, Any]) -> ActionOutput:
        """
        Execute the action. Must not raise.
        Returns: {"ok": bool, "result": dict|None, "error": dict|str|None}
        """
        pass
