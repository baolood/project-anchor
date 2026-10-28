"""Persist one public market-data capture.

Transport failures keep the inner error code. A bare transport failure with
no inner code is still TRANSPORT_FAILED. The caller supplies the bytes, so
this module does not open a socket, retry a host run, or send an order.
"""

from __future__ import annotations

import re
import time
from typing import Callable

from kraken_prop.kraken_prop_c6_public_http_v1 import (
    PublicHttpError,
    PublicResponse,
    parse_public_response,
)


TRANSPORT_FAILED = "TRANSPORT_FAILED"
_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")
_MAX_CAUSE_DEPTH = 8


def persisted_failure_reason(exc: BaseException) -> str:
    """Return the inner error code, or TRANSPORT_FAILED when none exists."""
    specific: list[str] = []
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen and len(seen) < _MAX_CAUSE_DEPTH:
        seen.add(id(current))
        code = _error_code(current)
        if code is not None and code != TRANSPORT_FAILED:
            specific.append(code)
        current = current.__cause__ if current.__cause__ is not None else current.__context__
    if specific:
        return specific[-1]
    return TRANSPORT_FAILED


def capture_public(
    url: str,
    *,
    fetch: Callable[[str], bytes],
    persist: Callable[[dict[str, object]], None] | None = None,
) -> dict[str, object]:
    """Capture one public response and persist OK or the inner failure code."""
    if not isinstance(url, str) or url == "":
        raise PublicHttpError("MALFORMED_URL")
    started = time.monotonic()
    try:
        raw = fetch(url)
        response = parse_public_response(raw)
        record = _success_record(url, response, _elapsed_ms(started))
    except Exception as exc:
        record = _failure_record(url, persisted_failure_reason(exc), _elapsed_ms(started))
    if persist is not None:
        persist(record)
    return record


def _success_record(url: str, response: PublicResponse, elapsed_ms: int) -> dict[str, object]:
    if response.status_code < 200 or response.status_code > 299:
        return _failure_record(url, f"HTTP_{response.status_code}", elapsed_ms)
    return {
        "url": url,
        "status": "OK",
        "reason": "",
        "elapsed_ms": elapsed_ms,
        "http_status": response.status_code,
        "set_cookie": list(response.values("set-cookie")),
    }


def _failure_record(url: str, reason: str, elapsed_ms: int) -> dict[str, object]:
    return {
        "url": url,
        "status": "FAILED",
        "reason": reason,
        "elapsed_ms": elapsed_ms,
        "http_status": None,
        "set_cookie": [],
    }


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.monotonic() - started) * 1000))


def _error_code(exc: BaseException) -> str | None:
    for attr in ("code", "reason_code"):
        value = getattr(exc, attr, None)
        if isinstance(value, str) and _CODE_RE.fullmatch(value):
            return value
    if exc.args and isinstance(exc.args[0], str) and _CODE_RE.fullmatch(exc.args[0]):
        return exc.args[0]
    return None
