#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${OUT:-/tmp/anchor_e2e_checklist_extreme_mode_e2e_last.out}"
BASE="${BASE:-http://127.0.0.1:8000}"

say(){ echo "[$(date +%H:%M:%S)] $*"; }

# 默认不跑：必须显式 EXTREME_MODE_E2E=1
if [[ "${EXTREME_MODE_E2E:-0}" != "1" ]]; then
  {
    echo "MODULE=extreme_mode_e2e"
    echo "SKIPPED=YES"
    echo "PASS_OR_FAIL=PASS"
    echo "FAIL_REASON="
    echo "OUT=$OUT"
  } | tee "$OUT" >/dev/null
  exit 0
fi

say "RUN extreme_mode_run.sh (evidence will be under /tmp/anchor_extreme_*)"
cd "$ROOT" && BASE="$BASE" CAPITAL_USD="${CAPITAL_USD:-1000}" ./scripts/extreme_mode_run.sh

DONE=$(grep -oE 'DONE=[0-9]+' /tmp/anchor_extreme_outcome_last.out 2>/dev/null | tail -n 1 | cut -d= -f2 || echo "")
FAILED=$(grep -oE 'FAILED=[0-9]+' /tmp/anchor_extreme_outcome_last.out 2>/dev/null | tail -n 1 | cut -d= -f2 || echo "")

# 断言：必须有 FAILED（触发硬限制），且 daily smoke 必须 DONE
SMOKE_STATUS=$(grep -oE 'status=[^ ]+' /tmp/anchor_extreme_daily_smoke_last.out 2>/dev/null | tail -n 1 | cut -d= -f2 || echo "")
FAIL_REASON=""

if [[ -z "${FAILED:-}" || "${FAILED}" -lt 1 ]]; then
  FAIL_REASON="NO_FAILED_IN_EXTREME"
fi
if [[ "${SMOKE_STATUS:-}" != "DONE" ]]; then
  FAIL_REASON="${FAIL_REASON:+$FAIL_REASON,}DAILY_SMOKE_NOT_DONE"
fi

PASS_OR_FAIL="PASS"
if [[ -n "$FAIL_REASON" ]]; then PASS_OR_FAIL="FAIL"; fi

{
  echo "MODULE=extreme_mode_e2e"
  echo "SKIPPED=NO"
  echo "EXTREME_DONE=${DONE:-}"
  echo "EXTREME_FAILED=${FAILED:-}"
  echo "EXTREME_OUT=/tmp/anchor_extreme_outcome_last.out"
  echo "EXTREME_RISK_STATE=/tmp/anchor_extreme_risk_state_last.json"
  echo "EXTREME_DAILY_SMOKE=/tmp/anchor_extreme_daily_smoke_last.out"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
} | tee "$OUT" >/dev/null

if [[ "$PASS_OR_FAIL" != "PASS" ]]; then exit 1; fi
