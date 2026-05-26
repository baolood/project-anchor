#!/usr/bin/env bash
# Verifies the bounded final-dispatch-preflight contract for a future real
# handoff executor dispatch without injecting credentials or changing runtime.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_executor_final_dispatch_preflight_contract.sh

Checks a fixture matrix for the future real handoff executor-final-dispatch-
preflight contract.

Allowed contract themes:
- reviewed state must already be ready_for_real_review
- executor-launch-approval-gate contract must already be green
- final dispatch preflight must remain explicitly blocked for dispatch
- expected executor posture must remain mock / real_enable=0

Rejected contract themes:
- external request explicit approval missing
- credential runtime not verified
- testnet_only not confirmed
- operator window not current
- rollback packet not current
- review artifact not current
- live trading requested
- raw secret present in payload
- unexpected exchange base URL

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
    "dispatch_preflight_id",
    "reviewed_state",
    "executor_launch_approval_gate_status",
    "external_request_explicit_approval",
    "credential_runtime_verified",
    "testnet_only_confirmed",
    "operator_window_current",
    "rollback_packet_current",
    "review_artifact_current",
    "live_trading_requested",
    "approved_exchange_base_url",
    "expected_executor_mode",
    "expected_real_enable",
    "payload_notes",
    "ticket_ref",
}

APPROVED_BASE_URL = "https://testnet.binancefuture.com"

FORBIDDEN_KEYS = {
    "api_key",
    "secret",
    "raw_secret",
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
    "external_request_now",
}

REQUIRED_STRING_KEYS = {
    "dispatch_preflight_id",
    "reviewed_state",
    "executor_launch_approval_gate_status",
    "external_request_explicit_approval",
    "credential_runtime_verified",
    "testnet_only_confirmed",
    "operator_window_current",
    "rollback_packet_current",
    "review_artifact_current",
    "live_trading_requested",
    "approved_exchange_base_url",
    "expected_executor_mode",
    "expected_real_enable",
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
    if payload.get("external_request_explicit_approval") != "false":
        reasons.append("external_request_explicit_approval_missing")
    if payload.get("credential_runtime_verified") != "false":
        reasons.append("credential_runtime_not_verified")
    if payload.get("testnet_only_confirmed") != "false":
        reasons.append("testnet_only_not_confirmed")
    if payload.get("operator_window_current") != "false":
        reasons.append("operator_window_not_current")
    if payload.get("rollback_packet_current") != "false":
        reasons.append("rollback_packet_not_current")
    if payload.get("review_artifact_current") != "false":
        reasons.append("review_artifact_not_current")
    if payload.get("live_trading_requested") != "false":
        reasons.append("live_trading_requested")
    if payload.get("approved_exchange_base_url") != APPROVED_BASE_URL:
        reasons.append("unexpected_exchange_base_url")
    if payload.get("expected_executor_mode") != "mock":
        reasons.append("invalid_expected_executor_mode")
    if payload.get("expected_real_enable") != "0":
        reasons.append("invalid_expected_real_enable")

    notes = payload.get("payload_notes")
    if notes is not None and not isinstance(notes, str):
        reasons.append("invalid_payload_notes")

    for key, value in payload.items():
        if isinstance(value, str):
            lowered = value.lower()
            if "real-secret" in lowered or "real-key" in lowered or "private_key" in lowered:
                reasons.append(f"raw_secret_present_in_payload:{key}")

    return reasons


def assert_case(name, payload, should_pass):
    reasons = validate(payload)
    passed = not reasons
    if passed != should_pass:
        raise SystemExit(
            "REAL_HANDOFF_EXECUTOR_FINAL_DISPATCH_PREFLIGHT_CONTRACT_CHECK FAIL: "
            f"{name}: expected {'PASS' if should_pass else 'BLOCKED'}, got "
            f"{'PASS' if passed else 'BLOCKED'} ({';'.join(reasons) or 'none'})"
        )
    return name


base = {
    "dispatch_preflight_id": "real-handoff-executor-final-dispatch-preflight-20260526-001",
    "reviewed_state": "ready_for_real_review",
    "executor_launch_approval_gate_status": "green",
    "external_request_explicit_approval": "false",
    "credential_runtime_verified": "false",
    "testnet_only_confirmed": "false",
    "operator_window_current": "false",
    "rollback_packet_current": "false",
    "review_artifact_current": "false",
    "live_trading_requested": "false",
    "approved_exchange_base_url": APPROVED_BASE_URL,
    "expected_executor_mode": "mock",
    "expected_real_enable": "0",
    "payload_notes": "bounded final dispatch preflight contract",
    "ticket_ref": "RHEFDP-001",
}

covered = [
    assert_case("clean_blocked_by_default", dict(base), True),
    assert_case("external_request_explicit_approval_missing", dict(base, external_request_explicit_approval="true"), False),
    assert_case("credential_runtime_not_verified", dict(base, credential_runtime_verified="true"), False),
    assert_case("testnet_only_not_confirmed", dict(base, testnet_only_confirmed="true"), False),
    assert_case("operator_window_not_current", dict(base, operator_window_current="true"), False),
    assert_case("rollback_packet_not_current", dict(base, rollback_packet_current="true"), False),
    assert_case("review_artifact_not_current", dict(base, review_artifact_current="true"), False),
    assert_case("live_trading_requested", dict(base, live_trading_requested="true"), False),
    assert_case("raw_secret_present_in_payload", dict(base, payload_notes="contains real-secret"), False),
    assert_case("unexpected_exchange_base_url", dict(base, approved_exchange_base_url="https://evil.example.com"), False),
]

print(
    "REAL_HANDOFF_EXECUTOR_FINAL_DISPATCH_PREFLIGHT_CONTRACT_CHECK PASS: fixture matrix intact for "
    + ",".join(covered)
)
PY
