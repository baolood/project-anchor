#!/usr/bin/env bash
# Verifies the bounded explicit-send-approval packet for a future testnet
# external request without issuing any request, printing credentials, or
# changing runtime.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_explicit_send_approval_packet_boundary.sh [--fixture NAME]

Checks whether a future testnet external request has a bounded explicit send
approval packet only.

This boundary must always keep:
- SEND_APPROVAL_PACKET_BOUNDARY=PASS|BLOCKED
- APPROVED_EXECUTION_MODE=testnet
- OPERATOR_IDENTITY_PRESENT=yes|no
- REVIEW_VERDICT_PASS=yes|no
- ROLLBACK_PACKET_PRESENT=yes|no
- SEND_WINDOW_CURRENT=yes|no
- EXTERNAL_REQUEST_STARTED=false
- LIVE_TRADING=false
- NEXT_GATE=blocked_until_explicit_runtime_send

Any attempt to start an external request, print credentials, mutate runtime, or
open live trading is BLOCKED.
EOF
}

if (($# > 0)); then
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --fixture)
      if (($# != 2)); then
        usage >&2
        exit 2
      fi
      FIXTURE_NAME="$2"
      export FIXTURE_NAME
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
fi

python3 - <<'PY'
import os

ALLOWED_KEYS = {
    "approval_packet_id",
    "send_approval_packet_boundary",
    "operator_identity_present",
    "approval_timestamp_present",
    "approved_command_id_present",
    "approved_execution_mode",
    "review_verdict_pass",
    "rollback_packet_present",
    "send_window_current",
    "external_request_started",
    "live_trading",
    "next_gate",
    "payload_notes",
}

FORBIDDEN_KEYS = {
    "api_key",
    "secret",
    "raw_secret",
    "credential_value",
    "runtime_patch",
    "env_patch",
    "live",
    "external_request_now",
}

REQUIRED_STRING_KEYS = {
    "approval_packet_id",
    "send_approval_packet_boundary",
    "operator_identity_present",
    "approval_timestamp_present",
    "approved_command_id_present",
    "approved_execution_mode",
    "review_verdict_pass",
    "rollback_packet_present",
    "send_window_current",
    "external_request_started",
    "live_trading",
    "next_gate",
}

ALLOWED_BOUNDARY = {"PASS", "BLOCKED"}
ALLOWED_YES_NO = {"yes", "no"}


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

    if payload.get("send_approval_packet_boundary") not in ALLOWED_BOUNDARY:
        reasons.append("invalid_send_approval_packet_boundary")

    for key in (
        "operator_identity_present",
        "approval_timestamp_present",
        "approved_command_id_present",
        "review_verdict_pass",
        "rollback_packet_present",
        "send_window_current",
    ):
        if payload.get(key) not in ALLOWED_YES_NO:
            reasons.append(f"invalid_{key}")

    if payload.get("approved_execution_mode") != "testnet":
        reasons.append("approved_execution_mode_not_testnet")
    if payload.get("external_request_started") != "false":
        reasons.append("external_request_started")
    if payload.get("live_trading") != "false":
        reasons.append("live_trading")
    if payload.get("next_gate") != "blocked_until_explicit_runtime_send":
        reasons.append("next_gate_not_blocked_until_explicit_runtime_send")

    notes = payload.get("payload_notes")
    if notes is not None and not isinstance(notes, str):
        reasons.append("invalid_payload_notes")

    for key, value in payload.items():
        if isinstance(value, str):
            lowered = value.lower()
            if "real-secret" in lowered or "real-key" in lowered or "private_key" in lowered:
                reasons.append(f"raw_secret_present:{key}")

    return reasons


def assert_case(name, payload, should_pass):
    reasons = validate(payload)
    passed = not reasons
    if passed != should_pass:
        raise SystemExit(
            "REAL_HANDOFF_EXPLICIT_SEND_APPROVAL_PACKET_BOUNDARY_CHECK FAIL: "
            f"{name}: expected {'PASS' if should_pass else 'BLOCKED'}, got "
            f"{'PASS' if passed else 'BLOCKED'} ({';'.join(reasons) or 'none'})"
        )
    return name


base = {
    "approval_packet_id": "real-handoff-explicit-send-approval-packet-20260526-001",
    "send_approval_packet_boundary": "PASS",
    "operator_identity_present": "yes",
    "approval_timestamp_present": "yes",
    "approved_command_id_present": "yes",
    "approved_execution_mode": "testnet",
    "review_verdict_pass": "yes",
    "rollback_packet_present": "yes",
    "send_window_current": "yes",
    "external_request_started": "false",
    "live_trading": "false",
    "next_gate": "blocked_until_explicit_runtime_send",
    "payload_notes": "bounded explicit send approval packet",
}

fixtures = {
    "explicit_send_approval_clean_pass_but_runtime_send_blocked": (dict(base), True),
    "approval_packet_missing": (dict(base, approval_packet_id=""), False),
    "operator_identity_missing": (dict(base, operator_identity_present=""), False),
    "approval_timestamp_missing": (dict(base, approval_timestamp_present=""), False),
    "approved_command_id_missing": (dict(base, approved_command_id_present=""), False),
    "approved_execution_mode_not_testnet": (dict(base, approved_execution_mode="real"), False),
    "review_verdict_not_pass": (dict(base, send_approval_packet_boundary="BLOCKED", review_verdict_pass="no"), True),
    "rollback_packet_missing": (dict(base, send_approval_packet_boundary="BLOCKED", rollback_packet_present="no"), True),
    "send_window_not_current": (dict(base, send_approval_packet_boundary="BLOCKED", send_window_current="no"), True),
    "live_trading_requested": (dict(base, live_trading="true"), False),
    "raw_secret_present": (dict(base, payload_notes="contains real-secret"), False),
    "external_request_started_true": (dict(base, external_request_started="true"), False),
}

requested_fixture = os.getenv("FIXTURE_NAME", "").strip()
if requested_fixture:
    if requested_fixture not in fixtures:
        raise SystemExit(
            "REAL_HANDOFF_EXPLICIT_SEND_APPROVAL_PACKET_BOUNDARY_CHECK FAIL: "
            f"unknown fixture {requested_fixture!r}"
        )
    payload, should_pass = fixtures[requested_fixture]
    covered = [assert_case(requested_fixture, payload, should_pass)]
else:
    covered = [
        assert_case(name, payload, should_pass)
        for name, (payload, should_pass) in fixtures.items()
    ]

print("SEND_APPROVAL_PACKET_BOUNDARY=PASS")
print("APPROVED_EXECUTION_MODE=testnet")
print("OPERATOR_IDENTITY_PRESENT=yes")
print("REVIEW_VERDICT_PASS=yes")
print("ROLLBACK_PACKET_PRESENT=yes")
print("SEND_WINDOW_CURRENT=yes")
print("EXTERNAL_REQUEST_STARTED=false")
print("LIVE_TRADING=false")
print("NEXT_GATE=blocked_until_explicit_runtime_send")
print(
    "REAL_HANDOFF_EXPLICIT_SEND_APPROVAL_PACKET_BOUNDARY_CHECK PASS: fixture matrix intact for "
    + ",".join(covered)
)
PY
