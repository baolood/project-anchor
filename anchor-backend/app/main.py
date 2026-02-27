import asyncio
import os
import random
import uuid
from datetime import datetime

from fastapi import Body, FastAPI, HTTPException, Query, Request
from app.api.routes import router
from app.api.ops import router as ops_router
from app.domain_events import append_domain_event_pool

try:
    import asyncpg  # type: ignore
except Exception:
    asyncpg = None  # type: ignore


app = FastAPI(title="Anchor Backend", version="0.1.0")
app.include_router(router)
app.include_router(ops_router)


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


@app.get("/ops/kill-switch")
async def get_kill_switch():
    """Read-only: report whether kill switch is enabled (env or redis). Worker respects it and does not pick when ON."""
    from app.ops.kill_switch import get_kill_switch_state
    enabled, source = get_kill_switch_state()
    return {"enabled": enabled, "source": source}


@app.post("/ops/kill-switch")
async def post_kill_switch(request: Request, body: dict = Body(default_factory=dict)):
    """Set kill switch via Redis. OPS_TOKEN required if set. Writes KILL_SWITCH_SET audit event."""
    ops_token = (os.getenv("OPS_TOKEN") or "").strip()
    if ops_token:
        token = (request.headers.get("x-ops-token") or "").strip()
        if token != ops_token:
            raise HTTPException(status_code=401, detail="Unauthorized")
    enabled = body.get("enabled", False) if isinstance(body, dict) else False
    from app.ops.kill_switch import set_kill_switch_redis, get_kill_switch_state
    ok = set_kill_switch_redis(bool(enabled))
    if ok:
        try:
            pool = await _get_domain_pg_pool()
            await append_domain_event_pool(
                pool,
                "ops-kill-switch",
                "KILL_SWITCH_SET",
                0,
                {"enabled": bool(enabled), "source": "redis", "actor": "ops_api"},
            )
        except Exception as e:
            print(f"[ops/kill-switch] audit append failed: {e}", flush=True)
    enabled_out, source_out = get_kill_switch_state()
    if ok:
        try:
            pool = await _get_domain_pg_pool()
            from app.ops.state_store import upsert_state_pool
            await upsert_state_pool(
                pool,
                "kill_switch",
                {"enabled": enabled_out, "source": source_out, "actor": "ops_api"},
            )
        except Exception as e:
            print(f"[ops/kill-switch] state_store upsert failed: {e}", flush=True)
    return {"enabled": enabled_out, "source": source_out}


