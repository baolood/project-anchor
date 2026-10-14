"""Public HTTP response reader for C6 market-data capture.

A public ticker response may repeat list-valued headers. Set-Cookie is the
important case: each field is its own cookie, and comma-joining would corrupt
Expires dates. Repeated names outside the safe set are still rejected.

This module does not open sockets, send orders, or read credentials.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


HEADERS_REJECTED = "HEADERS_REJECTED"
MALFORMED_HEADERS = "MALFORMED_HEADERS"
MALFORMED_STATUS = "MALFORMED_STATUS"
INCOMPLETE_HEADERS = "INCOMPLETE_HEADERS"

# List-valued response fields. Set-Cookie must stay as separate values.
SAFE_REPEATED_RESPONSE_HEADERS = frozenset(
    {
        "set-cookie",
        "cache-control",
        "warning",
        "via",
        "link",
        "vary",
        "www-authenticate",
        "proxy-authenticate",
        "server-timing",
        "accept-ch",
        "report-to",
        "nel",
        "access-control-expose-headers",
    }
)

_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")
_NAME_RE = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
_VERSIONS = frozenset({"HTTP/1.0", "HTTP/1.1", "HTTP/2"})
_MAX_HEADERS = 128
_MAX_NAME_LEN = 256
_MAX_VALUE_LEN = 16384


class PublicHttpError(Exception):
    """A public-response read failed with a stable error code."""

    def __init__(self, code: str, detail: str = ""):
        if not isinstance(code, str) or _CODE_RE.fullmatch(code) is None:
            raise ValueError("public http error code must be an uppercase token")
        self.code = code
        self.detail = detail
        super().__init__(code if detail == "" else f"{code}: {detail}")


@dataclass(frozen=True)
class PublicResponse:
    http_version: str
    status_code: int
    reason_phrase: str
    headers: tuple[tuple[str, str], ...]
    body: bytes

    def values(self, name: str) -> tuple[str, ...]:
        key = name.lower()
        return tuple(value for header, value in self.headers if header.lower() == key)


def collect_response_headers(fields: Iterable[tuple[str, str]]) -> tuple[tuple[str, str], ...]:
    """Keep every safe repeated response header. Reject any other repeat."""
    kept: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name, value in fields:
        if not isinstance(name, str) or not isinstance(value, str):
            raise PublicHttpError(MALFORMED_HEADERS)
        canonical = _header_name(name)
        cleaned = _header_value(value)
        key = canonical.lower()
        if key in seen and key not in SAFE_REPEATED_RESPONSE_HEADERS:
            raise PublicHttpError(HEADERS_REJECTED, key)
        seen.add(key)
        kept.append((canonical, cleaned))
        if len(kept) > _MAX_HEADERS:
            raise PublicHttpError(MALFORMED_HEADERS, "too_many_headers")
    return tuple(kept)


def parse_public_response(raw: bytes) -> PublicResponse:
    """Parse one public HTTP response message, including repeated Set-Cookie."""
    if not isinstance(raw, (bytes, bytearray)):
        raise PublicHttpError(MALFORMED_HEADERS)
    head, body = _split_head(bytes(raw))
    lines = _decode_lines(head)
    if not lines:
        raise PublicHttpError(MALFORMED_STATUS)
    version, status_code, reason = _parse_status(lines[0])
    headers = collect_response_headers(_parse_field(line) for line in lines[1:])
    return PublicResponse(version, status_code, reason, headers, body)


def _split_head(raw: bytes) -> tuple[bytes, bytes]:
    candidates = [index for index in (raw.find(b"\r\n\r\n"), raw.find(b"\n\n")) if index >= 0]
    if not candidates:
        raise PublicHttpError(INCOMPLETE_HEADERS)
    index = min(candidates)
    separator = b"\r\n\r\n" if raw.startswith(b"\r\n\r\n", index) else b"\n\n"
    return raw[:index], raw[index + len(separator) :]


def _decode_lines(head: bytes) -> list[str]:
    if b"\x00" in head:
        raise PublicHttpError(MALFORMED_HEADERS)
    try:
        text = head.decode("ascii")
    except UnicodeDecodeError as exc:
        raise PublicHttpError(MALFORMED_HEADERS) from exc
    if "\r\n" in text:
        return text.split("\r\n")
    return text.split("\n")


def _parse_status(line: str) -> tuple[str, int, str]:
    parts = line.split(" ", 2)
    if len(parts) < 2 or parts[0] not in _VERSIONS or len(parts[1]) != 3 or not parts[1].isdigit():
        raise PublicHttpError(MALFORMED_STATUS)
    reason = parts[2].strip() if len(parts) == 3 else ""
    return parts[0], int(parts[1]), reason


def _parse_field(line: str) -> tuple[str, str]:
    if line == "" or line[0] in " \t" or ":" not in line:
        raise PublicHttpError(MALFORMED_HEADERS)
    name, value = line.split(":", 1)
    return name, value


def _header_name(name: str) -> str:
    canonical = name.strip(" \t")
    if (
        canonical == ""
        or len(canonical) > _MAX_NAME_LEN
        or _NAME_RE.fullmatch(canonical) is None
    ):
        raise PublicHttpError(MALFORMED_HEADERS)
    return canonical


def _header_value(value: str) -> str:
    if "\r" in value or "\n" in value or "\x00" in value or len(value) > _MAX_VALUE_LEN:
        raise PublicHttpError(MALFORMED_HEADERS)
    return value.strip(" \t")
