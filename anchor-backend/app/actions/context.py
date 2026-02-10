"""
Lightweight execution context for domain command actions.
Provides normalized fields so actions do not have to unpack the raw row.
"""
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ActionContext:
    """Normalized view of a picked domain command for Action.run()."""

    now_ts: int
    command_id: str
    cmd_type: str
    attempt: int
    payload: Dict[str, Any]
    raw: Dict[str, Any]

    def to_command_dict(self) -> Dict[str, Any]:
        """Dict suitable for action.run(command). Preserves id, type, attempt, payload."""
        return {
            "id": self.command_id,
            "type": self.cmd_type,
            "attempt": self.attempt,
            "payload": self.payload,
            **{k: v for k, v in self.raw.items() if k not in ("id", "type", "attempt", "payload")},
        }
