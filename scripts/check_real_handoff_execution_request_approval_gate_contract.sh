#!/usr/bin/env bash
# Verifies the bounded approval-gate contract for a future real handoff
# execution request without injecting credentials or changing runtime.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_execution_request_approval_gate_contract.sh

Checks a fixture matrix for the future real handoff execution-request approval
gate contract.

Allowed contract themes:
- reviewed state must already be ready_for_real_review
- execution-request envelope contract must already be green
- approval must remain review-only and must not trigger external requests

Rejected contract themes:
- approval missing
- review verdict not PASS
- first-controlled-send artifact missing
- real-fill check not PASS
- operator signoff missing
- credential state unknown
- live trading requested
- external request requested now

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
    "gate_id",
    "reviewed_state",
    "execution_request_envelope_contract_status",
    "review_verdict",
    "first_controlled_send_artifact_status",
    "real_fill_check_status",
    "operator_signoff_status",
    "credential_state",
    "external_request_now",
    "live_trading_requested",
    "ticket_ref",
    "notes",
}

FORBIDDEN_KEYS = {
    "api_key",
    "secret",
    "allow_external_request",
    "allow_runtime_mutation",
    "runtime_patch",
    "env_patch",
    "executor_mode",
    "real_enable",
}

REQUIRED_STRING_KEYS = {
    "gate_id",
    "reviewed_state",
    "execution_request_envelope_contract_status",
    "review_verdict",
    "first_controlled_send_artifact_status",
    "real_fill_check_status",
    "operator_signoff_status",
    "credential_state",
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
    if payload.get("execution_request_envelope_contract_status") != "green":
        reasons.append("execution_request_envelope_contract_not_green")
    if payload.get("review_verdict") != "PASS":
        reasons.append("review_verdict_not_pass")
    if payload.get("first_controlled_send_artifact_status") != "present":
        reasons.append("first_controlled_send_artifact_missing")
    if payload.get("real_fill_check_status") != "PASS":
        reasons.append("real_fill_check_not_pass")
    if payload.get("operator_signoff_status") != "present":
        reasons.append("operator_signoff_missing")
    if payload.get("credential_state") != "placeholder_only":
        reasons.append("credential_state_unknown")
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
            "REAL_HANDOFF_EXECUTION_REQUEST_APPROVAL_GATE_CONTRACT_CHECK FAIL: "
            f"{name}: expected {'PASS' if should_pass else 'BLOCKED'}, got "
            f"{'PASS' if passed else 'BLOCKED'} ({';'.join(reasons) or 'none'})"
        )
    return name


base = {
    "gate_id": "real-handoff-execution-approval-gate-20260526-001",
    "reviewed_state": "ready_for_real_review",
    "execution_request_envelope_contract_status": "green",
    "review_verdict": "PASS",
    "first_controlled_send_artifact_status": "present",
    "real_fill_check_status": "PASS",
    "operator_signoff_status": "present",
    "credential_state": "placeholder_only",
    "external_request_now": "false",
    "live_trading_requested": "false",
    "ticket_ref": "RHEAG-001",
    "notes": "bounded execution request approval gate contract",
}

covered = [
    assert_case("minimal_valid_execution_request_approval_gate", dict(base), True),
    assert_case("approval_missing", dict(base, operator_signoff_status="missing"), False),
    assert_case("review_verdict_not_pass", dict(base, review_verdict="BLOCKED"), False),
    assert_case("first_controlled_send_artifact_missing", dict(base, first_controlled_send_artifact_status="missing"), False),
    assert_case("real_fill_check_not_pass", dict(base, real_fill_check_status="FAIL"), False),
    assert_case("operator_signoff_missing", dict(base, operator_signoff_status="missing"), False),
    assert_case("credential_state_unknown", dict(base, credential_state="unknown"), False),
    assert_case("live_trading_requested", dict(base, live_trading_requested="true"), False),
    assert_case("external_request_now_true", dict(base, external_request_now="true"), False),
]

print(
    "REAL_HANDOFF_EXECUTION_REQUEST_APPROVAL_GATE_CONTRACT_CHECK PASS: fixture matrix intact for "
    + ",".join(covered)
)
PY