@app.get("/ops/state")
async def get_ops_state():
    """Aggregated ops state: kill_switch, worker_heartbeat, worker_panic, recent_ops_events. Never raises."""
    from datetime import datetime
    from app.ops.kill_switch import get_kill_switch_state
    kill_enabled, kill_source = get_kill_switch_state()
    kill_switch = {"enabled": kill_enabled, "source": kill_source}
    worker_heartbeat = None
    worker_panic = None
    recent_ops_events = []
    try:
        pool = await _get_domain_pg_pool()
        from app.ops.state_store import get_state_pool
        state = await get_state_pool(pool)
        if state.get("worker_heartbeat"):
            worker_heartbeat = state["worker_heartbeat"].get("value")
        if state.get("worker_panic"):
            wp_raw = state["worker_panic"].get("value")
            worker_panic = dict(wp_raw) if isinstance(wp_raw, dict) else {}
            last_at = worker_panic.get("last_panic_at") or worker_panic.get("last_trigger_at")
            last_ts = _parse_iso_to_ts(last_at) if last_at else None
            worker_panic["cooldown_sec"] = PANIC_GUARD_COOLDOWN_SEC
            if last_ts:
                elapsed = datetime.utcnow().timestamp() - last_ts
                worker_panic["cooldown_remaining"] = max(0, int(PANIC_GUARD_COOLDOWN_SEC - elapsed))
            else:
                worker_panic["cooldown_remaining"] = 0
        if state.get("kill_switch"):
            kill_switch = state["kill_switch"].get("value") or kill_switch

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT command_id, event_type, payload, created_at
                FROM domain_events
                WHERE command_id IN ('ops-kill-switch', 'ops-worker')
                ORDER BY created_at DESC
                LIMIT 20
                """
            )
        def iso(v):
            return v.isoformat() if v is not None else None
        recent_ops_events = [
            {
                "command_id": r["command_id"],
                "event_type": r["event_type"],
                "payload": _ensure_json_result(r["payload"]),
                "created_at": iso(r["created_at"]),
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[ops/state] query failed: {e}", flush=True)
    return {
        "kill_switch": kill_switch,
        "worker_heartbeat": worker_heartbeat,
        "worker_panic": worker_panic,
        "recent_ops_events": recent_ops_events,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def _panic_guard_ops_allowed() -> bool:
    """Only allow trigger/reset in local/testnet. Reject in prod."""
    mode = (os.getenv("EXEC_MODE") or os.getenv("NEXT_PUBLIC_EXEC_MODE") or "").strip().lower()
    if mode in ("prod", "production"):
        return False
    return True


PANIC_GUARD_COOLDOWN_SEC = int(os.getenv("PANIC_GUARD_COOLDOWN_SEC", "60"))


def _parse_iso_to_ts(iso_str: str | None) -> float | None:
    if not iso_str:
        return None
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception:
        return None


@app.post("/ops/panic_guard/trigger")
async def post_panic_guard_trigger(request: Request):
    """Manual panic guard drill: set kill switch ON + worker_panic state. Only local/testnet. 409 if in cooldown."""
    if not _panic_guard_ops_allowed():
        raise HTTPException(status_code=403, detail="Panic guard ops disabled in prod")
    ops_token = (os.getenv("OPS_TOKEN") or "").strip()
    if ops_token:
        token = (request.headers.get("x-ops-token") or "").strip()
        if token != ops_token:
            raise HTTPException(status_code=401, detail="Unauthorized")

    actor = (request.headers.get("x-anchor-actor") or "").strip() or "unknown"
    source = (request.headers.get("x-anchor-source") or "").strip() or "unknown"
    exec_mode_val = (os.getenv("EXEC_MODE") or os.getenv("NEXT_PUBLIC_EXEC_MODE") or "unknown").strip() or "unknown"

    from app.ops.kill_switch import set_kill_switch_redis, get_kill_switch_state
    from app.ops.state_store import upsert_state_pool, get_state_pool

    now_iso = datetime.utcnow().isoformat() + "Z"
    now_ts = datetime.utcnow().timestamp()
    cooldown_sec = PANIC_GUARD_COOLDOWN_SEC

    try:
        pool = await _get_domain_pg_pool()
        state = await get_state_pool(pool)
        wp = (state.get("worker_panic") or {}).get("value") or {}
        last_at = wp.get("last_panic_at") or wp.get("last_trigger_at")
        last_ts = _parse_iso_to_ts(last_at)
        if last_ts is not None and (now_ts - last_ts) < cooldown_sec:
            remaining = int(cooldown_sec - (now_ts - last_ts))
            raise HTTPException(
                status_code=409,
                detail=f"Panic guard in cooldown. {remaining}s remaining.",
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ops/panic_guard/trigger] cooldown check failed: {e}", flush=True)

    ok = set_kill_switch_redis(True)
    try:
        pool = await _get_domain_pg_pool()
        await upsert_state_pool(
            pool,
            "worker_panic",
            {
                "last_panic_at": now_iso,
                "last_trigger_at": now_iso,
                "count": 1,
                "window_sec": 60,
                "source": source,
                "actor": actor,
                "triggered": True,
                "event_type": "PANIC_GUARD_TRIGGER",
                "ts": now_iso,
                "exec_mode": exec_mode_val,
            },
        )
        await append_domain_event_pool(
            pool,
            "ops-panic-guard",
            "PANIC_GUARD_TRIGGERED",
            0,
            {"source": source, "actor": actor, "ts": now_iso, "exec_mode": exec_mode_val},
        )
    except Exception as e:
        print(f"[ops/panic_guard/trigger] failed: {e}", flush=True)
    enabled_out, source_out = get_kill_switch_state()
    return {
        "ok": ok,
        "kill_switch": {"enabled": enabled_out, "source": source_out},
        "cooldown_sec": cooldown_sec,
        "cooldown_remaining": 0,
    }


@app.post("/ops/panic_guard/reset")
async def post_panic_guard_reset(request: Request):
    """Reset panic guard: set kill switch OFF + clear worker_panic. Only local/testnet."""
    if not _panic_guard_ops_allowed():
        raise HTTPException(status_code=403, detail="Panic guard ops disabled in prod")
    ops_token = (os.getenv("OPS_TOKEN") or "").strip()
    if ops_token:
        token = (request.headers.get("x-ops-token") or "").strip()
        if token != ops_token:
            raise HTTPException(status_code=401, detail="Unauthorized")

    actor = (request.headers.get("x-anchor-actor") or "").strip() or "unknown"
    source = (request.headers.get("x-anchor-source") or "").strip() or "unknown"
    exec_mode_val = (os.getenv("EXEC_MODE") or os.getenv("NEXT_PUBLIC_EXEC_MODE") or "unknown").strip() or "unknown"
    now_iso = datetime.utcnow().isoformat() + "Z"

    from app.ops.kill_switch import set_kill_switch_redis, get_kill_switch_state
    from app.ops.state_store import upsert_state_pool
    ok = set_kill_switch_redis(False)
    try:
        pool = await _get_domain_pg_pool()
        await upsert_state_pool(
            pool,
            "worker_panic",
            {
                "last_panic_at": None,
                "last_trigger_at": None,
                "count": 0,
                "triggered": False,
                "source": source,
                "actor": actor,
                "event_type": "PANIC_GUARD_RESET",
                "ts": now_iso,
                "exec_mode": exec_mode_val,
            },
        )
        await append_domain_event_pool(
            pool,
            "ops-panic-guard",
            "PANIC_GUARD_RESET",
            0,
            {"source": source, "actor": actor, "ts": now_iso, "exec_mode": exec_mode_val},
        )
    except Exception as e:
        print(f"[ops/panic_guard/reset] failed: {e}", flush=True)
    enabled_out, source_out = get_kill_switch_state()
    return {"ok": ok, "kill_switch": {"enabled": enabled_out, "source": source_out}}


@app.get("/ops/state/history")
async def get_ops_state_history(limit: int = Query(50, ge=1, le=200)):
    """Recent ops_state_history rows. Never raises."""
    try:
        pool = await _get_domain_pg_pool()
        from app.ops.state_store import get_state_history_pool
        rows = await get_state_history_pool(pool, limit)
        def iso(v):
            return v.isoformat() if v is not None else None
        return [
            {
                "id": r["id"],
                "key": r["key"],
                "value": r["value"],
                "created_at": iso(r["created_at"]),
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[ops/state/history] query failed: {e}", flush=True)
        return []


@app.get("/ops/worker")
async def get_ops_worker():
    """Read-only: kill switch, telegram enabled, last worker heartbeat. Never raises."""
    from app.ops.kill_switch import get_kill_switch_state
    kill_enabled, kill_source = get_kill_switch_state()
    telegram_enabled = (os.getenv("TELEGRAM_NOTIFY_ENABLED") or "").strip() == "1"
    last_heartbeat_at = None
    try:
        pool = await _get_domain_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT created_at FROM domain_events
                WHERE event_type = 'WORKER_HEARTBEAT'
                ORDER BY created_at DESC LIMIT 1
                """
            )
            if row and row.get("created_at"):
                last_heartbeat_at = row["created_at"].isoformat()
    except Exception as e:
        print(f"[ops/worker] query failed: {e}", flush=True)
    return {
        "kill_switch_enabled": kill_enabled,
        "kill_switch_source": kill_source,
        "telegram_enabled": telegram_enabled,
        "last_heartbeat_at": last_heartbeat_at,
    }


