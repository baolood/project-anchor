"""MF4_BRK4H_4R signal core. Public 4h candles only. No I/O and no orders.

The decision logic lives in this module so the webhook hook and the eval
guard can change without rewriting it. ``decide`` is the only entry the
watcher uses.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


STRATEGY = "MF4_BRK4H_4R"
LOOKBACK = 4
R_MULTIPLE = 4


def decide(
    candles: Sequence[Mapping[str, Any]],
    position: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return triggers and at most one OPEN or EXIT for the last closed bar."""
    view = _triggers(candles)
    signal = None
    if view["ready"]:
        signal = _signal(view, position)
    state = "FLAT"
    if isinstance(position, Mapping) and position.get("side") in {"long", "short"}:
        state = str(position["side"]).upper()
    if signal and signal["type"] == "EXIT":
        state = "FLAT"
    elif signal and signal["type"] == "OPEN":
        state = str(signal["side"]).upper()
    return {
        "strategy": STRATEGY,
        "ready": view["ready"],
        "state": state,
        "trend": view["trend"],
        "long_trigger_gt": view["long_trigger_gt"],
        "short_trigger_lt": view["short_trigger_lt"],
        "close": view["close"],
        "bar_time": view["bar_time"],
        "signal": signal,
        "reason": view["reason"] if signal is None else signal["reason"],
    }


def _triggers(candles: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    usable = [bar for bar in candles if _bar_ok(bar)]
    if len(usable) < LOOKBACK + 1:
        return {
            "ready": False,
            "trend": "unknown",
            "long_trigger_gt": None,
            "short_trigger_lt": None,
            "close": None,
            "bar_time": None,
            "bar_low": None,
            "bar_high": None,
            "reason": "need_more_candles",
        }
    window = usable[-(LOOKBACK + 1) : -1]
    last = usable[-1]
    long_trigger = max(float(bar["high"]) for bar in window)
    short_trigger = min(float(bar["low"]) for bar in window)
    close = float(last["close"])
    mid = (long_trigger + short_trigger) / 2.0
    if close > mid:
        trend = "up"
    elif close < mid:
        trend = "down"
    else:
        trend = "flat"
    return {
        "ready": True,
        "trend": trend,
        "long_trigger_gt": long_trigger,
        "short_trigger_lt": short_trigger,
        "close": close,
        "bar_time": last.get("time"),
        "bar_low": float(last["low"]),
        "bar_high": float(last["high"]),
        "reason": "no_signal",
    }


def _signal(view: Mapping[str, Any], position: Mapping[str, Any] | None) -> dict[str, Any] | None:
    close = float(view["close"])
    side = None
    if isinstance(position, Mapping):
        side = position.get("side")
    if side not in {"long", "short"}:
        if close > float(view["long_trigger_gt"]):
            return _open("long", close, float(view["bar_low"]))
        if close < float(view["short_trigger_lt"]):
            return _open("short", close, float(view["bar_high"]))
        return None
    try:
        sl = float(position["sl"])
        tp = float(position["tp"])
    except (TypeError, ValueError, KeyError):
        return None
    if side == "long" and (close <= sl or close >= tp):
        reason = "stop" if close <= sl else "target"
        return {"type": "EXIT", "side": "long", "price": close, "reason": reason}
    if side == "short" and (close >= sl or close <= tp):
        reason = "stop" if close >= sl else "target"
        return {"type": "EXIT", "side": "short", "price": close, "reason": reason}
    return None


def _open(side: str, price: float, stop: float) -> dict[str, Any] | None:
    distance = abs(price - stop)
    if distance <= 0:
        return None
    if side == "long" and stop >= price:
        return None
    if side == "short" and stop <= price:
        return None
    tp = price + R_MULTIPLE * distance if side == "long" else price - R_MULTIPLE * distance
    return {
        "type": "OPEN",
        "side": side,
        "price": price,
        "sl": stop,
        "tp": tp,
        "reason": "close_through_4h_channel",
    }


def _bar_ok(bar: Mapping[str, Any]) -> bool:
    try:
        high = float(bar["high"])
        low = float(bar["low"])
        close = float(bar["close"])
    except (TypeError, ValueError, KeyError):
        return False
    return high >= low and high >= close >= low
