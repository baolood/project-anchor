"""
Risk v2 Hard Limits: per-command validation before execution.
Validates: single_trade_risk, net_exposure, leverage, daily_drawdown, stop_required.
Used by worker to reject risk commands that exceed limits.
"""
import os
from typing import Any, Optional, Tuple

from sqlalchemy import text

RISK_HARD_LIMITS_BLOCK_REASON_PREFIX = "RISK_HARD_LIMITS_"
TRADE_CMD_TYPES = frozenset({"QUOTE"})


def _float(s: str | None, default: float) -> float:
    if not s or not str(s).strip():
        return default
    try:
        return float(str(s).strip())
    except ValueError:
        return default


def _risk_hard_limits_config() -> dict:
    return {
        "max_single_trade_risk_pct": _float(os.getenv("MAX_SINGLE_TRADE_RISK_PCT"), 0.5),
        "max_net_exposure_pct": _float(os.getenv("MAX_NET_EXPOSURE_PCT"), 30.0),
        "max_leverage": _float(os.getenv("MAX_LEVERAGE"), 5.0),
        "max_daily_drawdown_pct": _float(os.getenv("MAX_DAILY_DRAWDOWN_PCT"), 3.0),
        "capital_usd": _float(os.getenv("CAPITAL_USD"), 0.0),
    }


def _get_notional(payload: dict) -> float:
    """Extract notional from QUOTE payload (notional or notional_usd). Default 0."""
    v = payload.get("notional") or payload.get("notional_usd")
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def validate_single_trade_risk(
    cmd_type: str, payload: dict, capital: float, max_pct: float
) -> Tuple[bool, Optional[str]]:
    """Single trade notional as % of capital must be <= max_pct."""
    if cmd_type not in TRADE_CMD_TYPES:
        return (True, None)
    if capital <= 0:
        return (True, None)
    notional = _get_notional(payload)
    if notional <= 0:
        return (True, None)
    pct = (notional / capital) * 100.0
    if pct > max_pct:
        return (False, f"SINGLE_TRADE_RISK_EXCEEDED:{pct:.2f}%>={max_pct}%")
    return (True, None)


def validate_net_exposure(
    cmd_type: str,
    payload: dict,
    current_exposure_usd: float,
    capital: float,
    max_pct: float,
) -> Tuple[bool, Optional[str]]:
    """(current_exposure + new notional) / capital * 100 must be <= max_pct."""
    if cmd_type not in TRADE_CMD_TYPES:
        return (True, None)
    if capital <= 0:
        return (True, None)
    notional = _get_notional(payload)
    total = current_exposure_usd + notional
    pct = (total / capital) * 100.0
    if pct > max_pct:
        return (False, f"NET_EXPOSURE_EXCEEDED:{pct:.2f}%>={max_pct}%")
    return (True, None)


def validate_leverage(
    cmd_type: str,
    payload: dict,
    current_exposure_usd: float,
    capital: float,
    max_leverage: float,
) -> Tuple[bool, Optional[str]]:
    """(current_exposure + new notional) / capital must be <= max_leverage."""
    if cmd_type not in TRADE_CMD_TYPES:
        return (True, None)
    if capital <= 0:
        return (True, None)
    notional = _get_notional(payload)
    total = current_exposure_usd + notional
    lev = total / capital
    if lev > max_leverage:
        return (False, f"LEVERAGE_EXCEEDED:{lev:.2f}>={max_leverage}")
    return (True, None)


def validate_daily_drawdown(
    today_loss_pct: float, max_pct: float
) -> Tuple[bool, Optional[str]]:
    """today_loss_pct must be < max_pct."""
    if today_loss_pct >= max_pct:
        return (False, f"DAILY_DRAWDOWN_EXCEEDED:{today_loss_pct:.2f}%>={max_pct}%")
    return (True, None)


def validate_stop_required(cmd_type: str, payload: dict) -> Tuple[bool, Optional[str]]:
    """QUOTE must have stop_loss or stop_price in payload."""
    if cmd_type not in TRADE_CMD_TYPES:
        return (True, None)
    has_stop = (
        payload.get("stop_loss") is not None
        or payload.get("stop_price") is not None
    )
    if not has_stop:
        return (False, "STOP_REQUIRED:missing stop_loss or stop_price")
    return (True, None)


