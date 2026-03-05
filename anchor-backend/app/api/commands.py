import hashlib
import json
import traceback
from uuid import UUID, uuid4
from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException, Body, Request
from app.system.idempotency import get_idempotency, request_hash, try_start_idempotency, finish_idempotency_ok, finish_idempotency_error
from app.ops.kill_switch import get_kill_switch_state
from app.system.risk_gate import check_create_command
from app.system.risk_state import get_risk_state
from sqlalchemy import text

from app.db import async_session

router = APIRouter(prefix="/commands", tags=["commands"])


# Observability: audit actions into ops_audit (no schema change)
def _actor_from_headers(request: Request) -> str:
    k = request.headers.get("X-ANCHOR-KEY", "")
    if not k:
        return "anon"
    h = hashlib.sha256(k.encode("utf-8")).hexdigest()[:8]
    return f"key:{h}"


async def _audit(action: str, actor: str, detail: dict) -> None:
    try:
        async with async_session() as sess:
            async with sess.begin():
                await sess.execute(
                    text(
                        "INSERT INTO ops_audit (actor, action, detail) VALUES (:actor, :action, CAST(:detail AS jsonb))"
                    ),
                    {"actor": actor, "action": action, "detail": json.dumps(detail, ensure_ascii=False)},
                )
    except Exception:
        pass


@router.post("")
async def create_command(
    request: Request,
    payload: Dict[str, Any] = Body(default_factory=dict),
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
):
    actor = _actor_from_headers(request)
    idem_key = x_idempotency_key

    # Kill switch
    enabled, _source = get_kill_switch_state()
    if enabled:
        await _audit(
            "COMMAND_CREATE_DENIED",
            actor,
            {"code": "KILL_SWITCH_ON", "reason": "kill switch enabled", "idempotency_key": idem_key},
        )
        raise HTTPException(status_code=423, detail="Kill switch enabled")

    # Risk gate (risk_gate_global, etc.)
    ok, gate_detail = await check_create_command(payload, idem_key)
    if not ok:
        await _audit(
            "COMMAND_CREATE_DENIED",
            actor,
            {
                "code": gate_detail.get("code", "RISK_GATE_DENY"),
                "reason": gate_detail.get("reason", ""),
                "idempotency_key": idem_key,
            },
        )
        raise HTTPException(status_code=403, detail=gate_detail)

    # Policy: MAX_SINGLE_TRADE_RISK (from risk_state policy_limits + payload.risk_usd)
    try:
        limits = await get_risk_state("policy_limits") or {}
        max_usd = float(limits.get("max_single_trade_risk_usd") or 0)
        if max_usd > 0:
            inner = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
            risk_usd = float(inner.get("risk_usd") or payload.get("risk_usd") or 0)
            if risk_usd > max_usd:
                reason = f"MAX_SINGLE_TRADE_RISK:{risk_usd}>{max_usd}"
                await _audit(
                    "COMMAND_CREATE_DENIED",
                    actor,
                    {"code": "MAX_SINGLE_TRADE_RISK", "reason": reason, "idempotency_key": idem_key},
                )
                raise HTTPException(
                    status_code=403,
                    detail={"code": "MAX_SINGLE_TRADE_RISK", "reason": reason},
                )
    except HTTPException:
        raise
    except Exception:
        pass

    # --- PHASE310_IDEMPOTENCY_KEYS ---
    if idem_key:
        req_hash = request_hash(payload)
        st = await try_start_idempotency(idem_key, req_hash)
        if st == "EXISTS_DIFF":
            await _audit("IDEMPOTENCY_CONFLICT", actor, {"idempotency_key": idem_key})
            raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_CONFLICT", "key": idem_key})
        if st == "EXISTS_SAME":
            row = await get_idempotency(idem_key)
            if row and row.get("status") == "DONE" and row.get("response") is not None:
                r = row["response"]
                await _audit(
                    "COMMAND_CREATE_ACCEPTED",
                    actor,
                    {"command_id": r["id"], "idempotency_key": idem_key},
                )
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
            await _audit(
                "COMMAND_CREATE_ACCEPTED",
                actor,
                {"command_id": resp["id"], "idempotency_key": idem_key},
            )
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
                await _audit(
                    "COMMAND_CREATE_ACCEPTED",
                    actor,
                    {"command_id": resp["id"], "idempotency_key": idem_key},
                )
                if idem_key:
                    await finish_idempotency_ok(idem_key, resp)
                return resp
            raise HTTPException(status_code=500, detail="db insert failed")

        resp = {"id": str(cmd_id), "idempotency_key": x_idempotency_key, "status": "ACCEPTED"}
        await _audit(
            "COMMAND_CREATE_ACCEPTED",
            actor,
            {"command_id": resp["id"], "idempotency_key": idem_key},
        )
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
