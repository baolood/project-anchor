#!/usr/bin/env bash
# Verifies the bounded runtime-presence boundary for future testnet credentials
# without printing secrets or changing runtime.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_testnet_credential_runtime_presence_boundary.sh

Checks that testnet credential runtime presence can only be classified as a
bounded presence state.

This boundary must always keep:
- TESTNET_CREDENTIAL_RUNTIME_PRESENCE=present|missing|unknown
- SECRET_VALUE_PRINTED=false
- EXTERNAL_REQUEST_STARTED=false
- RUNTIME_MUTATION=false
- LIVE_TRADING=false
- NEXT_GATE=blocked_until_operator_approval

Any attempt to print secret values, start external requests, mutate runtime,
perform live trading, or skip the operator-approval gate is BLOCKED.
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
    "presence_boundary_id",
    "testnet_credential_runtime_presence",
    "secret_value_printed",
    "external_request_started",
    "runtime_mutation",
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
    "presence_boundary_id",
    "testnet_credential_runtime_presence",
    "secret_value_printed",
    "external_request_started",
    "runtime_mutation",
    "live_trading",
    "next_gate",
}

ALLOWED_PRESENCE = {"present", "missing", "unknown"}


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

    if payload.get("testnet_credential_runtime_presence") not in ALLOWED_PRESENCE:
        reasons.append("invalid_presence_state")
    if payload.get("secret_value_printed") != "false":
        reasons.append("secret_value_printed")
    if payload.get("external_request_started") != "false":
        reasons.append("external_request_started")
    if payload.get("runtime_mutation") != "false":
        reasons.append("runtime_mutation")
    if payload.get("live_trading") != "false":
        reasons.append("live_trading")
    if payload.get("next_gate") != "blocked_until_operator_approval":
        reasons.append("next_gate_not_blocked_until_operator_approval")

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
            "REAL_HANDOFF_TESTNET_CREDENTIAL_RUNTIME_PRESENCE_BOUNDARY_CHECK FAIL: "
            f"{name}: expected {'PASS' if should_pass else 'BLOCKED'}, got "
            f"{'PASS' if passed else 'BLOCKED'} ({';'.join(reasons) or 'none'})"
        )
    return name


base = {
    "presence_boundary_id": "real-handoff-testnet-credential-runtime-presence-20260526-001",
    "testnet_credential_runtime_presence": "unknown",
    "secret_value_printed": "false",
    "external_request_started": "false",
    "runtime_mutation": "false",
    "live_trading": "false",
    "next_gate": "blocked_until_operator_approval",
    "payload_notes": "bounded testnet credential runtime presence boundary",
}

covered = [
    assert_case("presence_unknown_clean", dict(base), True),
    assert_case("presence_present_clean", dict(base, testnet_credential_runtime_presence="present"), True),
    assert_case("presence_missing_clean", dict(base, testnet_credential_runtime_presence="missing"), True),
    assert_case("secret_value_printed", dict(base, secret_value_printed="true"), False),
    assert_case("external_request_started", dict(base, external_request_started="true"), False),
    assert_case("runtime_mutation", dict(base, runtime_mutation="true"), False),
    assert_case("live_trading", dict(base, live_trading="true"), False),
    assert_case("raw_secret_present", dict(base, payload_notes="contains real-secret"), False),
    assert_case("next_gate_opened", dict(base, next_gate="allowed_now"), False),
]

print("TESTNET_CREDENTIAL_RUNTIME_PRESENCE=unknown")
print("SECRET_VALUE_PRINTED=false")
print("EXTERNAL_REQUEST_STARTED=false")
print("RUNTIME_MUTATION=false")
print("LIVE_TRADING=false")
print("NEXT_GATE=blocked_until_operator_approval")
print(
    "REAL_HANDOFF_TESTNET_CREDENTIAL_RUNTIME_PRESENCE_BOUNDARY_CHECK PASS: fixture matrix intact for "
    + ",".join(covered)
)
PY