def _summary_from_payload(payload) -> str | None:
    """Extract summary from payload: message > code > error.message > error.code. Returns None if empty."""
    if payload is None or not isinstance(payload, dict):
        return None
    msg = payload.get("message")
    if msg is not None and str(msg).strip():
        return str(msg).strip()[:240]
    code = payload.get("code")
    if code is not None and str(code).strip():
        return str(code).strip()[:240]
    err = payload.get("error")
    if isinstance(err, dict):
        em = err.get("message")
        if em is not None and str(em).strip():
            return str(em).strip()[:240]
        ec = err.get("code")
        if ec is not None and str(ec).strip():
            return str(ec).strip()[:240]
    return None


def _risk_config():
    """Risk env config. Never raises."""
    def _float(s: str | None, default: float) -> float:
        if not s or not s.strip():
            return default
        try:
            return float(s.strip())
        except ValueError:
            return default

    def _int(s: str | None, default: int) -> int:
        if not s or not s.strip():
            return default
        try:
            return int(s.strip())
        except ValueError:
            return default

    return {
        "daily_loss_budget_pct": _float(os.getenv("RISK_DAILY_LOSS_BUDGET_PCT"), 2.0),
        "lockout_loss_pct": _float(os.getenv("RISK_LOCKOUT_LOSS_PCT"), 2.0),
        "lockout_consec_losses": _int(os.getenv("RISK_LOCKOUT_CONSEC_LOSSES"), 3),
        "lockout_minutes": _int(os.getenv("RISK_LOCKOUT_MINUTES"), 1440),
        "capital_usd": _float(os.getenv("CAPITAL_USD"), 0.0),
    }


