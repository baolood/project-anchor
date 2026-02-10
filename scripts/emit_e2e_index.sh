#!/usr/bin/env bash
set -euo pipefail

INDEX_OUT="${INDEX_OUT:-/tmp/anchor_e2e_index_last.out}"
VERIFY_ALL_OUT="${VERIFY_ALL_OUT:-/tmp/anchor_e2e_verify_all_release.out}"
RELEASE_OUT="${RELEASE_OUT:-/tmp/anchor_e2e_release_up_and_verify_last.out}"

# Index of all e2e output paths (for paste-ready navigation)
{
  echo "=============================="
  echo "MODULE=anchor_e2e_index"
  echo "TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "RELEASE_OUT=${RELEASE_OUT}"
  echo "VERIFY_ALL_OUT=${VERIFY_ALL_OUT}"
  echo "CHECKLIST_RETRY_OUT=${CHECKLIST_RETRY_OUT:-/tmp/anchor_e2e_checklist_retry_e2e_last.out}"
  echo "CHECKLIST_EVENTS_OUT=${CHECKLIST_EVENTS_OUT:-/tmp/anchor_e2e_checklist_events_e2e_last.out}"
  echo "CHECKLIST_QUOTE_OUT=${CHECKLIST_QUOTE_OUT:-/tmp/anchor_e2e_checklist_quote_e2e_last.out}"
  echo "CHECKLIST_LIST_RETRY_UI_OUT=${CHECKLIST_LIST_RETRY_UI_OUT:-/tmp/anchor_e2e_checklist_list_retry_ui_e2e_last.out}"
  echo "CHECKLIST_CREATE_FORM_UI_OUT=${CHECKLIST_CREATE_FORM_UI_OUT:-/tmp/anchor_e2e_checklist_create_form_ui_e2e_last.out}"
  echo "CHECKLIST_CREATE_NAV_EVENTS_OUT=${CHECKLIST_CREATE_NAV_EVENTS_OUT:-/tmp/anchor_e2e_checklist_create_navigate_events_e2e_last.out}"
  echo "CHECKLIST_DETAIL_EXPLAINER_OUT=${CHECKLIST_DETAIL_EXPLAINER_OUT:-/tmp/anchor_e2e_checklist_detail_explainer_e2e_last.out}"
  echo "CHECKLIST_POLICY_BLOCK_EXPLAINER_OUT=${CHECKLIST_POLICY_BLOCK_EXPLAINER_OUT:-/tmp/anchor_e2e_checklist_policy_block_explainer_e2e_last.out}"
  echo "CHECKLIST_CREATE_PAYLOAD_SCHEMA_UI_OUT=${CHECKLIST_CREATE_PAYLOAD_SCHEMA_UI_OUT:-/tmp/anchor_e2e_checklist_create_payload_schema_ui_e2e_last.out}"
  echo "=============================="
} | tee "$INDEX_OUT"
