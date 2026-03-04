import json
import traceback
from uuid import UUID, uuid4
from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException, Body
from app.system.idempotency import get_idempotency, request_hash, try_start_idempotency, finish_idempotency_ok, finish_idempotency_error
from app.ops.kill_switch import get_kill_switch_state
from sqlalchemy import text

from app.db import async_session

router = APIRouter(prefix="/commands", tags=["commands"])


@router.post("")
async def create_command(
    payload: Dict[str, Any] = Body(default_factory=dict),
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
):
    enabled, _source = get_kill_switch_state()
    if enabled:
        raise HTTPException(status_code=423, detail="Kill switch enabled")

    # --- PHASE310_IDEMPOTENCY_KEYS ---
    idem_key = x_idempotency_key
    if idem_key:
        req_hash = request_hash(payload)
        st = await try_start_idempotency(idem_key, req_hash)
        if st == "EXISTS_DIFF":
            raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_CONFLICT", "key": idem_key})
        if st == "EXISTS_SAME":
            row = await get_idempotency(idem_key)
            if row and row.get("status") == "DONE" and row.get("response") is not None:
                r = row["response"]
                return {"id": r["id"], "idempotency_key": r["idempotency_key"], "status": r["status"]}
            if row and row.get("status") == "IN_PROGRESS":
                raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_IN_PROGRESS", "key": idem_key})

    """
    Idempotent command submit:
    - If idempotency_key exists -> return existing id
    - Else insert a new command row with status PENDING
    """
    payload_json = json.dumps(payload, ensure_ascii=True)

    async with async_session() as db:
        row = (
            await db.execute(
                text("select id from commands where idempotency_key=:k"),
                {"k": x_idempotency_key},
            )
        ).first()
        if row:
            resp = {"id": str(row[0]), "idempotency_key": x_idempotency_key, "status": "ACCEPTED"}
            if idem_key:
                await finish_idempotency_ok(idem_key, resp)
            return resp

        cmd_id = uuid4()

        try:
            await db.execute(
                text(
                    "insert into commands(id, idempotency_key, payload, status) "
                    "values ((:id)::uuid, :k, (:p)::jsonb, 'PENDING')"
                ),
                {"id": str(cmd_id), "k": x_idempotency_key, "p": payload_json},
            )
            await db.commit()
        except Exception as e:
            # show the real DB error in logs
            print("create_command insert failed:", repr(e), flush=True)
            traceback.print_exc()
            await db.rollback()

            # if a concurrent insert won, return it
            row2 = (
                await db.execute(
                    text("select id from commands where idempotency_key=:k"),
                    {"k": x_idempotency_key},
                )
            ).first()
            if row2:
                resp = {"id": str(row2[0]), "idempotency_key": x_idempotency_key, "status": "ACCEPTED"}
                if idem_key:
                    await finish_idempotency_ok(idem_key, resp)
                return resp
            raise HTTPException(status_code=500, detail="db insert failed")

        resp = {"id": str(cmd_id), "idempotency_key": x_idempotency_key, "status": "ACCEPTED"}
        if idem_key:
            await finish_idempotency_ok(idem_key, resp)
        return resp


def _is_uuid(s: str) -> bool:
    if not s or len(s) != 36:
        return False
    try:
        UUID(s)
        return True
    except (ValueError, TypeError):
        return False


@router.get("/{command_id}")
async def get_command(command_id: str):
    """
    Step 8 (A-route): Request observability
    - The POST /commands returns an `id` (request_id) that is the `commands.id`
    - This endpoint lets you query status/result by that id
    - Non-UUID ids (e.g. domain-command ids like flaky-xxx) return 404 with deprecation hint.
    """
    if not _is_uuid(command_id):
        raise HTTPException(
            status_code=404,
            detail="Deprecated. Use /domain-commands/{id}",
        )
    async with async_session() as db:
        row = (
            await db.execute(
                text(
                    "select id, idempotency_key, status, payload, error, created_at, updated_at "
                    "from commands where id = (:id)::uuid"
                ),
                {"id": command_id},
            )
        ).first()

        if not row:
            raise HTTPException(status_code=404, detail="command not found")

        return {
            "id": str(row[0]),
            "idempotency_key": row[1],
            "status": row[2],
            "payload": row[3],
            "error": row[4],
            "created_at": row[5].isoformat() if row[5] else None,
            "updated_at": row[6].isoformat() if row[6] else None,
        }
