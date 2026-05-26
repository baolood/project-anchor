#!/usr/bin/env bash
# Emits a machine-readable evidence snapshot for the bounded real credential
# placeholder boundary using review-safe fixtures.
set -euo pipefail

OUT_FILE="${OUT_FILE:-}"
FIXTURE="review"

require_value() {
  local opt="$1"
  local val="${2:-}"
  if [[ -z "$val" || "$val" == --* ]]; then
    echo "REAL_CREDENTIAL_PLACEHOLDER_EVIDENCE FAIL: ${opt} requires a value." >&2
    exit 2
  fi
}

while (($# > 0)); do
  case "$1" in
    --fixture)
      require_value "--fixture" "${2:-}"
      FIXTURE="${2:-}"
      shift 2
      ;;
    --out)
      require_value "--out" "${2:-}"
      OUT_FILE="${2:-}"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/real_credential_placeholder_evidence_report.sh [--fixture <review|drift>] [--out <path>]

Fields:
  REAL_CREDENTIAL_PLACEHOLDER_EVIDENCE
  FIXTURE
  REAL_CREDENTIAL_PLACEHOLDER_BOUNDARY
  REAL_CREDENTIAL_PLACEHOLDER_POLICY
  PLACEHOLDER_EXTERNAL_REQUEST_ALLOWED
  PLACEHOLDER_RUNTIME_MUTATION_ALLOWED
  PLACEHOLDER_LIVE_TRADING_ALLOWED
  PLACEHOLDER_EXPECTED_EXECUTOR_MODE
  PLACEHOLDER_EXPECTED_REAL_ENABLE
  PLACEHOLDER_SLOT_COUNT
  PLACEHOLDER_SLOTS

Fixtures:
  review  placeholder-only bounded posture
  drift   intentionally invalid posture for review evidence only

This report does not inject credentials, mutate runtime, issue external
requests, or authorize live trading.
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
  PLACEHOLDER_FIXTURE="$FIXTURE" python3 - <<'PY'
import os
import sys

fixture = os.environ["PLACEHOLDER_FIXTURE"]

payload = {
    "TESTNET_EXCHANGE_API_KEY": "<placeholder>",
    "TESTNET_EXCHANGE_API_SECRET": "<placeholder>",
    "TESTNET_EXCHANGE_KEY_ID": "NOT_COLLECTED",
    "expected_executor_mode": "mock",
    "expected_real_enable": "0",
    "notes": "review-only placeholder contract",
}

if fixture == "review":
    pass
elif fixture == "drift":
    payload["expected_executor_mode"] = "real"
    payload["expected_real_enable"] = "1"
    payload["notes"] = "drift fixture for review evidence only"
else:
    print(
        "REAL_CREDENTIAL_PLACEHOLDER_EVIDENCE FAIL: unsupported fixture: "
        f"{fixture}",
        file=sys.stderr,
    )
    sys.exit(2)

slots = [
    "TESTNET_EXCHANGE_API_KEY",
    "TESTNET_EXCHANGE_API_SECRET",
    "TESTNET_EXCHANGE_KEY_ID",
]

policy = "placeholder_only"
if payload["expected_executor_mode"] != "mock" or payload["expected_real_enable"] != "0":
    policy = "invalid"

print("REAL_CREDENTIAL_PLACEHOLDER_EVIDENCE")
print(f"FIXTURE={fixture}")
print("REAL_CREDENTIAL_PLACEHOLDER_BOUNDARY=present")
print(f"REAL_CREDENTIAL_PLACEHOLDER_POLICY={policy}")
print("PLACEHOLDER_EXTERNAL_REQUEST_ALLOWED=no")
print("PLACEHOLDER_RUNTIME_MUTATION_ALLOWED=no")
print("PLACEHOLDER_LIVE_TRADING_ALLOWED=no")
print(f"PLACEHOLDER_EXPECTED_EXECUTOR_MODE={payload['expected_executor_mode']}")
print(f"PLACEHOLDER_EXPECTED_REAL_ENABLE={payload['expected_real_enable']}")
print(f"PLACEHOLDER_SLOT_COUNT={len(slots)}")
print("PLACEHOLDER_SLOTS=" + ",".join(slots))
PY
)"

echo "$report"

if [[ -n "$OUT_FILE" ]]; then
  if [[ "${OUT_FILE}" == */ ]]; then
    echo "REAL_CREDENTIAL_PLACEHOLDER_EVIDENCE FAIL: --out expects a file path, got directory-like path: ${OUT_FILE}" >&2
    exit 2
  fi
  if [[ -d "${OUT_FILE}" ]]; then
    echo "REAL_CREDENTIAL_PLACEHOLDER_EVIDENCE FAIL: --out expects a file path, got directory: ${OUT_FILE}" >&2
    exit 2
  fi
  mkdir -p "$(dirname "$OUT_FILE")"
  printf '%s\n' "$report" > "$OUT_FILE"
  echo "WROTE_REPORT=$OUT_FILE"
fi
