"""
Risk lockout: execution guardrail. When lockout is active, block non-allowlist commands.
Used by worker to reject risk commands before execution.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Tuple

from sqlalchemy import text

RISK_LOCKOUT_ALLOWLIST = frozenset({"NOOP"})
RISK_LOCKOUT_BLOCK_REASON = "RISK_LOCKOUT_ACTIVE"
REDIS_LOCKOUT_CLEARED_KEY = "anchor:risk_lockout_cleared"
LOCKOUT_CLEAR_TTL_SEC = 3600
_redis_client: Any = None


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        _redis_client = redis.Redis.from_url(url, decode_responses=True)
        return _redis_client
    except Exception as e:
        print(f"[risk/lockout] redis init failed: {e}", flush=True)
        return None


def clear_lockout_redis() -> bool:
    """Set Redis key to clear lockout for TTL sec. Returns True on success."""
    try:
        r = _get_redis()
        if r is not None:
            r.set(REDIS_LOCKOUT_CLEARED_KEY, "1", ex=LOCKOUT_CLEAR_TTL_SEC)
            return True
    except Exception as e:
        print(f"[risk/lockout] clear_lockout_redis failed: {e}", flush=True)
    return False


def _is_lockout_cleared_redis() -> bool:
    """True if lockout was manually cleared via Redis. Never raises."""
    try:
        r = _get_redis()
        if r is not None and r.get(REDIS_LOCKOUT_CLEARED_KEY) == "1":
            return True
    except Exception:
        pass
    return False


def _risk_config() -> dict:
    """Risk env config. Never raises."""
    def _float(s: str | None, default: float) -> float:
        if not s or not str(s).strip():
            return default
        try:
            return float(str(s).strip())
        except ValueError:
            return default

    def _int(s: str | None, default: int) -> int:
        if not s or not str(s).strip():
            return default
        try:
            return int(str(s).strip())
        except ValueError:
            return default

    return {
        "lockout_loss_pct": _float(os.getenv("RISK_LOCKOUT_LOSS_PCT"), 2.0),
        "lockout_consec_losses": _int(os.getenv("RISK_LOCKOUT_CONSEC_LOSSES"), 3),
        "lockout_minutes": _int(os.getenv("RISK_LOCKOUT_MINUTES"), 1440),
    }


async def is_lockout_active(engine: Any) -> Tuple[bool, str, str]:
    """
    Returns (active, lockout_until_iso, lockout_reason).
    Uses same logic as /risk/state. Never raises.
    """
    if (os.getenv("RISK_LOCKOUT_DISABLE") or "").strip() == "1":
        return (False, "", "")
    if _is_lockout_cleared_redis():
        return (False, "", "")

    try:
        cfg = _risk_config()
        lockout_consec = cfg["lockout_consec_losses"]
        lockout_loss_pct = cfg["lockout_loss_pct"]
        lockout_min = cfg["lockout_minutes"]
        consecutive_losses = 0
        today_loss_pct = 0.0

        async with engine.begin() as conn:
            r = await conn.execute(
                text(
                    """
                    SELECT COUNT(*) AS cnt FROM domain_events
                    WHERE created_at::date = CURRENT_DATE
                      AND event_type = 'MARK_FAILED'
                    """
                )
            )
            row = r.mappings().first()
            if row and row.get("cnt"):
                consecutive_losses = int(row["cnt"] or 0)

        reasons = []
        if today_loss_pct >= lockout_loss_pct:
            reasons.append("daily_loss_pct")
        if consecutive_losses >= lockout_consec:
            reasons.append("consecutive_losses")

        if not reasons:
            return (False, "", "")

        until_dt = datetime.now(timezone.utc) + timedelta(minutes=lockout_min)
        lockout_until = until_dt.isoformat().replace("+00:00", "Z")
        reason = "; ".join(reasons)
        return (True, lockout_until, reason)
    except Exception as e:
        print(f"[risk/lockout] is_lockout_active failed: {e}", flush=True)
        return (False, "", "")


def is_command_allowed(cmd_type: str) -> bool:
    """True if command type is in allowlist (NOOP, view, reset/ack, etc.)."""
    t = (cmd_type or "").strip().upper()
    return t in RISK_LOCKOUT_ALLOWLIST
