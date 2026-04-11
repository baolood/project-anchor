import asyncio
import os
import time
from collections import deque
from typing import Any, Dict, Optional

from sqlalchemy import text

from app.workers import command_worker as cw
from app.actions.protocol import Action, ActionOutput
from app.actions.registry import get_action, init_actions, register
from app.actions.runner import DomainCommandRunner
from app.domain_events import append_domain_event
from app.policies.registry import get_policies, init_policies
from app.risk.lockout import is_lockout_active, is_command_allowed
from app.risk.hard_limits import risk_guard
from app.risk.policy_engine import RiskPolicyEngine

# Ensure actions and policies are registered when worker module loads
init_actions()
init_policies()


class PositionsPreviewAction(Action):
    name = "POSITIONS_PREVIEW"

    def run(self, command: Dict[str, Any]) -> ActionOutput:
        payload = command.get("payload") or {}

        positions = [
            {"symbol": "BTCUSDT", "side": "LONG", "qty": 0.25, "entry_price": 15800.0},
            {"symbol": "ETHUSDT", "side": "SHORT", "qty": 1.5, "entry_price": 3200.0},
        ]

        symbol = payload.get("symbol")
        if symbol is not None:
            if not isinstance(symbol, str) or symbol != "BTCUSDT":
                return {"ok": False, "result": None, "error": {"code": "invalid_symbol"}}
            positions = [item for item in positions if item["symbol"] == symbol]

        side = payload.get("side")
        if side is not None:
            if side not in {"LONG", "SHORT"}:
                return {"ok": False, "result": None, "error": {"code": "invalid_side"}}
            positions = [item for item in positions if item["side"] == side]

        raw_qty_min = payload.get("qty_min")
        if raw_qty_min is not None:
            if isinstance(raw_qty_min, bool):
                return {"ok": False, "result": None, "error": {"code": "invalid_qty_min"}}
            try:
                qty_min = float(raw_qty_min)
            except (TypeError, ValueError):
                return {"ok": False, "result": None, "error": {"code": "invalid_qty_min"}}
            if qty_min <= 0:
                return {"ok": False, "result": None, "error": {"code": "invalid_qty_min"}}
            positions = [item for item in positions if float(item["qty"]) >= qty_min]

        raw_limit = payload.get("limit")
        limit = None
        if raw_limit is not None:
            if isinstance(raw_limit, bool):
                return {"ok": False, "result": None, "error": {"code": "invalid_limit"}}
            try:
                limit = int(raw_limit)
            except (TypeError, ValueError):
                return {"ok": False, "result": None, "error": {"code": "invalid_limit"}}
            if limit <= 0:
                return {"ok": False, "result": None, "error": {"code": "invalid_limit"}}

        order = payload.get("order")
        if order is not None and order not in {"asc", "desc"}:
            return {"ok": False, "result": None, "error": {"code": "invalid_order"}}

        order_by = payload.get("order_by")
        if order_by is not None:
            if order_by != "qty":
                return {"ok": False, "result": None, "error": {"code": "invalid_order_by"}}
            positions = sorted(positions, key=lambda item: float(item["qty"]), reverse=(order == "desc"))
        elif order is not None:
            return {"ok": False, "result": None, "error": {"code": "invalid_order"}}

        if limit is not None:
            positions = positions[:limit]

        return {
            "ok": True,
            "result": {
                "ok": True,
                "type": "positions_preview",
                "positions": positions,
            },
            "error": None,
        }


register(PositionsPreviewAction())


