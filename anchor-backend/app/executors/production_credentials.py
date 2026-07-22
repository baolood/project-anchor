from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple


REQUIRED_PRODUCTION_CREDENTIAL_FIELDS = [
    "PRODUCTION_EXCHANGE_BASE_URL",
    "PRODUCTION_EXCHANGE_API_KEY",
    "PRODUCTION_EXCHANGE_API_SECRET",
    "PRODUCTION_EXCHANGE_KEY_ID",
]

ALLOWED_PRODUCTION_BASE_URLS = {"https://api.binance.com"}


def _failure(code: str, *, field_status: Dict[str, str] | None = None) -> Tuple[None, Dict[str, Any]]:
    return None, {
        "ok": False,
        "code": code,
        "field_status": field_status or {},
        "secret_value_disclosed": False,
    }


def parse_env_lines(raw: str) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key in REQUIRED_PRODUCTION_CREDENTIAL_FIELDS:
            values[key] = value.strip().strip('"').strip("'")
    return values


def validate_production_credential_values(values: Dict[str, str]) -> Tuple[bool, Dict[str, str], str | None]:
    field_status: Dict[str, str] = {}
    for field in REQUIRED_PRODUCTION_CREDENTIAL_FIELDS:
        field_status[field] = "PRESENT_VALID" if values.get(field) else "MISSING_INVALID"

    base_url = values.get("PRODUCTION_EXCHANGE_BASE_URL", "").rstrip("/")
    if base_url and base_url not in ALLOWED_PRODUCTION_BASE_URLS:
        field_status["PRODUCTION_EXCHANGE_BASE_URL"] = "MISSING_INVALID"

    if all(status == "PRESENT_VALID" for status in field_status.values()):
        return True, field_status, None
    return False, field_status, "PRODUCTION_CREDENTIAL_SHAPE_INVALID"


def load_production_credentials(
    path: str | Path | None,
    *,
    allow_read: bool = False,
) -> Tuple[Dict[str, str] | None, Dict[str, Any]]:
    if not allow_read:
        return _failure("PRODUCTION_CREDENTIAL_READ_NOT_AUTHORIZED")
    if path is None:
        return _failure("PRODUCTION_CREDENTIAL_PATH_MISSING")

    credential_path = Path(path)
    try:
        raw = credential_path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 - loader should fail closed.
        return _failure(f"PRODUCTION_CREDENTIAL_FILE_UNREADABLE:{type(exc).__name__}")

    values = parse_env_lines(raw)
    ok, field_status, reason = validate_production_credential_values(values)
    if not ok:
        return _failure(reason or "PRODUCTION_CREDENTIAL_SHAPE_INVALID", field_status=field_status)

    credentials = {
        "base_url": values["PRODUCTION_EXCHANGE_BASE_URL"].rstrip("/"),
        "api_key": values["PRODUCTION_EXCHANGE_API_KEY"],
        "api_secret": values["PRODUCTION_EXCHANGE_API_SECRET"],
        "key_id": values["PRODUCTION_EXCHANGE_KEY_ID"],
    }
    return credentials, {
        "ok": True,
        "code": "PRODUCTION_CREDENTIALS_LOADED",
        "field_status": field_status,
        "secret_value_disclosed": False,
    }


def redacted_credential_shape(credentials: Dict[str, str] | None, report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "loaded": credentials is not None and bool(report.get("ok")),
        "base_url_present": bool(credentials and credentials.get("base_url")),
        "api_key_present": bool(credentials and credentials.get("api_key")),
        "api_secret_present": bool(credentials and credentials.get("api_secret")),
        "key_id_present": bool(credentials and credentials.get("key_id")),
        "field_status": dict(report.get("field_status") or {}),
        "secret_value_disclosed": False,
    }