async def _fetch_risk_context(engine: Any) -> Tuple[float, float]:
    """
    Returns (current_exposure_usd, today_loss_pct). Never raises.
    current_exposure = sum(notional) from QUOTE where status IN ('DONE','PENDING').
    RUNNING is excluded (the command being validated is RUNNING).
    """
    exposure = 0.0
    today_loss_pct = 0.0
    try:
        async with engine.begin() as conn:
            r = await conn.execute(
                text(
                    """
                    SELECT COALESCE(SUM(
                        COALESCE(
                            (payload->>'notional')::float,
                            (payload->>'notional_usd')::float,
                            0
                        )
                    ), 0) AS exposure
                    FROM commands_domain
                    WHERE type = 'QUOTE' AND status IN ('DONE', 'PENDING')
                    """
                )
            )
            row = r.mappings().first()
            if row and row.get("exposure") is not None:
                exposure = float(row["exposure"])
    except Exception:
        pass
    return (exposure, today_loss_pct)


async def risk_guard(
    engine: Any,
    cmd_type: str,
    payload: dict,
    current_exposure_usd: Optional[float] = None,
    today_loss_pct: Optional[float] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Run all hard limit validations. Returns (ok, fail_reason).
    ok=True means pass; ok=False means block with fail_reason.
    Non-trade commands always pass.
    """
    disable = (os.getenv("RISK_HARD_LIMITS_DISABLE") or "").strip()
    if disable == "1":
        return (True, None)
    cfg = _risk_hard_limits_config()

    cmd_type = (cmd_type or "").strip().upper()
    if cmd_type not in TRADE_CMD_TYPES:
        return (True, None)

    if not isinstance(payload, dict):
        payload = {}

    if current_exposure_usd is None or today_loss_pct is None:
        exposure, loss_pct = await _fetch_risk_context(engine)
        current_exposure_usd = current_exposure_usd if current_exposure_usd is not None else exposure
        today_loss_pct = today_loss_pct if today_loss_pct is not None else loss_pct

    capital = cfg["capital_usd"]
    max_single = cfg["max_single_trade_risk_pct"]
    max_exposure = cfg["max_net_exposure_pct"]
    max_lev = cfg["max_leverage"]
    max_dd = cfg["max_daily_drawdown_pct"]

    # 1) stop required
    ok, reason = validate_stop_required(cmd_type, payload)
    if not ok:
        return (False, f"{RISK_HARD_LIMITS_BLOCK_REASON_PREFIX}{reason}")

    # 2) single trade risk
    ok, reason = validate_single_trade_risk(cmd_type, payload, capital, max_single)
    if not ok:
        return (False, f"{RISK_HARD_LIMITS_BLOCK_REASON_PREFIX}{reason}")

    # 3) net exposure (atomic risk_state or computed)
    notional = _get_notional(payload)
    max_exposure_usd_val = capital * (max_exposure / 100.0)
    exposure_for_leverage = current_exposure_usd
    if (os.getenv("RISK_EXPOSURE_ATOMIC") or "").strip() == "1":
        try:
            async with engine.begin() as conn:
                from app.risk.atomic_exposure_guard import atomic_exposure_guard, RiskError
                exposure_for_leverage = await atomic_exposure_guard(
                    conn, notional, max_exposure_usd_val
                )
        except RiskError as e:
            return (False, f"{RISK_HARD_LIMITS_BLOCK_REASON_PREFIX}{str(e)}")
    else:
        ok, reason = validate_net_exposure(
            cmd_type, payload, current_exposure_usd, capital, max_exposure
        )
        if not ok:
            return (False, f"{RISK_HARD_LIMITS_BLOCK_REASON_PREFIX}{reason}")

    # 4) leverage (in atomic mode, exposure_for_leverage = new total; pass prev for validate)
    leverage_current = (
        exposure_for_leverage - notional
        if (os.getenv("RISK_EXPOSURE_ATOMIC") or "").strip() == "1"
        else current_exposure_usd
    )
    ok, reason = validate_leverage(
        cmd_type, payload, leverage_current, capital, max_lev
    )
    if not ok:
        return (False, f"{RISK_HARD_LIMITS_BLOCK_REASON_PREFIX}{reason}")

    # 5) daily drawdown
    ok, reason = validate_daily_drawdown(today_loss_pct, max_dd)
    if not ok:
        return (False, f"{RISK_HARD_LIMITS_BLOCK_REASON_PREFIX}{reason}")

    return (True, None)
