#!/usr/bin/env bash
# Verifies the bounded launch-gate contract for a future real handoff executor
# activation without injecting credentials or changing runtime.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_executor_activation_launch_gate_contract.sh [--fixture <name>]

Checks a fixture matrix for the future real handoff executor-activation launch
gate contract.

Allowed contract themes:
- reviewed state must already be ready_for_real_review
- executor-activation window contract must already be green
- launch gate must remain explicitly not approved for external request
- expected executor posture must remain mock / real_enable=0

Rejected contract themes:
- approval missing
- activation window not open
- credential state unknown
- external request not explicitly approved
- live trading requested
- runtime mutation requested
- review artifact missing
- operator signoff missing
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
        echo "REAL_HANDOFF_EXECUTOR_ACTIVATION_LAUNCH_GATE_CONTRACT_CHECK FAIL: --fixture requires a value" >&2
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
    "launch_gate_id",
    "reviewed_state",
    "executor_activation_window_status",
    "approval_state",
    "activation_window_open",
    "credential_state",
    "external_request_explicitly_approved",
    "live_trading_requested",
    "runtime_mutation_requested",
    "review_artifact_status",
    "operator_signoff_status",
    "rollback_plan_status",
    "expected_executor_mode",
    "expected_real_enable",
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
    "live",
    "real_mode",
    "external_request_now",
}

REQUIRED_STRING_KEYS = {
    "launch_gate_id",
    "reviewed_state",
    "executor_activation_window_status",
    "approval_state",
    "activation_window_open",
    "credential_state",
    "external_request_explicitly_approved",
    "live_trading_requested",
    "runtime_mutation_requested",
    "review_artifact_status",
    "operator_signoff_status",
    "rollback_plan_status",
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
    if payload.get("executor_activation_window_status") != "green":
        reasons.append("activation_window_not_open")
    if payload.get("approval_state") != "present":
        reasons.append("approval_missing")
    if payload.get("activation_window_open") != "false":
        reasons.append("activation_window_not_open")
    if payload.get("credential_state") != "placeholder_only":
        reasons.append("credential_state_unknown")
    if payload.get("external_request_explicitly_approved") != "false":
        reasons.append("external_request_not_explicitly_approved")
    if payload.get("live_trading_requested") != "false":
        reasons.append("live_trading_requested")
    if payload.get("runtime_mutation_requested") != "false":
        reasons.append("runtime_mutation_requested")
    if payload.get("review_artifact_status") != "present":
        reasons.append("review_artifact_missing")
    if payload.get("operator_signoff_status") != "present":
        reasons.append("operator_signoff_missing")
    if payload.get("rollback_plan_status") != "present":
        reasons.append("rollback_plan_missing")
    if payload.get("expected_executor_mode") != "mock":
        reasons.append("invalid_expected_executor_mode")
    if payload.get("expected_real_enable") != "0":
        reasons.append("invalid_expected_real_enable")

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
            "REAL_HANDOFF_EXECUTOR_ACTIVATION_LAUNCH_GATE_CONTRACT_CHECK FAIL: "
            f"{name}: expected {'PASS' if should_pass else 'BLOCKED'}, got "
            f"{'PASS' if passed else 'BLOCKED'} ({';'.join(reasons) or 'none'})"
        )
    return name


base = {
    "launch_gate_id": "real-handoff-executor-activation-launch-gate-20260526-001",
    "reviewed_state": "ready_for_real_review",
    "executor_activation_window_status": "green",
    "approval_state": "present",
    "activation_window_open": "false",
    "credential_state": "placeholder_only",
    "external_request_explicitly_approved": "false",
    "live_trading_requested": "false",
    "runtime_mutation_requested": "false",
    "review_artifact_status": "present",
    "operator_signoff_status": "present",
    "rollback_plan_status": "present",
    "expected_executor_mode": "mock",
    "expected_real_enable": "0",
    "ticket_ref": "RHELG-001",
    "notes": "bounded executor activation launch gate contract",
}

cases = {
    "not_approved_default": (dict(base), True),
    "approval_missing": (dict(base, approval_state="missing"), False),
    "window_closed_violation": (dict(base, activation_window_open="true"), False),
    "credential_unknown": (dict(base, credential_state="unknown"), False),
    "approved_but_still_blocked": (dict(base, external_request_explicitly_approved="true"), False),
    "live_requested": (dict(base, live_trading_requested="true"), False),
    "runtime_mutation_requested": (dict(base, runtime_mutation_requested="true"), False),
    "review_artifact_missing": (dict(base, review_artifact_status="missing"), False),
    "operator_signoff_missing": (dict(base, operator_signoff_status="missing"), False),
    "rollback_plan_missing": (dict(base, rollback_plan_status="missing"), False),
    "secret_value_present": (dict(base, api_key="real-key"), False),
}

fixture = os.environ.get("FIXTURE", "matrix")

if fixture == "matrix":
    covered = [assert_case(name, payload, should_pass) for name, (payload, should_pass) in cases.items()]
else:
    if fixture not in cases:
        raise SystemExit(
            "REAL_HANDOFF_EXECUTOR_ACTIVATION_LAUNCH_GATE_CONTRACT_CHECK FAIL: "
            f"unsupported fixture {fixture}"
        )
    payload, should_pass = cases[fixture]
    covered = [assert_case(fixture, payload, should_pass)]

print(
    "REAL_HANDOFF_EXECUTOR_ACTIVATION_LAUNCH_GATE_CONTRACT_CHECK PASS: fixture matrix intact for "
    + ",".join(covered)
)
PY