def _risk_state_fallback(status: str = "ERROR") -> dict:
    """Minimal safe response on error. Never raises."""
    from datetime import datetime
    cfg = _risk_config()
    return {
        "status": status,
        "daily_loss_budget_pct": cfg["daily_loss_budget_pct"],
        "daily_loss_budget_usd": 0.0,
        "today_pnl": 0.0,
        "today_loss_pct": 0.0,
        "consecutive_losses": 0,
        "net_exposure_usd": 0.0,
        "positions_count": 0,
        "lockout_enabled": False,
        "lockout_reason": "",
        "lockout_until": "",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "thresholds": {
            "lockout_loss_pct": cfg["lockout_loss_pct"],
            "lockout_consec_losses": cfg["lockout_consec_losses"],
            "lockout_minutes": cfg["lockout_minutes"],
        },
    }


@app.post("/ops/dev/reset-pending-domain-commands")
async def post_ops_dev_reset_pending_domain():
    """E2E helper: mark all PENDING domain commands as FAILED with RESET_FOR_E2E. No auth."""
    pool = await _get_domain_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            UPDATE commands_domain
            SET status = 'FAILED', error = 'RESET_FOR_E2E', updated_at = NOW()
            WHERE status = 'PENDING'
            RETURNING id
            """
        )
    return {"updated": len(rows)}


@app.post("/risk/lockout/clear")
async def post_risk_lockout_clear():
    """Clear risk lockout for LOCKOUT_CLEAR_TTL_SEC. No auth in v1.2."""
    from app.risk.lockout import clear_lockout_redis
    ok = clear_lockout_redis()
    return {"cleared": ok, "ttl_sec": 3600}


@app.get("/risk/state")
async def get_risk_state():
    """Risk control state: budget, today PnL, consecutive_losses, exposure, lockout. Never raises."""
    from datetime import datetime, timedelta
    try:
        cfg = _risk_config()
        daily_loss_budget_pct = cfg["daily_loss_budget_pct"]
        capital_usd = cfg["capital_usd"]
        daily_loss_budget_usd = (capital_usd * daily_loss_budget_pct / 100.0) if capital_usd > 0 else 0.0
        today_pnl = 0.0
        today_loss_pct = 0.0
        consecutive_losses = 0
        net_exposure_usd = 0.0
        positions_count = 0
        lockout_enabled = False
        lockout_reason = ""
        lockout_until = ""
        status = "OK"
        try:
            pool = await _get_domain_pg_pool()
            async with pool.acquire() as conn:
                failed_row = await conn.fetchrow(
                    """
                    SELECT COUNT(*) AS cnt FROM domain_events
                    WHERE created_at::date = CURRENT_DATE
                      AND event_type = 'MARK_FAILED'
                    """
                )
                if failed_row and failed_row.get("cnt"):
                    consecutive_losses = int(failed_row["cnt"] or 0)

                pos_row = await conn.fetchrow(
                    """
                    SELECT COUNT(*) AS cnt FROM commands_domain
                    WHERE status IN ('PENDING', 'PROCESSING')
                    """
                )
                if pos_row and pos_row.get("cnt"):
                    positions_count = int(pos_row["cnt"] or 0)

                exp_row = await conn.fetchrow(
                    "SELECT current_exposure_usd FROM risk_state WHERE id = 1"
                )
                if exp_row is not None and exp_row.get("current_exposure_usd") is not None:
                    net_exposure_usd = float(exp_row["current_exposure_usd"])
        except Exception as e:
            print(f"[risk/state] query failed: {e}", flush=True)
            status = "UNKNOWN"

        lockout_loss_pct = cfg["lockout_loss_pct"]
        lockout_consec = cfg["lockout_consec_losses"]
        lockout_min = cfg["lockout_minutes"]
        reasons = []
        if today_loss_pct >= lockout_loss_pct:
            reasons.append("daily_loss_pct")
        if consecutive_losses >= lockout_consec:
            reasons.append("consecutive_losses")
        if reasons:
            try:
                from app.risk.lockout import _is_lockout_cleared_redis
                if _is_lockout_cleared_redis():
                    lockout_enabled = False
                    lockout_reason = ""
                else:
                    lockout_enabled = True
                    lockout_reason = "; ".join(reasons)
                    until_dt = datetime.utcnow() + timedelta(minutes=lockout_min)
                    lockout_until = until_dt.isoformat() + "Z"
            except Exception:
                lockout_enabled = True
                lockout_reason = "; ".join(reasons)
                until_dt = datetime.utcnow() + timedelta(minutes=lockout_min)
                lockout_until = until_dt.isoformat() + "Z"
        if reasons and lockout_enabled:
            until_dt = datetime.utcnow() + timedelta(minutes=lockout_min)
            lockout_until = until_dt.isoformat() + "Z"
            try:
                pool = await _get_domain_pg_pool()
                should_append = False
                async with pool.acquire() as conn:
                    last = await conn.fetchrow(
                        """
                        SELECT created_at FROM domain_events
                        WHERE command_id = 'ops-risk-lockout' AND event_type = 'RISK_LOCKOUT'
                        ORDER BY created_at DESC LIMIT 1
                        """
                    )
                if not last or not last.get("created_at"):
                    should_append = True
                else:
                    from datetime import timezone
                    ts = last["created_at"]
                    ts_utc = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts
                    age_sec = (datetime.now(timezone.utc) - ts_utc).total_seconds()
                    if age_sec > 60:
                        should_append = True
                if should_append:
                    await append_domain_event_pool(
                        pool,
                        "ops-risk-lockout",
                        "RISK_LOCKOUT",
                        0,
                        {
                            "enabled": True,
                            "reason": lockout_reason,
                            "until": lockout_until,
                            "today_loss_pct": today_loss_pct,
                            "consecutive_losses": consecutive_losses,
                        },
                    )
            except Exception as e:
                print(f"[risk/state] audit RISK_LOCKOUT failed: {e}", flush=True)

        return {
            "status": status,
            "daily_loss_budget_pct": daily_loss_budget_pct,
            "daily_loss_budget_usd": daily_loss_budget_usd,
            "today_pnl": today_pnl,
            "today_loss_pct": today_loss_pct,
            "consecutive_losses": consecutive_losses,
            "net_exposure_usd": net_exposure_usd,
            "positions_count": positions_count,
            "lockout_enabled": lockout_enabled,
            "lockout_reason": lockout_reason,
            "lockout_until": lockout_until,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "thresholds": {
                "lockout_loss_pct": lockout_loss_pct,
                "lockout_consec_losses": lockout_consec,
                "lockout_minutes": lockout_min,
            },
        }
    except Exception as e:
        print(f"[risk/state] unexpected error: {e}", flush=True)
        return _risk_state_fallback("ERROR")


@app.get("/ops/summary")
async def get_ops_summary(
    minutes: int = Query(30, ge=1, le=1440),
    limit: int = Query(10, ge=1, le=200),
):
    """Return counts (FAILED, POLICY_BLOCK, EXCEPTION, KILL_SWITCH_ON) and recent events in time window."""
    pool = await _get_domain_pg_pool()
    counts = {"FAILED": 0, "POLICY_BLOCK": 0, "EXCEPTION": 0, "KILL_SWITCH_ON": 0}

    async with pool.acquire() as conn:
        # window_start = now - interval 'X minutes'
        failed_row = await conn.fetchrow(
            """
            SELECT COUNT(*) AS cnt FROM commands_domain
            WHERE updated_at >= NOW() - ($1::int * interval '1 minute')
              AND status = 'FAILED'
            """,
            minutes,
        )
        if failed_row:
            counts["FAILED"] = failed_row["cnt"] or 0

        policy_row = await conn.fetchrow(
            """
            SELECT COUNT(*) AS cnt FROM domain_events
            WHERE created_at >= NOW() - ($1::int * interval '1 minute')
              AND event_type = 'POLICY_BLOCK'
            """,
            minutes,
        )
        if policy_row:
            counts["POLICY_BLOCK"] = policy_row["cnt"] or 0

        exc_row = await conn.fetchrow(
            """
            SELECT COUNT(*) AS cnt FROM domain_events
            WHERE created_at >= NOW() - ($1::int * interval '1 minute')
              AND event_type = 'EXCEPTION'
            """,
            minutes,
        )
        if exc_row:
            counts["EXCEPTION"] = exc_row["cnt"] or 0

        kill_row = await conn.fetchrow(
            """
            SELECT COUNT(*) AS cnt FROM domain_events
            WHERE created_at >= NOW() - ($1::int * interval '1 minute')
              AND event_type = 'KILL_SWITCH_ON'
            """,
            minutes,
        )
        if kill_row:
            counts["KILL_SWITCH_ON"] = kill_row["cnt"] or 0

        # recent events
        recent_rows = await conn.fetch(
            """
            SELECT command_id, event_type, payload, created_at
            FROM domain_events
            WHERE created_at >= NOW() - ($1::int * interval '1 minute')
              AND event_type IN ('POLICY_BLOCK', 'EXCEPTION', 'MARK_FAILED', 'KILL_SWITCH_ON')
            ORDER BY created_at DESC
            LIMIT $2
            """,
            minutes,
            limit,
        )

    def iso(v):
        return v.isoformat() if v is not None else None

    recent = []
    import json
    for r in recent_rows:
        payload = _ensure_json_result(r["payload"]) or {}
        cmd_type = None
        if isinstance(payload, dict) and payload.get("type") is not None:
            cmd_type = str(payload["type"])
        summary = _summary_from_payload(payload)
        if summary is None and payload:
            raw = json.dumps(payload, ensure_ascii=False) if isinstance(payload, dict) else str(payload)
            summary = (raw[:240] + "...") if len(raw) > 240 else raw
        recent.append({
            "created_at": iso(r["created_at"]) or "",
            "command_id": r["command_id"] or "",
            "event_type": r["event_type"] or "",
            "cmd_type": cmd_type,
            "summary": summary or "",
        })

    return {
        "window_minutes": minutes,
        "counts": counts,
        "recent": recent,
    }


def _json_dumps(obj) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False)


async def _create_domain_command(cmd_id_prefix: str, cmd_type: str, payload: dict | None = None, cmd_id: str | None = None) -> dict:
    pool = await _get_domain_pg_pool()
    if cmd_id is None:
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


async def _domain_command_response_by_id(domain_id: str) -> dict:
    """Fetch domain command and return response dict (same shape as GET). Raises HTTPException if not found."""
    pool = await _get_domain_pg_pool()
    sql = """
    SELECT id, type, status, attempt, locked_by, locked_at, result, error, payload, created_at, updated_at
    FROM commands_domain WHERE id = $1;
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, domain_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Not Found")

    def iso(v):
        return v.isoformat() if v is not None else None

    payload = _ensure_json_result(row["payload"]) or {}
    result = _ensure_json_result(row["result"]) or {}
    return {
        "id": row["id"],
        "type": row["type"],
        "status": row["status"],
        "attempt": row["attempt"],
        "locked_by": row["locked_by"],
        "locked_at": iso(row["locked_at"]),
        "result": result,
        "error": row["error"],
        "payload": payload,
        "created_at": iso(row["created_at"]),
        "updated_at": iso(row["updated_at"]),
    }


