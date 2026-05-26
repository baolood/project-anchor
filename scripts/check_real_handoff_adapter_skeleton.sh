#!/usr/bin/env bash
# Verifies the real handoff adapter skeleton keeps its bounded mock-posture
# contract without requiring real credentials or external requests.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_adapter_skeleton.sh

Checks that the real handoff adapter skeleton:
- accepts a canonical mock-posture fixture
- rejects key drift and credential-bearing fixtures via a bounded fixture matrix
- stays review-safe and credential-value-free

This script does not inject credentials, mutate runtime, issue external
requests, or approve live trading.
EOF
}

if (($# > 0)); then
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "REAL_HANDOFF_ADAPTER_SKELETON_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

cd "${ROOT}/anchor-backend"

  python3 - <<'PY'
from typing import Dict

from app.executors.testnet_real_handoff_adapter import (
    build_real_handoff_adapter_skeleton,
    build_real_handoff_runtime_snapshot,
)


def fail(msg: str) -> None:
    raise SystemExit(f"REAL_HANDOFF_ADAPTER_SKELETON_CHECK FAIL: {msg}")


base_fixture = {
    "TESTNET_EXCHANGE_BASE_URL": "https://testnet.binancefuture.com",
    "TESTNET_EXECUTOR_MODE": "mock",
    "TESTNET_EXECUTOR_REAL_ENABLE": "0",
    "TESTNET_EXCHANGE_API_KEY": "",
    "TESTNET_EXCHANGE_API_SECRET": "",
    "TESTNET_EXCHANGE_KEY_ID": "",
}

def merged_fixture(**overrides: str) -> Dict[str, str]:
    fixture = dict(base_fixture)
    fixture.update(overrides)
    return fixture


cases = [
    {
        "name": "mock_clean",
        "fixture": merged_fixture(),
        "expect_review_blocked": False,
        "expect_credential_free": True,
        "expect_blocked": [],
    },
    {
        "name": "drift_real_mode",
        "fixture": merged_fixture(TESTNET_EXECUTOR_MODE="real"),
        "expect_review_blocked": True,
        "expect_credential_free": False,
        "expect_blocked": ["executor_mode_not_mock"],
    },
    {
        "name": "drift_real_enable",
        "fixture": merged_fixture(TESTNET_EXECUTOR_REAL_ENABLE="1"),
        "expect_review_blocked": True,
        "expect_credential_free": False,
        "expect_blocked": ["real_enable_not_zero"],
    },
    {
        "name": "credential_present_but_mock",
        "fixture": merged_fixture(TESTNET_EXCHANGE_API_KEY="real-key"),
        "expect_review_blocked": True,
        "expect_credential_free": False,
        "expect_blocked": [],
    },
    {
        "name": "base_url_missing",
        "fixture": merged_fixture(TESTNET_EXCHANGE_BASE_URL=""),
        "expect_review_blocked": True,
        "expect_credential_free": True,
        "expect_blocked": ["base_url_missing"],
    },
]

covered = []
for case in cases:
    name = case["name"]
    adapter = build_real_handoff_adapter_skeleton(case["fixture"])
    runtime = adapter["current_runtime"]
    review_blocked = (not adapter["task_opening_allowed"]) or bool(runtime["blocked_reasons"])

    if runtime["configured_origin"] != case["fixture"]["TESTNET_EXCHANGE_BASE_URL"]:
        fail(f"{name}: configured origin mismatch")
    if review_blocked != case["expect_review_blocked"]:
        fail(f"{name}: unexpected review_blocked classification")
    if runtime["credential_free_mock_posture"] != case["expect_credential_free"]:
        fail(f"{name}: unexpected credential_free_mock_posture state")
    for blocked_reason in case["expect_blocked"]:
        if blocked_reason not in runtime["blocked_reasons"]:
            fail(f"{name}: missing blocked reason {blocked_reason}")

    snapshot = build_real_handoff_runtime_snapshot(case["fixture"])
    api_key = str(case["fixture"].get("TESTNET_EXCHANGE_API_KEY", ""))
    api_secret = str(case["fixture"].get("TESTNET_EXCHANGE_API_SECRET", ""))
    key_id = str(case["fixture"].get("TESTNET_EXCHANGE_KEY_ID", ""))

    if api_key and api_key in str(snapshot):
        fail(f"{name}: snapshot leaked api key value")
    if api_secret and api_secret in str(snapshot):
        fail(f"{name}: snapshot leaked api secret value")
    if key_id and key_id in str(snapshot):
        fail(f"{name}: snapshot leaked key id value")

    covered.append(name)

print(
    "REAL_HANDOFF_ADAPTER_SKELETON_CHECK PASS: fixture matrix intact for "
    + ",".join(covered)
)
PY
