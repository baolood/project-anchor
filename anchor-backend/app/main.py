import asyncio
import os
import random
import uuid
from datetime import datetime

from fastapi import Body, FastAPI, HTTPException
from app.api.routes import router
from app.domain_events import append_domain_event_pool

try:
    import asyncpg  # type: ignore
except Exception:
    asyncpg = None  # type: ignore


app = FastAPI(title="Anchor Backend", version="0.1.0")
app.include_router(router)


def _now_z() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _ensure_json_result(x):
    import json

    if x is None:
        return None
    if isinstance(x, dict):
        return x
    # asyncpg 正常情况下会把 jsonb 映射成 dict；如果某些历史数据是字符串，这里兜底解析
    if isinstance(x, str):
        try:
            v = json.loads(x)
            return v
        except Exception:
            # 解析失败时保持原值，以免静默丢信息
            return x
    return x


async def command_state_driver():
    """
    MVP driver (in-memory):
    - every 2s, pick the oldest PENDING command (if any) from app/api/commands.py _COMMANDS
    - move it to PROCESSING, then DONE/FAILED
    """
    from app.api import commands as commands_mod  # type: ignore

    while True:
        try:
            cmds = getattr(commands_mod, "_COMMANDS", None)
            if isinstance(cmds, list) and len(cmds) > 0:
                pending = [c for c in cmds if c.get("status") == "PENDING"]
                if pending:
                    pending.sort(key=lambda c: c.get("created_at", ""))
                    cmd = pending[0]

                    cmd["status"] = "PROCESSING"
                    cmd["updated_at"] = _now_z()

                    await asyncio.sleep(1)

                    if random.random() < 0.9:
                        cmd["status"] = "DONE"
                        cmd["error"] = None
                    else:
                        cmd["status"] = "FAILED"
                        cmd["error"] = "mock failure"

                    cmd["updated_at"] = _now_z()
        except Exception:
            pass

        await asyncio.sleep(2)


def _normalize_asyncpg_dsn(dsn: str) -> str:
    dsn = (dsn or "").strip()
    if dsn.startswith("postgresql+asyncpg://"):
        return "postgresql://" + dsn[len("postgresql+asyncpg://") :]
    return dsn


async def _get_domain_pg_pool():
    pool = getattr(app.state, "domain_pg_pool", None)
    if pool is not None:
        return pool

    if asyncpg is None:
        raise RuntimeError("asyncpg is not installed in the backend container.")

    dsn = _normalize_asyncpg_dsn(os.getenv("DATABASE_URL", ""))
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set.")

    pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=5)
    app.state.domain_pg_pool = pool
    return pool


@app.on_event("startup")
async def _startup():
    asyncio.create_task(command_state_driver())
    try:
        await _get_domain_pg_pool()
    except Exception:
        pass


@app.on_event("shutdown")
async def _shutdown():
    pool = getattr(app.state, "domain_pg_pool", None)
    if pool is not None:
        await pool.close()


@app.get("/health")
async def health():
    return {"ok": True}


def _json_dumps(obj) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False)


