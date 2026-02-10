from typing import Any, Dict

from app.actions.protocol import Action, ActionOutput


class NoopAction(Action):
    name = "NOOP"

    def run(self, command: Dict[str, Any]) -> ActionOutput:
        payload = command.get("payload") or {}
        return {
            "ok": True,
            "result": {"ok": True, "type": "noop", "payload": payload},
            "error": None,
        }
