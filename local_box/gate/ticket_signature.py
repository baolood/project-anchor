"""Local signing helper for :func:`execution_gate`.

Mirrors the archived ``execution_service`` draft verifier (SHA256 + shared
secret) so ``local_box`` does not depend on a top-level ``execution_service``
package. Keep in sync with ``docs/archive/execution_service_draft/execution_service/verifier.py`` if that algorithm changes.
"""

from __future__ import annotations

import hashlib

from shared.schemas import ExecutionTicket

SECRET = "anchor-secret"


def sign_ticket(ticket: ExecutionTicket) -> str:
    mode = ticket.mode.value if hasattr(ticket.mode, "value") else str(ticket.mode)
    raw = f"{ticket.ticket_id}:{ticket.command_id}:{ticket.symbol}:{ticket.qty}:{mode}"
    return hashlib.sha256((raw + SECRET).encode()).hexdigest()
