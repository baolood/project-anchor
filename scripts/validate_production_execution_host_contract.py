#!/usr/bin/env python3
"""Validate the production execution host contract without network or secrets."""

from __future__ import annotations

import json
import os
import platform
import pwd
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "config" / "production_execution_host_contract.json"
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "production_execution_host_contract_validation.json"
MD_OUT = REPORTS_DIR / "production_execution_host_contract_validation.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def git_value(args: list[str], cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def current_user() -> str | None:
    try:
        return pwd.getpwuid(os.getuid()).pw_name
    except KeyError:
        return None


def observed_state(repo_root: Path) -> dict[str, Any]:
    return {
        "hostname": socket.gethostname().split(".")[0],
        "os_family": platform.system(),
        "repo_path": str(repo_root),
        "branch": git_value(["branch", "--show-current"], repo_root),
        "head": git_value(["rev-parse", "--short", "HEAD"], repo_root),
        "git_status_short": git_value(["status", "--short"], repo_root),
        "user": current_user(),
    }


def validate(data: dict[str, Any], *, repo_root: Path = ROOT, observed: dict[str, Any] | None = None) -> dict[str, Any]:
    obs = observed or observed_state(repo_root)
    errors: list[str] = []
    checks = {
        "hostname_matches": obs.get("hostname") == data.get("expected_hostname"),
        "os_family_matches": obs.get("os_family") == data.get("expected_os_family"),
        "repo_path_matches": obs.get("repo_path") == data.get("expected_repo_path"),
        "branch_matches": obs.get("branch") == data.get("expected_branch"),
        "workspace_clean": obs.get("git_status_short") == "",
        "api_ip_whitelist_present": bool(data.get("expected_binance_api_ip_whitelist")),
        "runtime_identity_expected": bool(data.get("expected_runtime_identity")),
    }
    for name, passed in checks.items():
        if not passed:
            errors.append(name)

    result = "PASS" if not errors else "BLOCKED"
    return {
        "generated_at": utc_now(),
        "result": result,
        "errors": errors,
        "expected": {
            "hostname": data.get("expected_hostname"),
            "os_family": data.get("expected_os_family"),
            "repo_path": data.get("expected_repo_path"),
            "branch": data.get("expected_branch"),
            "binance_api_ip_whitelist": data.get("expected_binance_api_ip_whitelist"),
            "runtime_identity": data.get("expected_runtime_identity"),
        },
        "observed": obs,
        "checks": checks,
        "boundary": {
            "credential_file_read": "NO",
            "secret_value_read": "NO",
            "secret_value_disclosed": "NO",
            "dns_lookup": "NO",
            "socket_opened": "NO",
            "production_signing_executed": "NO",
            "production_http_network_attempted": "NO",
            "production_request_sent": "NO",
            "production_order_sent": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }


def markdown(report: dict[str, Any]) -> str:
    errors = "\n".join(f"- {item}" for item in report["errors"]) or "- none"
    checks = "\n".join(f"- {key}: {value}" for key, value in report["checks"].items())
    expected = "\n".join(f"- {key}: {value}" for key, value in report["expected"].items())
    observed = "\n".join(f"- {key}: {value}" for key, value in report["observed"].items())
    boundary = "\n".join(f"- {key}: {value}" for key, value in report["boundary"].items())
    return f"""# Production Execution Host Contract Validation

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}

## Expected

{expected}

## Observed

{observed}

## Checks

{checks}

## Errors

{errors}

## Boundary

{boundary}
"""


def main(argv: list[str]) -> int:
    input_path = Path(argv[1]).resolve() if len(argv) > 1 else DEFAULT_INPUT
    data = read_json(input_path)
    if not data:
        print("PRODUCTION_EXECUTION_HOST_CONTRACT_VALIDATION=FAIL")
        print("FAIL_REASON=INPUT_UNREADABLE_OR_EMPTY")
        return 2

    report = validate(data)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(markdown(report), encoding="utf-8")

    print("[Production Execution Host Contract Validation]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(f"errors: {len(report['errors'])}")
    print(f"observed_hostname: {report['observed'].get('hostname')}")
    print(f"observed_os_family: {report['observed'].get('os_family')}")
    print(f"observed_repo_path: {report['observed'].get('repo_path')}")
    print("credential_file_read: NO")
    print("secret_value_disclosed: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
