#!/usr/bin/env python3
"""Create exactly one non-executable production command record in local Postgres.

This drill proves the production command creation path can persist a bounded
PRODUCTION_ORDER_INTENT record without making it worker-executable. It does not
read secrets, sign payloads, open sockets, or send production requests.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "production_non_executable_command_creation_drill.json"
MD_OUT = REPORTS_DIR / "production_non_executable_command_creation_drill.md"
COMPOSE_FILE = ROOT / "anchor-backend" / "docker-compose.yml"

sys.path.insert(0, str(ROOT / "anchor-backend"))

from app.trade_gate_production import (  # noqa: E402
    PRODUCTION_COMMAND_CREATED_STATUS,
    PRODUCTION_COMMAND_TYPE,
    PRODUCTION_IDEMPOTENCY_KEY,
    production_order_command_creation_payload,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def valid_body() -> dict:
    return {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "notional": 4,
        "order_type": "market",
        "execution_mode": "production",
        "market": "binance_spot",
        "source": "ops_manual",
        "idempotency_key": PRODUCTION_IDEMPOTENCY_KEY,
    }


def run_psql(sql: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(COMPOSE_FILE),
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "anchor",
            "-d",
            "anchor",
            "-v",
            "ON_ERROR_STOP=1",
            "-t",
            "-A",
        ],
        input=sql,
        text=True,
        capture_output=True,
        cwd=str(ROOT),
        check=False,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def sql_json(value: dict) -> str:
    return json.dumps(value, sort_keys=True).replace("$", "\\u0024")


def build_report() -> tuple[dict, int]:
    generated_at = utc_now()
    command_id = "prod-order-drill-" + generated_at.replace(":", "").replace("-", "")
    payload = production_order_command_creation_payload(valid_body())
    errors: list[str] = []

    pre_sql = """
SELECT COALESCE(COUNT(*), 0)
FROM commands_domain
WHERE type = 'PRODUCTION_ORDER_INTENT'
  AND status IN ('PENDING', 'RUNNING');
"""
    pre_code, pre_stdout, pre_stderr = run_psql(pre_sql)
    pre_worker_executable_count = None
    if pre_code == 0:
        try:
            pre_worker_executable_count = int(pre_stdout.splitlines()[-1])
        except Exception:
            errors.append("PRE_WORKER_EXECUTABLE_COUNT_PARSE_FAILED")
    else:
        errors.append("PRE_QUERY_FAILED")

    insert_sql = f"""
INSERT INTO commands_domain
  (id, type, status, payload, attempt, created_at, updated_at)
VALUES
  ('{command_id}', '{PRODUCTION_COMMAND_TYPE}', '{PRODUCTION_COMMAND_CREATED_STATUS}',
   $json${sql_json(payload)}$json$::jsonb, 0, NOW(), NOW())
RETURNING id, type, status, attempt;
"""
    insert_code, insert_stdout, insert_stderr = run_psql(insert_sql)
    if insert_code != 0:
        errors.append("INSERT_FAILED")

    time.sleep(2)

    verify_sql = f"""
