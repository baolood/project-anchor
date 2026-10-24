"""Refuse Line A and sealed ledger paths. DEPLOY=NO.

Writers under ops/mf4 must not open the Official ledger StateDirectory, the
read-only mirror, the legacy equity CSV, the governance register, or the
PASS LINE freeze record.
"""

from __future__ import annotations

from pathlib import Path


_LINE_A_MARKERS = (
    "affl-v2-official-ledger",
    "anchor-official-ledger",
    "anchor-ledger-mirror",
)
_PROTECTED_FILES = (
    "anchor_fake_fill_equity_v2_official.csv",
    "ANCHOR_C9_GOVERNANCE_REGISTER.jsonl",
    "PROJECT_ANCHOR_PASS_LINE_V1_1_FREEZE_RECORD.md",
)


def sealed_reason(path: Path) -> str | None:
    """Return a refusal reason, or None when the path is writable."""
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    text = str(resolved)
    if "/var/lib/private" in text:
        return "sealed_private_state"
    for part in resolved.parts:
        if part in _PROTECTED_FILES:
            return "sealed_protected_file"
        if part in {"affl-v2-official-ledger", "anchor-official-ledger", "anchor-ledger-mirror"}:
            return "sealed_line_a"
        if part.startswith("anchor-official-ledger"):
            return "sealed_line_a"
        if "affl-v2-official-ledger" in part:
            return "sealed_line_a"
    for marker in _LINE_A_MARKERS:
        if marker in text:
            return "sealed_line_a"
    return None
