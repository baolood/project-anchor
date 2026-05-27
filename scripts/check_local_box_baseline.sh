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

# Real handoff opening decision packet line must stay bounded as one closeout gate:
# opening-decision-packet contract matrix + opening-decision-packet review-surface alignment.
if ! bash "${ROOT}/scripts/check_real_handoff_opening_decision_packet_line.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff opening decision packet line check failed" >&2
  exit 1
fi

# Real handoff opening signoff packet contract must stay review-safe before any
# future opening signoff packet can move closer to credential injection or
# runtime changes.
if ! "${ROOT}/scripts/check_real_handoff_opening_signoff_packet_contract.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff opening signoff packet contract check failed" >&2
  exit 1
fi

# Real handoff opening task contract must stay review-safe before any future
# opening task can move closer to credential injection, runtime changes, or
# external requests.
if ! "${ROOT}/scripts/check_real_handoff_opening_task_contract.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff opening task contract check failed" >&2
  exit 1
fi

# Real handoff execution request envelope contract must stay review-safe before
# any future executor-facing request can move closer to credential injection,
# runtime changes, or external requests.
if ! "${ROOT}/scripts/check_real_handoff_execution_request_envelope_contract.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff execution request envelope contract check failed" >&2
  exit 1
fi

# Real handoff execution request approval gate must stay review-safe before any
# future executor-facing request can move closer to external requests.
if ! "${ROOT}/scripts/check_real_handoff_execution_request_approval_gate_contract.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff execution request approval gate contract check failed" >&2
  exit 1
fi

# Real handoff executor activation preflight contract must stay review-safe
# before any future executor activation can move closer to external requests.
if ! "${ROOT}/scripts/check_real_handoff_executor_activation_preflight_contract.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff executor activation preflight contract check failed" >&2
  exit 1
fi

# Real handoff executor activation intent contract must stay review-safe before
# any future executor activation can move closer to external requests.
if ! "${ROOT}/scripts/check_real_handoff_executor_activation_intent_contract.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff executor activation intent contract check failed" >&2
  exit 1
fi

# Real handoff executor activation window contract must stay review-safe before
# any future executor activation can move closer to external requests.
if ! "${ROOT}/scripts/check_real_handoff_executor_activation_window_contract.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff executor activation window contract check failed" >&2
  exit 1
fi

# Real handoff executor activation launch gate must stay fail-closed as a
# fixture matrix before any future executor activation can move closer to
# external requests.
if ! "${ROOT}/scripts/check_real_handoff_executor_activation_launch_gate_contract.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff executor activation launch gate contract check failed" >&2
  exit 1
fi

# Real handoff executor launch packet contract must stay review-safe as a
# fixture matrix before any future executor launch can move closer to external
# requests.
if ! "${ROOT}/scripts/check_real_handoff_executor_launch_packet_contract.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff executor launch packet contract check failed" >&2
  exit 1
fi

# Real handoff executor launch intent contract must stay review-safe before any
# future executor launch can move closer to external requests.
if ! "${ROOT}/scripts/check_real_handoff_executor_launch_intent_contract.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff executor launch intent contract check failed" >&2
  exit 1
fi

# Real handoff executor launch window contract must stay review-safe before any
# future executor launch can move closer to external requests.
if ! "${ROOT}/scripts/check_real_handoff_executor_launch_window_contract.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff executor launch window contract check failed" >&2
  exit 1
fi

# Real handoff executor launch approval gate must stay fail-closed before any
# future executor launch can move closer to external requests.
if ! "${ROOT}/scripts/check_real_handoff_executor_launch_approval_gate_contract.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff executor launch approval gate contract check failed" >&2
  exit 1
fi

# Real handoff executor launch rollback packet contract must stay review-safe
# before any future executor launch can move closer to external requests.
if ! "${ROOT}/scripts/check_real_handoff_executor_launch_rollback_packet_contract.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff executor launch rollback packet contract check failed" >&2
  exit 1
fi

# Real handoff executor final dispatch preflight contract must stay fail-closed
# before any future executor dispatch can move closer to external requests.
if ! "${ROOT}/scripts/check_real_handoff_executor_final_dispatch_preflight_contract.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff executor final dispatch preflight contract check failed" >&2
  exit 1
