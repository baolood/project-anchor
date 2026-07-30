#!/usr/bin/env python3
"""Render a non-sending Telegram payload from the monitoring alert outbox."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_REPORT_DIR = Path("/var/lib/project-anchor/reports")
DEFAULT_NOTIFICATION = DEFAULT_REPORT_DIR / "post_production_monitoring_alert_notification.json"
DEFAULT_JSON_OUT = DEFAULT_REPORT_DIR / "post_production_monitoring_telegram_payload.json"
DEFAULT_MD_OUT = DEFAULT_REPORT_DIR / "post_production_monitoring_telegram_payload.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return {
            "result": "UNREADABLE",
            "status": "POST_PRODUCTION_MONITORING_NOTIFICATION_UNREADABLE",
            "error": exc.__class__.__name__,
            "boundary": {
                "credential_file_read": "NO",
                "secret_value_disclosed": "NO",
                "production_http_network_attempted": "NO",
                "new_production_request_sent": "NO",
                "second_production_request_sent": "NO",
                "go_live": "NO-GO",
                "live_trading": "NO-GO",
            },
        }
    return data if isinstance(data, dict) else {"result": "UNREADABLE"}


def render_message(notification: dict[str, Any]) -> str:
    failed_checks = notification.get("failed_checks")
    failed_count = len(failed_checks) if isinstance(failed_checks, list) else 0
    boundary = notification.get("boundary") if isinstance(notification.get("boundary"), dict) else {}
    return "\n".join(
        [
            "[Project Anchor] Post-production monitoring alert",
            f"notification={notification.get('result', 'UNKNOWN')}",
            f"alert={notification.get('alert_result', 'UNKNOWN')}",
            f"status={notification.get('alert_status', 'UNKNOWN')}",
            f"reason={notification.get('reason', 'n/a')}",
            f"failed_checks={failed_count}",
            f"new_production_request_sent={boundary.get('new_production_request_sent', 'NO')}",
            f"go_live={boundary.get('go_live', 'NO-GO')}",
            f"live_trading={boundary.get('live_trading', 'NO-GO')}",
        ]
    )


def build_payload(notification: dict[str, Any]) -> dict[str, Any]:
    sendable = notification.get("result") == "EMITTED"
    return {
        "generated_at": utc_now(),
        "result": "READY_TO_SEND" if sendable else "SUPPRESSED",
        "status": (
            "POST_PRODUCTION_MONITORING_TELEGRAM_PAYLOAD_READY"
            if sendable
            else "POST_PRODUCTION_MONITORING_TELEGRAM_PAYLOAD_SUPPRESSED"
        ),
        "channel": "telegram",
        "send_authorized": "NO",
        "send_attempted": "NO",
        "message": render_message(notification),
        "source_notification_result": notification.get("result"),
        "source_notification_status": notification.get("status"),
        "boundary": {
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
        },
    }


def markdown(payload: dict[str, Any]) -> str:
    boundary = "\n".join(f"- {key}: {value}" for key, value in payload["boundary"].items())
    return f"""# Post Production Monitoring Telegram Payload

Generated at: `{payload["generated_at"]}`

## Result

- result: {payload["result"]}
- status: {payload["status"]}
- channel: {payload["channel"]}
- send authorized: {payload["send_authorized"]}
- send attempted: {payload["send_attempted"]}
- source notification result: {payload["source_notification_result"]}

## Message

```text
{payload["message"]}
```

## Boundary

{boundary}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notification-json", type=Path, default=DEFAULT_NOTIFICATION)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MD_OUT)
    args = parser.parse_args()

    notification = load_json(args.notification_json)
    payload = build_payload(notification)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_out.write_text(markdown(payload), encoding="utf-8")

    print("[Post Production Monitoring Telegram Payload]")
    print(f"result: {payload['result']}")
    print(f"status: {payload['status']}")
    print(f"json: {args.json_out}")
    print(f"markdown: {args.markdown_out}")
    print("alerting_env_read: NO")
    print("telegram_http_attempted: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
