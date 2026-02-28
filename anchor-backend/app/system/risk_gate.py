from __future__ import annotations

import os
from typing import Any, Dict, Tuple

from app.runtime.kill_switch import is_enabled


def _mode() -> str:
    return (os.getenv("RISK_GATE_MODE", "off") or "off").strip().lower()


def check_create_command(payload: Dict[str, Any], idem_key: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Minimal Risk Gate for Phase 3.1
    - off: always allow
    - deny_all: always deny (acceptance test)
    - on: currently allow (reserved for future risk rules)
    """
    # Runtime Kill Switch (Phase 3.2)
    if is_enabled():
        return False, {
            "ok": False,
            "code": "KILL_SWITCH_ON",
            "reason": "runtime kill switch enabled",
        }

    mode = _mode()
    if mode == "deny_all":
        return False, {
            "ok": False,
            "code": "RISK_GATE_DENY",
            "reason": "RISK_GATE_MODE=deny_all",
            "meta": {
                "mode": mode,
                "idempotency_key": idem_key,
            },
        }

    # mode == off/on default allow
    return True, {"ok": True, "meta": {"mode": mode}}
