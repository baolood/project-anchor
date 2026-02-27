from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Body, Query
from sqlalchemy import text

from app.db import async_session
from app.runtime.kill_switch import is_enabled as kill_is_enabled, set_enabled as kill_set_enabled

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/kill-switch")
async def get_kill_switch():
    return {"enabled": bool(kill_is_enabled())}


@router.post("/kill-switch")
async def set_kill_switch(enabled: bool = Body(..., embed=True)):
    kill_set_enabled(bool(enabled))
    # Phase 3.5: write to ops_audit when kill-switch is toggled
    async with async_session() as s:
        async with s.begin():
            await s.execute(
                text("""
                    INSERT INTO ops_audit (id, ts, actor, action, detail)
                    VALUES (gen_random_uuid(), NOW(), :actor, :action, CAST(:detail AS jsonb))
                """),
                {
                    "actor": "api",
                    "action": "KILL_SWITCH_SET",
                    "detail": '{"enabled": %s}' % ("true" if enabled else "false"),
                },
            )
    return {"enabled": bool(kill_is_enabled())}


@router.get("/audit")
async def list_ops_audit(limit: int = Query(50, ge=1, le=200)):
    async with async_session() as s:
        r = await s.execute(
            text("""
                SELECT id, ts, actor, action, detail
                FROM ops_audit
                ORDER BY ts DESC
                LIMIT :limit
            """),
            {"limit": int(limit)},
        )
        rows = r.fetchall()

    out: List[Dict[str, Any]] = []
    for (rid, ts_val, actor_val, action_val, detail_val) in rows:
        out.append({
            "id": str(rid),
            "action": action_val,
            "payload": detail_val if isinstance(detail_val, dict) else (detail_val or {}),
            "created_at": ts_val.isoformat() if getattr(ts_val, "isoformat", None) else str(ts_val) if ts_val else None,
            "actor": actor_val,
        })
    return out
