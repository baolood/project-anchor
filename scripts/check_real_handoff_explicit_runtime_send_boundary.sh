#!/usr/bin/env bash
# Verifies the bounded explicit-runtime-send boundary for a future testnet
# external request without issuing any request, printing credentials, or
# changing runtime.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_explicit_runtime_send_boundary.sh [--fixture NAME]

Checks whether a future testnet external request may reach the final explicit
runtime-send boundary only.

This boundary must always keep:
- RUNTIME_SEND_BOUNDARY=PASS|BLOCKED
- APPROVED_EXECUTION_MODE=testnet
- APPROVAL_PACKET_PRESENT=yes|no
- EXPLICIT_RUNTIME_SEND_PRESENT=yes|no
- CREDENTIAL_RUNTIME_VERIFIED=yes|no
- REVIEW_VERDICT_PASS=yes|no
- ROLLBACK_PACKET_PRESENT=yes|no
- SEND_WINDOW_CURRENT=yes|no
- EXTERNAL_REQUEST_STARTED=false
- LIVE_TRADING=false
- NEXT_GATE=blocked_before_real_request

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
    "runtime_send_boundary_id",
    "runtime_send_boundary",
    "approval_packet_present",
    "explicit_runtime_send_present",
    "approved_execution_mode",
    "credential_runtime_verified",
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
    "runtime_send_boundary_id",
    "runtime_send_boundary",
    "approval_packet_present",
    "explicit_runtime_send_present",
    "approved_execution_mode",
    "credential_runtime_verified",
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

    if payload.get("runtime_send_boundary") not in ALLOWED_BOUNDARY:
        reasons.append("invalid_runtime_send_boundary")

    for key in (
        "approval_packet_present",
        "explicit_runtime_send_present",
        "credential_runtime_verified",
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
    if payload.get("next_gate") != "blocked_before_real_request":
        reasons.append("next_gate_not_blocked_before_real_request")

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
            "REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_BOUNDARY_CHECK FAIL: "
            f"{name}: expected {'PASS' if should_pass else 'BLOCKED'}, got "
            f"{'PASS' if passed else 'BLOCKED'} ({';'.join(reasons) or 'none'})"
        )
    return name, payload, passed


base = {
    "runtime_send_boundary_id": "real-handoff-explicit-runtime-send-boundary-20260527-001",
    "runtime_send_boundary": "BLOCKED",
    "approval_packet_present": "yes",
    "explicit_runtime_send_present": "yes",
    "approved_execution_mode": "testnet",
    "credential_runtime_verified": "yes",
    "review_verdict_pass": "yes",
    "rollback_packet_present": "yes",
    "send_window_current": "yes",
    "external_request_started": "false",
    "live_trading": "false",
    "next_gate": "blocked_before_real_request",
    "payload_notes": "bounded explicit runtime send boundary",
}

fixtures = {
    "runtime_send_clean_blocked_by_default": (dict(base), True),
    "approval_packet_missing": (dict(base, runtime_send_boundary="PASS", approval_packet_present=""), False),
    "explicit_runtime_send_missing": (dict(base, runtime_send_boundary="PASS", explicit_runtime_send_present=""), False),
    "approved_execution_mode_not_testnet": (dict(base, runtime_send_boundary="PASS", approved_execution_mode="real"), False),
    "credential_runtime_not_verified": (dict(base, runtime_send_boundary="BLOCKED", credential_runtime_verified="no"), True),
    "review_verdict_not_pass": (dict(base, runtime_send_boundary="BLOCKED", review_verdict_pass="no"), True),
    "rollback_packet_missing": (dict(base, runtime_send_boundary="BLOCKED", rollback_packet_present="no"), True),
    "send_window_not_current": (dict(base, runtime_send_boundary="BLOCKED", send_window_current="no"), True),
    "next_gate_not_blocked_before_real_request": (dict(base, runtime_send_boundary="PASS", next_gate="ready_to_send"), False),
    "runtime_patch_present": (dict(base, runtime_send_boundary="PASS", runtime_patch="export TESTNET_EXECUTOR_REAL_ENABLE=1"), False),
    "live_trading_requested": (dict(base, runtime_send_boundary="PASS", live_trading="true"), False),
    "raw_secret_present": (dict(base, runtime_send_boundary="PASS", payload_notes="contains real-secret"), False),
    "external_request_started_true": (dict(base, runtime_send_boundary="PASS", external_request_started="true"), False),
}

requested_fixture = os.getenv("FIXTURE_NAME", "").strip()
if requested_fixture:
    if requested_fixture not in fixtures:
        raise SystemExit(
            "REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_BOUNDARY_CHECK FAIL: "
            f"unknown fixture {requested_fixture!r}"
        )
    payload, should_pass = fixtures[requested_fixture]
    covered = [assert_case(requested_fixture, payload, should_pass)]
else:
    covered = [
        assert_case(name, payload, should_pass)
        for name, (payload, should_pass) in fixtures.items()
    ]

summary_payload = covered[0][1] if requested_fixture else base
summary_result = covered[0][2] if requested_fixture else True

print(f"RUNTIME_SEND_BOUNDARY={summary_payload['runtime_send_boundary']}")
print(f"APPROVED_EXECUTION_MODE={summary_payload['approved_execution_mode']}")
print(f"APPROVAL_PACKET_PRESENT={summary_payload['approval_packet_present']}")
print(f"EXPLICIT_RUNTIME_SEND_PRESENT={summary_payload['explicit_runtime_send_present']}")
print(f"CREDENTIAL_RUNTIME_VERIFIED={summary_payload['credential_runtime_verified']}")
print(f"REVIEW_VERDICT_PASS={summary_payload['review_verdict_pass']}")
print(f"ROLLBACK_PACKET_PRESENT={summary_payload['rollback_packet_present']}")
print(f"SEND_WINDOW_CURRENT={summary_payload['send_window_current']}")
print("EXTERNAL_REQUEST_STARTED=false")
print("LIVE_TRADING=false")
print(f"NEXT_GATE={summary_payload['next_gate']}")
print(f"FIXTURE_EXPECTED_RESULT={'PASS' if summary_result else 'BLOCKED'}")
print(f"FIXTURE_VALIDATION_RESULT={'PASS' if summary_result else 'BLOCKED'}")
print(
    "REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_BOUNDARY_CHECK PASS: fixture matrix intact for "
    + ",".join(name for name, _, _ in covered)
)
PY
