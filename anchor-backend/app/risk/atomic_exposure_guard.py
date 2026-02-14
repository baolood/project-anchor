"""
Atomic exposure guard: lock risk_state row, check limit, increment in one transaction.
Uses risk_state table (single-row ledger). On allow: reserves exposure. Never raises except RiskError.
"""
from decimal import Decimal

from sqlalchemy import text


class RiskError(Exception):
    """Raised when exposure limit exceeded."""
    pass


async def atomic_exposure_guard(conn, notional: float, max_exposure_usd: float) -> float:
    """
    Atomically: lock risk_state, check current+notional <= max, then increment.
    If over limit, raises RiskError. Caller must NOT commit on error.
    Returns new exposure (current + notional) on success, for leverage/drawdown checks.
    conn: async SQLAlchemy connection (from engine.begin() or similar).
    """
    notional_dec = Decimal(str(notional))
    max_dec = Decimal(str(max_exposure_usd))

    r = await conn.execute(
        text("SELECT current_exposure_usd FROM risk_state WHERE id=1 FOR UPDATE")
    )
    row = r.mappings().first()
    if not row:
        raise RiskError("risk_state row missing")
    current = Decimal(str(row["current_exposure_usd"]))
    total = current + notional_dec

    if total > max_dec:
        raise RiskError("NET_EXPOSURE_EXCEEDED")

    await conn.execute(
        text("""
            UPDATE risk_state
            SET current_exposure_usd = current_exposure_usd + :notional,
                updated_at = NOW()
            WHERE id = 1
        """),
        {"notional": float(notional)},
    )
    return float(current + notional_dec)
