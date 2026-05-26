#!/usr/bin/env bash
# Verifies the bounded contract for a future real handoff opening signoff
# packet without injecting credentials or changing runtime.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_opening_signoff_packet_contract.sh

Checks a fixture matrix for the future real handoff opening-signoff-packet
contract.

Allowed contract themes:
- reviewed state must already be ready_for_real_review
- opening-decision-packet line must already be green
- expected executor posture must remain mock / real_enable=0
- packet references, signoff labels, and credential slot names may appear

Rejected contract themes:
- non-green opening-decision-packet line
- real-mode or real-enable expectations
- runtime mutation requests
- external request requests
- live trading requests
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
    "packet_id",
    "reviewed_state",
    "opening_decision_packet_line_status",
    "evidence_command_id",
    "artifact_path",
    "signoff_packet_path",
    "expected_executor_mode",
    "expected_real_enable",
    "credential_slots_requested",
    "signoff_role",
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
    "packet_id",
    "reviewed_state",
    "opening_decision_packet_line_status",
    "evidence_command_id",
    "artifact_path",
    "signoff_packet_path",
    "expected_executor_mode",
    "expected_real_enable",
    "signoff_role",
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
    if payload.get("opening_decision_packet_line_status") != "green":
        reasons.append("opening_decision_packet_line_not_green")
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
            "REAL_HANDOFF_OPENING_SIGNOFF_PACKET_CONTRACT_CHECK FAIL: "
            f"{name}: expected {'PASS' if should_pass else 'BLOCKED'}, got "
            f"{'PASS' if passed else 'BLOCKED'} ({';'.join(reasons) or 'none'})"
        )
    return name


base = {
    "packet_id": "real-handoff-opening-signoff-packet-20260526-001",
    "reviewed_state": "ready_for_real_review",
    "opening_decision_packet_line_status": "green",
    "evidence_command_id": "order-mocksmoke-20260525111528",
    "artifact_path": "docs/reviews/real_testnet/FIRST_CONTROLLED_SEND_2026-05-25_order-mocksmoke-20260525111528.md",
    "signoff_packet_path": "docs/REAL_TESTNET_FIRST_REAL_REQUEST_OPERATOR_SIGNOFF_RECORD_V1.md",
    "expected_executor_mode": "mock",
    "expected_real_enable": "0",
    "credential_slots_requested": [
        "TESTNET_EXCHANGE_API_KEY",
        "TESTNET_EXCHANGE_API_SECRET",
        "TESTNET_EXCHANGE_KEY_ID",
    ],
    "signoff_role": "operator_signoff",
    "ticket_ref": "RHOSP-001",
    "notes": "bounded opening signoff packet contract",
}

covered = [
    assert_case("minimal_valid_opening_signoff_packet", dict(base), True),
    assert_case("reviewed_state_not_ready", dict(base, reviewed_state="synthetic_only"), False),
    assert_case("opening_decision_packet_line_not_green", dict(base, opening_decision_packet_line_status="blocked"), False),
    assert_case("real_mode_requested", dict(base, expected_executor_mode="real"), False),
    assert_case("real_enable_requested", dict(base, expected_real_enable="1"), False),
    assert_case("runtime_mutation_requested", dict(base, runtime_patch="export TESTNET_EXECUTOR_REAL_ENABLE=1"), False),
    assert_case("external_request_requested", dict(base, allow_external_request="yes"), False),
    assert_case("live_trading_requested", dict(base, allow_live_trading="yes"), False),
    assert_case("secret_value_present", dict(base, TESTNET_EXCHANGE_API_KEY="real-key"), False),
]

print(
    "REAL_HANDOFF_OPENING_SIGNOFF_PACKET_CONTRACT_CHECK PASS: fixture matrix intact for "
    + ",".join(covered)
)
PY
