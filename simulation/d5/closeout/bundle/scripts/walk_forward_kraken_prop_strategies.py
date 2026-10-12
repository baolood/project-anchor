#!/usr/bin/env python3
"""Bounded multi-market walk-forward research for Kraken Prop."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from backtest_kraken_prop_strategy import ema, fetch_futures_ohlc
from research_kraken_prop_strategies import simulate


SignalFn = Callable[[list[dict[str, float]]], list[int]]


def ema_signal(fast_period: int, slow_period: int) -> SignalFn:
    def build(rows: list[dict[str, float]]) -> list[int]:
        closes = [row["close"] for row in rows]
        fast, slow = ema(closes, fast_period), ema(closes, slow_period)
        return [0 if i < slow_period else (1 if fast[i] > slow[i] else -1) for i in range(len(rows))]
    return build


def breakout_signal(lookback: int) -> SignalFn:
    def build(rows: list[dict[str, float]]) -> list[int]:
        signals = [0] * len(rows)
        for i in range(lookback, len(rows)):
            prior = rows[i - lookback:i]
            if rows[i]["close"] > max(row["high"] for row in prior):
                signals[i] = 1
            elif rows[i]["close"] < min(row["low"] for row in prior):
                signals[i] = -1
            else:
                signals[i] = signals[i - 1]
        return signals
    return build


def rsi_values(closes: list[float], period: int = 14) -> list[float | None]:
    values: list[float | None] = [None] * len(closes)
    gains = [0.0]
    losses = [0.0]
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    for i in range(period, len(closes)):
        gain = sum(gains[i - period + 1:i + 1]) / period
        loss = sum(losses[i - period + 1:i + 1]) / period
        values[i] = 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)
    return values


def rsi_signal(lower: float, upper: float, with_trend: bool = False) -> SignalFn:
    def build(rows: list[dict[str, float]]) -> list[int]:
        closes = [row["close"] for row in rows]
        rsi = rsi_values(closes)
        fast, slow = ema(closes, 20), ema(closes, 50)
        signals = [0] * len(rows)
        for i in range(50, len(rows)):
            if rsi[i] is None:
                continue
            long_ok = not with_trend or fast[i] > slow[i]
            short_ok = not with_trend or fast[i] < slow[i]
            if rsi[i] < lower and long_ok:
                signals[i] = 1
            elif rsi[i] > upper and short_ok:
                signals[i] = -1
        return signals
    return build


def strong_trend_signal() -> SignalFn:
    def build(rows: list[dict[str, float]]) -> list[int]:
        closes = [row["close"] for row in rows]
        fast, slow = ema(closes, 50), ema(closes, 100)
        signals = [0] * len(rows)
        for i in range(100, len(rows)):
            strength = abs(fast[i] - slow[i]) / closes[i]
            if strength >= 0.01:
                signals[i] = 1 if fast[i] > slow[i] else -1
        return signals
    return build


def breakout_with_strong_trend_signal() -> SignalFn:
    breakout = breakout_signal(55)
    trend = strong_trend_signal()

    def build(rows: list[dict[str, float]]) -> list[int]:
        breakout_values = breakout(rows)
        trend_values = trend(rows)
        return [
            breakout_values[i]
            if trend_values[i] and breakout_values[i] == trend_values[i]
            else 0
            for i in range(len(rows))
        ]
    return build


def candidates() -> dict[str, SignalFn]:
    return {
        "ema_10_30": ema_signal(10, 30),
        "ema_20_50": ema_signal(20, 50),
        "ema_50_100": ema_signal(50, 100),
        "breakout_10": breakout_signal(10),
        "breakout_20": breakout_signal(20),
        "breakout_55": breakout_signal(55),
        "rsi_25_75": rsi_signal(25, 75),
        "rsi_30_70": rsi_signal(30, 70),
        "rsi_35_65": rsi_signal(35, 65),
        "rsi_trend_35_65": rsi_signal(35, 65, True),
        "rsi_trend_40_60": rsi_signal(40, 60, True),
        "ema_50_100_strength_1pct": strong_trend_signal(),
        "breakout_55_strength_1pct": breakout_with_strong_trend_signal(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Kraken Prop multi-market walk-forward research.")
    parser.add_argument("--symbols", default="PI_XBTUSD,PI_ETHUSD")
    parser.add_argument("--resolution", default="4h")
    parser.add_argument("--lookback-days", type=int, default=730)
    parser.add_argument("--out-json", type=Path, required=True)
    args = parser.parse_args()

    symbols = [item.strip() for item in args.symbols.split(",") if item.strip()]
    all_results: dict[str, dict] = {}
    eligible: list[str] = []
    strategy_builders = candidates()

    market_rows = {
        symbol: fetch_futures_ohlc(
            "https://futures.kraken.com", symbol, args.resolution, args.lookback_days
        )
        for symbol in symbols
    }
    for name, signal_fn in strategy_builders.items():
        folds: list[dict] = []
        total_profit = 0.0
        total_loss = 0.0
        total_trades = 0
        max_drawdown = 0.0
        every_fold_positive = True
        for symbol, rows in market_rows.items():
            signals = signal_fn(rows)
            length = len(rows)
            boundaries = [int(length * value) for value in (0.4, 0.6, 0.8, 1.0)]
            for fold_index in range(3):
                start, end = boundaries[fold_index], boundaries[fold_index + 1]
                metrics = simulate(rows, signals, start, end)
                folds.append({"symbol": symbol, "fold": fold_index + 1, **metrics})
                total_profit += metrics["gross_profit"]
                total_loss += metrics["gross_loss"]
                total_trades += metrics["trades"]
                max_drawdown = max(max_drawdown, metrics["max_drawdown_pct"])
                every_fold_positive = every_fold_positive and metrics["net_pnl"] > 0
        aggregate_pf = total_profit / total_loss if total_loss else None
        passed = (
            every_fold_positive
            and total_trades >= 60
            and aggregate_pf is not None
            and aggregate_pf >= 1.2
            and max_drawdown < 3
        )
        all_results[name] = {
            "eligible": passed,
            "every_fold_positive": every_fold_positive,
            "test_trades": total_trades,
            "aggregate_profit_factor": round(aggregate_pf, 4) if aggregate_pf is not None else None,
            "max_fold_drawdown_pct": round(max_drawdown, 4),
            "folds": folds,
        }
        if passed:
            eligible.append(name)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "result": "PASS" if eligible else "REJECTED",
        "decision": "PAPER_OBSERVATION_ELIGIBLE" if eligible else "NO_STRATEGY_READY",
        "symbols": symbols,
        "resolution": args.resolution,
        "lookback_days": args.lookback_days,
        "candidate_count": len(strategy_builders),
        "walk_forward_rule": "40% warmup followed by three non-overlapping 20% test folds per market",
        "results": all_results,
        "eligible_strategies": eligible,
        "private_api_attempted": False,
        "production_order_sent": False,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"RESULT={payload['result']}")
    print(f"DECISION={payload['decision']}")
    for name, result in all_results.items():
        print(f"STRATEGY={name} ELIGIBLE={result['eligible']} ALL_FOLDS_POSITIVE={result['every_fold_positive']} TRADES={result['test_trades']} PF={result['aggregate_profit_factor']} MAX_FOLD_DD={result['max_fold_drawdown_pct']}")
    print("PRIVATE_API_ATTEMPTED=NO")
    print("PRODUCTION_ORDER_SENT=NO")
    return 0 if eligible else 1


if __name__ == "__main__":
    raise SystemExit(main())
