from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from sqlalchemy import text

from app.db import async_session


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def request_hash(payload: Any) -> str:
    s = _stable_json(payload)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


async def get_idempotency(key: str) -> Optional[dict]:
    async with async_session() as s:
        r = await s.execute(
            text(
                """
                SELECT key, request_hash, response, status
                FROM idempotency_keys
                WHERE key=:key
                """
            ),
            {"key": key},
        )
        row = r.mappings().first()
        return dict(row) if row else None


async def try_start_idempotency(key: str, req_hash: str) -> str:
    async with async_session() as s:
        async with s.begin():
            r = await s.execute(
                text(
                    """
                    SELECT request_hash
                    FROM idempotency_keys
                    WHERE key=:key
                    FOR UPDATE
                    """
                ),
                {"key": key},
            )
            row = r.first()
            if row:
                existing = row[0]
                return "EXISTS_SAME" if existing == req_hash else "EXISTS_DIFF"

            await s.execute(
                text(
                    """
                    INSERT INTO idempotency_keys (key, request_hash, status)
                    VALUES (:key, :request_hash, 'IN_PROGRESS')
                    """
                ),
                {"key": key, "request_hash": req_hash},
            )
            return "STARTED"


async def finish_idempotency_ok(key: str, response_obj: Any) -> None:
    async with async_session() as s:
        async with s.begin():
            await s.execute(
                text(
                    """
                    UPDATE idempotency_keys
                    SET response=CAST(:resp AS jsonb),
                        status='DONE',
                        updated_at=NOW()
                    WHERE key=:key
                    """
                ),
                {"key": key, "resp": _stable_json(response_obj)},
            )


async def finish_idempotency_error(key: str, response_obj: Any) -> None:
    async with async_session() as s:
        async with s.begin():
            await s.execute(
                text(
                    """
                    UPDATE idempotency_keys
                    SET response=CAST(:resp AS jsonb),
                        status='ERROR',
                        updated_at=NOW()
                    WHERE key=:key
                    """
                ),
                {"key": key, "resp": _stable_json(response_obj)},
            )
