from shared.schemas import ExecutionTicket
import hashlib

SECRET = "anchor-secret"


def sign_ticket(ticket: ExecutionTicket) -> str:
    mode = ticket.mode.value if hasattr(ticket.mode, "value") else str(ticket.mode)
    raw = f"{ticket.ticket_id}:{ticket.command_id}:{ticket.symbol}:{ticket.qty}:{mode}"
    return hashlib.sha256((raw + SECRET).encode()).hexdigest()


def verify_ticket(ticket: ExecutionTicket) -> bool:
    expected = sign_ticket(ticket)
    return expected == ticket.signature
