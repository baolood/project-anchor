"""
Default pipeline steps: validate → execute → postprocess.
"""
from typing import Any, Dict, List, Optional

from app.actions.context import ActionContext
from app.actions.pipeline import Step
from app.actions.protocol import ActionOutput


class ValidateStep(Step):
    """Ensure command has id, type; payload is dict; attempt is int."""

    name = "validate"

    def run(
        self,
        ctx: Any,
        command_dict: Dict[str, Any],
        prev_output: Optional[ActionOutput] = None,
    ) -> ActionOutput:
        if "id" not in command_dict:
            command_dict["id"] = getattr(ctx, "command_id", "") or ""
        if "type" not in command_dict:
            command_dict["type"] = getattr(ctx, "cmd_type", "") or ""
        if not isinstance(command_dict.get("payload"), dict):
            command_dict["payload"] = {}
        try:
            command_dict["attempt"] = int(command_dict.get("attempt", 0) or 0)
        except (TypeError, ValueError):
            command_dict["attempt"] = 0
        return {"ok": True, "result": None, "error": None}


class ExecuteStep(Step):
    """Run action core logic (run_core)."""

    name = "execute"

    def __init__(self, action: Any):
        self._action = action

    def run(
        self,
        ctx: Any,
        command_dict: Dict[str, Any],
        prev_output: Optional[ActionOutput] = None,
    ) -> ActionOutput:
        action = self._action
        run_core = getattr(action, "run_core", None) or getattr(action, "_run_core", None)
        if run_core is None:
            return {"ok": False, "result": None, "error": {"code": "NO_RUN_CORE", "message": "action has no run_core"}}
        return run_core(command_dict)


class PostprocessStep(Step):
    """If ok=True and result is dict, add ts if missing; do not break existing result."""

    name = "postprocess"

    def run(
        self,
        ctx: Any,
        command_dict: Dict[str, Any],
        prev_output: Optional[ActionOutput] = None,
    ) -> ActionOutput:
        if prev_output is None or not prev_output.get("ok"):
            return prev_output or {"ok": False, "result": None, "error": None}
        result = prev_output.get("result")
        if not isinstance(result, dict):
            return prev_output
        now_ts = getattr(ctx, "now_ts", None)
        if now_ts is not None and "ts" not in result:
            result = {**result, "ts": now_ts}
            return {**prev_output, "result": result}
        return prev_output


def default_pipeline_steps(action: Any, ctx: ActionContext) -> List[Step]:
    """Default steps when action does not define custom steps."""
    return [
        ValidateStep(),
        ExecuteStep(action),
        PostprocessStep(),
    ]