@app.post("/domain-commands/noop")
async def create_domain_noop(request: Request, body: dict = Body(default_factory=dict)):
    """Create NOOP. API-level idempotency via x-idempotency-key: same key -> same command id returned."""
    idempotency_key = (request.headers.get("x-idempotency-key") or "").strip()
    payload = dict(body) if body else {}

    if idempotency_key:
        pool = await _get_domain_pg_pool()
        async with pool.acquire() as conn:
            # Check if key already exists
            row = await conn.fetchrow(
                "SELECT first_command_id FROM idempotency_keys WHERE idempotency_key = $1",
                idempotency_key,
            )
            if row is not None:
                return await _domain_command_response_by_id(row["first_command_id"])

            # Claim key: INSERT ON CONFLICT DO NOTHING (concurrency safe)
            cmd_id = f"noop-{uuid.uuid4()}"
            await conn.execute(
                """
                INSERT INTO idempotency_keys (idempotency_key, first_command_id, first_seen_at, last_seen_at)
                VALUES ($1, $2, NOW(), NOW())
                ON CONFLICT (idempotency_key) DO NOTHING
                """,
                idempotency_key,
                cmd_id,
            )
            # Re-select: if another request won, existing_id != cmd_id
            row = await conn.fetchrow(
                "SELECT first_command_id FROM idempotency_keys WHERE idempotency_key = $1",
                idempotency_key,
            )
            existing_id = row["first_command_id"] if row else None
            if existing_id is not None and existing_id != cmd_id:
                # Lost race: winner may still be creating; retry fetch briefly
                for _ in range(10):
                    try:
                        return await _domain_command_response_by_id(existing_id)
                    except HTTPException as e:
                        if e.status_code == 404:
                            await asyncio.sleep(0.1)
                            continue
                        raise

        # We won: create the command with the claimed id
        payload["idempotency_key"] = idempotency_key
        await _create_domain_command("noop", "NOOP", payload, cmd_id=cmd_id)
        return await _domain_command_response_by_id(cmd_id)

    return await _create_domain_command("noop", "NOOP", payload)


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
    if payload.get("notional_usd") is not None and payload.get("notional") is None:
        payload["notional"] = payload["notional_usd"]
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
        # ops-worker, ops-kill-switch are system command_ids; events may exist without commands_domain row
        if domain_id not in ("ops-worker", "ops-kill-switch"):
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
    SELECT id, type, status, attempt, locked_by, locked_at, result, error, payload, created_at, updated_at
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
            "payload": _ensure_json_result(r["payload"]),
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
    SELECT id, type, status, attempt, locked_by, locked_at, result, error, payload, created_at, updated_at
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

    payload = _ensure_json_result(row["payload"]) or {}
    result = _ensure_json_result(row["result"]) or {}
    if isinstance(result, dict) and result.get("_binance_testnet"):
        payload = dict(payload)
        payload["_binance_testnet"] = result["_binance_testnet"]

    return {
        "id": row["id"],
        "type": row["type"],
        "status": row["status"],
        "attempt": row["attempt"],
        "locked_by": row["locked_by"],
        "locked_at": iso(row["locked_at"]),
        "result": result,
        "error": row["error"],
        "payload": payload,
        "created_at": iso(row["created_at"]),
        "updated_at": iso(row["updated_at"]),
    }

