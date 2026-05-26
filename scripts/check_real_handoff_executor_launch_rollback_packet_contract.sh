#!/usr/bin/env bash
# Verifies the bounded launch-rollback-packet contract for a future real
# handoff executor launch without injecting credentials or changing runtime.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_executor_launch_rollback_packet_contract.sh

Checks a fixture matrix for the future real handoff executor-launch-rollback-
packet contract.

Allowed contract themes:
- reviewed state must already be ready_for_real_review
- executor-launch-approval-gate contract must already be green
- rollback packet must remain review_only and mock / real_enable=0
- approved base URL, review artifact pointers, and placeholder-only
  credential state may appear

Rejected contract themes:
- non-green executor-launch-approval-gate contract
- packet that requests rollback_now
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

python3 - <<'PY'
ALLOWED_KEYS = {
    "rollback_packet_id",
    "reviewed_state",
    "executor_launch_approval_gate_status",
    "rollback_packet_mode",
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
    "rollback_now",
}

REQUIRED_STRING_KEYS = {
    "rollback_packet_id",
    "reviewed_state",
    "executor_launch_approval_gate_status",
    "rollback_packet_mode",
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
    if payload.get("executor_launch_approval_gate_status") != "green":
        reasons.append("executor_launch_approval_gate_not_green")
    if payload.get("rollback_packet_mode") != "review_only":
        reasons.append("rollback_packet_mode_not_review_only")
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
            "REAL_HANDOFF_EXECUTOR_LAUNCH_ROLLBACK_PACKET_CONTRACT_CHECK FAIL: "
            f"{name}: expected {'PASS' if should_pass else 'BLOCKED'}, got "
            f"{'PASS' if passed else 'BLOCKED'} ({';'.join(reasons) or 'none'})"
        )
    return name


base = {
    "rollback_packet_id": "real-handoff-executor-launch-rollback-packet-20260526-001",
    "reviewed_state": "ready_for_real_review",
    "executor_launch_approval_gate_status": "green",
    "rollback_packet_mode": "review_only",
    "review_artifact_status": "present",
    "rollback_plan_status": "present",
    "expected_executor_mode": "mock",
    "expected_real_enable": "0",
    "credential_state": "placeholder_only",
    "approved_exchange_base_url": APPROVED_BASE_URL,
    "external_request_now": "false",
    "live_trading_requested": "false",
    "ticket_ref": "RHELRP-001",
    "notes": "bounded executor launch rollback packet contract",
}

covered = [
    assert_case("minimal_valid_executor_launch_rollback_packet", dict(base), True),
    assert_case("launch_approval_gate_not_green", dict(base, executor_launch_approval_gate_status="blocked"), False),
    assert_case("rollback_now_requested", dict(base, rollback_packet_mode="rollback_now"), False),
    assert_case("review_artifact_missing", dict(base, review_artifact_status="missing"), False),
    assert_case("rollback_plan_missing", dict(base, rollback_plan_status="missing"), False),
    assert_case("real_mode_requested", dict(base, expected_executor_mode="real"), False),
    assert_case("real_enable_requested", dict(base, expected_real_enable="1"), False),
    assert_case("credential_state_unknown", dict(base, credential_state="unknown"), False),
    assert_case("unapproved_exchange_base_url", dict(base, approved_exchange_base_url="https://evil.example.com"), False),
    assert_case("external_request_now_true", dict(base, external_request_now="true"), False),
    assert_case("live_trading_requested", dict(base, live_trading_requested="true"), False),
    assert_case("secret_value_present", dict(base, api_key="real-key"), False),
]

print(
    "REAL_HANDOFF_EXECUTOR_LAUNCH_ROLLBACK_PACKET_CONTRACT_CHECK PASS: fixture matrix intact for "
    + ",".join(covered)
)
PY
