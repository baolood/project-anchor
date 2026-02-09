import asyncio
import os
from typing import Any, Dict, Optional

from sqlalchemy import text

from app.workers import command_worker as cw


def _ensure_json_object(x):
    import json
    if x is None:
        return {}
    if isinstance(x, dict):
        return x
    if isinstance(x, str):
        try:
            v = json.loads(x)
            return v if isinstance(v, dict) else {"value": v}
        except Exception:
            return {"value": x}
    return {"value": x}


# 直接复用 command_worker 里的异步引擎和环境配置
engine = cw.engine

POLL_INTERVAL_SEC = float(
    os.getenv("DOMAIN_WORKER_POLL_INTERVAL_SEC", os.getenv("WORKER_POLL_INTERVAL_SEC", "1.0"))
)
DOMAIN_WORKER_ID = os.getenv("DOMAIN_WORKER_ID", "domain-worker")


async def _domain_mark_done(command_id: str, result: Optional[Dict[str, Any]] = None) -> int:
    import json

    result_obj = _ensure_json_object(result)
    result_json = json.dumps(result_obj, ensure_ascii=False)

    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                """
                UPDATE commands_domain
                SET status='DONE',
                    result=(:result)::jsonb,
                    error=NULL,
                    updated_at=NOW()
                WHERE id=:id AND status IN ('PENDING','RUNNING')
                """
            ),
            {"id": command_id, "result": result_json},
        )

    print(f"[domain] mark DONE id={command_id} type(result)={type(result).__name__}", flush=True)
    return r.rowcount


async def _domain_mark_failed(
    command_id: str, reason: str, detail: Optional[Dict[str, Any]] = None
) -> int:
    import json

    result_obj = _ensure_json_object(
        {"ok": False, "reason": reason, "detail": detail or {}}
    )
    result_json = json.dumps(result_obj, ensure_ascii=False)

    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                """
                UPDATE commands_domain
                SET status='FAILED',
                    result=(:result)::jsonb,
                    error=:reason,
                    updated_at=NOW()
                WHERE id=:id AND status IN ('PENDING','RUNNING')
                """
            ),
            {"id": command_id, "result": result_json, "reason": reason},
        )

    print(f"[domain] mark FAILED id={command_id} type(result)={type(result).__name__}", flush=True)
    return r.rowcount


async def _pick_one_domain() -> Optional[Dict[str, Any]]:
    """
    从 commands_domain 中按 created_at 升序取一条 PENDING，并加锁/打标记。
    使用 SKIP LOCKED 保证多实例下不会重复处理同一条（幂等）。
    """
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                """
                WITH cte AS (
                    SELECT id
                    FROM commands_domain
                    WHERE status='PENDING'
                    ORDER BY created_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                UPDATE commands_domain
                SET status='RUNNING',
                    attempt = attempt + 1,
                    locked_by = :locked_by,
                    locked_at = NOW(),
                    updated_at = NOW()
                WHERE id IN (SELECT id FROM cte)
                RETURNING id, type, payload
                """
            ),
            {"locked_by": DOMAIN_WORKER_ID},
        )
        row = r.mappings().first()
        if not row:
            return None

        return {
            "id": str(row["id"]),
            "type": row.get("type"),
            "payload": row.get("payload") or {},
        }


async def _process_domain_one(item: Dict[str, Any]) -> None:
    cid = item["id"]
    raw_payload = item.get("payload") or {}

    cmd_type = (str(item.get("type") or "")).strip().lower()

    try:
        # 目前仅有 NOOP，一律视作成功回显
        result: Dict[str, Any] = {
            "ok": True,
            "type": cmd_type or "noop",
            "ts": cw._now_ts(),
            "payload": raw_payload,
        }

        rows = await _domain_mark_done(cid, result)
        print(f"DOMAIN DONE rows={rows} id={cid}", flush=True)

    except Exception as e:
        rows = await _domain_mark_failed(
            cid,
            "exception",
            {"error": str(e), "payload": raw_payload},
        )
        print(f"DOMAIN FAILED rows={rows} id={cid} err={e}", flush=True)


async def domain_worker_loop() -> None:
    print("domain worker started, polling commands_domain...", flush=True)

    while True:
        item: Optional[Dict[str, Any]] = None
        try:
            item = await _pick_one_domain()
            if not item:
                await asyncio.sleep(POLL_INTERVAL_SEC)
                continue

            print(
                f"picked domain command id={item['id']} "
                f"type={item.get('type')} "
                f"payload={cw._safe_json(item.get('payload'))}",
                flush=True,
            )

            await _process_domain_one(item)

        except Exception as e:
            print(f"domain worker error: {e}", flush=True)
            await asyncio.sleep(1.0)


async def main() -> None:
    """
    同一个容器进程里同时跑：
    - 现有 commands worker（命令总线）
    - 新的 domain worker（commands_domain）
    """
    t1 = asyncio.create_task(cw.main())
    t2 = asyncio.create_task(domain_worker_loop())
    await asyncio.gather(t1, t2)


if __name__ == "__main__":
    asyncio.run(main())

