import asyncio
import os
from typing import Any, Dict, Optional

from sqlalchemy import text

from app.workers import command_worker as cw
from app.actions.registry import get_action, init_actions
from app.actions.runner import DomainCommandRunner
from app.domain_events import append_domain_event
from app.policies.registry import get_policies, init_policies

# Ensure actions and policies are registered when worker module loads
init_actions()
init_policies()


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

    print(f"[domain] mark FAILED id={command_id} reason={reason!r}", flush=True)
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
                RETURNING id, type, payload, attempt
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
            "attempt": int(row["attempt"]) if row.get("attempt") is not None else 0,
        }


async def domain_worker_loop() -> None:
    print("domain worker started, polling commands_domain...", flush=True)

    runner = DomainCommandRunner(
        _pick_one_domain,
        get_action,
        _domain_mark_done,
        _domain_mark_failed,
        now_ts_fn=cw._now_ts,
        append_event_fn=append_domain_event,
        policies=get_policies(),
        policy_engine=engine,
    )

    while True:
        try:
            res = await runner.run_one()
            if res is None:
                await asyncio.sleep(POLL_INTERVAL_SEC)
                continue
            print(
                f"picked domain command id={res['id']} type={res['type']} final_status={res['final_status']}",
                flush=True,
            )
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

