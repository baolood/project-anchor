#!/usr/bin/env python3
"""Validate post-production Telegram alerting readiness without sending.

Default mode only checks file metadata. It does not read alerting.env contents,
does not open sockets, and does not send Telegram messages. Field presence
checks require --inspect-env and still never report secret values.
"""

from __future__ import annotations

import argparse
import json
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ENV = Path("/etc/project-anchor/alerting.env")
DEFAULT_REPORT_DIR = Path("reports")
DEFAULT_JSON_OUT = DEFAULT_REPORT_DIR / "post_production_alerting_readiness.json"
DEFAULT_MD_OUT = DEFAULT_REPORT_DIR / "post_production_alerting_readiness.md"

EXPECTED_OWNER = "root"
EXPECTED_GROUP = "project_anchor_runtime"
EXPECTED_MODE = "640"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _owner_name(st: os.stat_result) -> str:
    import pwd

    try:
        return pwd.getpwuid(st.st_uid).pw_name
    except KeyError:
        return str(st.st_uid)


def _group_name(st: os.stat_result) -> str:
    import grp

    try:
        return grp.getgrgid(st.st_gid).gr_name
    except KeyError:
        return str(st.st_gid)


def build_result(
    *,
    env_path: Path,
    inspect_env: bool,
    expected_owner: str,
    expected_group: str,
    expected_mode: str,
) -> tuple[dict[str, Any], int]:
    boundary = {
        "alerting_env_content_read": "NO",
        "telegram_bot_token_value_disclosed": "NO",
        "telegram_chat_id_value_disclosed": "NO",
        "telegram_http_attempted": "NO",
        "telegram_message_sent": "NO",
        "production_env_read": "NO",
        "production_request_sent": "NO",
        "second_production_request_sent": "NO",
        "canary_rerun": "NO",
        "go_live": "NO-GO",
        "live_trading": "NO-GO",
    }
    checks: dict[str, Any] = {
        "path": str(env_path),
        "exists": "NO",
        "owner": "",
        "group": "",
        "mode": "",
        "expected_owner": expected_owner,
        "expected_group": expected_group,
        "expected_mode": expected_mode,
        "owner_match": "NO",
        "group_match": "NO",
        "mode_match": "NO",
        "telegram_notify_enabled_present": "NOT_INSPECTED",
        "telegram_notify_enabled_valid": "NOT_INSPECTED",
        "telegram_bot_token_present": "NOT_INSPECTED",
        "telegram_chat_id_present": "NOT_INSPECTED",
    }
    result: dict[str, Any] = {
        "generated_at": utc_now(),
        "result": "BLOCKED",
        "status": "POST_PRODUCTION_ALERTING_READINESS_BLOCKED",
        "failure_code": "",
        "inspect_env_requested": inspect_env,
        "checks": checks,
        "boundary": boundary,
    }

    try:
        st = env_path.stat()
    except OSError:
        result["failure_code"] = "ALERTING_ENV_FILE_MISSING_OR_UNREADABLE_METADATA"
        return result, 1

    mode = oct(stat.S_IMODE(st.st_mode))[2:]
    owner = _owner_name(st)
    group = _group_name(st)
    checks.update(
        {
            "exists": "YES",
            "owner": owner,
            "group": group,
            "mode": mode,
            "owner_match": "YES" if owner == expected_owner else "NO",
            "group_match": "YES" if group == expected_group else "NO",
            "mode_match": "YES" if mode == expected_mode else "NO",
        }
    )

    metadata_failures = [
        name
        for name in ("owner_match", "group_match", "mode_match")
        if checks[name] != "YES"
    ]
    if metadata_failures:
        result["failure_code"] = "ALERTING_ENV_METADATA_CONTRACT_MISMATCH"
        result["metadata_failures"] = metadata_failures
        return result, 1

    if not inspect_env:
        result["failure_code"] = "ALERTING_ENV_FIELD_INSPECTION_NOT_AUTHORIZED"
        return result, 1

    boundary["alerting_env_content_read"] = "YES"
    try:
        values = parse_env_file(env_path)
    except OSError:
        result["failure_code"] = "ALERTING_ENV_CONTENT_UNREADABLE"
        return result, 1

    notify_value = values.get("TELEGRAM_NOTIFY_ENABLED", "").strip()
    checks["telegram_notify_enabled_present"] = "YES" if notify_value else "NO"
    checks["telegram_notify_enabled_valid"] = "YES" if notify_value == "1" else "NO"
    checks["telegram_bot_token_present"] = "YES" if values.get("TELEGRAM_BOT_TOKEN", "").strip() else "NO"
    checks["telegram_chat_id_present"] = "YES" if values.get("TELEGRAM_CHAT_ID", "").strip() else "NO"

    field_failures = [
        name
        for name in (
            "telegram_notify_enabled_present",
            "telegram_notify_enabled_valid",
            "telegram_bot_token_present",
            "telegram_chat_id_present",
        )
        if checks[name] != "YES"
    ]
    if field_failures:
        result["failure_code"] = "ALERTING_ENV_FIELD_CONTRACT_MISMATCH"
        result["field_failures"] = field_failures
        return result, 1

    result["result"] = "PASS"
    result["status"] = "POST_PRODUCTION_ALERTING_READY"
    return result, 0


def markdown(result: dict[str, Any]) -> str:
    checks = "\n".join(f"- {key}: {value}" for key, value in result["checks"].items())
    boundary = "\n".join(f"- {key}: {value}" for key, value in result["boundary"].items())
    failure_code = result["failure_code"] or "none"
    return f"""# Post Production Alerting Readiness

Generated at: `{result["generated_at"]}`

## Result

- result: {result["result"]}
- status: {result["status"]}
- failure code: {failure_code}
- inspect env requested: {result["inspect_env_requested"]}

## Checks

{checks}

## Boundary

{boundary}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alerting-env", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MD_OUT)
    parser.add_argument("--expected-owner", default=EXPECTED_OWNER)
    parser.add_argument("--expected-group", default=EXPECTED_GROUP)
    parser.add_argument("--expected-mode", default=EXPECTED_MODE)
    parser.add_argument("--inspect-env", action="store_true")
    args = parser.parse_args()

    result, exit_code = build_result(
        env_path=args.alerting_env,
        inspect_env=args.inspect_env,
        expected_owner=args.expected_owner,
        expected_group=args.expected_group,
        expected_mode=args.expected_mode,
    )
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_out.write_text(markdown(result), encoding="utf-8")

    print("[Post Production Alerting Readiness]")
    print(f"result: {result['result']}")
    print(f"status: {result['status']}")
    print(f"failure_code: {result['failure_code']}")
    print(f"json: {args.json_out}")
    print(f"markdown: {args.markdown_out}")
    print(f"alerting_env_content_read: {result['boundary']['alerting_env_content_read']}")
    print(f"telegram_http_attempted: {result['boundary']['telegram_http_attempted']}")
    print(f"telegram_message_sent: {result['boundary']['telegram_message_sent']}")
    print(f"production_request_sent: {result['boundary']['production_request_sent']}")
    print(f"go_live: {result['boundary']['go_live']}")
    print(f"live_trading: {result['boundary']['live_trading']}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