# --- ops state history export (JSON/CSV) ---
from fastapi import Response, Query
import json as _json
import csv as _csv
import io as _io
from datetime import datetime, timedelta, timezone

def _is_prod_exec_mode() -> bool:
    try:
        import os
        v = (os.getenv("EXEC_MODE") or os.getenv("NEXT_PUBLIC_EXEC_MODE") or "").lower()
        return v in ("prod", "production")
    except Exception:
        return False

@app.get("/ops/state/history/export")
async def ops_state_history_export(
    from_ts: str | None = Query(default=None),
    to_ts: str | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=10000),
    event_type: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    source: str | None = Query(default=None),
):
    if _is_prod_exec_mode():
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="export disabled in prod")
    now = datetime.now(timezone.utc)
    if not from_ts:
        from_dt = now - timedelta(days=7)
    else:
        from_dt = datetime.fromisoformat(from_ts.replace("Z", "+00:00"))
    to_dt = datetime.fromisoformat(to_ts.replace("Z", "+00:00")) if to_ts else now

    pool = await _get_domain_pg_pool()
    from app.ops.state_store import get_state_history_export_rows
    rows = await get_state_history_export_rows(
        pool,
        from_dt=from_dt,
        to_dt=to_dt,
        limit=limit,
        event_type=event_type,
        actor=actor,
        source=source,
    )
    out = []
    for r in rows:
        ts_str = r.get("ts", "")
        if hasattr(ts_str, "isoformat"):
            ts_str = ts_str.isoformat()
        else:
            ts_str = str(ts_str) if ts_str else ""
        out.append({
            "ts": ts_str,
            "event_type": r.get("event_type", ""),
            "exec_mode": r.get("exec_mode", ""),
            "actor": r.get("actor", ""),
            "source": r.get("source", ""),
            "payload_json": _json.dumps(r.get("payload_json") or {}, ensure_ascii=False),
        })
    return out

