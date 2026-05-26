#!/usr/bin/env bash
# Verifies the bounded audit envelope for a future dry-run dispatch without
# injecting credentials or changing runtime.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_dry_run_dispatch_audit_envelope.sh [--fixture <name>]

Checks that a future dry-run dispatch produces an auditable envelope.

This envelope must always keep:
- DRY_RUN_DISPATCH_AUDIT_ENVELOPE=PASS
- ADAPTER_MODE=dry_run
- EXTERNAL_REQUEST_STARTED=false
- RUNTIME_MUTATION=false
- LIVE_TRADING=false
- AUDIT_RESULT_PRESENT=true
- REVIEW_VERDICT_REQUIRED=true

Any request to switch adapter mode, start external requests, mutate runtime,
perform live trading, omit audit evidence, or omit review verdict requirements
is BLOCKED.
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
        echo "REAL_HANDOFF_DRY_RUN_DISPATCH_AUDIT_ENVELOPE_CHECK FAIL: --fixture requires a value" >&2
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
    "audit_envelope_id",
    "adapter_mode",
    "external_request_started",
    "runtime_mutation",
    "live_trading",
    "audit_result_present",
    "review_verdict_required",
    "payload_notes",
}

FORBIDDEN_KEYS = {
    "api_key",
    "secret",
    "raw_secret",
    "real_mode",
    "external_request_now",
    "runtime_patch",
    "env_patch",
    "live",
}

REQUIRED_STRING_KEYS = {
    "audit_envelope_id",
    "adapter_mode",
    "external_request_started",
    "runtime_mutation",
    "live_trading",
    "audit_result_present",
    "review_verdict_required",
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

    if payload.get("adapter_mode") != "dry_run":
        reasons.append("adapter_mode_not_dry_run")
    if payload.get("external_request_started") != "false":
        reasons.append("external_request_started")
    if payload.get("runtime_mutation") != "false":
        reasons.append("runtime_mutation")
    if payload.get("live_trading") != "false":
        reasons.append("live_trading")
    if payload.get("audit_result_present") != "true":
        reasons.append("audit_result_missing")
    if payload.get("review_verdict_required") != "true":
        reasons.append("review_verdict_not_required")

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
            "REAL_HANDOFF_DRY_RUN_DISPATCH_AUDIT_ENVELOPE_CHECK FAIL: "
            f"{name}: expected {'PASS' if should_pass else 'BLOCKED'}, got "
            f"{'PASS' if passed else 'BLOCKED'} ({';'.join(reasons) or 'none'})"
        )
    return name


base = {
    "audit_envelope_id": "real-handoff-dry-run-dispatch-audit-envelope-20260526-001",
    "adapter_mode": "dry_run",
    "external_request_started": "false",
    "runtime_mutation": "false",
    "live_trading": "false",
    "audit_result_present": "true",
    "review_verdict_required": "true",
    "payload_notes": "bounded dry run dispatch audit envelope",
}

cases = {
    "clean_dry_run_pass": (dict(base), True),
    "external_request_started_true_blocked": (dict(base, external_request_started="true"), False),
    "runtime_mutation_true_blocked": (dict(base, runtime_mutation="true"), False),
    "live_trading_true_blocked": (dict(base, live_trading="true"), False),
    "audit_result_missing_blocked": (dict(base, audit_result_present="false"), False),
    "review_verdict_missing_blocked": (dict(base, review_verdict_required="false"), False),
    "adapter_mode_not_dry_run_blocked": (dict(base, adapter_mode="real"), False),
    "raw_secret_present_blocked": (dict(base, payload_notes="contains real-secret"), False),
}

fixture = os.environ.get("FIXTURE", "matrix")

if fixture == "matrix":
    covered = [assert_case(name, payload, should_pass) for name, (payload, should_pass) in cases.items()]
else:
    if fixture not in cases:
        raise SystemExit(
            "REAL_HANDOFF_DRY_RUN_DISPATCH_AUDIT_ENVELOPE_CHECK FAIL: "
            f"unsupported fixture {fixture}"
        )
    payload, should_pass = cases[fixture]
    covered = [assert_case(fixture, payload, should_pass)]

print("DRY_RUN_DISPATCH_AUDIT_ENVELOPE=PASS")
print("ADAPTER_MODE=dry_run")
print("EXTERNAL_REQUEST_STARTED=false")
print("RUNTIME_MUTATION=false")
print("LIVE_TRADING=false")
print("AUDIT_RESULT_PRESENT=true")
print("REVIEW_VERDICT_REQUIRED=true")
print(
    "REAL_HANDOFF_DRY_RUN_DISPATCH_AUDIT_ENVELOPE_CHECK PASS: fixture matrix intact for "
    + ",".join(covered)
)
PY
