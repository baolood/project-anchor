#!/usr/bin/env python3
"""Fail-closed Telegram sender for post-production monitoring alerts.

Default mode is a non-sending precheck. Real Telegram delivery requires
--execute and a READY_TO_SEND payload. Even in execute mode, secret values are
never printed or written to reports.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_REPORT_DIR = Path("/var/lib/project-anchor/reports")
DEFAULT_PAYLOAD = DEFAULT_REPORT_DIR / "post_production_monitoring_telegram_payload.json"
DEFAULT_ENV = Path("/etc/project-anchor/alerting.env")
DEFAULT_JSON_OUT = DEFAULT_REPORT_DIR / "post_production_monitoring_telegram_send_result.json"
DEFAULT_MD_OUT = DEFAULT_REPORT_DIR / "post_production_monitoring_telegram_send_result.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return {"result": "UNREADABLE", "error": exc.__class__.__name__}
    return data if isinstance(data, dict) else {"result": "UNREADABLE"}


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def build_result(
    payload: dict[str, Any],
    *,
    execute: bool,
    env_path: Path,
    opener: Any | None = None,
) -> tuple[dict[str, Any], int]:
    boundary = {
        "alerting_env_read": "NO",
        "telegram_bot_token_read": "NO",
        "telegram_chat_id_read": "NO",
        "secret_value_disclosed": "NO",
        "telegram_http_attempted": "NO",
        "production_env_read": "NO",
        "production_request_sent": "NO",
        "second_production_request_sent": "NO",
        "canary_rerun": "NO",
        "go_live": "NO-GO",
        "live_trading": "NO-GO",
    }
    result = {
        "generated_at": utc_now(),
        "result": "BLOCKED",
        "status": "POST_PRODUCTION_MONITORING_TELEGRAM_SEND_BLOCKED",
        "execute_requested": execute,
        "source_payload_result": payload.get("result"),
        "send_attempted": "NO",
        "send_result": "NOT_ATTEMPTED",
        "failure_code": "",
        "boundary": boundary,
    }

    if payload.get("result") != "READY_TO_SEND":
        result["status"] = "POST_PRODUCTION_MONITORING_TELEGRAM_SEND_SUPPRESSED"
        result["failure_code"] = "PAYLOAD_NOT_READY_TO_SEND"
        return result, 1

    if not execute:
        result["failure_code"] = "EXECUTE_FLAG_REQUIRED"
        return result, 1

    boundary["alerting_env_read"] = "YES"
    try:
        env = parse_env_file(env_path)
    except OSError:
        result["failure_code"] = "ALERTING_ENV_UNREADABLE"
        return result, 1

    token = env.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = env.get("TELEGRAM_CHAT_ID", "").strip()
    if token:
        boundary["telegram_bot_token_read"] = "YES"
    if chat_id:
        boundary["telegram_chat_id_read"] = "YES"
    if env.get("TELEGRAM_NOTIFY_ENABLED", "").strip() != "1":
        result["failure_code"] = "TELEGRAM_NOTIFY_NOT_ENABLED"
        return result, 1
    if not token or not chat_id:
        result["failure_code"] = "TELEGRAM_CREDENTIALS_MISSING"
        return result, 1

    message = str(payload.get("message", ""))[:4000]
    body = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body,
        method="POST",
    )
    boundary["telegram_http_attempted"] = "YES"
    result["send_attempted"] = "YES"
    open_call = opener or urllib.request.urlopen
    try:
        with open_call(request, timeout=10) as response:
            status = getattr(response, "status", None) or getattr(response, "code", None)
            if status == 200:
                result["result"] = "PASS"
                result["status"] = "POST_PRODUCTION_MONITORING_TELEGRAM_SEND_DELIVERED"
                result["send_result"] = "DELIVERED"
                return result, 0
            result["failure_code"] = f"TELEGRAM_HTTP_STATUS_{status}"
            return result, 1
    except urllib.error.HTTPError as exc:
        result["failure_code"] = f"TELEGRAM_HTTP_STATUS_{exc.code}"
        return result, 1
    except Exception as exc:  # noqa: BLE001 - result must fail closed for any transport error.
        result["failure_code"] = f"TELEGRAM_SEND_ERROR_{exc.__class__.__name__}"
        return result, 1


def markdown(result: dict[str, Any]) -> str:
    boundary = "\n".join(f"- {key}: {value}" for key, value in result["boundary"].items())
    return f"""# Post Production Monitoring Telegram Send Result

Generated at: `{result["generated_at"]}`

## Result

- result: {result["result"]}
- status: {result["status"]}
- execute requested: {result["execute_requested"]}
- source payload result: {result["source_payload_result"]}
- send attempted: {result["send_attempted"]}
- send result: {result["send_result"]}
- failure code: {result["failure_code"]}

## Boundary

{boundary}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload-json", type=Path, default=DEFAULT_PAYLOAD)
    parser.add_argument("--alerting-env", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MD_OUT)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    payload = load_json(args.payload_json)
    result, exit_code = build_result(payload, execute=args.execute, env_path=args.alerting_env)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_out.write_text(markdown(result), encoding="utf-8")

    print("[Post Production Monitoring Telegram Send Result]")
    print(f"result: {result['result']}")
    print(f"status: {result['status']}")
    print(f"send_attempted: {result['send_attempted']}")
    print(f"failure_code: {result['failure_code']}")
    print(f"json: {args.json_out}")
    print(f"markdown: {args.markdown_out}")
    print(f"alerting_env_read: {result['boundary']['alerting_env_read']}")
    print(f"telegram_http_attempted: {result['boundary']['telegram_http_attempted']}")
    print(f"production_request_sent: {result['boundary']['production_request_sent']}")
    print(f"go_live: {result['boundary']['go_live']}")
    print(f"live_trading: {result['boundary']['live_trading']}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
