import os
import time
import hmac
import hashlib
import urllib.parse
import json
from typing import Any, Dict, Optional
import urllib.request
import urllib.error

DEFAULT_BASE = "https://testnet.binancefuture.com"


class BinanceFuturesTestnetExecutor:
    """
    Minimal Binance Futures Testnet executor (no websockets, no order sync loop).
    Uses signed REST calls.
    """

    def __init__(self) -> None:
        self.base = os.getenv("BINANCE_FUTURES_BASE", DEFAULT_BASE).rstrip("/")
        self.api_key = os.getenv("BINANCE_API_KEY", "")
        self.api_secret = os.getenv("BINANCE_API_SECRET", "")
        if not self.api_key or not self.api_secret:
            raise RuntimeError("BINANCE_API_KEY/BINANCE_API_SECRET missing")
        self.recv_window = int(os.getenv("BINANCE_RECV_WINDOW", "5000"))

    def _sign(self, query: str) -> str:
        return hmac.new(
            self.api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def _request(self, method: str, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        ts = int(time.time() * 1000)
        params = dict(params)
        params["timestamp"] = ts
        params["recvWindow"] = self.recv_window

        query = urllib.parse.urlencode(params, doseq=True)
        sig = self._sign(query)
        url = f"{self.base}{path}?{query}&signature={sig}"

        req = urllib.request.Request(url=url, method=method.upper())
        req.add_header("X-MBX-APIKEY", self.api_key)

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"BINANCE_HTTP_{e.code}:{body}") from e
        except Exception as e:
            raise RuntimeError(f"BINANCE_REQ_FAILED:{e}") from e

    def get_mark_price(self, symbol: str) -> float:
        out = self._request("GET", "/fapi/v1/premiumIndex", {"symbol": symbol})
        mp = out.get("markPrice")
        if mp is None:
            raise RuntimeError(f"BINANCE_NO_MARK_PRICE:{out}")
        return float(mp)

    def place_limit_ioc(
        self, symbol: str, side: str, quantity: float, price: float
    ) -> Dict[str, Any]:
        params = {
            "symbol": symbol,
            "side": side,
            "type": "LIMIT",
            "timeInForce": "IOC",
            "quantity": self._fmt_qty(quantity),
            "price": self._fmt_price(price),
            "newOrderRespType": "RESULT",
        }
        return self._request("POST", "/fapi/v1/order", params)

    def _fmt_qty(self, q: float) -> str:
        return f"{q:.3f}".rstrip("0").rstrip(".")

    def _fmt_price(self, p: float) -> str:
        return f"{p:.1f}".rstrip("0").rstrip(".")


def notional_to_qty(symbol: str, notional_usd: float, mark_price: float) -> float:
    """Compute qty ensuring Binance min notional 100 USDT."""
    raw = float(notional_usd) / float(mark_price)
    min_qty_for_100 = 100.0 / float(mark_price) if mark_price else 0.002
    q = max(raw, min_qty_for_100)
    q = round(q, 4)
    if q <= 0:
        q = 0.002  # ~100+ USDT at 50k
    return q