class BalancePreviewAction(Action):
    name = "BALANCE_PREVIEW"

    @staticmethod
    def _normalize_read_only_fetch_failure(message: str) -> ActionOutput:
        error_detail = {
            "code": "read_only_fetch_failed",
            "message": message,
            "normalized_failure": True,
            "failed_stage": "executor/read_only_fetch",
            "failure_scope": "external_dependency",
        }
        return {
            "ok": False,
            "result": {
                "ok": False,
                "type": "balance_preview",
                "read_only": True,
                "normalized_failure": True,
                "failed_stage": "executor/read_only_fetch",
                "failure_scope": "external_dependency",
            },
            "error": error_detail,
        }

    def run(self, command: Dict[str, Any]) -> ActionOutput:
        payload = command.get("payload") or {}

        read_only = payload.get("read_only", False)
        if not isinstance(read_only, bool):
            return {"ok": False, "result": None, "error": {"code": "invalid_read_only"}}

        balances = [
            {"asset": "USDT", "free": 1000.0},
            {"asset": "BTC", "free": 0.5},
        ]

        raw_limit = payload.get("limit")
        limit = None
        if raw_limit is not None:
            if isinstance(raw_limit, bool):
                return {"ok": False, "result": None, "error": {"code": "invalid_limit"}}
            try:
                limit = int(raw_limit)
            except (TypeError, ValueError):
                return {"ok": False, "result": None, "error": {"code": "invalid_limit"}}
            if limit <= 0:
                return {"ok": False, "result": None, "error": {"code": "invalid_limit"}}

        raw_offset = payload.get("offset")
        offset = 0
        if raw_offset is not None:
            if isinstance(raw_offset, bool):
                return {"ok": False, "result": None, "error": {"code": "invalid_offset"}}
            try:
                offset = int(raw_offset)
            except (TypeError, ValueError):
                return {"ok": False, "result": None, "error": {"code": "invalid_offset"}}
            if offset < 0:
                return {"ok": False, "result": None, "error": {"code": "invalid_offset"}}

        sort = payload.get("sort")
        if sort is not None and sort != "asset":
            return {"ok": False, "result": None, "error": {"code": "invalid_sort"}}

        view = payload.get("view")
        if view is not None and view != "summary":
            return {"ok": False, "result": None, "error": {"code": "invalid_view"}}

        include_zero = payload.get("include_zero", False)
        if not isinstance(include_zero, bool):
            return {"ok": False, "result": None, "error": {"code": "invalid_include_zero"}}
        if include_zero and not any(item["asset"] == "ETH" for item in balances):
            balances = list(balances) + [{"asset": "ETH", "free": 0.0}]

        asset = payload.get("asset")
        if asset is not None:
            if not isinstance(asset, str) or not cw.SYMBOL_RE.fullmatch(asset):
                return {"ok": False, "result": None, "error": {"code": "invalid_asset"}}

        if read_only:
            try:
                from app.executors.binance_futures_testnet import BinanceFuturesTestnetExecutor

                ex = BinanceFuturesTestnetExecutor()
                raw_balances = ex._request("GET", "/fapi/v2/balance", {})
                if not isinstance(raw_balances, list):
                    raise RuntimeError(f"BINANCE_BALANCE_SHAPE:{raw_balances}")

                balances = []
                for item in raw_balances:
                    asset_name = str(item.get("asset") or "").strip().upper()
                    if not asset_name:
                        continue
                    free_raw = item.get("availableBalance")
                    if free_raw is None:
                        free_raw = item.get("balance")
                    balances.append({"asset": asset_name, "free": float(free_raw or 0.0)})
            except Exception as e:
                return self._normalize_read_only_fetch_failure(str(e))

        if asset is not None:
            balances = [item for item in balances if item["asset"] == asset]
            if not balances:
                return {"ok": False, "result": None, "error": {"code": "invalid_asset"}}

        if sort == "asset":
            balances = sorted(balances, key=lambda item: item["asset"])

        if offset:
            balances = balances[offset:]

        if limit is not None:
            balances = balances[:limit]

        if view == "summary":
            result = {
                "ok": True,
                "type": "balance_preview",
                "view": "summary",
                "balance_count": len(balances),
                "total_free": sum(float(item["free"]) for item in balances),
            }
        else:
            result = {
                "ok": True,
                "type": "balance_preview",
                "balances": balances,
            }
        if read_only:
            result["read_only"] = True

        return {"ok": True, "result": result, "error": None}


register(BalancePreviewAction())


class QuotePreviewAction(Action):
    name = "QUOTE"

    def run(self, command: Dict[str, Any]) -> ActionOutput:
        payload = command.get("payload") or {}

        symbol = payload.get("symbol")
        if not symbol:
            return {"ok": False, "result": None, "error": {"code": "missing_symbol"}}
        if not isinstance(symbol, str) or symbol != "BTCUSDT":
            return {"ok": False, "result": None, "error": {"code": "invalid_symbol"}}

        side = payload.get("side")
        if side is not None and side not in {"BUY", "SELL"}:
            return {"ok": False, "result": None, "error": {"code": "invalid_side"}}

        raw_notional = payload.get("notional")
        notional = None
        if raw_notional is not None:
            if isinstance(raw_notional, bool):
                return {"ok": False, "result": None, "error": {"code": "invalid_notional"}}
            try:
                notional = float(raw_notional)
            except (TypeError, ValueError):
                return {"ok": False, "result": None, "error": {"code": "invalid_notional"}}
            if notional <= 0:
                return {"ok": False, "result": None, "error": {"code": "invalid_notional"}}

        bid = 15995.0
        ask = 16005.0
        result = {
            "ok": True,
            "type": "quote",
            "symbol": symbol,
            "bid": bid,
            "ask": ask,
            "mid": (bid + ask) / 2.0,
        }
        if side is not None:
            result["side"] = side
        if notional is not None:
            result["notional"] = notional

        return {"ok": True, "result": result, "error": None}


register(QuotePreviewAction())


class PreviewAction(Action):
    name = "PREVIEW"

    def run(self, command: Dict[str, Any]) -> ActionOutput:
        payload = command.get("payload") or {}

        symbol = payload.get("symbol")
        if not symbol:
            return {"ok": False, "result": None, "error": {"code": "missing_symbol"}}
        if not isinstance(symbol, str) or symbol != "BTCUSDT":
            return {"ok": False, "result": None, "error": {"code": "invalid_symbol"}}

        side = payload.get("side", "BUY")
        if side not in {"BUY", "SELL"}:
            return {"ok": False, "result": None, "error": {"code": "invalid_side"}}

        raw_notional = payload.get("notional")
        notional = None
        if raw_notional is not None:
            if isinstance(raw_notional, bool):
                return {"ok": False, "result": None, "error": {"code": "invalid_notional"}}
            try:
                notional = float(raw_notional)
            except (TypeError, ValueError):
                return {"ok": False, "result": None, "error": {"code": "invalid_notional"}}
            if notional <= 0:
                return {"ok": False, "result": None, "error": {"code": "invalid_notional"}}

        result = {
            "ok": True,
            "type": "preview",
            "symbol": symbol,
            "side": side,
            "preview_price": 16000.0,
        }
        if notional is not None:
            result["notional"] = notional

        return {"ok": True, "result": result, "error": None}


