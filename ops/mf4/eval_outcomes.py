#!/usr/bin/env python3
"""Append-only manual eval trade log. DEPLOY=NO. No orders.

Kraken Prop has no API. The operator records each closed eval trade into
``eval_trades.jsonl``. The file is append-only. Line A, the sealed ledger,
the legacy equity CSV, the governance register, and the PASS LINE freeze
record are refused and never opened.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

try:
    from ops.mf4.sealed import sealed_reason
except ImportError:  # host copy runs as a script from its own directory
    from sealed import sealed_reason


TRADES_NAME = "eval_trades.jsonl"
FILE_MODE = 0o640
PROP_FEE = 0.0004
_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
_REASONS = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
REQUIRED = (
    "signal_id",
    "side",
    "entry",
    "stop",
    "tp",
    "size",
    "realized_r",
    "commission",
    "funding",
    "mae",
    "mfe",
    "duration_h",
    "exit_reason",
)


def trade_risk_usd(size: Any, entry: Any, stop: Any) -> float | None:
    """Dollar risk implied by size = risk / (|entry-stop| + 2*0.0004*entry)."""
    size_f = _finite(size)
    entry_f = _finite(entry)
    stop_f = _finite(stop)
    if size_f is None or entry_f is None or stop_f is None:
        return None
    if size_f <= 0 or entry_f <= 0:
        return None
    return size_f * (abs(entry_f - stop_f) + 2.0 * PROP_FEE * entry_f)


def append_trade(
    out_dir: Path,
    trade: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> Path:
    """Append one trade. Refuses sealed paths and never rewrites earlier lines."""
    refusal = sealed_reason(out_dir)
    if refusal is not None:
        raise ValueError(refusal)
    record = normalize_trade(trade, now=now)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(out_dir, 0o750)
    except OSError:
        pass
    target = out_dir / TRADES_NAME
    if sealed_reason(target) is not None:
        raise ValueError("sealed_line_a")
    if target.is_symlink():
        raise ValueError("symlink_refused")
    line = json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, FILE_MODE)
    try:
        info = os.fstat(fd)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise ValueError("not_a_regular_file")
        os.write(fd, line.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        os.chmod(target, FILE_MODE)
    except OSError:
        pass
    return target


def read_trades(path: Path, *, max_bytes: int = 8 * 1024 * 1024) -> list[dict[str, Any]]:
    """Read a trade log. Symlinks and sealed paths are refused."""
    if sealed_reason(path) is not None:
        raise ValueError("sealed_line_a")
    if path.is_symlink():
        raise ValueError("symlink_refused")
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ValueError("unreadable") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("not_a_regular_file")
        if info.st_size > max_bytes:
            raise ValueError("too_large")
        blob = os.read(fd, max_bytes)
    finally:
        os.close(fd)
    rows: list[dict[str, Any]] = []
    for line in blob.decode("utf-8", errors="replace").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def summarize_costs(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Sum and average commission and funding, both expressed in R."""
    commission_r = 0.0
    funding_r = 0.0
    realized: list[float] = []
    priced = 0
    for row in rows:
        risk = trade_risk_usd(row.get("size"), row.get("entry"), row.get("stop"))
        realized_r = _finite(row.get("realized_r"))
        if realized_r is not None:
            realized.append(realized_r)
        fee = _finite(row.get("commission"))
        carry = _finite(row.get("funding"))
        if risk is None or risk <= 0 or fee is None or carry is None:
            continue
        priced += 1
        commission_r += fee / risk
        funding_r += carry / risk
    mean_r = None if not realized else sum(realized) / len(realized)
    return {
        "trades": len(rows),
        "priced": priced,
        "commission_r_sum": _round(commission_r),
        "funding_r_sum": _round(funding_r),
        "cost_r_sum": _round(commission_r + funding_r),
        "commission_r_mean": None if priced == 0 else _round(commission_r / priced),
        "funding_r_mean": None if priced == 0 else _round(funding_r / priced),
        "cost_r_mean": None if priced == 0 else _round((commission_r + funding_r) / priced),
        "mean_realized_r": None if mean_r is None else _round(mean_r),
    }


