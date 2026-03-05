from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import hashlib
import json


def actor_from_request(request) -> str:
    key = request.headers.get("X-ANCHOR-KEY")
    if not key:
        return "anon"
    h = hashlib.sha256(key.encode()).hexdigest()[:8]
    return f"key:{h}"


async def audit(
    session: AsyncSession,
    action: str,
    actor: str,
    detail: Dict[str, Any],
):
    await session.execute(
        text("""
        insert into ops_audit(action, actor, detail)
        values (:action, :actor, CAST(:detail AS jsonb))
        """),
        {
            "action": action,
            "actor": actor,
            "detail": json.dumps(detail, ensure_ascii=False),
        },
    )
