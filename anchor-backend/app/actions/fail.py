from typing import Any, Dict

from app.actions.protocol import Action, ActionOutput


class FailAction(Action):
    name = "FAIL"

    def run(self, command: Dict[str, Any]) -> ActionOutput:
        return {
            "ok": False,
            "result": None,
            "error": {"code": "INTENTIONAL_FAIL", "message": "fail command for e2e test"},
        }
