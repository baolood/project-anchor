#!/usr/bin/env python3
"""Backtest a conservative long-only Kraken Prop strategy on public OHLC data."""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def ema(values: list[float], period: int) -> list[float]:
    alpha = 2 / (period + 1)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1 - alpha) * result[-1])
    return result


def fetch_ohlc(api_url: str, pair: str, interval: int) -> list[dict[str, float]]:
    query = urllib.parse.urlencode({"pair": pair, "interval": interval})
    request = urllib.request.Request(
        f"{api_url.rstrip('/')}/0/public/OHLC?{query}",
        headers={"User-Agent": "project-anchor/kraken-prop-backtest"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("error"):
        raise RuntimeError(f"kraken_ohlc_error:{payload['error']}")
    result = payload.get("result", {})
    rows = next((value for key, value in result.items() if key != "last"), None)
    if not isinstance(rows, list) or len(rows) < 100:
        raise RuntimeError("insufficient_ohlc_rows")
    return [
        {
            "time": float(row[0]),
            "open": float(row[1]),
            "high": float(row[2]),
            "low": float(row[3]),
            "close": float(row[4]),
        }
        for row in rows[:-1]
    ]


def fetch_futures_ohlc(
    api_url: str,
    symbol: str,
    resolution: str,
    lookback_days: int = 365,
) -> list[dict[str, Any]]:
    """Fetch closed Kraken futures candles and stamp NOMINAL bar boundaries.

    Every returned row carries, in addition to its existing keys, two additive
    UTC ISO-8601 strings computed here (once) from the candle's open instant and
    the resolution step:

        bar_open_at  = the candle's open instant
        bar_close_at = bar_open_at + one resolution step

    ``bar_close_at`` is the NOMINAL bar close. It is derived purely from the bar
    schedule: it is NOT proof that the data reached the system, and it is NOT the
    computation time or the publish time of anything derived from the bar. Callers
    must REUSE these row values instead of recomputing them.
    """
    resolution_seconds = {
        "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
        "1h": 3600, "4h": 14400, "12h": 43200, "1d": 86400, "1w": 604800,
    }
    step = resolution_seconds.get(resolution)
    if step is None:
        raise ValueError("unsupported_futures_resolution")
    end = int(time.time())
    cursor = end - lookback_days * 86400
    candles: list[dict[str, Any]] = []
    while cursor < end:
        query = urllib.parse.urlencode({"from": cursor, "to": end, "count": 2000})
        request = urllib.request.Request(
            f"{api_url.rstrip('/')}/api/charts/v1/trade/{symbol}/{resolution}?{query}",
            headers={"User-Agent": "project-anchor/kraken-prop-backtest"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        page = payload.get("candles")
        if not isinstance(page, list) or not page:
            break
        candles.extend(page)
        next_cursor = int(float(page[-1]["time"]) / 1000) + step
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        if not payload.get("more_candles"):
            break
        time.sleep(0.25)
    if len(candles) < 100:
        raise RuntimeError("insufficient_futures_ohlc_rows")
    deduplicated = {int(float(row["time"])): row for row in candles}
    rows = [
        {
            "time": float(row["time"]) / 1000,
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        }
        for _, row in sorted(deduplicated.items())
    ]
    rows = sorted(rows, key=lambda row: row["time"])[:-1]
    for row in rows:
        # Nominal bar boundaries, computed once here from the open instant and the
        # resolution step. These are schedule-derived, not arrival/publish evidence.
        open_seconds = row["time"]
        row["bar_open_at"] = datetime.fromtimestamp(open_seconds, timezone.utc).isoformat()
        row["bar_close_at"] = datetime.fromtimestamp(open_seconds + step, timezone.utc).isoformat()
    return rows


def run_backtest(rows: list[dict[str, float]], config: dict[str, Any]) -> dict[str, Any]:
    closes = [row["close"] for row in rows]
    fast = ema(closes, config["fast_ema"])
    slow = ema(closes, config["slow_ema"])
    equity = config["starting_equity"]
    peak = equity
    max_drawdown = 0.0
    position: dict[str, float] | None = None
    trades: list[dict[str, Any]] = []
    fee_rate = config["commission_bps_per_side"] / 10_000
    slippage_rate = config["slippage_bps_per_side"] / 10_000

    for index in range(config["slow_ema"] + 1, len(rows)):
        row = rows[index]
        if position is None:
            crossed_up = fast[index - 1] <= slow[index - 1] and fast[index] > slow[index]
            if crossed_up and row["close"] > fast[index]:
                entry = row["close"] * (1 + slippage_rate)
                position = {
                    "entry": entry,
                    "entry_time": row["time"],
                    "stop": entry * (1 - config["stop_loss_pct"] / 100),
                    "target": entry * (1 + config["take_profit_pct"] / 100),
                }
            continue

        exit_price = None
        reason = ""
        if row["low"] <= position["stop"]:
            exit_price = position["stop"] * (1 - slippage_rate)
            reason = "stop_loss"
        elif row["high"] >= position["target"]:
            exit_price = position["target"] * (1 - slippage_rate)
            reason = "take_profit"
        elif fast[index - 1] >= slow[index - 1] and fast[index] < slow[index]:
            exit_price = row["close"] * (1 - slippage_rate)
            reason = "trend_exit"

        if exit_price is not None:
            gross_return = exit_price / position["entry"] - 1
            fees = config["notional"] * fee_rate * 2
            pnl = config["notional"] * gross_return - fees
            equity += pnl
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, (peak - equity) / config["starting_equity"] * 100)
            trades.append({
                "entry_time": datetime.fromtimestamp(position["entry_time"], timezone.utc).isoformat(),
                "exit_time": datetime.fromtimestamp(row["time"], timezone.utc).isoformat(),
                "reason": reason,
                "pnl": round(pnl, 4),
            })
            position = None

    wins = [trade for trade in trades if trade["pnl"] > 0]
    losses = [trade for trade in trades if trade["pnl"] <= 0]
    gross_profit = sum(trade["pnl"] for trade in wins)
    gross_loss = abs(sum(trade["pnl"] for trade in losses))
    return {
        "bars": len(rows),
        "period_start": datetime.fromtimestamp(rows[0]["time"], timezone.utc).isoformat(),
        # LEGACY SEMANTICS (documented, value unchanged): `period_end` holds the OPEN
        # time of the last closed candle, not its close. The nominal close of that
        # candle is exposed separately (per row) as `bar_close_at`.
        "period_end": datetime.fromtimestamp(rows[-1]["time"], timezone.utc).isoformat(),
        "trade_count": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(len(wins) / len(trades) * 100, 2) if trades else 0.0,
        "net_pnl": round(equity - config["starting_equity"], 4),
        "return_pct": round((equity / config["starting_equity"] - 1) * 100, 4),
        "max_drawdown_pct": round(max_drawdown, 4),
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else None,
        "open_position_at_end": position is not None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Kraken Prop public-data strategy backtest.")
    parser.add_argument("--pair", default="XBTUSD")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--data-source", choices=("spot", "futures"), default="futures")
    parser.add_argument("--symbol", default="PI_XBTUSD")
    parser.add_argument("--resolution", default="1h")
    parser.add_argument("--lookback-days", type=int, default=365)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--api-url", default="")
    args = parser.parse_args()

    config = {
        "starting_equity": 5000.0,
        "notional": 1000.0,
        "fast_ema": 20,
        "slow_ema": 50,
        "stop_loss_pct": 1.0,
        "take_profit_pct": 1.5,
        "commission_bps_per_side": 4.0,
        "slippage_bps_per_side": 2.0,
    }
    if args.data_source == "futures":
        api_url = args.api_url or "https://futures.kraken.com"
        rows = fetch_futures_ohlc(api_url, args.symbol, args.resolution, args.lookback_days)
        market_name = args.symbol
        interval_name = args.resolution
        data_source = "Kraken public Futures REST OHLC"
    else:
        api_url = args.api_url or "https://api.kraken.com"
        rows = fetch_ohlc(api_url, args.pair, args.interval)
        market_name = args.pair
        interval_name = str(args.interval)
        data_source = "Kraken public Spot REST OHLC proxy"
    metrics = run_backtest(rows, config)
    pass_rules = {
        "positive_net_pnl": metrics["net_pnl"] > 0,
        "profit_factor_at_least_1_2": metrics["profit_factor"] is not None and metrics["profit_factor"] >= 1.2,
        "max_drawdown_below_internal_3_pct": metrics["max_drawdown_pct"] < 3,
        "at_least_10_closed_trades": metrics["trade_count"] >= 10,
    }
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "result": "PASS" if all(pass_rules.values()) else "REJECTED",
        "decision": "PAPER_OBSERVATION_ELIGIBLE" if all(pass_rules.values()) else "STRATEGY_NOT_READY",
        "data_source": data_source,
        "market": market_name,
        "interval": interval_name,
        "strategy": "EMA20/EMA50 long-only crossover with fixed stop and target",
        "config": config,
        "metrics": metrics,
        "pass_rules": pass_rules,
        "credential_file_read": False,
        "private_api_attempted": False,
        "production_order_sent": False,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"RESULT={payload['result']}")
    print(f"DECISION={payload['decision']}")
    for key, value in metrics.items():
        print(f"{key.upper()}={value}")
    print("PRIVATE_API_ATTEMPTED=NO")
    print("PRODUCTION_ORDER_SENT=NO")
    return 0 if payload["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