fi

# Real handoff executor dry-run dispatch boundary must stay dry-run only before
# any future executor dispatch can move closer to external requests.
if ! "${ROOT}/scripts/check_real_handoff_executor_dry_run_dispatch_boundary.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff executor dry-run dispatch boundary check failed" >&2
  exit 1
fi

# Real handoff dry-run dispatch audit envelope must stay auditable before any
# future executor dispatch can move closer to external requests.
if ! "${ROOT}/scripts/check_real_handoff_dry_run_dispatch_audit_envelope.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff dry-run dispatch audit envelope check failed" >&2
  exit 1
fi

# Real handoff testnet credential runtime presence must stay bounded before any
# future operator approval can move closer to credential-backed dispatch.
if ! "${ROOT}/scripts/check_real_handoff_testnet_credential_runtime_presence_boundary.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff testnet credential runtime presence boundary check failed" >&2
  exit 1
fi

# Real handoff testnet external request dry approval must stay request-free
# before any future explicit send approval can be considered.
if ! "${ROOT}/scripts/check_real_handoff_testnet_external_request_dry_approval_boundary.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff testnet external request dry approval boundary check failed" >&2
  exit 1
fi

# Real handoff explicit send approval packet must stay request-free before any
# future runtime send approval can be considered.
if ! "${ROOT}/scripts/check_real_handoff_explicit_send_approval_packet_boundary.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff explicit send approval packet boundary check failed" >&2
  exit 1
fi

# Real handoff explicit runtime send line must stay hard-blocked as one
# closeout gate before any future real external request can be considered.
if ! "${ROOT}/scripts/check_real_handoff_explicit_runtime_send_line.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real handoff explicit runtime send line check failed" >&2
  exit 1
fi

# First-real-request gate bundle closeout must stay coherent as a docs-only
# decision stack before any future actual controlled send can be considered.
if ! "${ROOT}/scripts/check_real_testnet_first_real_request_gate_bundle_closeout.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: first real request gate bundle closeout check failed" >&2
  exit 1
fi

# First-controlled-send readiness review must stay bounded as a review-only
# pre-scheduling surface before any future scheduling can be considered.
if ! "${ROOT}/scripts/check_real_testnet_first_controlled_send_readiness_review.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: first controlled send readiness review check failed" >&2
  exit 1
fi

# First-controlled-send scheduling decision record must stay bounded as a
# docs-only schedule-or-block surface before any future scheduling can be considered.
if ! "${ROOT}/scripts/check_real_testnet_first_controlled_send_scheduling_decision_record.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: first controlled send scheduling decision record check failed" >&2
  exit 1
fi

# First-controlled-send decision bundle must stay bounded as a docs-only
# pre-scheduling decision stack before any future scheduling can be considered.
if ! "${ROOT}/scripts/check_real_testnet_first_controlled_send_decision_bundle.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: first controlled send decision bundle check failed" >&2
  exit 1
fi

# First-controlled-send decision bundle closeout must stay coherent as a
# docs-only closeout surface before any future scheduling can be considered.
if ! "${ROOT}/scripts/check_real_testnet_first_controlled_send_decision_bundle_closeout.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: first controlled send decision bundle closeout check failed" >&2
  exit 1
fi

# First-controlled-send schedule packet must stay bounded as a docs-only
# operational evidence packet before any future scheduling can be considered.
if ! "${ROOT}/scripts/check_real_testnet_first_controlled_send_schedule_packet.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: first controlled send schedule packet check failed" >&2
  exit 1
fi

# Real testnet external executor mocked V1 must stay offline, explicitly gated,
# and reviewable before any future real-wire expansion is considered.
if ! "${ROOT}/scripts/check_real_testnet_external_executor_mocked_v1.sh"; then
  echo "LOCAL_BOX_BASELINE_CHECK FAIL: real testnet external executor mocked V1 check failed" >&2
  exit 1
fi

echo "LOCAL_BOX_BASELINE_CHECK PASS: required local_box baseline objects present"
exit 0