@app.get("/ops/state/history/export.csv")
async def ops_state_history_export_csv(
    from_ts: str | None = Query(default=None),
    to_ts: str | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=10000),
    event_type: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    source: str | None = Query(default=None),
):
    if _is_prod_exec_mode():
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="export disabled in prod")
    now = datetime.now(timezone.utc)
    if not from_ts:
        from_dt = now - timedelta(days=7)
    else:
        from_dt = datetime.fromisoformat(from_ts.replace("Z", "+00:00"))
    to_dt = datetime.fromisoformat(to_ts.replace("Z", "+00:00")) if to_ts else now

    pool = await _get_domain_pg_pool()
    from app.ops.state_store import get_state_history_export_rows
    rows = await get_state_history_export_rows(
        pool,
        from_dt=from_dt,
        to_dt=to_dt,
        limit=limit,
        event_type=event_type,
        actor=actor,
        source=source,
    )

    buf = _io.StringIO()
    w = _csv.writer(buf)
    w.writerow(["ts","event_type","exec_mode","actor","source","payload_json"])
    for r in rows:
        ts_str = r.get("ts", "")
        if hasattr(ts_str, "isoformat"):
            ts_str = ts_str.isoformat()
        else:
            ts_str = str(ts_str) if ts_str else ""
        w.writerow([
            ts_str,
            r.get("event_type", ""),
            r.get("exec_mode", ""),
            r.get("actor", ""),
            r.get("source", ""),
            _json.dumps(r.get("payload_json") or {}, ensure_ascii=False),
        ])
    data = buf.getvalue().encode("utf-8")
    headers = {
        "Content-Disposition": "attachment; filename=ops_state_history_export.csv"
    }
    return Response(content=data, media_type="text/csv; charset=utf-8", headers=headers)
