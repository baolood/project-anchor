from __future__ import annotations

from typing import Dict

_STATE: Dict[str, bool] = {"enabled": False}

def is_enabled() -> bool:
    return _STATE["enabled"]

def set_enabled(v: bool) -> None:
    _STATE["enabled"] = bool(v)
