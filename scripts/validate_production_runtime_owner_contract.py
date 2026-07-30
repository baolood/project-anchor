#!/usr/bin/env python3
"""Validate the production runtime owner contract without reading secrets.

This validator only checks identity resolvability and file metadata. It does
not read /etc/project-anchor/production.env contents, change ownership or mode,
use sudo, sign payloads, open network sockets, or send production requests.
"""

from __future__ import annotations

import grp
import json
import pwd
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "production_runtime_owner_contract.json"
REPORTS_DIR = ROOT / "reports"
JSON_OUT = REPORTS_DIR / "production_runtime_owner_contract_validation.json"
MD_OUT = REPORTS_DIR / "production_runtime_owner_contract_validation.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def identity_exists(name: str, *, group: bool = False) -> bool:
    if not name:
        return False
    try:
        grp.getgrnam(name) if group else pwd.getpwnam(name)
    except KeyError:
        return False
    return True


def owner_group_mode(path: Path) -> dict[str, Any]:
    try:
        st = path.stat()
    except FileNotFoundError:
        return {
            "exists": False,
            "owner": None,
            "group": None,
            "mode": None,
            "stat_error": "FILE_NOT_FOUND",
        }
    except PermissionError:
        return {
            "exists": None,
            "owner": None,
            "group": None,
            "mode": None,
            "stat_error": "PERMISSION_DENIED",
        }

    try:
        owner = pwd.getpwuid(st.st_uid).pw_name
    except KeyError:
        owner = str(st.st_uid)
    try:
        group = grp.getgrgid(st.st_gid).gr_name
    except KeyError:
        group = str(st.st_gid)
    return {
        "exists": True,
        "owner": owner,
        "group": group,
        "mode": f"{stat.S_IMODE(st.st_mode):03o}",
        "stat_error": None,
    }


def validate(config: dict[str, Any]) -> dict[str, Any]:
    env_path = Path(str(config.get("canonical_env_path") or ""))
    runtime_identity = str(config.get("runtime_identity") or "")
    runtime_group = str(config.get("runtime_group") or "")
    expected_owner = str(config.get("expected_env_owner") or "")
    expected_group = str(config.get("expected_env_group") or "")
    expected_mode = str(config.get("expected_env_mode") or "")
    observed = owner_group_mode(env_path)

    checks = {
        "runtime_identity_explicit": bool(runtime_identity),
        "runtime_identity_resolved": identity_exists(runtime_identity),
        "runtime_group_explicit": bool(runtime_group),
        "runtime_group_resolved": identity_exists(runtime_group, group=True),
        "env_owner_expectation_explicit": bool(expected_owner),
        "env_group_expectation_explicit": bool(expected_group),
        "env_mode_expectation_600": expected_mode == "600",
        "env_file_exists": observed["exists"] is True,
        "owner_match": observed["owner"] == expected_owner,
        "group_match": observed["group"] == expected_group,
        "mode_match": observed["mode"] == expected_mode,
        "interactive_sudo_required_no": config.get("interactive_sudo_required") == "NO",
        "group_based_secret_access_no": config.get("group_based_secret_access") == "NO",
        "owner_mismatch_fail_closed": config.get("owner_mismatch_fail_closed") == "YES",
        "mode_mismatch_fail_closed": config.get("mode_mismatch_fail_closed") == "YES",
        "identity_unresolved_fail_closed": config.get("identity_unresolved_fail_closed") == "YES",
        "stat_permission_failure_fail_closed": (
            config.get("stat_permission_failure_fail_closed") == "YES"
        ),
        "production_env_change_authorized_no": (
            config.get("production_env_change_authorized") == "NO"
        ),
        "owner_or_mode_change_authorized_no": (
            config.get("owner_or_mode_change_authorized") == "NO"
        ),
        "production_request_authorized_no": config.get("production_request_authorized") == "NO",
        "go_live_no_go": config.get("go_live") == "NO-GO",
        "live_trading_no_go": config.get("live_trading") == "NO-GO",
    }
    errors = [name for name, passed in checks.items() if not passed]
    result = "PASS" if not errors else "BLOCKED"
    return {
        "generated_at": utc_now(),
        "result": result,
        "errors": errors,
        "contract": {
            "runtime_identity": runtime_identity,
            "runtime_group": runtime_group,
            "canonical_env_path": str(env_path),
            "expected_env_owner": expected_owner,
            "expected_env_group": expected_group,
            "expected_env_mode": expected_mode,
            "interactive_sudo_required": config.get("interactive_sudo_required"),
            "group_based_secret_access": config.get("group_based_secret_access"),
        },
        "observed_env": observed,
        "checks": checks,
        "boundary": {
            "production_env_changed": "NO",
            "owner_mode_changed": "NO",
            "secret_value_read": "NO",
            "secret_value_disclosed": "NO",
            "production_signing_executed": "NO",
            "production_http_network_attempted": "NO",
            "production_request_sent": "NO",
            "production_order_sent": "NO",
            "transport_called_when_blocked": "NO",
            "canary_executed": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }


def markdown(report: dict[str, Any]) -> str:
    contract = report["contract"]
    observed = report["observed_env"]
    checks = "\n".join(
        f"- {name}: {'PASS' if passed else 'FAIL'}"
        for name, passed in report["checks"].items()
    )
    errors = "\n".join(f"- {item}" for item in report["errors"]) or "- none"
    boundary = report["boundary"]
    return f"""# Production Runtime Owner Contract Validation

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}

## Contract

- runtime identity: {contract["runtime_identity"]}
- runtime group: {contract["runtime_group"]}
- canonical env path: `{contract["canonical_env_path"]}`
- expected env owner: {contract["expected_env_owner"]}
- expected env group: {contract["expected_env_group"]}
- expected env mode: {contract["expected_env_mode"]}
- interactive sudo required: {contract["interactive_sudo_required"]}
- group-based secret access: {contract["group_based_secret_access"]}

## Observed Env Metadata

- exists: {observed["exists"]}
- owner: {observed["owner"]}
- group: {observed["group"]}
- mode: {observed["mode"]}
- stat error: {observed["stat_error"]}

## Checks

{checks}

## Errors

{errors}

## Boundary

- production env changed: {boundary["production_env_changed"]}
- owner/mode changed: {boundary["owner_mode_changed"]}
- secret value read: {boundary["secret_value_read"]}
- secret value disclosed: {boundary["secret_value_disclosed"]}
- production signing executed: {boundary["production_signing_executed"]}
- production HTTP/network attempted: {boundary["production_http_network_attempted"]}
- production request sent: {boundary["production_request_sent"]}
- production order sent: {boundary["production_order_sent"]}
- transport called when blocked: {boundary["transport_called_when_blocked"]}
- canary executed: {boundary["canary_executed"]}
- go-live: {boundary["go_live"]}
- live trading: {boundary["live_trading"]}
"""


def main() -> int:
    config = read_json(CONFIG_PATH)
    report = validate(config)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(markdown(report), encoding="utf-8")

    print("[Production Runtime Owner Contract Validation]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(f"errors: {len(report['errors'])}")
    print(f"runtime_identity: {report['contract']['runtime_identity']}")
    print(f"expected_env_owner: {report['contract']['expected_env_owner']}")
    print(f"observed_owner: {report['observed_env']['owner']}")
    print(f"observed_mode: {report['observed_env']['mode']}")
    print("secret_value_read: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
