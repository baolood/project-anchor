#!/usr/bin/env bash
# Baseline presence check for local_box. Spec: docs/LOCAL_BOX_BASELINE_CHECK_SCRIPT_SPEC_V1.md
# CI: local-box-baseline job "check"; see README.md (section "CI").
# Run from repository root: ./scripts/check_local_box_baseline.sh
set -euo pipefail

if (($# > 0)); then
  case "$1" in
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/check_local_box_baseline.sh

Verifies required parent-repo paths exist, then runs scripts/check_checklist_curl_guardrails.sh.

Required paths include (among others) core local_box trees, requirements pins,
artifacts/go-live/README.md, and .github/pull_request_template.md.

See README.md (section "CI"). Spec: docs/LOCAL_BOX_BASELINE_CHECK_SCRIPT_SPEC_V1.md
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Run: ./scripts/check_local_box_baseline.sh --help" >&2
      exit 2
      ;;
  esac
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

REQUIRED_PATHS=(
  "local_box"
  "local_box/runner.py"
  "local_box/self_check/checks.py"
  "requirements.txt"
  "requirements.in"
  "shared/schemas.py"
  "risk_engine/client.py"
  "local_box/gate/ticket_signature.py"
  # Tracked onboarding for go-live daily snapshots (see docs/GO_LIVE_CHECKLIST.md §7).
  "artifacts/go-live/README.md"
  # GitHub PR body stub (see PR_DESCRIPTION.md and CONTRIBUTING.md).
  ".github/pull_request_template.md"
)

missing=()
for rel in "${REQUIRED_PATHS[@]}"; do
  if [[ ! -e "${ROOT}/${rel}" ]]; then
    missing+=("$rel")
  fi
done

if ((${#missing[@]} > 0)); then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: STOP local_box baseline not ready (missing: ${missing[*]})" >&2
  exit 1
fi

# Script guardrail: checklist curl calls must keep timeout protection.
if ! "${ROOT}/scripts/check_checklist_curl_guardrails.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: checklist curl guardrails check failed" >&2
  exit 1
fi

echo "LOCAL_BOX_BASELINE_CHECK PASS: required local_box baseline objects present"
exit 0
