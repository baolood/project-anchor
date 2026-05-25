#!/usr/bin/env bash
# Verifies that the first-controlled-send status report and its gates agree on
# the current repository state.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_first_controlled_send_status_integration.sh

Checks that the first-controlled-send status stack is internally consistent
for the current repository state.

Expected current posture:
- STATE=synthetic_only
- state gate passes for synthetic_only
- domain gate remains blocked

This script does not authorize a real controlled send or live trading.
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

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "FIRST_CONTROLLED_SEND_STATUS_INTEGRATION FAIL: cannot resolve repository root" >&2
  exit 1
}

STATUS_SCRIPT="${ROOT}/scripts/first_controlled_send_status_report.sh"

fail() {
  echo "FIRST_CONTROLLED_SEND_STATUS_INTEGRATION FAIL: $1" >&2
  exit 1
}

status_output="$("$STATUS_SCRIPT")"
grep -q '^STATE=synthetic_only$' <<<"$status_output" || fail "status report is not synthetic_only"
grep -q '^DOMAIN_WORTH_BUYING=no$' <<<"$status_output" || fail "domain worth buying should still be no"
grep -q '^EXTERNAL_SHOWCASE_READY=no$' <<<"$status_output" || fail "external showcase should still be no"

state_gate_output="$("$STATUS_SCRIPT" --require-state synthetic_only)"
grep -q 'FIRST_CONTROLLED_SEND_STATE_GATE PASS: STATE=synthetic_only' <<<"$state_gate_output" || fail "state gate did not pass for synthetic_only"

if domain_gate_output="$("$STATUS_SCRIPT" --check-domain-gate 2>&1)"; then
  fail "domain gate unexpectedly passed"
fi
if ! grep -q 'FIRST_CONTROLLED_SEND_DOMAIN_GATE BLOCKED: DOMAIN_WORTH_BUYING=no' <<<"$domain_gate_output"; then
  fail "domain gate did not block with the expected message"
fi

echo "FIRST_CONTROLLED_SEND_STATUS_INTEGRATION PASS: synthetic_only stack consistent"
