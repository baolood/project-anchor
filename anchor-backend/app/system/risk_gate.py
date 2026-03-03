from __future__ import annotations

import os
from typing import Any, Dict, Tuple

from app.runtime.kill_switch import is_enabled
from app.system.risk_state import get_risk_state


def _mode() -> str:
    return (os.getenv("RISK_GATE_MODE", "off") or "off").strip().lower()

## PHASE38_RISK_STATE_CONFIG
async def _risk_cfg(key: str) -> dict:
    try:
        v = await get_risk_state(key)
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}

async def _risk_bool(key: str, default: bool = False) -> bool:
    cfg = await _risk_cfg(key)
    v = cfg.get("enabled", default)
    return bool(v)




async def check_create_command(payload: Dict[str, Any], idem_key: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Minimal Risk Gate for Phase 3.1
    - off: always allow
    - deny_all: always deny (acceptance test)
    - on: currently allow (reserved for future risk rules)
    """
    # PHASE38: optional global gate (persisted in risk_state)
    cfg_global = await _risk_cfg("risk_gate_global")
    if cfg_global.get("enabled") is True:
        reason = cfg_global.get("reason") or "risk_gate_global.enabled=true"
        return False, {"ok": False, "code": "RISK_GATE_GLOBAL", "reason": reason}

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
