#!/usr/bin/env python3
"""Print the example anchor-control-mcp systemd unit. Does not install it."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "anchor-backend"))

from app.mcp.host_sidecar import render_service_unit, unit_problems  # noqa: E402


def main() -> int:
    text = render_service_unit()
    problems = unit_problems(text)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
