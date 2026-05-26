#!/usr/bin/env bash
# Verifies the dry-run-only dispatch boundary for a future real handoff
# executor adapter without injecting credentials or changing runtime.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_executor_dry_run_dispatch_boundary.sh

Checks that a future real handoff dispatch envelope can only enter a dry-run
executor adapter boundary.

This boundary must always keep:
- ADAPTER_MODE=dry_run
- EXTERNAL_REQUEST_STARTED=false
- RUNTIME_MUTATION=false
- LIVE_TRADING=false
- AUDIT_RESULT_PRESENT=true

Any request to switch adapter mode, start external requests, mutate runtime,
perform live trading, or omit audit evidence is BLOCKED.
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
    "dispatch_boundary_id",
    "adapter_mode",
    "external_request_started",
    "runtime_mutation",
    "live_trading",
    "audit_result_present",
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
    "dispatch_boundary_id",
    "adapter_mode",
    "external_request_started",
    "runtime_mutation",
    "live_trading",
    "audit_result_present",
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
            "REAL_HANDOFF_EXECUTOR_DRY_RUN_DISPATCH_BOUNDARY_CHECK FAIL: "
            f"{name}: expected {'PASS' if should_pass else 'BLOCKED'}, got "
            f"{'PASS' if passed else 'BLOCKED'} ({';'.join(reasons) or 'none'})"
        )
    return name


base = {
    "dispatch_boundary_id": "real-handoff-executor-dry-run-dispatch-20260526-001",
    "adapter_mode": "dry_run",
    "external_request_started": "false",
    "runtime_mutation": "false",
    "live_trading": "false",
    "audit_result_present": "true",
    "payload_notes": "bounded dry run dispatch boundary",
}

covered = [
    assert_case("dry_run_clean", dict(base), True),
    assert_case("adapter_mode_real", dict(base, adapter_mode="real"), False),
    assert_case("external_request_started", dict(base, external_request_started="true"), False),
    assert_case("runtime_mutation", dict(base, runtime_mutation="true"), False),
    assert_case("live_trading", dict(base, live_trading="true"), False),
    assert_case("audit_result_missing", dict(base, audit_result_present="false"), False),
    assert_case("raw_secret_present", dict(base, payload_notes="contains real-secret"), False),
]

print("DRY_RUN_DISPATCH_BOUNDARY=PASS")
print("ADAPTER_MODE=dry_run")
print("EXTERNAL_REQUEST_STARTED=false")
print("RUNTIME_MUTATION=false")
print("LIVE_TRADING=false")
print("AUDIT_RESULT_PRESENT=true")
print(
    "REAL_HANDOFF_EXECUTOR_DRY_RUN_DISPATCH_BOUNDARY_CHECK PASS: fixture matrix intact for "
    + ",".join(covered)
)
PY
