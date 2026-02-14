"""
Kill switch: env (priority) or Redis. Never raises; failures return (False, "none").
"""
import os
from typing import Optional, Tuple

REDIS_KEY = "anchor:kill_switch"
_redis_client: Optional[object] = None


def _get_redis_client():
    """Lazy init redis client. Returns None on failure."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        _redis_client = redis.Redis.from_url(url, decode_responses=True)
        return _redis_client
    except Exception as e:
        print(f"[kill_switch] redis init failed: {e}", flush=True)
        return None


def get_kill_switch_state() -> Tuple[bool, str]:
    """Returns (enabled, source). Priority: env > redis > none."""
    if (os.getenv("ANCHOR_KILL_SWITCH") or "").strip() == "1":
        return (True, "env")
    try:
        r = _get_redis_client()
        if r is not None:
            val = r.get(REDIS_KEY)
            if val == "1":
                return (True, "redis")
    except Exception as e:
        print(f"[kill_switch] redis get failed: {e}", flush=True)
    return (False, "none")


def set_kill_switch_redis(enabled: bool) -> bool:
    """Set redis key. Returns True on success, False on failure. Never raises."""
    try:
        r = _get_redis_client()
        if r is not None:
            r.set(REDIS_KEY, "1" if enabled else "0")
            return True
    except Exception as e:
        print(f"[kill_switch] redis set failed: {e}", flush=True)
    return False
