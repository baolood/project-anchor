#!/usr/bin/env bash
# Verifies the bounded input contract for any future real handoff
# implementation task without injecting credentials or mutating runtime.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_task_input_contract.sh

Checks a fixture matrix for the future real handoff task input contract.

Allowed contract themes:
- review-ready evidence references only
- expected executor posture must remain mock / real_enable=0
- requested credential slots may be named, but values may not appear

Rejected contract themes:
- secret-bearing values
- runtime mutation requests
- external request requests
- live trading requests
- real-mode posture requests

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
    "handoff_id",
    "requested_by",
    "reviewed_state",
    "evidence_command_id",
    "artifact_path",
    "host_label",
    "configured_origin",
    "expected_executor_mode",
    "expected_real_enable",
    "credential_slots_requested",
    "ticket_ref",
    "notes",
}

ALLOWED_SLOTS = {
    "TESTNET_EXCHANGE_API_KEY",
    "TESTNET_EXCHANGE_API_SECRET",
    "TESTNET_EXCHANGE_KEY_ID",
}

FORBIDDEN_KEYS = {
    "TESTNET_EXCHANGE_API_KEY",
    "TESTNET_EXCHANGE_API_SECRET",
    "TESTNET_EXCHANGE_KEY_ID",
    "allow_external_request",
    "allow_runtime_mutation",
    "allow_live_trading",
    "runtime_patch",
    "env_patch",
    "executor_mode",
    "real_enable",
}

REQUIRED_STRING_KEYS = {
    "handoff_id",
    "requested_by",
    "reviewed_state",
    "evidence_command_id",
    "artifact_path",
    "host_label",
    "configured_origin",
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
    if payload.get("expected_executor_mode") != "mock":
        reasons.append("invalid_expected_executor_mode")
    if payload.get("expected_real_enable") != "0":
        reasons.append("invalid_expected_real_enable")

    slots = payload.get("credential_slots_requested")
    if not isinstance(slots, list) or not slots:
        reasons.append("invalid_credential_slots_requested")
    else:
        for slot in slots:
            if slot not in ALLOWED_SLOTS:
                reasons.append(f"invalid_credential_slot:{slot}")

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
            "REAL_HANDOFF_TASK_INPUT_CONTRACT_CHECK FAIL: "
            f"{name}: expected {'PASS' if should_pass else 'BLOCKED'}, got "
            f"{'PASS' if passed else 'BLOCKED'} ({';'.join(reasons) or 'none'})"
        )
    return name


base = {
    "handoff_id": "real-handoff-20260526-001",
    "requested_by": "baolood",
    "reviewed_state": "ready_for_real_review",
    "evidence_command_id": "order-mocksmoke-20260525111528",
    "artifact_path": "docs/reviews/real_testnet/FIRST_CONTROLLED_SEND_2026-05-25_order-mocksmoke-20260525111528.md",
    "host_label": "binance_futures_testnet",
    "configured_origin": "https://testnet.binancefuture.com",
    "expected_executor_mode": "mock",
    "expected_real_enable": "0",
    "credential_slots_requested": [
        "TESTNET_EXCHANGE_API_KEY",
        "TESTNET_EXCHANGE_API_SECRET",
        "TESTNET_EXCHANGE_KEY_ID",
    ],
    "ticket_ref": "RH-001",
    "notes": "bounded handoff planning input",
}

covered = [
    assert_case("minimal_valid_input", dict(base), True),
    assert_case("secret_value_present", dict(base, TESTNET_EXCHANGE_API_KEY="real-key"), False),
    assert_case("runtime_mutation_requested", dict(base, runtime_patch="export TESTNET_EXECUTOR_REAL_ENABLE=1"), False),
    assert_case("external_request_requested", dict(base, allow_external_request="yes"), False),
    assert_case("real_mode_requested", dict(base, expected_executor_mode="real"), False),
    assert_case("live_trading_requested", dict(base, allow_live_trading="yes"), False),
    assert_case("missing_evidence_command_id", dict(base, evidence_command_id=""), False),
]

print(
    "REAL_HANDOFF_TASK_INPUT_CONTRACT_CHECK PASS: fixture matrix intact for "
    + ",".join(covered)
)
PY
