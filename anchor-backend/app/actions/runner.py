"""
DomainCommandRunner: pick one command → policies → pipeline(action) → mark_done / mark_failed.
Emits append-only events at key points (PICKED, POLICY_ALLOW/POLICY_BLOCK, ACTION_OK/ACTION_FAIL, MARK_DONE, MARK_FAILED, EXCEPTION).
No prints inside; returns a result dict for the worker to log.
"""
import json
import time
from typing import Any, Callable, Dict, List, Optional

from app.actions.context import ActionContext
from app.actions.pipeline import run_action_with_pipeline
from app.actions.steps import default_pipeline_steps
from app.policies.runner import run_policies
from app.policies.protocol import Policy


def _result_summary(obj: Any, max_keys: int = 5) -> Dict[str, Any]:
    """Small summary for event payload (<=8KB target)."""
    if obj is None:
        return {}
    if not isinstance(obj, dict):
        return {"result_summary": str(obj)[:200]}
    return {k: obj[k] for k in list(obj.keys())[:max_keys] if k in ("ok", "type", "attempt", "ts", "code", "message")}


class DomainCommandRunner:
    """
    Encapsulates: pick one domain command, resolve action, run it, persist outcome.
    Reuses existing pick_one_domain, mark_done, mark_failed (injected).
    Optional append_event_fn(command_id, event_type, attempt, payload) for audit trail.
    """

    def __init__(
        self,
        pick_one_fn: Callable,
        get_action_fn: Callable[[str], Any],
        mark_done_fn: Callable,
        mark_failed_fn: Callable,
        now_ts_fn: Optional[Callable[[], int]] = None,
        append_event_fn: Optional[Callable] = None,
        policies: Optional[List[Policy]] = None,
        policy_engine: Any = None,
    ):
        self._pick_one = pick_one_fn
        self._get_action = get_action_fn
        self._mark_done = mark_done_fn
        self._mark_failed = mark_failed_fn
        self._now_ts = now_ts_fn or (lambda: int(time.time() * 1000))
        self._append_event = append_event_fn
        self._policies = list(policies) if policies else []
        self._policy_engine = policy_engine

    async def run_one(self) -> Optional[Dict[str, Any]]:
        """
        Pick one PENDING command, run its action, persist DONE or FAILED.
        Returns None if no command was picked; otherwise {"id", "type", "final_status": "DONE"|"FAILED"}.
        Never raises; any exception is turned into FAILED or None.
        """
        try:
            item = await self._pick_one()
        except Exception:
            return None
        if not item:
            return None

        cid = item.get("id") or ""
        cmd_type = (str(item.get("type") or "")).strip().upper()
        attempt = int(item.get("attempt") or 0)
        payload = item.get("payload") or {}
        raw = dict(item)

        if self._append_event:
            try:
                await self._append_event(cid, "PICKED", attempt, {"type": cmd_type})
            except Exception:
                pass

        context = ActionContext(
            now_ts=self._now_ts(),
            command_id=cid,
            cmd_type=cmd_type,
            attempt=attempt,
            payload=payload,
            raw=raw,
        )
        command = context.to_command_dict()

        # Policy guardrails: block => mark_failed + POLICY_BLOCK + MARK_FAILED
        if self._policies and self._policy_engine is not None:
            try:
                allowed, decision = await run_policies(
                    self._policies, context, command, self._policy_engine
                )
            except Exception:
                allowed, decision = True, None
            if not allowed and decision:
                if self._append_event:
                    try:
                        await self._append_event(
                            cid, "POLICY_BLOCK", attempt,
                            {"code": decision.get("code"), "message": decision.get("message"), "detail": decision.get("detail")},
                        )
                    except Exception:
                        pass
                try:
                    reason = decision.get("code") or "POLICY_BLOCK"
                    detail = decision.get("detail") or {"message": decision.get("message")}
                    await self._mark_failed(cid, reason, detail)
                except Exception:
                    pass
                if self._append_event:
                    try:
                        await self._append_event(cid, "MARK_FAILED", attempt, {"error": decision})
                    except Exception:
                        pass
                return {"id": cid, "type": cmd_type, "final_status": "FAILED"}
            if self._append_event and allowed:
                try:
                    await self._append_event(
                        cid, "POLICY_ALLOW", attempt,
                        {"policies": [p.name for p in self._policies]},
                    )
                except Exception:
                    pass

        action = self._get_action(cmd_type)
        if action is None:
            if self._append_event:
                try:
                    await self._append_event(cid, "ACTION_FAIL", attempt, {"error": {"code": "UNKNOWN_TYPE", "type": cmd_type}, "type": cmd_type})
                except Exception:
                    pass
            try:
                await self._mark_failed(cid, "UNKNOWN_TYPE", {"type": cmd_type})
            except Exception:
                pass
            if self._append_event:
                try:
                    await self._append_event(cid, "MARK_FAILED", attempt, {"reason": "UNKNOWN_TYPE", "type": cmd_type})
                except Exception:
                    pass
            return {"id": cid, "type": cmd_type, "final_status": "FAILED"}

        try:
            out = run_action_with_pipeline(action, context, command, default_pipeline_steps)
        except Exception as e:
            out = {
                "ok": False,
                "result": None,
                "error": {"code": "ACTION_EXCEPTION", "message": str(e)},
            }
            if self._append_event:
                try:
                    await self._append_event(cid, "EXCEPTION", attempt, {"code": "ACTION_EXCEPTION", "message": str(e)})
                except Exception:
                    pass

        if self._append_event:
            try:
                if out.get("ok") is True:
                    await self._append_event(cid, "ACTION_OK", attempt, {"result": _result_summary(out.get("result"))})
                else:
                    await self._append_event(cid, "ACTION_FAIL", attempt, {"error": out.get("error"), "type": cmd_type})
            except Exception:
                pass

        try:
            if out.get("ok") is True:
                result = out.get("result")
                if result is not None and "ts" not in result:
                    result = {**result, "ts": self._now_ts()}
                await self._mark_done(cid, result)
                if self._append_event:
                    try:
                        await self._append_event(cid, "MARK_DONE", attempt, {"result_summary": _result_summary(result)})
                    except Exception:
                        pass
                return {"id": cid, "type": cmd_type, "final_status": "DONE"}
            else:
                err = out.get("error")
                reason = (
                    json.dumps(err, ensure_ascii=False)
                    if isinstance(err, dict)
                    else str(err or "ACTION_FAILED")
                )
                detail = err if isinstance(err, dict) else {"error": str(err)}
                await self._mark_failed(cid, reason, detail)
                if self._append_event:
                    try:
                        await self._append_event(cid, "MARK_FAILED", attempt, {"error": detail, "type": cmd_type})
                    except Exception:
                        pass
                return {"id": cid, "type": cmd_type, "final_status": "FAILED"}
        except Exception as e:
            if self._append_event:
                try:
                    await self._append_event(cid, "EXCEPTION", attempt, {"code": "RUNNER_PERSIST", "message": str(e)})
                except Exception:
                    pass
            try:
                await self._mark_failed(
                    cid,
                    "RUNNER_PERSIST_ERROR",
                    {"message": "runner could not persist outcome"},
                )
            except Exception:
                pass
            return {"id": cid, "type": cmd_type, "final_status": "FAILED"}
