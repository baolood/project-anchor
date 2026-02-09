import asyncio
import os
import time
from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@postgres:5432/postgres")
POLL_INTERVAL_SEC = float(os.getenv("WORKER_POLL_INTERVAL_SEC", "1.0"))
BATCH_SIZE = int(os.getenv("WORKER_BATCH_SIZE", "10"))

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)


def _now_ts() -> int:
    return int(time.time())


def _safe_json(obj: Any) -> str:
    # 仅用于日志，避免 repr 太乱
    try:
        import json
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)


def _normalize_command(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    兼容三种输入：
    1) 新标准：{ type, request_id?, name?, payload? }
    2) 旧UI：{ name, payload } -> 自动补 type=noop
    3) 旧执行：{ action:"execute", command_id:"..." } -> 转为 type=execute, payload={c    3) 旧�   """
    obj = dict(payload or {})

    # 旧执行格式：action=execute
    if (not obj.get("type")) and obj.get("action") == "execute":
        obj["type"] = "execute"
        cmd_id = obj.get("command_id") or obj.get("id")
        obj["payload"] = {"command_id": cmd_id}

    # 旧 UI 创建：{name, payload} 没有 type
    if (not obj.get("type")) and obj.get("name"):
        obj["type"] = "noop"
        obj["request_id"] = obj.get("request_id") or f"ui-{_now_ts()}"

    return obj


async def mark_done(command_id: str, result: Optional[Dict[str, Any]] = None) -> int:
    import json
    result_json = json.dumps(result or {}, ensure_ascii=False)
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                """
                UPDATE commands
                SET status='DONE',
                    result=:result,
                    updated_at=NOW()
                WHERE id=:id AND status IN ('PENDING','RUNNING')
                """
            ),
            {"id": command_id, "result": result_json},
        )
        return r.rowcount


async def mark_failed(command_id: str, reason: str, detail: Optional[Dict[str, Any]] = None) -> int:
    import json
    result_json = json.dumps({"ok": False, "reason": reason, "detail": detail or {}}, ensure_ascii=False)
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                """
                UPDATE commands
                SET status='FAILED',
                    result=:result,
                    updated_at=NOW()
                WHERE id=:id AND status IN ('PENDING','RUNNING')
                """
            ),
            {"id": command_id, "result": result_json},
        )
        return r.rowcount


async def pick_one() -> Optional[Dict[str, Any]]:
    """
    用 SKIP LOCKED 防止多 worker 抢同一条。
    """
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                """
                WITH cte AS (
                    SELECT id
                    FROM commands
                    WHERE status='PENDING'
                    ORDER BY created_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                UPDATE commands
                SET status='RUNNING',
                    updated_at=NOW()
                WHERE id IN (SELECT id FROM cte)
                RETURNING id, idempotency_key, payload
                """
            )
        )
        row = r.mappings().first()
        if not row:
            return None

        # payload 存在 DB 里通常是 json / jsonb，asyncpg 会转成 dict
        return {
            "id": str(row["id"]),
            "idempotency_key": row.get("idempotency_key"),
            "payload": row.get("payload") or {},
        }


async def handle_ping(cmd: Dict[str, Any], raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": True, "type": "ping", "ts": _now_ts()}


async def handle_noop(cmd: Dict[str, Any], raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": True, "type": "noop", "echo": raw_payload}


async def handle_execute(cmd: Dict[str, Any], raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    先跑通闭环：收到 execute 就 DONE，并把目标 command_id 回显。
    真实执行逻辑以后再接。
    """
    payload = raw_payload.get("payload")
    target_id = None
    if isinstance(payload, dict):
        target_id = payload.get("command_id") or payload.get("id")
    target_id = target_id or raw_payload.get("command_id") or raw_payload.get("id")

    if not target_id:
        raise ValueError("missing_command_id")

    return {"ok": True, "type": "execute", "executed_command_id": str(target_id), "ts": _now_ts()}


async def process_one(item: Dict[str, Any]) -> None:
    cid = item["id"]
    raw_payload = item.get("payload") or {}
    norm = _normalize_command(raw_payload)

    cmd_type = (norm.get("type") or "").strip()

    try:
        if cmd_type == "ping":
            result = await handle_ping(item, norm)
            rows = await mark_done(cid, result)
            print(f"DONE rows={rows} id={cid}", flush=True)
            return

        if cmd_type == "noop":
            result = await handle_noop(item, norm)
            rows = await mark_done(cid, result)
            print(f"DONE rows={rows} id={cid}", flush=True)
            return

        if cmd_type == "execute":
            result = await handle_execute(item, norm)
            rows = await mark_done(cid, result)
            print(f"DONE rows={rows} id={cid}", flush=True)
            return

        # 不认识的 type
        rows = await mark_failed(cid, "missing_type", {"seen_type": cmd_type, "payload": norm})
        print(f"FAILED rows={rows} id={cid} reason=missing_type", flush=True)

    except Exception as e:
        rows = await mark_failed(cid, "exception", {"error": str(e), "payload": norm})
        print(f"FAILED rows={rows} id={cid} reason=exception err={e}", flush=True)


async def main():
    print("worker started, polling commands...", flush=True)

    while True:
        item = None
        try:
            item = await pick_one()
            if not item:
                await asyncio.sleep(POLL_INTERVAL_SEC)
                continue

            print(
                f"picked command id={item['id']} key={item.get('idempotency_key')} payload={_safe_json(item.get('payload'))}",
                flush=True,
            )
            await process_one(item)

        except Exception as e:
            print(f"worker error: {e}", flush=True)
            await asyncio.sleep(1.0)


if __name__ == "__main__":
    asyncio.run(main())