SELECT json_build_object(
  'id', id,
  'type', type,
  'status', status,
  'attempt', attempt,
  'worker_executable', status IN ('PENDING', 'RUNNING'),
  'production_request_sent', COALESCE((payload->>'production_request_sent')::boolean, false),
  'production_signing_executed', COALESCE((payload->>'production_signing_executed')::boolean, false),
  'production_http_network_executed', COALESCE((payload->>'production_http_network_executed')::boolean, false),
  'command_creation_only', COALESCE((payload->>'command_creation_only')::boolean, false)
)
FROM commands_domain
WHERE id = '{command_id}';
"""
    verify_code, verify_stdout, verify_stderr = run_psql(verify_sql)
    row = {}
    if verify_code == 0 and verify_stdout:
        try:
            row = json.loads(verify_stdout.splitlines()[-1])
        except Exception:
            errors.append("VERIFY_ROW_PARSE_FAILED")
    else:
        errors.append("VERIFY_QUERY_FAILED")

    post_code, post_stdout, post_stderr = run_psql(pre_sql)
    post_worker_executable_count = None
    if post_code == 0:
        try:
            post_worker_executable_count = int(post_stdout.splitlines()[-1])
        except Exception:
            errors.append("POST_WORKER_EXECUTABLE_COUNT_PARSE_FAILED")
    else:
        errors.append("POST_QUERY_FAILED")

    checks = {
        "insert_succeeded": insert_code == 0,
        "inserted_type_matches": row.get("type") == PRODUCTION_COMMAND_TYPE,
        "inserted_status_non_executable": row.get("status") == PRODUCTION_COMMAND_CREATED_STATUS,
        "worker_executable_false": row.get("worker_executable") is False,
        "attempt_zero": row.get("attempt") == 0,
        "command_creation_only_true": row.get("command_creation_only") is True,
        "production_signing_executed_false": row.get("production_signing_executed") is False,
        "production_http_network_executed_false": row.get("production_http_network_executed") is False,
        "production_request_sent_false": row.get("production_request_sent") is False,
        "worker_executable_count_unchanged": (
            pre_worker_executable_count == post_worker_executable_count
            and post_worker_executable_count == 0
        ),
    }
    result = "PASS" if not errors and all(checks.values()) else "FAIL"
    report = {
        "generated_at": generated_at,
        "result": result,
        "command_id": command_id,
        "command_type": PRODUCTION_COMMAND_TYPE,
        "command_status": row.get("status"),
        "worker_executable": row.get("worker_executable"),
        "pre_worker_executable_count": pre_worker_executable_count,
        "post_worker_executable_count": post_worker_executable_count,
        "checks": checks,
        "errors": errors,
        "insert_stdout": insert_stdout,
        "insert_stderr_present": bool(insert_stderr),
        "query_errors_present": any([pre_stderr, verify_stderr, post_stderr]),
        "boundary": {
            "secret_read": "NO",
            "production_signing_executed": "NO",
            "dns_lookup_performed": "NO",
            "socket_opened": "NO",
            "production_http_network_executed": "NO",
            "production_request_sent": "NO",
            "canary_rerun": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    return report, 0 if result == "PASS" else 1


def markdown(report: dict) -> str:
    checks = "\n".join(
        f"- {key}: {'PASS' if value else 'FAIL'}"
        for key, value in report["checks"].items()
    )
    errors = "\n".join(f"- {item}" for item in report["errors"]) or "- none"
    return f"""# Production Non-Executable Command Creation Drill

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- command id: `{report["command_id"]}`
- command type: `{report["command_type"]}`
- command status: `{report["command_status"]}`
- worker executable: {str(report["worker_executable"]).lower()}
- pre worker executable count: {report["pre_worker_executable_count"]}
- post worker executable count: {report["post_worker_executable_count"]}

## Checks

{checks}

## Errors

{errors}

## Boundary

- secret read: {report["boundary"]["secret_read"]}
- production signing executed: {report["boundary"]["production_signing_executed"]}
- DNS lookup performed: {report["boundary"]["dns_lookup_performed"]}
- socket opened: {report["boundary"]["socket_opened"]}
- production HTTP/network executed: {report["boundary"]["production_http_network_executed"]}
- production request sent: {report["boundary"]["production_request_sent"]}
- canary rerun: {report["boundary"]["canary_rerun"]}
- go-live: {report["boundary"]["go_live"]}
- live trading: {report["boundary"]["live_trading"]}
"""


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report, exit_code = build_report()
    JSON_OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(markdown(report), encoding="utf-8")

    print("[Production Non-Executable Command Creation Drill]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"result: {report['result']}")
    print(f"command_id: {report['command_id']}")
    print(f"command_status: {report['command_status']}")
    print(f"worker_executable: {str(report['worker_executable']).lower()}")
    print(f"production_request_sent: {report['boundary']['production_request_sent']}")
    print(f"go_live: {report['boundary']['go_live']}")
    print(f"live_trading: {report['boundary']['live_trading']}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
