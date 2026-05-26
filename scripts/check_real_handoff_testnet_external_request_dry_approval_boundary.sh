#!/usr/bin/env bash
# Verifies the bounded dry-approval boundary for a future testnet external
# request without issuing any request or changing runtime.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_testnet_external_request_dry_approval_boundary.sh [--fixture NAME]

Checks whether a future testnet external request may enter dry approval only.

This boundary must always keep:
- DRY_APPROVAL_BOUNDARY=PASS|BLOCKED
- CREDENTIAL_PRESENCE=present_redacted|missing|unknown
- REAL_REVIEW_READY=yes|no
- OPERATOR_APPROVAL_PRESENT=yes|no
- EXTERNAL_REQUEST_STARTED=false
- LIVE_TRADING=false
- NEXT_GATE=blocked_until_explicit_send_approval

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
    "dry_approval_id",
    "dry_approval_boundary",
    "credential_presence",
    "real_review_ready",
    "operator_approval_present",
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
    "external_request_now",
    "runtime_patch",
    "env_patch",
    "live",
}

REQUIRED_STRING_KEYS = {
    "dry_approval_id",
    "dry_approval_boundary",
    "credential_presence",
    "real_review_ready",
    "operator_approval_present",
    "external_request_started",
    "live_trading",
    "next_gate",
}

ALLOWED_BOUNDARY = {"PASS", "BLOCKED"}
ALLOWED_PRESENCE = {"present_redacted", "missing", "unknown"}
ALLOWED_BOOL = {"yes", "no"}


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

    if payload.get("dry_approval_boundary") not in ALLOWED_BOUNDARY:
        reasons.append("invalid_dry_approval_boundary")
    if payload.get("credential_presence") not in ALLOWED_PRESENCE:
        reasons.append("invalid_credential_presence")
    if payload.get("real_review_ready") not in ALLOWED_BOOL:
        reasons.append("invalid_real_review_ready")
    if payload.get("operator_approval_present") not in ALLOWED_BOOL:
        reasons.append("invalid_operator_approval_present")
    if payload.get("external_request_started") != "false":
        reasons.append("external_request_started")
    if payload.get("live_trading") != "false":
        reasons.append("live_trading")
    if payload.get("next_gate") != "blocked_until_explicit_send_approval":
        reasons.append("next_gate_not_blocked_until_explicit_send_approval")

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
            "REAL_HANDOFF_TESTNET_EXTERNAL_REQUEST_DRY_APPROVAL_BOUNDARY_CHECK FAIL: "
            f"{name}: expected {'PASS' if should_pass else 'BLOCKED'}, got "
            f"{'PASS' if passed else 'BLOCKED'} ({';'.join(reasons) or 'none'})"
        )
    return name


base = {
    "dry_approval_id": "real-handoff-testnet-external-request-dry-approval-20260526-001",
    "dry_approval_boundary": "PASS",
    "credential_presence": "unknown",
    "real_review_ready": "no",
    "operator_approval_present": "no",
    "external_request_started": "false",
    "live_trading": "false",
    "next_gate": "blocked_until_explicit_send_approval",
    "payload_notes": "bounded dry approval boundary",
}

fixtures = {
    "dry_approval_clean_pass_but_send_blocked": (dict(base), True),
    "credential_unknown_blocked": (dict(base, dry_approval_boundary="BLOCKED"), True),
    "real_review_not_ready_blocked": (dict(base, dry_approval_boundary="BLOCKED"), True),
    "operator_approval_missing_blocked": (dict(base, dry_approval_boundary="BLOCKED"), True),
    "credential_present_redacted_pass": (dict(base, credential_presence="present_redacted"), True),
    "credential_missing_pass": (dict(base, credential_presence="missing"), True),
    "real_review_ready_yes_pass": (dict(base, real_review_ready="yes"), True),
    "operator_approval_present_yes_pass": (dict(base, operator_approval_present="yes"), True),
    "external_request_started_true_blocked": (dict(base, external_request_started="true"), False),
    "live_trading_true_blocked": (dict(base, live_trading="true"), False),
    "secret_print_attempt_blocked": (dict(base, payload_notes="contains real-secret"), False),
    "send_approval_present_but_window_closed_blocked": (
        dict(base, dry_approval_boundary="BLOCKED", operator_approval_present="yes", real_review_ready="yes"),
        True,
    ),
}

requested_fixture = os.getenv("FIXTURE_NAME", "").strip()
if requested_fixture:
    if requested_fixture not in fixtures:
        raise SystemExit(
            "REAL_HANDOFF_TESTNET_EXTERNAL_REQUEST_DRY_APPROVAL_BOUNDARY_CHECK FAIL: "
            f"unknown fixture {requested_fixture!r}"
        )
    payload, should_pass = fixtures[requested_fixture]
    covered = [assert_case(requested_fixture, payload, should_pass)]
else:
    covered = [
        assert_case(name, payload, should_pass)
        for name, (payload, should_pass) in fixtures.items()
    ]

print("DRY_APPROVAL_BOUNDARY=PASS")
print("CREDENTIAL_PRESENCE=unknown")
print("REAL_REVIEW_READY=no")
print("OPERATOR_APPROVAL_PRESENT=no")
print("EXTERNAL_REQUEST_STARTED=false")
print("LIVE_TRADING=false")
print("NEXT_GATE=blocked_until_explicit_send_approval")
print(
    "REAL_HANDOFF_TESTNET_EXTERNAL_REQUEST_DRY_APPROVAL_BOUNDARY_CHECK PASS: fixture matrix intact for "
    + ",".join(covered)
)
PY
