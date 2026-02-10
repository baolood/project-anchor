"""
QUOTE action: local deterministic quote (no external API).
price from payload or hash(symbol); qty = notional / price.
"""
import hashlib
from typing import Any, Dict

from app.actions.protocol import Action, ActionOutput


def _derive_price(symbol: str, side: str) -> float:
    """Stable hash: sha256(symbol) first 8 hex -> int in [10, 100000], then BUY=+0, SELL=+1."""
    h = hashlib.sha256(symbol.encode("utf-8")).hexdigest()[:8]
    base = int(h, 16)
    lo, hi = 10, 100000
    price = lo + (base % (hi - lo + 1))
    if side.upper() == "SELL":
        price += 1
    return round(float(price), 2)


class QuoteAction(Action):
    name = "QUOTE"

    def run_core(self, command: Dict[str, Any]) -> ActionOutput:
        payload = command.get("payload") or {}
        symbol = str(payload.get("symbol") or "BTCUSDT").strip()
        side = str(payload.get("side") or "BUY").strip().upper()
        if side not in ("BUY", "SELL"):
            side = "BUY"
        notional = float(payload.get("notional", 100))
        if notional <= 0:
            notional = 100.0
        price_val = payload.get("price")
        if isinstance(price_val, (int, float)) and price_val > 0:
            price = round(float(price_val), 2)
        else:
            price = _derive_price(symbol, side)
        qty = round(notional / price, 8) if price else 0.0
        result = {
            "ok": True,
            "type": "quote",
            "symbol": symbol,
            "side": side,
            "notional": notional,
            "price": price,
            "qty": qty,
        }
        return {"ok": True, "result": result, "error": None}

    def run(self, command: Dict[str, Any]) -> ActionOutput:
        return self.run_core(command)
