from shared.schemas import ExecutionTicket, StrategyIntent, Stage, Status
from local_box.audit.event_store import (
    append_event,
    get_execution_receipt,
    list_events,
    list_pending_dispatches,
    mark_dispatch_retry,
    mark_dispatch_done,
    mark_executed,
    register_dispatch,
)
from local_box.gate.execution_gate import execution_gate
from local_box.normalize.command_normalizer import normalize_intent
from local_box.policy.policy_engine import evaluate_policy
from local_box.risk.risk_core import evaluate_risk
from risk_engine.client import get_receipt, send_ticket


MAX_DISPATCH_RETRIES = 3


def _retry_delay_seconds(retry_count: int) -> float:
    # First retry starts at 1s, then 2s / 4s / 8s...
    return min(60.0, float(2 ** max(0, retry_count - 1)))


def run_intent(intent: StrategyIntent) -> dict:
    cmd = normalize_intent(intent)
    append_event(
        command_id=cmd.command_id,
        stage=Stage.NORMALIZATION,
        status=Status.ACCEPTED,
        payload={"symbol": cmd.symbol, "side": cmd.side, "mode": cmd.mode.value},
    )

    risk_result = evaluate_risk(cmd)
    if risk_result.status != Status.ACCEPTED:
        append_event(
            command_id=cmd.command_id,
            stage=Stage.RISK,
            status=Status.REJECTED,
            payload=risk_result.data or {"reason": risk_result.reason},
        )
        return {
            "status": Status.FAILED.value,
            "stage": Stage.RISK.value,
            "reason": risk_result.reason,
            "detail": risk_result.data,
            "command_id": cmd.command_id,
            "events": [e.__dict__ for e in list_events(cmd.command_id)],
        }
    append_event(
        command_id=cmd.command_id,
        stage=Stage.RISK,
        status=Status.ACCEPTED,
        payload=risk_result.data or {},
    )

    policy_result = evaluate_policy(cmd)
    if policy_result.status != Status.ACCEPTED:
        append_event(
            command_id=cmd.command_id,
            stage=Stage.POLICY,
            status=Status.REJECTED,
            payload=policy_result.data or {"reason": policy_result.reason},
        )
        return {
            "status": Status.FAILED.value,
            "stage": Stage.POLICY.value,
            "reason": policy_result.reason,
            "detail": policy_result.data,
            "command_id": cmd.command_id,
            "events": [e.__dict__ for e in list_events(cmd.command_id)],
        }
    append_event(
        command_id=cmd.command_id,
        stage=Stage.POLICY,
        status=Status.ACCEPTED,
        payload=policy_result.data or {},
    )

    from local_box.self_check.checks import run_self_check, should_block_execution

    self_check_result = run_self_check()
    if should_block_execution(self_check_result):
        blocking_failures = [
            item.get("name")
            for item in (self_check_result.get("checks") or [])
            if item.get("blocking") and item.get("status") == "FAIL"
        ]
        append_event(
            command_id=cmd.command_id,
            stage=Stage.EXECUTION_GATE,
            status=Status.REJECTED,
            payload={
                "code": "SELF_CHECK_BLOCKED",
                "blocked": True,
                "blocked_by": "self_check",
                "blocking_failures": blocking_failures,
                "self_check": self_check_result,
            },
        )
        return {
            "ok": False,
            "code": "SELF_CHECK_BLOCKED",
            "blocked": True,
            "blocked_by": "self_check",
            "blocking_failures": blocking_failures,
            "status": Status.FAILED.value,
            "stage": Stage.EXECUTION_GATE.value,
            "command_id": cmd.command_id,
            "detail": {"self_check": self_check_result},
            "events": [e.__dict__ for e in list_events(cmd.command_id)],
        }

    try:
        ticket = execution_gate(cmd)
    except Exception as e:
        append_event(
            command_id=cmd.command_id,
            stage=Stage.EXECUTION_GATE,
            status=Status.REJECTED,
            payload={"reason": str(e)},
        )
        return {
            "status": Status.FAILED.value,
            "stage": Stage.EXECUTION_GATE.value,
            "reason": str(e),
            "command_id": cmd.command_id,
            "events": [e.__dict__ for e in list_events(cmd.command_id)],
        }

    append_event(
        command_id=cmd.command_id,
        stage=Stage.EXECUTION_GATE,
        status=Status.ACCEPTED,
        payload={"ticket_id": ticket.ticket_id},
    )

    register_dispatch(
        ticket_id=ticket.ticket_id,
        command_id=cmd.command_id,
        payload=ticket.__dict__,
    )
    try:
        response = send_ticket(ticket)
    except Exception as e:
        retry_state = mark_dispatch_retry(
            ticket.ticket_id,
            str(e),
            delay_sec=_retry_delay_seconds(1),
            max_retries=MAX_DISPATCH_RETRIES,
        )
        append_event(
            command_id=cmd.command_id,
            stage=Stage.EXECUTOR,
            status=Status.FAILED,
            payload={"error": str(e), "retry": retry_state},
        )
        return {
            "status": Status.FAILED.value,
            "stage": Stage.EXECUTOR.value,
            "command_id": cmd.command_id,
            "reason": str(e),
            "detail": retry_state,
            "events": [e.__dict__ for e in list_events(cmd.command_id)],
        }
    try:
        body = response.json()
    except Exception:
        body = {"error": response.text}

    if response.ok:
        mark_executed(cmd.command_id)
        mark_dispatch_done(ticket.ticket_id)
        append_event(
            command_id=cmd.command_id,
            stage=Stage.EXECUTOR,
            status=Status.DONE,
            payload=body,
        )
        return {
            "status": Status.DONE.value,
            "stage": Stage.EXECUTOR.value,
            "command_id": cmd.command_id,
            "result": body,
            "events": [e.__dict__ for e in list_events(cmd.command_id)],
        }

    retry_state = mark_dispatch_retry(
        ticket.ticket_id,
        body.get("error", "EXECUTION_FAILED"),
        delay_sec=_retry_delay_seconds(1),
        max_retries=MAX_DISPATCH_RETRIES,
    )
    append_event(
        command_id=cmd.command_id,
        stage=Stage.EXECUTOR,
        status=Status.FAILED,
        payload={"response": body, "retry": retry_state},
    )
    return {
        "status": Status.FAILED.value,
        "stage": Stage.EXECUTOR.value,
        "command_id": cmd.command_id,
        "reason": body.get("error", "EXECUTION_FAILED"),
        "detail": {"response": body, "retry": retry_state},
        "events": [e.__dict__ for e in list_events(cmd.command_id)],
    }


