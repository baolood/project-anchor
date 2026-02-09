# app/core/state.py
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any

import redis


@dataclass
class EngineState:
    mode: str = "STOPPED"          # STOPPED | RUNNING | COOLDOWN
    reason: str = ""
    exec_count: int = 0
    cooldown_until: Optional[int] = None  # unix timestamp (seconds) or None

    def to_dict(self) -> Dict[str, str]:
        # Redis HSET 不接受 None，所以这里统一转成字符串
        return {
            "mode": self.mode,
            "reason": self.reason,
            "exec_count": str(int(self.exec_count)),
            "cooldown_until": "" if self.cooldown_until is None else str(int(self.cooldown_until)),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EngineState":
        mode = d.get("mode") or "STOPPED"
        reason = d.get("reason") or ""
        exec_count_raw = d.get("exec_count") or 0
        cooldown_raw = d.get("cooldown_until") or ""

        try:
            exec_count = int(exec_count_raw)
        except Exception:
            exec_count = 0

        cooldown_until: Optional[int]
        if cooldown_raw in ("", None):
            cooldown_until = None
        else:
            try:
                cooldown_until = int(cooldown_raw)
            except Exception:
                cooldown_until = None

        return cls(mode=mode, reason=reason, exec_count=exec_count, cooldown_until=cooldown_until)

    def is_in_cooldown(self) -> bool:
        return self.cooldown_until is not None and int(time.time()) < int(self.cooldown_until)


class StateStore:
    def __init__(self, r: redis.Redis, prefix: str = "anchor:state:"):
        self.r = r
        self.prefix = prefix

    def _key(self, user_id: str) -> str:
        return f"{self.prefix}{user_id}"

    def get(self, user_id: str) -> EngineState:
        data = self.r.hgetall(self._key(user_id))
        if not data:
            return EngineState()
        return EngineState.from_dict(data)

    def set(self, user_id: str, state: EngineState) -> None:
        self.r.hset(self._key(user_id), mapping=state.to_dict())


# ✅ 关键：保证 routes.py 可以 import 到这两个名字
State = EngineState

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
_redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
store = StateStore(_redis)
