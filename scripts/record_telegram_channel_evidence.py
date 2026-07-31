#!/usr/bin/env python3
"""Record non-secret Telegram channel evidence for the ops dashboard."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON_OUT = ROOT / "reports" / "post_production_telegram_channel_evidence.json"
DEFAULT_MD_OUT = ROOT / "reports" / "post_production_telegram_channel_evidence.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_result(*, delivered: bool, source: str) -> dict[str, object]:
    status = "POST_PRODUCTION_TELEGRAM_CHANNEL_DELIVERY_CONFIRMED" if delivered else "POST_PRODUCTION_TELEGRAM_CHANNEL_DELIVERY_UNCONFIRMED"
    result = "PASS" if delivered else "BLOCKED"
    return {
        "generated_at": utc_now(),
        "result": result,
        "status": status,
        "channel": "telegram",
        "evidence_source": source,
        "delivery_observed": "YES" if delivered else "NO",
        "message_sent": "YES" if delivered else "NO",
        "secret_disclosed": "NO",
        "boundary": {
            "alerting_env_read": "NO",
            "telegram_bot_token_read": "NO",
            "telegram_chat_id_read": "NO",
            "secret_value_disclosed": "NO",
            "production_env_read": "NO",
            "production_request_sent": "NO",
            "second_production_request_sent": "NO",
            "canary_rerun": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }


def markdown(result: dict[str, object]) -> str:
    boundary = result["boundary"]
    assert isinstance(boundary, dict)
    boundary_lines = "\n".join(f"- {key}: {value}" for key, value in boundary.items())
    return f"""# Post Production Telegram Channel Evidence

Generated at: `{result["generated_at"]}`

## Result

- result: {result["result"]}
- status: {result["status"]}
- channel: {result["channel"]}
- evidence source: {result["evidence_source"]}
- delivery observed: {result["delivery_observed"]}
- message sent: {result["message_sent"]}
- secret disclosed: {result["secret_disclosed"]}

## Boundary

{boundary_lines}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delivered", action="store_true", help="Record an already-observed Telegram delivery.")
    parser.add_argument("--source", default="operator_observed_telegram_message")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MD_OUT)
    args = parser.parse_args()

    result = build_result(delivered=args.delivered, source=args.source)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_out.write_text(markdown(result), encoding="utf-8")

    print("[Post Production Telegram Channel Evidence]")
    print(f"result: {result['result']}")
    print(f"status: {result['status']}")
    print(f"delivery_observed: {result['delivery_observed']}")
    print(f"json: {args.json_out}")
    print(f"markdown: {args.markdown_out}")
    print("secret_disclosed: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