def normalize_trade(trade: Mapping[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Return the canonical JSON object for one appended line."""
    if not isinstance(trade, Mapping):
        raise ValueError("trade_rejected")
    missing = [key for key in REQUIRED if key not in trade]
    if missing:
        raise ValueError("trade_incomplete")
    signal_id = trade.get("signal_id")
    if not isinstance(signal_id, str) or _ID.fullmatch(signal_id.strip()) is None:
        raise ValueError("signal_id_rejected")
    side = trade.get("side")
    if side not in {"long", "short"}:
        raise ValueError("side_rejected")
    exit_reason = trade.get("exit_reason")
    if not isinstance(exit_reason, str) or _REASONS.fullmatch(exit_reason.strip()) is None:
        raise ValueError("exit_reason_rejected")
    entry = _required_finite(trade.get("entry"), positive=True)
    stop = _required_finite(trade.get("stop"), positive=True)
    tp = _required_finite(trade.get("tp"), positive=True)
    size = _required_finite(trade.get("size"), positive=True)
    realized_r = _required_finite(trade.get("realized_r"))
    commission = _required_finite(trade.get("commission"))
    funding = _required_finite(trade.get("funding"))
    mae = _required_finite(trade.get("mae"))
    mfe = _required_finite(trade.get("mfe"))
    duration_h = _required_finite(trade.get("duration_h"))
    if duration_h < 0:
        raise ValueError("duration_rejected")
    record = {
        "v": 1,
        "signal_id": signal_id.strip(),
        "side": side,
        "entry": entry,
        "stop": stop,
        "tp": tp,
        "size": size,
        "realized_r": realized_r,
        "commission": commission,
        "funding": funding,
        "mae": mae,
        "mfe": mfe,
        "duration_h": duration_h,
        "exit_reason": exit_reason.strip(),
        "recorded_at": _stamp(now),
    }
    if "gap_h" in trade and trade.get("gap_h") is not None:
        gap = _required_finite(trade.get("gap_h"), positive=True)
        record["gap_h"] = gap
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append one manual eval trade, or summarise costs")
    parser.add_argument("--trade", help="Path to one trade JSON object")
    parser.add_argument("--summary", action="store_true", help="Print the cost summary and do not append")
    parser.add_argument("--out-dir", default=os.environ.get("MF4_OUT_DIR", "/var/lib/anchor-mf4-watcher"))
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir)
    if sealed_reason(out_dir) is not None:
        print("EVAL_TRADE=REFUSED", file=sys.stderr)
        return 2
    target = out_dir / TRADES_NAME
    if args.summary:
        if not target.exists():
            print("EVAL_TRADE=SUMMARY")
            print(json.dumps(summarize_costs([]), separators=(",", ":"), sort_keys=True))
            print("DEPLOY=NO")
            return 0
        try:
            rows = read_trades(target)
        except ValueError:
            print("EVAL_TRADE=REFUSED", file=sys.stderr)
            return 2
        print("EVAL_TRADE=SUMMARY")
        print(json.dumps(summarize_costs(rows), separators=(",", ":"), sort_keys=True))
        print("DEPLOY=NO")
        return 0
    if not args.trade:
        print("EVAL_TRADE=REJECTED", file=sys.stderr)
        return 2
    source = Path(args.trade)
    if sealed_reason(source) is not None:
        print("EVAL_TRADE=REFUSED", file=sys.stderr)
        return 2
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("EVAL_TRADE=UNREADABLE", file=sys.stderr)
        return 2
    try:
        append_trade(out_dir, payload)
    except ValueError as exc:
        code = str(exc)
        if code.startswith("sealed") or code in {"symlink_refused", "not_a_regular_file"}:
            print("EVAL_TRADE=REFUSED", file=sys.stderr)
        else:
            print("EVAL_TRADE=REJECTED", file=sys.stderr)
        return 2
    print("EVAL_TRADE=APPENDED")
    print("DEPLOY=NO")
    return 0


def _required_finite(value: Any, *, positive: bool = False) -> float:
    number = _finite(value)
    if number is None:
        raise ValueError("number_rejected")
    if positive and number <= 0:
        raise ValueError("number_rejected")
    return number


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float, str)):
        try:
            number = float(str(value).strip())
        except (TypeError, ValueError):
            return None
        if number != number or number in {float("inf"), float("-inf")}:
            return None
        return number
    return None


def _round(value: float) -> float:
    return round(value, 6)


def _stamp(now: datetime | None) -> str:
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    raise SystemExit(main())
