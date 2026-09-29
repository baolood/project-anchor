"""Redact secrets before any MCP tool payload leaves the process."""

from __future__ import annotations

import re
from typing import Any


_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|api[_-]?secret|secret|password|passwd|token|dsn|database_url|"
    r"authorization|bearer|private[_-]?key|credential)\b\s*[:=]\s*([^\s,;\"']+)"
)
_URL_RE = re.compile(
    r"\b(?:postgres(?:ql)?|mysql|redis|mongodb|amqp|https?)://[^\s\"']+",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-+/=]+")
_SK_RE = re.compile(r"\bsk-[A-Za-z0-9]{8,}\b")
_PEM_RE = re.compile(r"-----BEGIN [A-Z0-9 ]+-----[\s\S]*?-----END [A-Z0-9 ]+-----")
_SECRET_KEY_RE = re.compile(
    r"(?i)(api[_-]?key|api[_-]?secret|secret|password|passwd|token|credential|"
    r"authorization|bearer|dsn|database_url|private[_-]?key|signature|"
    r"idempotency|client_order|external_order|order_id)"
)
_ENV_PATH_RE = re.compile(r"(?i)(^|/)\.env(\.|$)|\.pem$|\.key$|id_rsa")


def looks_sensitive_key(key: str) -> bool:
    return bool(_SECRET_KEY_RE.search(str(key)))


def looks_sensitive_path(path: str) -> bool:
    return bool(_ENV_PATH_RE.search(path.replace("\\", "/")))


def redact_text(text: str, extra_secrets: tuple[str, ...] = ()) -> str:
    redacted = text
    for secret in extra_secrets:
        if isinstance(secret, str) and len(secret) >= 8 and secret in redacted:
            redacted = redacted.replace(secret, "[REDACTED]")
    if _PEM_RE.search(redacted):
        return "[REDACTED_LINE]"
    redacted = _ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
    redacted = _URL_RE.sub("[REDACTED_URL]", redacted)
    redacted = _BEARER_RE.sub("Bearer [REDACTED]", redacted)
    redacted = _SK_RE.sub("[REDACTED]", redacted)
    return redacted


def redact_obj(value: Any, extra_secrets: tuple[str, ...] = (), depth: int = 0) -> Any:
    if depth > 8:
        return "[truncated]"
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in list(value.items())[:80]:
            name = str(key)
            if looks_sensitive_key(name):
                out[name] = "[REDACTED]"
            else:
                out[name] = redact_obj(item, extra_secrets, depth + 1)
        return out
    if isinstance(value, list):
        return [redact_obj(item, extra_secrets, depth + 1) for item in value[:50]]
    if isinstance(value, str):
        return redact_text(value, extra_secrets)[:2000]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return redact_text(str(value), extra_secrets)[:500]
