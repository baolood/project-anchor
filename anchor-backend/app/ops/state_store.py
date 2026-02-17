"""
Ops state store: persistent key-value + history for ops state.
Works with asyncpg pool (API) or SQLAlchemy engine (worker). Never raises.
"""
import json
import os
from typing import Any, Dict, List, Optional


def _normalize_dsn(dsn: str) -> str:
    dsn = (dsn or "").strip()
    if dsn.startswith("postgresql+asyncpg://"):
        return "postgresql://" + dsn[len("postgresql+asyncpg://") :]
    return dsn


async def _get_worker_pool():
    """Lazy pool for worker (state_store called from worker process)."""
    try:
        import asyncpg
        dsn = _normalize_dsn(os.getenv("DATABASE_URL", ""))
        if not dsn:
            return None
        return await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=3)
    except Exception as e:
        print(f"[state_store] worker pool init failed: {e}", flush=True)
        return None


_worker_pool: Optional[Any] = None


async def _get_or_create_worker_pool():
    global _worker_pool
    if _worker_pool is not None:
        return _worker_pool
    _worker_pool = await _get_worker_pool()
    return _worker_pool


async def upsert_state_pool(pool: Any, key: str, value: Dict[str, Any]) -> None:
    """Upsert ops_state and append to history. Uses asyncpg pool. Never raises."""
    try:
        value_json = json.dumps(value, ensure_ascii=False)
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ops_state (key, value, updated_at)
                VALUES ($1, $2::jsonb, NOW())
                ON CONFLICT (key) DO UPDATE SET value = $2::jsonb, updated_at = NOW()
                """,
                key,
                value_json,
            )
            await conn.execute(
                """
                INSERT INTO ops_state_history (key, value, created_at)
                VALUES ($1, $2::jsonb, NOW())
                """,
                key,
                value_json,
            )
    except Exception as e:
        print(f"[state_store] upsert_state_pool failed: {e}", flush=True)


async def upsert_state_engine(engine: Any, key: str, value: Dict[str, Any]) -> None:
    """Upsert ops_state and append to history. Uses SQLAlchemy engine. Never raises."""
    try:
        from sqlalchemy import text
        value_json = json.dumps(value, ensure_ascii=False)
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO ops_state (key, value, updated_at)
                    VALUES (:key, :value::jsonb, NOW())
                    ON CONFLICT (key) DO UPDATE SET value = :value::jsonb, updated_at = NOW()
                    """
                ),
                {"key": key, "value": value_json},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO ops_state_history (key, value, created_at)
                    VALUES (:key, :value::jsonb, NOW())
                    """
                ),
                {"key": key, "value": value_json},
            )
    except Exception as e:
        print(f"[state_store] upsert_state_engine failed: {e}", flush=True)


async def get_state_pool(pool: Any) -> Dict[str, Any]:
    """Return all ops_state key->value as dict. Never raises."""
    out = {}
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT key, value, updated_at FROM ops_state")
            for r in rows:
                k = r.get("key")
                if k:
                    v = r.get("value")
                    if isinstance(v, str):
                        try:
                            v = json.loads(v)
                        except Exception:
                            v = {"raw": v}
                    out[k] = {"value": v, "updated_at": r.get("updated_at")}
    except Exception as e:
        print(f"[state_store] get_state_pool failed: {e}", flush=True)
    return out


async def get_state_history_pool(pool: Any, limit: int = 50) -> List[Dict[str, Any]]:
    """Return recent ops_state_history rows. Never raises."""
    out = []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, key, value, created_at
                FROM ops_state_history
                ORDER BY created_at DESC
                LIMIT $1
                """,
                min(limit, 200),
            )
            for r in rows:
                v = r.get("value")
                if isinstance(v, str):
                    try:
                        v = json.loads(v)
                    except Exception:
                        v = {"raw": v}
                out.append({
                    "id": r.get("id"),
                    "key": r.get("key"),
                    "value": v,
                    "created_at": r.get("created_at"),
                })
    except Exception as e:
        print(f"[state_store] get_state_history_pool failed: {e}", flush=True)
    return out

# --- export helper (async, uses pool; schema: id, key, value jsonb, created_at) ---
from datetime import datetime as _dt
from typing import Any, Dict, List


async def get_state_history_export_rows(
    pool: Any,
    from_dt: _dt,
    to_dt: _dt,
    limit: int,
    event_type: str | None = None,
    actor: str | None = None,
    source: str | None = None,
) -> List[Dict[str, Any]]:
    """Export from ops_state_history. value is jsonb; we extract ts, event_type, exec_mode, actor, source."""
    out: List[Dict[str, Any]] = []
    try:
        clauses = ["created_at >= $1", "created_at <= $2"]
        params: List[Any] = [from_dt, to_dt]
        idx = 3
        if event_type:
            clauses.append(f"(value->>'event_type' = ${idx} OR key = ${idx})")
            params.append(event_type)
            idx += 1
        if actor:
            clauses.append(f"value->>'actor' = ${idx}")
            params.append(actor)
            idx += 1
        if source:
            clauses.append(f"value->>'source' = ${idx}")
            params.append(source)
            idx += 1
        params.append(min(max(1, limit), 10000))
        limit_idx = idx
        q = f"""
            SELECT id, key, value, created_at
            FROM ops_state_history
            WHERE {" AND ".join(clauses)}
            ORDER BY created_at DESC
            LIMIT ${limit_idx}
        """
        async with pool.acquire() as conn:
            rows = await conn.fetch(q, *params)
        for r in rows:
            v = r.get("value")
            if isinstance(v, str):
                try:
                    v = json.loads(v)
                except Exception:
                    v = {"raw": v}
            ts_val = (v.get("ts") if isinstance(v, dict) else None) or (r.get("created_at"))
            if hasattr(ts_val, "isoformat"):
                ts_val = ts_val.isoformat() if ts_val else ""
            elif ts_val is None:
                ts_val = ""
            evt = (v.get("event_type") if isinstance(v, dict) else None) or r.get("key") or ""
            out.append({
                "ts": ts_val,
                "event_type": evt,
                "exec_mode": (v.get("exec_mode") if isinstance(v, dict) else None) or "",
                "actor": (v.get("actor") if isinstance(v, dict) else None) or "",
                "source": (v.get("source") if isinstance(v, dict) else None) or "",
                "payload_json": v if isinstance(v, dict) else {},
            })
    except Exception as e:
        print(f"[state_store] get_state_history_export_rows failed: {e}", flush=True)
    return out