register(PreviewAction())


class CancelAction(Action):
    name = "CANCEL"

    def run(self, command: Dict[str, Any]) -> ActionOutput:
        payload = command.get("payload") or {}

        command_id = payload.get("command_id") or payload.get("id")
        if not command_id:
            return {"ok": False, "result": None, "error": {"code": "missing_command_id"}}

        reason = payload.get("reason")
        if reason is not None:
            if not isinstance(reason, str) or not reason.strip():
                return {"ok": False, "result": None, "error": {"code": "invalid_reason"}}

        result = {
            "ok": True,
            "type": "cancel",
            "canceled_command_id": str(command_id),
            "status": "canceled",
            "ts": cw._now_ts(),
        }
        if reason is not None:
            result["reason"] = reason

        return {"ok": True, "result": result, "error": None}


register(CancelAction())


class NoopAction(Action):
    name = "NOOP"

    def run(self, command: Dict[str, Any]) -> ActionOutput:
        payload = command.get("payload")
        if payload is None:
            payload = {}

        mode = payload.get("mode")
        if mode is not None:
            if not isinstance(mode, str) or mode not in {"basic"}:
                return {"ok": False, "result": None, "error": {"code": "invalid_mode"}}

        return {
            "ok": True,
            "result": {
                "ok": True,
                "type": "noop",
                "echo": payload,
            },
            "error": None,
        }


register(NoopAction())


class ExecuteAction(Action):
    name = "EXECUTE"

    def run(self, command: Dict[str, Any]) -> ActionOutput:
        payload = command.get("payload")
        target_id = None
        if isinstance(payload, dict):
            target_id = payload.get("command_id") or payload.get("id")
        if not target_id:
            return {"ok": False, "result": None, "error": {"code": "missing_command_id"}}

        return {
            "ok": True,
            "result": {
                "ok": True,
                "type": "execute",
                "executed_command_id": str(target_id),
                "ts": cw._now_ts(),
            },
            "error": None,
        }


register(ExecuteAction())


class PingAction(Action):
    name = "PING"

    def run(self, command: Dict[str, Any]) -> ActionOutput:
        payload = command.get("payload") or {}

        mode = payload.get("mode")
        if mode is not None:
            if not isinstance(mode, str) or mode not in {"basic"}:
                return {"ok": False, "result": None, "error": {"code": "invalid_mode"}}

        return {
            "ok": True,
            "result": {
                "ok": True,
                "type": "ping",
                "ts": cw._now_ts(),
            },
            "error": None,
        }


register(PingAction())


class OrderAction(Action):
    name = "ORDER"

    def run(self, command: Dict[str, Any]) -> ActionOutput:
        payload = command.get("payload") or {}

        symbol = payload.get("symbol")
        if not symbol:
            return {"ok": False, "result": None, "error": {"code": "missing_symbol"}}
        if not isinstance(symbol, str) or symbol != "BTCUSDT":
            return {"ok": False, "result": None, "error": {"code": "invalid_symbol"}}

        side = payload.get("side")
        if side not in {"BUY", "SELL"}:
            return {"ok": False, "result": None, "error": {"code": "invalid_side"}}

        raw_notional = payload.get("notional")
        if raw_notional is None:
            return {"ok": False, "result": None, "error": {"code": "missing_notional"}}
        if isinstance(raw_notional, bool):
            return {"ok": False, "result": None, "error": {"code": "invalid_notional"}}
        try:
            notional = float(raw_notional)
        except (TypeError, ValueError):
            return {"ok": False, "result": None, "error": {"code": "invalid_notional"}}
        if notional <= 0:
            return {"ok": False, "result": None, "error": {"code": "invalid_notional"}}
        if notional > 1000:
            return {"ok": False, "result": None, "error": {"code": "notional_too_large"}}

        return {
            "ok": True,
            "result": {
                "ok": True,
                "type": "order",
                "symbol": symbol,
                "side": side,
                "notional": notional,
                "ts": cw._now_ts(),
            },
            "error": None,
        }


register(OrderAction())


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
        hard_limit_cmd_type = "QUOTE" if cmd_type == "ORDER" else cmd_type
        return await risk_guard(engine, hard_limit_cmd_type, p)

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
    """Domain-only worker: run domain_worker_loop (commands_domain)."""
    from app.system.strict_check import run_strict_check
    await run_strict_check()

    await domain_worker_loop()


if __name__ == "__main__":
    asyncio.run(main())
