#!/usr/bin/env bash
# Emits a machine-readable evidence snapshot for the bounded real handoff
# explicit-runtime-send boundary using a hard-blocked review-only fixture.
set -euo pipefail

OUT_FILE="${OUT_FILE:-}"

require_value() {
  local opt="$1"
  local val="${2:-}"
  if [[ -z "$val" || "$val" == --* ]]; then
    echo "REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_EVIDENCE FAIL: ${opt} requires a value." >&2
    exit 2
  fi
}

while (($# > 0)); do
  case "$1" in
    --out)
      require_value "--out" "${2:-}"
      OUT_FILE="${2:-}"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/real_handoff_explicit_runtime_send_evidence_report.sh [--out <path>]

Fields:
  REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_EVIDENCE
  REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_BOUNDARY
  EXPLICIT_RUNTIME_SEND_APPROVAL_PACKET_PRESENT
  EXPLICIT_RUNTIME_SEND_PRESENT
  EXPLICIT_RUNTIME_SEND_CREDENTIAL_RUNTIME_VERIFIED
  EXPLICIT_RUNTIME_SEND_REVIEW_VERDICT_PASS
  EXPLICIT_RUNTIME_SEND_ROLLBACK_PACKET_PRESENT
  EXPLICIT_RUNTIME_SEND_WINDOW_CURRENT
  EXPLICIT_RUNTIME_SEND_EXTERNAL_REQUEST_ALLOWED
  EXPLICIT_RUNTIME_SEND_RUNTIME_MUTATION_ALLOWED
  EXPLICIT_RUNTIME_SEND_LIVE_TRADING_ALLOWED
  EXPLICIT_RUNTIME_SEND_NEXT_GATE
  EXPLICIT_RUNTIME_SEND_APPROVED_EXECUTION_MODE

This report uses a bounded hard-blocked fixture. It does not inject
credentials, mutate runtime, issue external requests, or authorize live
trading.
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Run with --help for usage." >&2
      exit 2
      ;;
  esac
done

report="$(
  python3 - <<'PY'
payload = {
    "runtime_send_boundary_id": "real-handoff-explicit-runtime-send-boundary-20260527-001",
    "runtime_send_boundary": "BLOCKED",
    "approval_packet_present": "yes",
    "explicit_runtime_send_present": "yes",
    "approved_execution_mode": "testnet",
    "credential_runtime_verified": "yes",
    "review_verdict_pass": "yes",
    "rollback_packet_present": "yes",
    "send_window_current": "yes",
    "next_gate": "blocked_before_real_request",
}

print("REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_EVIDENCE")
print(f"REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_BOUNDARY={payload['runtime_send_boundary']}")
print(f"EXPLICIT_RUNTIME_SEND_APPROVAL_PACKET_PRESENT={payload['approval_packet_present']}")
print(f"EXPLICIT_RUNTIME_SEND_PRESENT={payload['explicit_runtime_send_present']}")
print(f"EXPLICIT_RUNTIME_SEND_CREDENTIAL_RUNTIME_VERIFIED={payload['credential_runtime_verified']}")
print(f"EXPLICIT_RUNTIME_SEND_REVIEW_VERDICT_PASS={payload['review_verdict_pass']}")
print(f"EXPLICIT_RUNTIME_SEND_ROLLBACK_PACKET_PRESENT={payload['rollback_packet_present']}")
print(f"EXPLICIT_RUNTIME_SEND_WINDOW_CURRENT={payload['send_window_current']}")
print("EXPLICIT_RUNTIME_SEND_EXTERNAL_REQUEST_ALLOWED=no")
print("EXPLICIT_RUNTIME_SEND_RUNTIME_MUTATION_ALLOWED=no")
print("EXPLICIT_RUNTIME_SEND_LIVE_TRADING_ALLOWED=no")
print(f"EXPLICIT_RUNTIME_SEND_NEXT_GATE={payload['next_gate']}")
print(f"EXPLICIT_RUNTIME_SEND_APPROVED_EXECUTION_MODE={payload['approved_execution_mode']}")
PY
)"

echo "$report"

if [[ -n "$OUT_FILE" ]]; then
  if [[ "${OUT_FILE}" == */ ]]; then
    echo "REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_EVIDENCE FAIL: --out expects a file path, got directory-like path: ${OUT_FILE}" >&2
    exit 2
  fi
  if [[ -d "${OUT_FILE}" ]]; then
    echo "REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_EVIDENCE FAIL: --out expects a file path, got directory: ${OUT_FILE}" >&2
    exit 2
  fi
  mkdir -p "$(dirname "$OUT_FILE")"
  printf '%s\n' "$report" > "$OUT_FILE"
  echo "WROTE_REPORT=$OUT_FILE"
fi
