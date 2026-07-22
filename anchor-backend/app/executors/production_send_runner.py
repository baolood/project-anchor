from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from app.executors.production_credentials import (
    load_production_credentials,
    redacted_credential_shape,
)
from app.executors.production_order_executor import run_gated_production_order_request


def _blocked(
    code: str,
    *,
    ts: int,
    credential_report: Dict[str, Any] | None = None,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], Optional[str], Optional[Dict[str, Any]]]:
    error = {
        "code": code,
        "failure_family": code,
        "external_request_started": False,
        "external_order_id_present": False,
        "production_request_sent": False,
        "secret_value_disclosed": False,
        "ts": ts,
    }
    if credential_report is not None:
        error["credential_shape"] = redacted_credential_shape(None, credential_report)
    return ({"ok": False, "result": None, "error": error}, None, None, None)


def run_final_production_send(
    body: Dict[str, Any],
    gate_config: Dict[str, Any] | None,
    credential_path: str | Path | None,
    now_ts: int,
    *,
    now: datetime | None = None,
    execute: bool = False,
    credential_read_enabled: bool = False,
    opener: Optional[Callable[..., Any]] = None,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], Optional[str], Optional[Dict[str, Any]]]:
    if not credential_read_enabled:
        return _blocked("PRODUCTION_CREDENTIAL_READ_NOT_AUTHORIZED", ts=now_ts)

    credentials, credential_report = load_production_credentials(
        credential_path,
        allow_read=True,
    )
    if credentials is None:
        return _blocked(
            str(credential_report.get("code") or "PRODUCTION_CREDENTIALS_MISSING"),
            ts=now_ts,
            credential_report=credential_report,
        )

    outcome, requested_payload, terminal_type, terminal_payload = run_gated_production_order_request(
        body,
        gate_config,
        credentials,
        now_ts,
        now=now,
        execute=execute,
        opener=opener,
    )
    credential_shape = redacted_credential_shape(credentials, credential_report)
    if outcome.get("ok") is True and isinstance(outcome.get("result"), dict):
        outcome["result"]["credential_shape"] = credential_shape
        outcome["result"]["production_request_sent"] = bool(
            outcome["result"].get("external_request_started")
        )
        return outcome, requested_payload, terminal_type, terminal_payload

    if isinstance(outcome.get("error"), dict):
        outcome["error"]["credential_shape"] = credential_shape
        outcome["error"]["production_request_sent"] = False
    return outcome, requested_payload, terminal_type, terminal_payload
