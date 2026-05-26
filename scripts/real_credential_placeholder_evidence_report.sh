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
      case "$FIXTURE" in
        review|drift_real_posture|real_key_value_present|real_secret_value_present|runtime_mutation_intent_present|external_request_intent_present|live_trading_intent_present) ;;
        *)
          echo "REAL_CREDENTIAL_PLACEHOLDER_EVIDENCE FAIL: unsupported fixture: ${FIXTURE}" >&2
          exit 2
          ;;
      esac
      shift 2
      ;;
    --out)
      require_value "--out" "${2:-}"
      OUT_FILE="${2:-}"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/real_credential_placeholder_evidence_report.sh [--fixture <name>] [--out <path>]

Fields:
  REAL_CREDENTIAL_PLACEHOLDER_EVIDENCE
  FIXTURE
  PLACEHOLDER_VALIDATION
  PLACEHOLDER_BLOCKED_REASONS
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
  review
  drift_real_posture
  real_key_value_present
  real_secret_value_present
  runtime_mutation_intent_present
  external_request_intent_present
  live_trading_intent_present

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
elif fixture == "drift_real_posture":
    payload["expected_executor_mode"] = "real"
    payload["expected_real_enable"] = "1"
    payload["notes"] = "drift fixture for review evidence only"
elif fixture == "real_key_value_present":
    payload["TESTNET_EXCHANGE_API_KEY"] = "real-key"
elif fixture == "real_secret_value_present":
    payload["TESTNET_EXCHANGE_API_SECRET"] = "real-secret"
elif fixture == "runtime_mutation_intent_present":
    payload["notes"] = "export TESTNET_EXECUTOR_REAL_ENABLE=1 before handoff"
elif fixture == "external_request_intent_present":
    payload["notes"] = "send now external request after placeholder review"
elif fixture == "live_trading_intent_present":
    payload["notes"] = "live trading approval follows this placeholder handoff"

slots = [
    "TESTNET_EXCHANGE_API_KEY",
    "TESTNET_EXCHANGE_API_SECRET",
    "TESTNET_EXCHANGE_KEY_ID",
]

policy = "placeholder_only"
blocked_reasons = []
if payload["expected_executor_mode"] != "mock" or payload["expected_real_enable"] != "0":
    policy = "invalid"
    blocked_reasons.append("invalid_expected_executor_posture")
if payload["TESTNET_EXCHANGE_API_KEY"] not in {"<placeholder>", "<redacted>", "NOT_COLLECTED", ""}:
    policy = "invalid"
    blocked_reasons.append("real_key_value_present")
if payload["TESTNET_EXCHANGE_API_SECRET"] not in {"<placeholder>", "<redacted>", "NOT_COLLECTED", ""}:
    policy = "invalid"
    blocked_reasons.append("real_secret_value_present")
notes = payload["notes"].lower()
if "external request" in notes or "send now" in notes:
    policy = "invalid"
    blocked_reasons.append("external_request_intent_present")
if "live trading" in notes or "go live now" in notes:
    policy = "invalid"
    blocked_reasons.append("live_trading_intent_present")
if "export testnet_executor_real_enable=1" in notes:
    policy = "invalid"
    blocked_reasons.append("runtime_mutation_intent_present")

validation = "PASS" if not blocked_reasons else "BLOCKED"

print("REAL_CREDENTIAL_PLACEHOLDER_EVIDENCE")
print(f"FIXTURE={fixture}")
print(f"PLACEHOLDER_VALIDATION={validation}")
print("PLACEHOLDER_BLOCKED_REASONS=" + (",".join(blocked_reasons) or "none"))
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
