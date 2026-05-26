#!/usr/bin/env bash
# Verifies that the standalone real handoff adapter evidence report agrees with
# the first-controlled-send status report on the bounded mock-only review
# surface.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_adapter_report_integration.sh

Checks that:
- real_handoff_adapter_evidence_report.sh emits the bounded adapter evidence
- first_controlled_send_status_report.sh exposes the same review-safe posture
- both surfaces remain mock-only, no-external-request, no-runtime-mutation

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

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "REAL_HANDOFF_ADAPTER_REPORT_INTEGRATION FAIL: cannot resolve repository root" >&2
  exit 1
}

STATUS_SCRIPT="${ROOT}/scripts/first_controlled_send_status_report.sh"
EVIDENCE_SCRIPT="${ROOT}/scripts/real_handoff_adapter_evidence_report.sh"

fail() {
  echo "REAL_HANDOFF_ADAPTER_REPORT_INTEGRATION FAIL: $1" >&2
  exit 1
}

status_output="$("$STATUS_SCRIPT")"
evidence_output="$("$EVIDENCE_SCRIPT")"

status_adapter="$(grep '^REAL_HANDOFF_ADAPTER=' <<<"$status_output" | cut -d= -f2-)"
status_mode="$(grep '^REAL_HANDOFF_MODE=' <<<"$status_output" | cut -d= -f2-)"
status_external_request="$(grep '^EXTERNAL_REQUEST_ALLOWED=' <<<"$status_output" | cut -d= -f2-)"
status_runtime_mutation="$(grep '^RUNTIME_MUTATION_ALLOWED=' <<<"$status_output" | cut -d= -f2-)"

evidence_adapter="$(grep '^REAL_HANDOFF_ADAPTER=' <<<"$evidence_output" | cut -d= -f2-)"
evidence_mode="$(grep '^REAL_HANDOFF_MODE=' <<<"$evidence_output" | cut -d= -f2-)"
evidence_external_request="$(grep '^EXTERNAL_REQUEST_ALLOWED=' <<<"$evidence_output" | cut -d= -f2-)"
evidence_runtime_mutation="$(grep '^RUNTIME_MUTATION_ALLOWED=' <<<"$evidence_output" | cut -d= -f2-)"
evidence_live_trading="$(grep '^LIVE_TRADING_ALLOWED=' <<<"$evidence_output" | cut -d= -f2-)"

[[ "$status_adapter" == "present" ]] || fail "status report should expose real handoff adapter"
[[ "$evidence_adapter" == "present" ]] || fail "evidence report should expose real handoff adapter"
[[ "$status_adapter" == "$evidence_adapter" ]] || fail "adapter presence drift between status and evidence reports"

[[ "$status_mode" == "mock_only" ]] || fail "status report should stay mock_only"
[[ "$evidence_mode" == "mock_only" ]] || fail "evidence report should stay mock_only"
[[ "$status_mode" == "$evidence_mode" ]] || fail "mode drift between status and evidence reports"

[[ "$status_external_request" == "no" ]] || fail "status report must keep external requests disabled"
[[ "$evidence_external_request" == "no" ]] || fail "evidence report must keep external requests disabled"
[[ "$status_external_request" == "$evidence_external_request" ]] || fail "external-request flag drift between status and evidence reports"

[[ "$status_runtime_mutation" == "no" ]] || fail "status report must keep runtime mutation disabled"
[[ "$evidence_runtime_mutation" == "no" ]] || fail "evidence report must keep runtime mutation disabled"
[[ "$status_runtime_mutation" == "$evidence_runtime_mutation" ]] || fail "runtime-mutation flag drift between status and evidence reports"

[[ "$evidence_live_trading" == "no" ]] || fail "evidence report must keep live trading disabled"

echo "REAL_HANDOFF_ADAPTER_REPORT_INTEGRATION PASS: review surfaces aligned"
