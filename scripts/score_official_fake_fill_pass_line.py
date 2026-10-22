#!/usr/bin/env python3
"""Score a copied Official Fake-Fill JSONL against pass line V1.1.

The ledger path is opened read-only. This program does not write that file,
does not open the ledger StateDirectory, and does not place orders.

Exit status is 0 when a report was produced, including when the exam result
is FAIL or NOT_ELIGIBLE. Exit status is 2 when the path is refused or the
timestamps cannot be parsed. The exam grade is the JSON field ``overall``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval_scoring.line_a_pass_line import (  # noqa: E402
    FORBIDDEN_PATH_MARKERS,
    FROZEN_T0,
    GOVERNANCE_REGISTER_PATH,
    ScoringRefusal,
    score_ledger_file,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, help="Regular-file JSONL copy. Not the live StateDirectory.")
    parser.add_argument(
        "--t0",
        default=FROZEN_T0,
        help="Freeze time, ISO-8601 with a timezone. Default is the frozen T0.",
    )
    parser.add_argument("--t-score", default=None, help="Grading time, ISO-8601 with a timezone.")
    parser.add_argument(
        "--governance",
        default=str(GOVERNANCE_REGISTER_PATH),
        help="Governance JSONL. The default file is empty until a row is appended. An empty file is not zero incidents.",
    )
    parser.add_argument(
        "--random-seed",
        default=None,
        help="Pre-registered seed. The freeze left this blank. The expected random-direction book is the binding comparison.",
    )
    parser.add_argument(
        "--funding-cache",
        default=None,
        help="EXTERNAL_PUBLIC_FUNDING_V1 JSON cache. The scorer does not fetch rates.",
    )
    parser.add_argument(
        "--line",
        default=None,
        choices=("A", "B"),
        help="A is the research baseline (C6 and C7 not applicable). B scores C6 and C7.",
    )
    parser.add_argument("--out", default="-", help="Report path, or - for stdout. Cannot be the ledger path.")
    return parser


def _refuse_output(path: Path, ledger: Path) -> str | None:
    if path.resolve() == ledger.resolve():
        return "refusing to overwrite the ledger copy"
    text = str(path.resolve())
    for marker in FORBIDDEN_PATH_MARKERS:
        if marker in text:
            return f"refusing to write under a sealed ledger path containing {marker}"
    return None


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    ledger = Path(args.ledger)
    try:
        report = score_ledger_file(
            ledger,
            t0=args.t0,
            t_score=args.t_score,
            governance_path=args.governance,
            random_seed=args.random_seed,
            funding_cache=args.funding_cache,
            line=args.line,
        )
    except ScoringRefusal as exc:
        print(str(exc), file=sys.stderr)
        return 2
    payload = json.dumps(report, indent=2) + "\n"
    if args.out == "-":
        sys.stdout.write(payload)
        return 0
    out = Path(args.out)
    refusal = _refuse_output(out, ledger)
    if refusal is not None:
        print(refusal, file=sys.stderr)
        return 2
    out.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