async def _create_domain_command(cmd_id_prefix: str, cmd_type: str, payload: dict | None = None) -> dict:
    pool = await _get_domain_pg_pool()
    cmd_id = f"{cmd_id_prefix}-{uuid.uuid4()}"
    now = datetime.utcnow()
    payload_json = _json_dumps(payload if payload else {})
    sql = """
    INSERT INTO commands_domain
      (id, type, status, payload, attempt, created_at, updated_at)
    VALUES
      ($1, $2, 'PENDING', $3::jsonb, 0, $4, $4)
    RETURNING id, type, status, created_at, updated_at;
    """
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(sql, cmd_id, cmd_type, payload_json, now)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB insert failed: {e}")
    if row is None:
        raise HTTPException(status_code=500, detail="DB insert returned no row")
    return {
        "id": row["id"],
        "type": row["type"],
        "status": row["status"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


@app.post("/domain-commands/noop")
async def create_domain_noop():
    return await _create_domain_command("noop", "NOOP")


@app.post("/domain-commands/fail")
async def create_domain_fail():
    """Create a domain command that the worker will mark as FAILED (e2e test)."""
    return await _create_domain_command("fail", "FAIL")


@app.post("/domain-commands/flaky")
async def create_domain_flaky():
    """Create FLAKY: first run FAILED, after retry DONE (for retry e2e)."""
    return await _create_domain_command("flaky", "FLAKY")


@app.post("/domain-commands/quote")
async def create_domain_quote(body: dict = Body(default_factory=dict)):
    """Create QUOTE: payload defaults symbol=BTCUSDT, side=BUY, notional=100; optional price."""
    payload = dict(body) if body else {}
    defaults = {"symbol": "BTCUSDT", "side": "BUY", "notional": 100}
    for k, v in defaults.items():
        if k not in payload:
            payload[k] = v
    if "price" in payload and payload["price"] is None:
        del payload["price"]
    return await _create_domain_command("quote", "QUOTE", payload)


@app.post("/domain-commands/{domain_id}/retry")
async def retry_domain_command(domain_id: str):
    """Reset a FAILED command to PENDING (clear error/result/lock). Attempt only increments when worker picks. Same response shape as GET detail."""
    pool = await _get_domain_pg_pool()
    sql_select = "SELECT id, type, status, attempt FROM commands_domain WHERE id = $1;"
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql_select, domain_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Not Found")
    if row["status"] != "FAILED":
        raise HTTPException(
            status_code=400,
            detail=f"Only FAILED commands can be retried; current status is {row['status']}",
        )
    sql_update = """
    UPDATE commands_domain
    SET status = 'PENDING',
        error = NULL,
        result = NULL,
        locked_by = NULL,
        locked_at = NULL,
        updated_at = NOW()
    WHERE id = $1 AND status = 'FAILED'
    RETURNING id, type, status, attempt, locked_by, locked_at, result, error, created_at, updated_at;
    """
    async with pool.acquire() as conn:
        updated = await conn.fetchrow(sql_update, domain_id)
    if updated is None:
        raise HTTPException(status_code=409, detail="Command not retryable or already retried")
    await append_domain_event_pool(pool, domain_id, "RETRY", int(updated["attempt"]), {"type": updated["type"], "attempt": int(updated["attempt"])})
    def iso(v):
        return v.isoformat() if v is not None else None
    return {
        "id": updated["id"],
        "type": updated["type"],
        "status": updated["status"],
        "attempt": updated["attempt"],
        "locked_by": updated["locked_by"],
        "locked_at": iso(updated["locked_at"]),
        "result": _ensure_json_result(updated["result"]),
        "error": updated["error"],
        "created_at": iso(updated["created_at"]),
        "updated_at": iso(updated["updated_at"]),
    }


@app.get("/domain-commands/{domain_id}/events")
async def get_domain_command_events(domain_id: str, limit: int = 200):
    """List append-only events for a domain command, ordered by created_at ASC."""
    pool = await _get_domain_pg_pool()
    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT 1 FROM commands_domain WHERE id = $1", domain_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Not Found")
        rows = await conn.fetch(
            """
            SELECT id, command_id, event_type, attempt, payload, created_at
            FROM domain_events
            WHERE command_id = $1
            ORDER BY created_at ASC
            LIMIT $2
            """,
            domain_id,
            limit,
        )
    def iso(v):
        return v.isoformat() if v is not None else None

    return [
        {
            "id": r["id"],
            "command_id": r["command_id"],
            "event_type": r["event_type"],
            "attempt": r["attempt"],
            "payload": _ensure_json_result(r["payload"]),
            "created_at": iso(r["created_at"]),
        }
        for r in rows
    ]


@app.get("/domain-commands")
async def list_domain_commands(limit: int = 50):
    pool = await _get_domain_pg_pool()

    if limit < 1:
        limit = 1
    if limit > 200:
        limit = 200

    sql = """
    SELECT id, type, status, attempt, locked_by, locked_at, result, error, created_at, updated_at
    FROM commands_domain
    ORDER BY created_at DESC
    LIMIT $1;
    """

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB query failed: {e}")

    def iso(v):
        return v.isoformat() if v is not None else None

    return [
        {
            "id": r["id"],
            "type": r["type"],
            "status": r["status"],
            "attempt": r["attempt"],
            "locked_by": r["locked_by"],
            "locked_at": iso(r["locked_at"]),
            "result": _ensure_json_result(r["result"]),
            "error": r["error"],
            "created_at": iso(r["created_at"]),
            "updated_at": iso(r["updated_at"]),
        }
        for r in rows
    ]


@app.get("/domain-commands/{domain_id}")
async def get_domain_command(domain_id: str):
    """Get a single domain command by id (string, e.g. noop-uuid). Same shape as list items."""
    pool = await _get_domain_pg_pool()

    sql = """
    SELECT id, type, status, attempt, locked_by, locked_at, result, error, created_at, updated_at
    FROM commands_domain
    WHERE id = $1;
    """

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(sql, domain_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB query failed: {e}")

    if row is None:
        raise HTTPException(status_code=404, detail="Not Found")

    def iso(v):
        return v.isoformat() if v is not None else None

    return {
        "id": row["id"],
        "type": row["type"],
        "status": row["status"],
        "attempt": row["attempt"],
        "locked_by": row["locked_by"],
        "locked_at": iso(row["locked_at"]),
        "result": _ensure_json_result(row["result"]),
        "error": row["error"],
        "created_at": iso(row["created_at"]),
        "updated_at": iso(row["updated_at"]),
    }
