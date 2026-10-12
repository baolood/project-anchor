#!/usr/bin/env python3
"""Compare fixed Kraken Prop strategy families with a holdout period."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from backtest_kraken_prop_strategy import ema, fetch_futures_ohlc


SignalFn = Callable[[list[dict[str, float]]], list[int]]


def trend_signals(rows: list[dict[str, float]]) -> list[int]:
    closes = [row["close"] for row in rows]
    fast, slow = ema(closes, 20), ema(closes, 50)
    return [0 if i < 50 else (1 if fast[i] > slow[i] else -1) for i in range(len(rows))]


def breakout_signals(rows: list[dict[str, float]]) -> list[int]:
    signals = [0] * len(rows)
    for i in range(20, len(rows)):
        prior_high = max(row["high"] for row in rows[i - 20:i])
        prior_low = min(row["low"] for row in rows[i - 20:i])
        if rows[i]["close"] > prior_high:
            signals[i] = 1
        elif rows[i]["close"] < prior_low:
            signals[i] = -1
        else:
            signals[i] = signals[i - 1]
    return signals


def rsi_signals(rows: list[dict[str, float]]) -> list[int]:
    closes = [row["close"] for row in rows]
    signals = [0] * len(rows)
    gains = [0.0]
    losses = [0.0]
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    for i in range(14, len(rows)):
        avg_gain = sum(gains[i - 13:i + 1]) / 14
        avg_loss = sum(losses[i - 13:i + 1]) / 14
        rsi = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
        if rsi < 30:
            signals[i] = 1
        elif rsi > 70:
            signals[i] = -1
    return signals


def rsi_trend_pullback_signals(rows: list[dict[str, float]]) -> list[int]:
    closes = [row["close"] for row in rows]
    fast, slow = ema(closes, 20), ema(closes, 50)
    signals = [0] * len(rows)
    gains = [0.0]
    losses = [0.0]
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    for i in range(50, len(rows)):
        avg_gain = sum(gains[i - 13:i + 1]) / 14
        avg_loss = sum(losses[i - 13:i + 1]) / 14
        rsi = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
        if fast[i] > slow[i] and rsi < 40:
            signals[i] = 1
        elif fast[i] < slow[i] and rsi > 60:
            signals[i] = -1
    return signals


def simulate(rows: list[dict[str, float]], signals: list[int], start: int, end: int) -> dict[str, Any]:
    equity = 5000.0
    peak = equity
    max_drawdown = 0.0
    trades: list[float] = []
    position: dict[str, float] | None = None
    notional = 1000.0
    fee = notional * 0.0004 * 2
    slippage = 0.0002

    for i in range(max(start, 50), end):
        row, signal = rows[i], signals[i]
        previous_signal = signals[i - 1] if i > 0 else 0
        new_signal_event = bool(signal) and signal != previous_signal
        if position is None and new_signal_event:
            entry = row["close"] * (1 + slippage * signal)
            position = {
                "side": float(signal),
                "entry": entry,
                "stop": entry * (1 - signal * 0.01),
                "target": entry * (1 + signal * 0.015),
            }
            continue
        if position is None:
            continue

        side = position["side"]
        exit_price = None
        if side > 0:
            if row["low"] <= position["stop"]:
                exit_price = position["stop"] * (1 - slippage)
            elif row["high"] >= position["target"]:
                exit_price = position["target"] * (1 - slippage)
        else:
            if row["high"] >= position["stop"]:
                exit_price = position["stop"] * (1 + slippage)
            elif row["low"] <= position["target"]:
                exit_price = position["target"] * (1 + slippage)
        if exit_price is None and signal and signal != int(side):
            exit_price = row["close"] * (1 - slippage * side)

        if exit_price is not None:
            pnl = notional * ((exit_price / position["entry"] - 1) * side) - fee
            trades.append(pnl)
            equity += pnl
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, (peak - equity) / 5000 * 100)
            position = None

    wins = [pnl for pnl in trades if pnl > 0]
    losses = [pnl for pnl in trades if pnl <= 0]
    gross_loss = abs(sum(losses))
    return {
        "trades": len(trades),
        "net_pnl": round(sum(trades), 4),
        "win_rate_pct": round(len(wins) / len(trades) * 100, 2) if trades else 0.0,
        "profit_factor": round(sum(wins) / gross_loss, 4) if gross_loss else None,
        "gross_profit": round(sum(wins), 4),
        "gross_loss": round(gross_loss, 4),
        "max_drawdown_pct": round(max_drawdown, 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Kraken Prop fixed-strategy holdout research.")
    parser.add_argument("--symbol", default="PI_XBTUSD")
    parser.add_argument("--resolution", default="1h")
    parser.add_argument("--lookback-days", type=int, default=365)
    parser.add_argument("--out-json", type=Path, required=True)
    args = parser.parse_args()
    rows = fetch_futures_ohlc(
        "https://futures.kraken.com", args.symbol, args.resolution, args.lookback_days
    )
    split = int(len(rows) * 0.7)
    strategies: dict[str, SignalFn] = {
        "ema_trend_long_short": trend_signals,
        "donchian_breakout_long_short": breakout_signals,
        "rsi_mean_reversion_long_short": rsi_signals,
        "rsi_trend_pullback_long_short": rsi_trend_pullback_signals,
    }
    results: dict[str, Any] = {}
    eligible: list[str] = []
    for name, signal_fn in strategies.items():
        signals = signal_fn(rows)
        train = simulate(rows, signals, 0, split)
        holdout = simulate(rows, signals, split, len(rows))
        passed = (
            train["net_pnl"] > 0
            and holdout["net_pnl"] > 0
            and holdout["trades"] >= 10
            and holdout["profit_factor"] is not None
            and holdout["profit_factor"] >= 1.2
            and holdout["max_drawdown_pct"] < 3
        )
        results[name] = {"train": train, "holdout": holdout, "eligible": passed}
        if passed:
            eligible.append(name)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "result": "PASS" if eligible else "REJECTED",
        "decision": "PAPER_OBSERVATION_ELIGIBLE" if eligible else "NO_STRATEGY_READY",
        "data_source": "Kraken public Futures OHLC",
        "symbol": args.symbol,
        "resolution": args.resolution,
        "bars": len(rows),
        "split_index": split,
        "strategies": results,
        "eligible_strategies": eligible,
        "private_api_attempted": False,
        "production_order_sent": False,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"RESULT={payload['result']}")
    print(f"DECISION={payload['decision']}")
    for name, result in results.items():
        holdout = result["holdout"]
        print(f"STRATEGY={name} ELIGIBLE={result['eligible']} HOLDOUT_TRADES={holdout['trades']} HOLDOUT_PNL={holdout['net_pnl']} HOLDOUT_PF={holdout['profit_factor']} HOLDOUT_DD={holdout['max_drawdown_pct']}")
    print("PRIVATE_API_ATTEMPTED=NO")
    print("PRODUCTION_ORDER_SENT=NO")
    return 0 if eligible else 1


if __name__ == "__main__":
    raise SystemExit(main())
