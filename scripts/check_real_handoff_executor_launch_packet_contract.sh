#!/usr/bin/env bash
# Verifies the bounded launch-packet contract for a future real handoff
# executor launch without injecting credentials or changing runtime.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_executor_launch_packet_contract.sh [--fixture <name>]

Checks a fixture matrix for the future real handoff executor-launch-packet
contract.

Allowed contract themes:
- reviewed state must already be ready_for_real_review
- executor-activation launch gate contract must already be green
- launch packet must remain review_only and mock / real_enable=0
- approved base URL, review artifact pointers, and placeholder-only
  credential slots may appear

Rejected contract themes:
- non-green executor-activation launch gate
- packet that requests launch_now
- real-mode or real-enable expectations
- credential state unknown
- unapproved exchange base URL
- runtime mutation requests
- external request requests
- live trading requests
- review artifact missing
- rollback plan missing
- secret-bearing credential values

This script does not inject credentials, mutate runtime, issue external
requests, or authorize live trading.
EOF
}

FIXTURE="matrix"

while (($# > 0)); do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --fixture)
      shift
      if (($# == 0)); then
        echo "REAL_HANDOFF_EXECUTOR_LAUNCH_PACKET_CONTRACT_CHECK FAIL: --fixture requires a value" >&2
        exit 2
      fi
      FIXTURE="$1"
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
  shift
done

FIXTURE="${FIXTURE}" python3 - <<'PY'
import os

ALLOWED_KEYS = {
    "launch_packet_id",
    "reviewed_state",
    "executor_activation_launch_gate_status",
    "launch_packet_mode",
    "review_artifact_status",
    "rollback_plan_status",
    "expected_executor_mode",
    "expected_real_enable",
    "credential_state",
    "approved_exchange_base_url",
    "external_request_now",
    "live_trading_requested",
    "ticket_ref",
    "notes",
}

APPROVED_BASE_URL = "https://testnet.binancefuture.com"

FORBIDDEN_KEYS = {
    "api_key",
    "secret",
    "allow_external_request",
    "allow_runtime_mutation",
    "runtime_patch",
    "env_patch",
    "executor_mode",
    "real_enable",
    "live",
    "real_mode",
    "exchange_base_url",
    "unapproved_exchange_base_url",
    "launch_now",
}

REQUIRED_STRING_KEYS = {
    "launch_packet_id",
    "reviewed_state",
    "executor_activation_launch_gate_status",
    "launch_packet_mode",
    "review_artifact_status",
    "rollback_plan_status",
    "expected_executor_mode",
    "expected_real_enable",
    "credential_state",
    "approved_exchange_base_url",
    "external_request_now",
    "live_trading_requested",
}


def validate(payload):
    reasons = []
    unknown = sorted(set(payload.keys()) - ALLOWED_KEYS)
    if unknown:
        reasons.append("unknown_key:" + ",".join(unknown))

    for key in sorted(FORBIDDEN_KEYS):
        if key in payload:
            reasons.append(f"forbidden_key:{key}")

    for key in sorted(REQUIRED_STRING_KEYS):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            reasons.append(f"invalid_required_field:{key}")

    if payload.get("reviewed_state") != "ready_for_real_review":
        reasons.append("invalid_reviewed_state")
    if payload.get("executor_activation_launch_gate_status") != "green":
        reasons.append("executor_activation_launch_gate_not_green")
    if payload.get("launch_packet_mode") != "review_only":
        reasons.append("launch_packet_mode_not_review_only")
    if payload.get("review_artifact_status") != "present":
        reasons.append("review_artifact_missing")
    if payload.get("rollback_plan_status") != "present":
        reasons.append("rollback_plan_missing")
    if payload.get("expected_executor_mode") != "mock":
        reasons.append("invalid_expected_executor_mode")
    if payload.get("expected_real_enable") != "0":
        reasons.append("invalid_expected_real_enable")
    if payload.get("credential_state") != "placeholder_only":
        reasons.append("credential_state_unknown")
    if payload.get("approved_exchange_base_url") != APPROVED_BASE_URL:
        reasons.append("invalid_approved_exchange_base_url")
    if payload.get("external_request_now") != "false":
        reasons.append("external_request_now_true")
    if payload.get("live_trading_requested") != "false":
        reasons.append("live_trading_requested")

    notes = payload.get("notes")
    if notes is not None and not isinstance(notes, str):
        reasons.append("invalid_notes")

    for key, value in payload.items():
        if isinstance(value, str):
            lowered = value.lower()
            if "real-secret" in lowered or "real-key" in lowered or "private_key" in lowered:
                reasons.append(f"secret_value_present:{key}")

    return reasons


def assert_case(name, payload, should_pass):
    reasons = validate(payload)
    passed = not reasons
    if passed != should_pass:
        raise SystemExit(
            "REAL_HANDOFF_EXECUTOR_LAUNCH_PACKET_CONTRACT_CHECK FAIL: "
            f"{name}: expected {'PASS' if should_pass else 'BLOCKED'}, got "
            f"{'PASS' if passed else 'BLOCKED'} ({';'.join(reasons) or 'none'})"
        )
    return name


base = {
    "launch_packet_id": "real-handoff-executor-launch-packet-20260526-001",
    "reviewed_state": "ready_for_real_review",
    "executor_activation_launch_gate_status": "green",
    "launch_packet_mode": "review_only",
    "review_artifact_status": "present",
    "rollback_plan_status": "present",
    "expected_executor_mode": "mock",
    "expected_real_enable": "0",
    "credential_state": "placeholder_only",
    "approved_exchange_base_url": APPROVED_BASE_URL,
    "external_request_now": "false",
    "live_trading_requested": "false",
    "ticket_ref": "RHELP-001",
    "notes": "bounded executor launch packet contract",
}

cases = {
    "not_launchable_default": (dict(base), True),
    "launch_gate_not_green": (dict(base, executor_activation_launch_gate_status="blocked"), False),
    "launch_now_requested": (dict(base, launch_packet_mode="launch_now"), False),
    "review_artifact_missing": (dict(base, review_artifact_status="missing"), False),
    "rollback_plan_missing": (dict(base, rollback_plan_status="missing"), False),
    "real_mode_requested": (dict(base, expected_executor_mode="real"), False),
    "real_enable_requested": (dict(base, expected_real_enable="1"), False),
    "credential_state_unknown": (dict(base, credential_state="unknown"), False),
    "unapproved_exchange_base_url": (dict(base, approved_exchange_base_url="https://evil.example.com"), False),
    "external_request_now_true": (dict(base, external_request_now="true"), False),
    "live_trading_requested": (dict(base, live_trading_requested="true"), False),
    "secret_value_present": (dict(base, api_key="real-key"), False),
}

fixture = os.environ.get("FIXTURE", "matrix")

if fixture == "matrix":
    covered = [assert_case(name, payload, should_pass) for name, (payload, should_pass) in cases.items()]
else:
    if fixture not in cases:
        raise SystemExit(
            "REAL_HANDOFF_EXECUTOR_LAUNCH_PACKET_CONTRACT_CHECK FAIL: "
            f"unsupported fixture {fixture}"
        )
    payload, should_pass = cases[fixture]
    covered = [assert_case(fixture, payload, should_pass)]

print(
    "REAL_HANDOFF_EXECUTOR_LAUNCH_PACKET_CONTRACT_CHECK PASS: fixture matrix intact for "
    + ",".join(covered)
)
PY
