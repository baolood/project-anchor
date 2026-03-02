from __future__ import annotations
import json
from typing import Any, Optional, Dict
from sqlalchemy import text
from app.db import async_session

async def get_risk_state(key: str) -> Optional[Dict[str, Any]]:
    async with async_session() as s:
        r = await s.execute(text("SELECT value FROM risk_state WHERE key=:k"), {"k": key})
        row = r.first()
        return row[0] if row else None

async def set_risk_state(key: str, value: Dict[str, Any], actor: Optional[str] = None, note: Optional[str] = None) -> None:
    js = json.dumps(value)
    async with async_session() as s:
        async with s.begin():
            await s.execute(text("""
                INSERT INTO risk_state (key, value, updated_at)
                VALUES (:k, CAST(:v AS jsonb), NOW())
                ON CONFLICT (key) DO UPDATE SET value = CAST(:v AS jsonb), updated_at = NOW()
            """), {"k": key, "v": js})
            # append history (optional)
            await s.execute(text("""
                INSERT INTO risk_state_history (key, value, actor, note)
                VALUES (:k, CAST(:v AS jsonb), :actor, :note)
            """), {"k": key, "v": js, "actor": actor, "note": note})
