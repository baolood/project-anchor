import asyncio
import os
import random
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException
from app.api.routes import router

try:
    import asyncpg  # type: ignore
except Exception:
    asyncpg = None  # type: ignore


app = FastAPI(title="Anchor Backend", version="0.1.0")
app.include_router(router)


def _now_z() -> str:
    return datetime.utcnow().isoformat() + "Z"


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


@app.post("/domain-commands/noop")
async def create_domain_noop():
    pool = await _get_domain_pg_pool()

    cmd_id = f"noop-{uuid.uuid4()}"
    now = datetime.utcnow()

    sql = """
    INSERT INTO commands_domain
      (id, type, status, payload, attempt, created_at, updated_at)
    VALUES
      ($1, 'NOOP', 'PENDING', '{}'::jsonb, 0, $2, $2)
    RETURNING id, type, status, created_at, updated_at;
    """

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(sql, cmd_id, now)
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
            "result": r["result"],
            "error": r["error"],
            "created_at": iso(r["created_at"]),
            "updated_at": iso(r["updated_at"]),
        }
        for r in rows
    ]
