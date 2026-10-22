"""Read-only Official V2 row-hash verifier.

Vendored from ``affl_v2/engine.py`` in the Mac Official runner bundle
``affl-v2-official-auto-ingest-runtime.tgz``.

- That ``engine.py`` SHA-256 is
  ``299569516edda10e6464246457a5d3e6149ac56900fac04be90fd5fbcef1d1c8``.
- The r2.2 deploy-candidate ``engine.py`` SHA-256 is
  ``cd40e5a4186dd3314450388b91a30f06176d97040236a111f5a2093de3506e45``.
  Its ``canonical_json``, ``sha256_hex``, ``_row_body_for_hash``, and
  ``compute_row_hash`` are byte-identical to the bundle copy.
- ``GENESIS_PREV_HASH`` is ``affl_v2/config.py`` line 130: ``"GENESIS"``.

Evidence recorded by the Founder on 2026-10-22: this recipe, recomputed
read-only over a 2026-10-10 copy of the Official ledger, matched 808/808
``row_hash`` values and found 0 link breaks. This checkout does not contain
that copy, so the scorer does not repeat that count.

Re-check this file if the writer changes. A later writer hash is not this
recipe. This module does not write a ledger and does not import the writer.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping, Tuple

GENESIS_PREV_HASH = "GENESIS"
GOVERNANCE_GENESIS_PREV_HASH = "GOVERNANCE_GENESIS"

ENGINE_PY_SHA256 = "299569516edda10e6464246457a5d3e6149ac56900fac04be90fd5fbcef1d1c8"
ENGINE_PY_R22_SHA256 = "cd40e5a4186dd3314450388b91a30f06176d97040236a111f5a2093de3506e45"
ENGINE_SOURCE = "affl_v2/engine.py"
ENGINE_BUNDLE = "affl-v2-official-auto-ingest-runtime.tgz"
GENESIS_SOURCE = "affl_v2/config.py:130"


def canonical_json(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _row_body_for_hash(row: Dict[str, Any]) -> Dict[str, Any]:
    """Hash body excludes row_hash itself (computed over body + prev_hash)."""
    body = {k: v for k, v in row.items() if k != "row_hash"}
    return body


def compute_row_hash(row: Dict[str, Any], prev_hash: str) -> str:
    body = _row_body_for_hash(row)
    body["prev_hash"] = prev_hash
    return sha256_hex(canonical_json(body))


def verify_hash_chain(
    rows: List[Dict[str, Any]],
    *,
    genesis: str = GENESIS_PREV_HASH,
) -> Tuple[bool, str]:
    """Recompute every row. ``genesis`` is the previous hash before row 0.

    The Official ledger uses ``GENESIS``. The governance register uses its
    own constant so the two chains are not the same file.
    """
    prev = genesis
    for i, row in enumerate(rows):
        expected_prev = row.get("prev_hash")
        if expected_prev != prev:
            return False, f"prev_hash mismatch at index {i} id={row.get('ledger_event_id')}"
        stored = row.get("row_hash") or ""
        recomputed = compute_row_hash(row, prev)
        if not stored or stored != recomputed:
            return False, f"row_hash mismatch at index {i} id={row.get('ledger_event_id')}"
        prev = stored
    return True, "OK"


def seal_row(row: Mapping[str, Any], prev_hash: str) -> Dict[str, Any]:
    """Return a new row with ``prev_hash`` and ``row_hash`` filled.

    Tests and the governance template use this. It does not write a file.
    """
    body = {key: value for key, value in row.items() if key != "row_hash"}
    body["prev_hash"] = prev_hash
    sealed = dict(body)
    sealed["row_hash"] = compute_row_hash(body, prev_hash)
    return sealed


def seal_chain(rows: List[Mapping[str, Any]], genesis: str) -> List[Dict[str, Any]]:
    """Seal rows in order. The input rows are not mutated."""
    prev = genesis
    sealed_rows: List[Dict[str, Any]] = []
    for row in rows:
        sealed = seal_row(row, prev)
        sealed_rows.append(sealed)
        prev = str(sealed["row_hash"])
    return sealed_rows
