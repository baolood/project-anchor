#!/usr/bin/env python3
"""One forward dry-run round, executed locally inside the isolated copy.

Contract:
  * Runs exactly ONE round. Never a catch-up round: a missed tick means a missed round,
    and that is what the run log will show.
  * Retries only the SAME round id (a retry, not a new round) when the engine report
    write failed (return code 4); the engine state is already saved, so a retry cannot
    duplicate fills or fees.
  * Reads PUBLIC market data only. No credentials, no account, no orders.
  * Appends one JSON line per attempt to the run log, including the real start/end
    instants so sleep, network failure or errors are visible rather than hidden.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TRACK = HERE / "track_kraken_prop_forward_observation.py"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one forward dry-run round.")
    parser.add_argument("--round-index", type=int, required=True)
    parser.add_argument("--run-log", type=Path,
                        default=Path("reports/kraken_prop/dry-run-v1.jsonl"))
    parser.add_argument("--max-attempts", type=int, default=3)
    args = parser.parse_args()

    run_log = args.run_log if args.run_log.is_absolute() else ROOT / args.run_log
    run_log.parent.mkdir(parents=True, exist_ok=True)
    round_id = uuid.uuid4().hex          # stable across retries of THIS round

    returncode: int | None = None
    for attempt in range(1, args.max_attempts + 1):
        started = utcnow()
        proc = subprocess.run(
            [sys.executable, str(TRACK), "--round-id", round_id],
            cwd=str(ROOT), capture_output=True, text=True,
        )
        returncode = proc.returncode
        entry = {
            "round_index": args.round_index,
            "round_id": round_id,
            "attempt": attempt,
            "started_at": started,
            "finished_at": utcnow(),
            "returncode": returncode,
            "stdout_tail": proc.stdout.strip().splitlines()[-8:],
            "stderr_tail": proc.stderr.strip().splitlines()[-4:],
        }
        with run_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        if returncode != 4:              # 4 = B report write failed -> retry same round
            break

    return returncode if returncode is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
