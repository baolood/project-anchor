"""
Built-in policies: idempotency, rate limit, cooldown. Defaults set so e2e does not trigger.
"""
import os
import time
from typing import Any, Dict

from sqlalchemy import text

from app.policies.protocol import Policy, PolicyDecision


class IdempotencyPolicy(Policy):
    """
    Same (command_id, attempt) may only receive MARK_* once.
    Query domain_events for existing MARK_DONE or MARK_FAILED for this command_id + attempt.
    """

    name = "idempotency"

    async def check(
        self,
        ctx: Any,
        command_dict: Dict[str, Any],
        engine: Any,
    ) -> PolicyDecision:
        command_id = (command_dict.get("id") or "").strip() or (getattr(ctx, "command_id", "") or "")
        attempt = int(command_dict.get("attempt", 0) or getattr(ctx, "attempt", 0) or 0)
        if not command_id:
            return {"allowed": True, "code": "OK", "message": "no command_id", "detail": None}
        try:
            async with engine.begin() as conn:
                r = await conn.execute(
                    text(
                        """
                        SELECT 1 FROM domain_events
                        WHERE command_id = :command_id AND attempt = :attempt
                          AND event_type IN ('MARK_DONE', 'MARK_FAILED')
                        LIMIT 1
                        """
                    ),
                    {"command_id": command_id, "attempt": attempt},
                )
                row = r.first()
            if row:
                return {
                    "allowed": False,
                    "code": "IDEMPOTENT_BLOCK",
                    "message": "terminal state already written for this attempt",
                    "detail": {"command_id": command_id, "attempt": attempt},
                }
            return {"allowed": True, "code": "OK", "message": "ok", "detail": None}
        except Exception as e:
            return {"allowed": True, "code": "OK", "message": f"check error (allow): {e}", "detail": None}


def _rate_limit_key(cmd_type: str) -> str:
    return f"POLICY_RATE_LIMIT_PER_MINUTE_{cmd_type.upper()}"


class RateLimitPolicy(Policy):
    """
    Per-type rate limit: max N PICKED per minute (from domain_events).
    Default 100000 so e2e does not trigger.
    """

    name = "rate_limit"

    async def check(
        self,
        ctx: Any,
        command_dict: Dict[str, Any],
        engine: Any,
    ) -> PolicyDecision:
        cmd_type = (command_dict.get("type") or "").strip().upper() or (getattr(ctx, "cmd_type", "") or "").strip().upper()
        if not cmd_type:
            return {"allowed": True, "code": "OK", "message": "ok", "detail": None}
        limit = int(os.environ.get(_rate_limit_key(cmd_type), os.environ.get("POLICY_RATE_LIMIT_PER_MINUTE", "100000")))
        if limit <= 0:
            return {"allowed": True, "code": "OK", "message": "ok", "detail": None}
        try:
            async with engine.begin() as conn:
                r = await conn.execute(
                    text(
                        """
                        SELECT COUNT(*) AS cnt FROM domain_events
                        WHERE event_type = 'PICKED'
                          AND (payload->>'type') IS NOT NULL
                          AND (payload->>'type') = :cmd_type
                          AND created_at > NOW() - INTERVAL '60 seconds'
                        """
                    ),
                    {"cmd_type": cmd_type},
                )
                row = r.mappings().first()
            cnt = int(row["cnt"]) if row else 0
            if cnt >= limit:
                return {
                    "allowed": False,
                    "code": "RATE_LIMIT",
                    "message": f"type {cmd_type} over limit ({cnt} >= {limit}/min)",
                    "detail": {"type": cmd_type, "count": cnt, "limit": limit},
                }
            return {"allowed": True, "code": "OK", "message": "ok", "detail": None}
        except Exception as e:
            return {"allowed": True, "code": "OK", "message": f"check error (allow): {e}", "detail": None}


class CooldownAfterFailPolicy(Policy):
    """
    After a fail for this type, do not pick same type for X seconds.
    Default POLICY_FAIL_COOLDOWN_SECONDS=0 so e2e does not trigger.
    """

    name = "cooldown_after_fail"

    async def check(
        self,
        ctx: Any,
        command_dict: Dict[str, Any],
        engine: Any,
    ) -> PolicyDecision:
        cooldown_sec = int(os.environ.get("POLICY_FAIL_COOLDOWN_SECONDS", "0"))
        if cooldown_sec <= 0:
            return {"allowed": True, "code": "OK", "message": "ok", "detail": None}
        cmd_type = (command_dict.get("type") or "").strip().upper() or (getattr(ctx, "cmd_type", "") or "").strip().upper()
        if not cmd_type:
            return {"allowed": True, "code": "OK", "message": "ok", "detail": None}
        try:
            async with engine.begin() as conn:
                r = await conn.execute(
                    text(
                        """
                        SELECT MAX(created_at) AS last_fail FROM domain_events
                        WHERE event_type IN ('ACTION_FAIL', 'MARK_FAILED')
                          AND (payload->>'type') = :cmd_type
                          AND created_at > NOW() - INTERVAL '1 hour'
                        """
                    ),
                    {"cmd_type": cmd_type},
                )
                row = r.mappings().first()
            if not row or row["last_fail"] is None:
                return {"allowed": True, "code": "OK", "message": "ok", "detail": None}
            last_fail = row["last_fail"]
            now_ts = time.time()
            try:
                last_ts = last_fail.timestamp()
            except Exception:
                return {"allowed": True, "code": "OK", "message": "ok", "detail": None}
            if (now_ts - last_ts) < cooldown_sec:
                return {
                    "allowed": False,
                    "code": "COOLDOWN_AFTER_FAIL",
                    "message": f"type {cmd_type} in cooldown ({cooldown_sec}s)",
                    "detail": {"type": cmd_type, "cooldown_seconds": cooldown_sec},
                }
            return {"allowed": True, "code": "OK", "message": "ok", "detail": None}
        except Exception as e:
            return {"allowed": True, "code": "OK", "message": f"check error (allow): {e}", "detail": None}
