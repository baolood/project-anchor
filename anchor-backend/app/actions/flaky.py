from typing import Any, Dict

from app.actions.protocol import Action, ActionOutput


class FlakyAction(Action):
    name = "FLAKY"

    def run_core(self, command: Dict[str, Any]) -> ActionOutput:
        attempt = int(command.get("attempt") or 0)
        if attempt <= 1:
            return {
                "ok": False,
                "result": None,
                "error": {"code": "FLAKY_FAIL", "message": "flaky fails on attempt<=1"},
            }
        payload = command.get("payload") or {}
        return {
            "ok": True,
            "result": {"ok": True, "type": "flaky", "attempt": attempt, "payload": payload},
            "error": None,
        }

    def run(self, command: Dict[str, Any]) -> ActionOutput:
        return self.run_core(command)
