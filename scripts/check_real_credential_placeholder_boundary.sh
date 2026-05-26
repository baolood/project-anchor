#!/usr/bin/env bash
# Verifies the bounded placeholder policy for any future real credential
# handoff preparation without allowing real credential values or execution
# intent to slip in.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_credential_placeholder_boundary.sh

Checks a fixture matrix for real-credential placeholder handling.

Allowed:
- naming canonical TESTNET credential slots
- using explicit placeholder markers only
- keeping executor posture mock / real_enable=0

Blocked:
- any real-looking credential value
- any runtime mutation toggle
- any external-request intent
- any live-trading intent

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
PLACEHOLDER_VALUES = {"<placeholder>", "<redacted>", "NOT_COLLECTED", ""}
ALLOWED_KEYS = {
    "TESTNET_EXCHANGE_API_KEY",
    "TESTNET_EXCHANGE_API_SECRET",
    "TESTNET_EXCHANGE_KEY_ID",
    "expected_executor_mode",
    "expected_real_enable",
    "notes",
}


def validate(payload):
    reasons = []
    unknown = sorted(set(payload.keys()) - ALLOWED_KEYS)
    if unknown:
        reasons.append("unknown_key:" + ",".join(unknown))

    if payload.get("expected_executor_mode") != "mock":
        reasons.append("invalid_expected_executor_mode")
    if payload.get("expected_real_enable") != "0":
        reasons.append("invalid_expected_real_enable")

    for key in (
        "TESTNET_EXCHANGE_API_KEY",
        "TESTNET_EXCHANGE_API_SECRET",
        "TESTNET_EXCHANGE_KEY_ID",
    ):
        value = payload.get(key, "")
        if not isinstance(value, str):
            reasons.append(f"invalid_placeholder_type:{key}")
            continue
        if value not in PLACEHOLDER_VALUES:
            reasons.append(f"real_value_present:{key}")

    notes = payload.get("notes", "")
    if not isinstance(notes, str):
        reasons.append("invalid_notes")
    else:
        lowered = notes.lower()
        if "external request" in lowered or "send now" in lowered:
            reasons.append("external_request_intent_present")
        if "live trading" in lowered or "go live now" in lowered:
            reasons.append("live_trading_intent_present")
        if "export testnet_executor_real_enable=1" in lowered:
            reasons.append("runtime_mutation_intent_present")

    return reasons


def assert_case(name, payload, should_pass):
    reasons = validate(payload)
    passed = not reasons
    if passed != should_pass:
        raise SystemExit(
            "REAL_CREDENTIAL_PLACEHOLDER_BOUNDARY_CHECK FAIL: "
            f"{name}: expected {'PASS' if should_pass else 'BLOCKED'}, got "
            f"{'PASS' if passed else 'BLOCKED'} ({';'.join(reasons) or 'none'})"
        )
    return name


base = {
    "TESTNET_EXCHANGE_API_KEY": "<placeholder>",
    "TESTNET_EXCHANGE_API_SECRET": "<placeholder>",
    "TESTNET_EXCHANGE_KEY_ID": "NOT_COLLECTED",
    "expected_executor_mode": "mock",
    "expected_real_enable": "0",
    "notes": "review-only placeholder contract",
}

covered = [
    assert_case("placeholder_slots_only", dict(base), True),
    assert_case("real_key_value_present", dict(base, TESTNET_EXCHANGE_API_KEY="real-key"), False),
    assert_case("real_secret_value_present", dict(base, TESTNET_EXCHANGE_API_SECRET="real-secret"), False),
    assert_case("runtime_toggle_intent_present", dict(base, notes="export TESTNET_EXECUTOR_REAL_ENABLE=1 before handoff"), False),
    assert_case("external_request_intent_present", dict(base, notes="send now external request after injection"), False),
    assert_case("live_trading_intent_present", dict(base, notes="live trading approval follows this handoff"), False),
    assert_case("real_mode_expected", dict(base, expected_executor_mode="real"), False),
]

print(
    "REAL_CREDENTIAL_PLACEHOLDER_BOUNDARY_CHECK PASS: fixture matrix intact for "
    + ",".join(covered)
)
PY
