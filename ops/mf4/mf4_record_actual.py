#!/usr/bin/env python3
"""Record a manual eval snapshot. DEPLOY=NO. No orders.

``--account`` reads a JSON object the operator typed from the Kraken Prop
page and writes ``eval_account.json`` atomically, mode 0640. Kraken Prop has
no API. This script does not call one.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

try:
    from ops.mf4.sealed import sealed_reason
except ImportError:  # host copy runs as a script from its own directory
    from sealed import sealed_reason


ACCOUNT_NAME = "eval_account.json"
FILE_MODE = 0o640
REQUIRED = ("balance", "daily_ref_balance", "daily_ref_at", "snapshot_at")


def write_account(out_dir: Path, account: Mapping[str, Any]) -> Path:
    """Atomically write ``eval_account.json``. Refuses sealed paths."""
    refusal = sealed_reason(out_dir)
    if refusal is not None:
        raise ValueError(refusal)
    missing = [key for key in REQUIRED if account.get(key) in {None, ""}]
    if missing:
        raise ValueError("account_incomplete:" + ",".join(missing))
    if "position" in account and account["position"] is not None and not isinstance(account["position"], Mapping):
        raise ValueError("position_rejected")
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(out_dir, 0o750)
    except OSError:
        pass
    target = out_dir / ACCOUNT_NAME
    if sealed_reason(target) is not None:
        raise ValueError("sealed_line_a")
    payload = json.dumps(dict(account), separators=(",", ":"), sort_keys=True) + "\n"
    temporary = target.with_suffix(".json.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    fd = os.open(temporary, flags, FILE_MODE)
    try:
        os.write(fd, payload.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.chmod(temporary, FILE_MODE)
    os.replace(temporary, target)
    os.chmod(target, FILE_MODE)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write eval_account.json from a manual snapshot")
    parser.add_argument("--account", required=True, help="Path to the operator JSON snapshot")
    parser.add_argument("--out-dir", default=os.environ.get("MF4_OUT_DIR", "/var/lib/anchor-mf4-watcher"))
    args = parser.parse_args(argv)
    source = Path(args.account)
    out_dir = Path(args.out_dir)
    if sealed_reason(source) is not None or sealed_reason(out_dir) is not None:
        print("MF4_RECORD_ACTUAL=REFUSED", file=sys.stderr)
        return 2
    try:
        account = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("MF4_RECORD_ACTUAL=UNREADABLE", file=sys.stderr)
        return 2
    if not isinstance(account, dict):
        print("MF4_RECORD_ACTUAL=REJECTED", file=sys.stderr)
        return 2
    try:
        write_account(out_dir, account)
    except ValueError:
        print("MF4_RECORD_ACTUAL=REJECTED", file=sys.stderr)
        return 2
    print("MF4_RECORD_ACTUAL=WROTE")
    print("DEPLOY=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
