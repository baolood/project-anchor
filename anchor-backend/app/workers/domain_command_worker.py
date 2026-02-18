import asyncio
import os
import time
from collections import deque
from typing import Any, Dict, Optional

from sqlalchemy import text

from app.workers import command_worker as cw
from app.actions.registry import get_action, init_actions
from app.actions.runner import DomainCommandRunner
from app.domain_events import append_domain_event
from app.policies.registry import get_policies, init_policies
from app.risk.lockout import is_lockout_active, is_command_allowed
from app.risk.hard_limits import risk_guard
from app.risk.policy_engine import RiskPolicyEngine

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

# Kill switch: env (priority) or Redis. Event throttle + DB throttle.
def _kill_switch_state() -> tuple:
    """Returns (enabled: bool, source: 'env'|'redis'|'none'). Never raises."""
    from app.ops.kill_switch import get_kill_switch_state
    return get_kill_switch_state()


_kill_switch_written_ids: set = set()
_last_pending_check_ts: list = [0.0]
PENDING_CHECK_INTERVAL_SEC = 10.0

HEARTBEAT_INTERVAL_SEC = float(os.getenv("WORKER_HEARTBEAT_SECONDS", "30"))
_last_heartbeat_ts: list = [0.0]
WORKER_HEARTBEAT_COMMAND_ID = "anchor:worker_heartbeat"

# Panic guard: sliding window of unhandled exception timestamps
WORKER_PANIC_THRESHOLD = int(os.getenv("WORKER_PANIC_THRESHOLD", "999999"))
WORKER_PANIC_WINDOW_SECONDS = float(os.getenv("WORKER_PANIC_WINDOW_SECONDS", "60"))
WORKER_PANIC_COOLDOWN_SECONDS = float(os.getenv("WORKER_PANIC_COOLDOWN_SECONDS", "10"))
_panic_exception_timestamps: deque = deque(maxlen=1000)


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


async def _oldest_pending_command_id() -> Optional[str]:
    """Read-only: id of oldest PENDING command (no lock). Used when kill switch ON to attach KILL_SWITCH_ON event."""
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                "SELECT id FROM commands_domain WHERE status = 'PENDING' ORDER BY created_at ASC LIMIT 1"
            ),
        )
        row = r.mappings().first()
    return str(row["id"]) if row else None


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

    async def _is_lockout_blocked(cmd_type: str):
        active, until, reason = await is_lockout_active(engine)
        if not active:
            return (False, "", "")
        if is_command_allowed(cmd_type):
            return (False, "", "")
        return (True, until, reason)

    async def _risk_guard(cmd_type: str, payload: dict):
        p = payload or {}
        notional_usd = p.get("notional_usd") or p.get("notional") or p.get("amount_usd") or 0
        decision = RiskPolicyEngine.evaluate_single_trade({"notional_usd": notional_usd})
        if not decision.allowed:
            return (False, decision.reason)
        return await risk_guard(engine, cmd_type, p)

    runner = DomainCommandRunner(
        _pick_one_domain,
        get_action,
        _domain_mark_done,
        _domain_mark_failed,
        now_ts_fn=cw._now_ts,
        append_event_fn=append_domain_event,
        policies=get_policies(),
        policy_engine=engine,
        is_lockout_blocked_fn=_is_lockout_blocked,
        risk_guard_fn=_risk_guard,
    )

    while True:
        try:
            # Fault injection for e2e (must be inside outer try so Panic Guard catches it)
            if os.getenv("WORKER_INJECT_PANIC") == "1":
                raise RuntimeError("INJECTED_PANIC_FOR_E2E")

            now_ts = time.time()
            if now_ts - _last_heartbeat_ts[0] >= HEARTBEAT_INTERVAL_SEC:
                from datetime import datetime
                ts_iso = datetime.utcnow().isoformat() + "Z"
                await append_domain_event(
                    WORKER_HEARTBEAT_COMMAND_ID,
                    "WORKER_HEARTBEAT",
                    0,
                    {"worker": "domain", "reason": "loop"},
                )
                try:
                    from app.ops.state_store import upsert_state_engine
                    await upsert_state_engine(
                        engine,
                        "worker_heartbeat",
                        {"last_heartbeat_at": ts_iso, "source": "worker"},
                    )
                except Exception as ev:
                    print(f"[domain] worker_heartbeat state_store failed: {ev}", flush=True)
                _last_heartbeat_ts[0] = now_ts
            kill_enabled, kill_source = _kill_switch_state()
            if kill_enabled:
                now_ts = time.time()
                if now_ts - _last_pending_check_ts[0] >= PENDING_CHECK_INTERVAL_SEC:
                    pending_id = await _oldest_pending_command_id()
                    _last_pending_check_ts[0] = now_ts
                else:
                    pending_id = None
                if pending_id and pending_id not in _kill_switch_written_ids:
                    try:
                        await append_domain_event(
                            pending_id,
                            "KILL_SWITCH_ON",
                            0,
                            {"reason": "kill_switch", "source": kill_source},
                        )
                        _kill_switch_written_ids.add(pending_id)
                    except Exception as e:
                        print(f"[domain] KILL_SWITCH_ON append failed: {e}", flush=True)
                await asyncio.sleep(1.0)
                continue
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
            now = time.time()
            _panic_exception_timestamps.append(now)
            # Trim old timestamps outside window
            while _panic_exception_timestamps and _panic_exception_timestamps[0] < now - WORKER_PANIC_WINDOW_SECONDS:
                _panic_exception_timestamps.popleft()
            n = len(_panic_exception_timestamps)
            if n >= WORKER_PANIC_THRESHOLD:
                try:
                    from datetime import datetime
                    ts_iso = datetime.utcnow().isoformat() + "Z"
                    await append_domain_event(
                        "ops-worker",
                        "WORKER_PANIC",
                        0,
                        {
                            "reason": "unhandled_exception_storm",
                            "count": n,
                            "window_sec": WORKER_PANIC_WINDOW_SECONDS,
                            "source": "worker",
                        },
                    )
                    try:
                        from app.ops.state_store import upsert_state_engine
                        await upsert_state_engine(
                            engine,
                            "worker_panic",
                            {"last_panic_at": ts_iso, "count": n, "window_sec": WORKER_PANIC_WINDOW_SECONDS},
                        )
                    except Exception as ev2:
                        print(f"[domain] worker_panic state_store failed: {ev2}", flush=True)
                except Exception as ev:
                    print(f"[domain] WORKER_PANIC append failed: {ev}", flush=True)
                try:
                    from app.ops.kill_switch import set_kill_switch_redis
                    set_kill_switch_redis(True)
                except Exception:
                    pass
                try:
                    from app.ops.notify import send_telegram
                    send_telegram(
                        f"WORKER_PANIC unhandled_exception_storm count={n} window_sec={WORKER_PANIC_WINDOW_SECONDS}",
                        throttle_key="WORKER_PANIC",
                    )
                except Exception:
                    pass
                _panic_exception_timestamps.clear()
                print(f"[domain] PANIC GUARD triggered: sleep {WORKER_PANIC_COOLDOWN_SECONDS}s", flush=True)
                await asyncio.sleep(WORKER_PANIC_COOLDOWN_SECONDS)
                continue
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

