"""
Append-only domain event log. Never raises; failures are logged and swallowed.
Used by runner (SQLAlchemy engine) and retry endpoint (asyncpg pool).
"""
import json
from typing import Any, Dict, Optional

# Max payload size to store (bytes, approximate)
PAYLOAD_MAX_BYTES = 8000


def _trim_payload(payload: Dict[str, Any], max_bytes: int = PAYLOAD_MAX_BYTES) -> Dict[str, Any]:
    """Keep only small fields (code, message, type, attempt, ts, etc.) and truncate if needed."""
    if not payload:
        return {}
    # Prefer small summary keys
    small = {}
    for k in ("code", "message", "type", "attempt", "ts", "error", "result_summary"):
        if k in payload and payload[k] is not None:
            v = payload[k]
            if isinstance(v, (str, int, float, bool)):
                small[k] = v
            elif isinstance(v, dict):
                small[k] = {str(kk): (str(vv)[:200] if isinstance(vv, str) else vv) for kk, vv in list(v.items())[:10]}
            else:
                small[k] = str(v)[:500]
    out = small or dict(payload)
    raw = json.dumps(out, ensure_ascii=False)
    if len(raw.encode("utf-8")) <= max_bytes:
        return out
    # Truncate one big value
    for k in list(out.keys()):
        if isinstance(out[k], str) and len(out[k]) > 500:
            out[k] = out[k][:500] + "..."
            break
        if isinstance(out[k], dict):
            out[k] = {"_truncated": True, "keys": list(out[k].keys())[:5]}
            break
    return out


async def append_domain_event(
    command_id: str,
    event_type: str,
    attempt: int,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Append one event using SQLAlchemy engine (worker/runner). Never raises.
    """
    try:
        from sqlalchemy import text
        from app.workers import command_worker as cw
        pl = _trim_payload(payload or {})
        pl_json = json.dumps(pl, ensure_ascii=False)
        async with cw.engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO domain_events (command_id, event_type, attempt, payload)
                    VALUES (:command_id, :event_type, :attempt, (:payload)::jsonb)
                    """
                ),
                {"command_id": command_id, "event_type": event_type, "attempt": attempt, "payload": pl_json},
            )
    except Exception as e:
        print(f"[domain_events] append failed: {e}", flush=True)
    _maybe_notify_telegram(command_id, event_type, payload or {})


def _maybe_notify_telegram(
    command_id: str, event_type: str, payload: Dict[str, Any]
) -> None:
    """Notify critical events to Telegram (throttled). Never raises."""
    if event_type not in {"EXCEPTION", "POLICY_BLOCK", "KILL_SWITCH_ON"}:
        return
    try:
        from app.ops.notify import send_telegram
        cmd_type = (payload.get("type") or payload.get("code") or "")
        throttle_key = f"{event_type}_{cmd_type}" if cmd_type else event_type
        code = payload.get("code", "")
        msg = payload.get("message", "")
        text = f"[{event_type}] id={command_id} type={cmd_type} attempt={payload.get('attempt','')} code={code} message={msg}"
        send_telegram(text[:500], throttle_key=throttle_key)
    except Exception as e:
        print(f"[domain_events] notify_telegram failed: {e}", flush=True)


async def append_domain_event_pool(
    pool: Any,
    command_id: str,
    event_type: str,
    attempt: int,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Append one event using asyncpg pool (API/main). Never raises.
    """
    try:
        pl = _trim_payload(payload or {})
        pl_json = json.dumps(pl, ensure_ascii=False)
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO domain_events (command_id, event_type, attempt, payload)
                VALUES ($1, $2, $3, $4::jsonb)
                """,
                command_id,
                event_type,
                attempt,
                pl_json,
            )
    except Exception as e:
        print(f"[domain_events] append_pool failed: {e}", flush=True)
