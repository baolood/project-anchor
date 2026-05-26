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
docs/RULES.md (operational rules SSOT), docs/GO_LIVE_CHECKLIST.md, artifacts/go-live/README.md,
and .github/pull_request_template.md.

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
  # Operational rules SSOT (go-live reporter CI vs local evidence; see scripts/check_go_live_rules.sh).
  "docs/RULES.md"
  # Go-live execution board + CI reporter input (see scripts/go_live_status_report.sh).
  "docs/GO_LIVE_CHECKLIST.md"
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

# First-controlled-send status stack must stay internally consistent while
# the project remains in its current reviewed posture.
if ! "${ROOT}/scripts/check_first_controlled_send_status_integration.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: first-controlled-send status integration check failed" >&2
  exit 1
fi

# Real handoff adapter skeleton must keep its bounded mock-posture contract
# before any future credential handoff implementation is allowed to start.
if ! "${ROOT}/scripts/check_real_handoff_adapter_skeleton.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff adapter skeleton check failed" >&2
  exit 1
fi

# Real handoff review surfaces must stay aligned so reviewers do not see
# conflicting evidence between the standalone adapter report and the status
# stack.
if ! "${ROOT}/scripts/check_real_handoff_adapter_report_integration.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff adapter report integration check failed" >&2
  exit 1
fi

# Drift posture must remain visibly blocked before any real credential
# handoff work can move past review-safe fixtures.
if ! "${ROOT}/scripts/check_real_handoff_adapter_runtime_fixture_drift.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff adapter runtime fixture drift check failed" >&2
  exit 1
fi

# Real handoff task-input line must stay bounded as one closeout gate:
# review-only contract + review-surface alignment.
if ! "${ROOT}/scripts/check_real_handoff_task_input_line.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff task input line check failed" >&2
  exit 1
fi

# Real credential placeholder line must stay bounded as one closeout gate:
# placeholder boundary matrix + placeholder review-surface alignment.
if ! bash "${ROOT}/scripts/check_real_credential_placeholder_line.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real credential placeholder line check failed" >&2
  exit 1
fi

# Real handoff opening prereq line must stay bounded as one closeout gate:
# opening-prereq contract matrix + opening-prereq review-surface alignment.
if ! bash "${ROOT}/scripts/check_real_handoff_opening_prereq_line.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff opening prereq line check failed" >&2
  exit 1
fi

# Real handoff opening bundle line must stay bounded as one closeout gate:
# opening-bundle contract matrix + opening-bundle review-surface alignment.
if ! bash "${ROOT}/scripts/check_real_handoff_opening_bundle_line.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff opening bundle line check failed" >&2
  exit 1
fi

# Real handoff opening decision packet contract must stay review-safe before
# any future opening decision packet can move closer to credential injection or
# runtime changes.
if ! "${ROOT}/scripts/check_real_handoff_opening_decision_packet_contract.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff opening decision packet contract check failed" >&2
  exit 1
fi

echo "LOCAL_BOX_BASELINE_CHECK PASS: required local_box baseline objects present"
exit 0
