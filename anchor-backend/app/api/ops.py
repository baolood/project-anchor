from __future__ import annotations

from typing import Any, Dict, List, Optional

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
    return {"enabled": bool(kill_is_enabled())}

# == PHASE34_OPS_AUDIT ==
@router.get("/audit")
async def list_ops_audit(limit: int = Query(50, ge=1, le=200)):
    async with async_session() as s:
        r = await s.execute(text("""
            SELECT id, ts, actor, action, detail
            FROM ops_audit
            ORDER BY ts DESC
            LIMIT :limit
        """), {"limit": int(limit)})
        rows = r.fetchall()

    out: List[Dict[str, Any]] = []
    for (rid, ts, actor, action, detail) in rows:
        out.append({
            "id": str(rid),
            "action": action,
            "payload": detail,
            "created_at": ts.isoformat() if ts else None,
            "actor": actor,
        })
    return out