def recover_pending_dispatches() -> list[dict]:
    recovered: list[dict] = []
    for row in list_pending_dispatches(ready_only=True):
        ticket_id = row["ticket_id"]
        command_id = row["command_id"]
        retry_count = int(row.get("retry_count") or 0)

        receipt = get_execution_receipt(ticket_id)
        if receipt is None:
            try:
                resp = get_receipt(ticket_id)
                if resp.ok:
                    receipt = resp.json()
            except Exception:
                receipt = None

        if receipt is None:
            payload = row.get("payload") or {}
            try:
                response = send_ticket(ExecutionTicket(**payload))
                body = response.json()
            except Exception as e:
                retry_state = mark_dispatch_retry(
                    ticket_id,
                    str(e),
                    delay_sec=_retry_delay_seconds(retry_count + 1),
                    max_retries=MAX_DISPATCH_RETRIES,
                )
                append_event(
                    command_id=command_id,
                    stage=Stage.EXECUTOR,
                    status=Status.FAILED,
                    payload={"recovered": True, "error": str(e), "retry": retry_state},
                )
                recovered.append(
                    {
                        "command_id": command_id,
                        "ticket_id": ticket_id,
                        "status": retry_state["status"],
                    }
                )
                continue

            if response.ok:
                mark_executed(command_id)
                mark_dispatch_done(ticket_id)
                append_event(
                    command_id=command_id,
                    stage=Stage.EXECUTOR,
                    status=Status.DONE,
                    payload={"recovered": True, **body},
                )
                recovered.append(
                    {
                        "command_id": command_id,
                        "ticket_id": ticket_id,
                        "status": "RECOVERED_DONE",
                    }
                )
            else:
                retry_state = mark_dispatch_retry(
                    ticket_id,
                    body.get("error", "EXECUTION_FAILED"),
                    delay_sec=_retry_delay_seconds(retry_count + 1),
                    max_retries=MAX_DISPATCH_RETRIES,
                )
                append_event(
                    command_id=command_id,
                    stage=Stage.EXECUTOR,
                    status=Status.FAILED,
                    payload={"recovered": True, "response": body, "retry": retry_state},
                )
                recovered.append(
                    {
                        "command_id": command_id,
                        "ticket_id": ticket_id,
                        "status": retry_state["status"],
                    }
                )
            continue

        status = receipt.get("status")
        payload = receipt.get("payload") or {}

        if status == Status.DONE.value:
            mark_executed(command_id)
            mark_dispatch_done(ticket_id)
            append_event(
                command_id=command_id,
                stage=Stage.EXECUTOR,
                status=Status.DONE,
                payload={"recovered": True, **payload},
            )
            recovered.append(
                {
                    "command_id": command_id,
                    "ticket_id": ticket_id,
                    "status": "RECOVERED_DONE",
                }
            )
        elif status == Status.FAILED.value:
            mark_dispatch_done(ticket_id)
            append_event(
                command_id=command_id,
                stage=Stage.EXECUTOR,
                status=Status.FAILED,
                payload={"recovered": True, **payload},
            )
            recovered.append(
                {
                    "command_id": command_id,
                    "ticket_id": ticket_id,
                    "status": "RECOVERED_FAILED",
                }
            )

    return recovered
