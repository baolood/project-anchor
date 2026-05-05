from shared.schemas import ExecutionTicket, NormalizedCommand, ExecMode, new_ticket_id

from local_box.gate.ticket_signature import sign_ticket
from local_box.audit.event_store import is_executed
import time

# Kill Switch
KILL_SWITCH = False


def set_kill_switch(value: bool):
    global KILL_SWITCH
    KILL_SWITCH = value


def get_kill_switch() -> bool:
    return KILL_SWITCH


def execution_gate(cmd: NormalizedCommand) -> ExecutionTicket:
    if KILL_SWITCH:
        raise Exception("KILL_SWITCH_ACTIVE")

    # 幂等控制
    if is_executed(cmd.command_id):
        raise Exception("DUPLICATE_COMMAND")

    ticket = ExecutionTicket(
        ticket_id=new_ticket_id(),
        command_id=cmd.command_id,
        symbol=cmd.symbol,
        side=cmd.side,
        qty=cmd.qty,
        price=cmd.price,
        mode=cmd.mode,
        issued_at=time.time(),
        signature=""
    )

    ticket.signature = sign_ticket(ticket)

    return ticket
