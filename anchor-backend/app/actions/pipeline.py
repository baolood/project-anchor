"""
Action Pipeline: run actions through steps (validate → execute → postprocess).
StepOutput = ActionOutput; any step returning ok=False stops the pipeline.
"""
from typing import Any, Dict, List, Optional

from app.actions.protocol import ActionOutput

# StepOutput is ActionOutput (keep simple)
StepOutput = ActionOutput


class Step:
    """Step protocol: name, run(ctx, command_dict, prev_output) -> ActionOutput."""

    name: str = ""

    def run(
        self,
        ctx: Any,
        command_dict: Dict[str, Any],
        prev_output: Optional[ActionOutput] = None,
    ) -> ActionOutput:
        """Execute step. prev_output is the output of the previous step (None for first)."""
        raise NotImplementedError


def run_pipeline(
    steps: List[Step],
    ctx: Any,
    command_dict: Dict[str, Any],
) -> ActionOutput:
    """
    Run steps in order. On first ok=False return immediately.
    Exceptions → ok=False, error={code: "STEP_EXCEPTION", step: name, message: str(e)}.
    """
    out: Optional[ActionOutput] = None
    for step in steps:
        try:
            out = step.run(ctx, command_dict, out)
        except Exception as e:
            return {
                "ok": False,
                "result": None,
                "error": {
                    "code": "STEP_EXCEPTION",
                    "step": getattr(step, "name", "?"),
                    "message": str(e),
                },
            }
        if out is None or not out.get("ok"):
            return out if out is not None else {
                "ok": False,
                "result": None,
                "error": {"code": "STEP_FAILED", "message": "step returned no output"},
            }
    return out or {"ok": False, "result": None, "error": None}


def run_action_with_pipeline(
    action: Any,
    ctx: Any,
    command_dict: Dict[str, Any],
    default_steps_fn: Any,
) -> ActionOutput:
    """
    Run action via pipeline. If action has no custom steps, use default_steps_fn(action, ctx).
    """
    steps = getattr(action, "steps", None)
    if steps is None:
        steps = default_steps_fn(action, ctx)
    return run_pipeline(steps, ctx, command_dict)
