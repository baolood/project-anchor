# app/core/audit.py
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from typing import List, Optional

from redis import Redis


def now_ts() -> int:
    return int(time.time())


@dataclass
class AuditEvent:
    ts: int
    user_id: str
    action: str            # "START" | "STOP" | "COOLDOWN" | ...
    from_mode: str
    to_mode: str
    reason: str = ""


class AuditLog:
    """
    Append-only audit log stored in Redis List.
    Key: audit:{user_id}
    Each item: JSON string of AuditEvent.
    """

    def __init__(self) -> None:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        # decode_responses=True -> returns str, and accepts str
        self.r = Redis.from_url(redis_url, decode_responses=True)

    def _key(self, user_id: str) -> str:
        return f"audit:{user_id}"

    def append(self, ev: AuditEvent, keep_last: int = 2000) -> None:
        key = self._key(ev.user_id)
        self.r.rpush(key, json.dumps(asdict(ev), ensure_ascii=False))
        # keep last N
        self.r.ltrim(key, -keep_last, -1)

    def tail(self, user_id: str, n: int = 50) -> List[dict]:
        key = self._key(user_id)
        items = self.r.lrange(key, max(0, -n), -1)
        out: List[dict] = []
        for s in items:
            try:
                out.append(json.loads(s))
            except Exception:
                out.append({"raw": s})
        return out
