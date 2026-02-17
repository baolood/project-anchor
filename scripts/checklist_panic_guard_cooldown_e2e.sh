#!/usr/bin/env bash
# Panic Guard Cooldown E2E: trigger within cooldown returns 409.
# Step0: POST trigger -> 200
# Step1: Immediately POST trigger again -> 409 + contains "cooldown"
# Step2: POST reset -> 200
set -euo pipefail

OUT="${OUT:-/tmp/anchor_e2e_checklist_panic_guard_cooldown_e2e_last.out}"
CONSOLE_PRECHECK="${CONSOLE_PRECHECK:-http://127.0.0.1:3000}"

PASS_OR_FAIL=FAIL
FAIL_REASON=""

echo "=============================="
echo "MODULE=panic_guard_cooldown_e2e"
echo "Step0: POST /api/proxy/ops/panic_guard/trigger 200"
echo "=============================="
trigger_resp="$(curl -sS --noproxy '*' -X POST -H "Content-Type: application/json" -w "\n%{http_code}" "$CONSOLE_PRECHECK/api/proxy/ops/panic_guard/trigger")"
trigger_code="$(echo "$trigger_resp" | tail -1)"
trigger_body="$(echo "$trigger_resp" | sed '$d')"
if [ "$trigger_code" != "200" ]; then
  echo "FAIL_REASON=first_trigger_not_200"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  exit 1
fi
echo "OK: first trigger 200"

echo "=============================="
echo "Step1: Immediately POST trigger again -> 409 + cooldown"
echo "=============================="
trigger2_resp="$(curl -sS --noproxy '*' -X POST -H "Content-Type: application/json" -w "\n%{http_code}" "$CONSOLE_PRECHECK/api/proxy/ops/panic_guard/trigger")"
trigger2_code="$(echo "$trigger2_resp" | tail -1)"
trigger2_body="$(echo "$trigger2_resp" | sed '$d')"
if [ "$trigger2_code" != "409" ]; then
  echo "FAIL_REASON=second_trigger_not_409"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  curl -sS --noproxy '*' -X POST -H "Content-Type: application/json" "$CONSOLE_PRECHECK/api/proxy/ops/panic_guard/reset" >/dev/null || true
  exit 1
fi
if ! echo "$trigger2_body" | grep -qi "cooldown"; then
  echo "FAIL_REASON=409_response_missing_cooldown"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  curl -sS --noproxy '*' -X POST -H "Content-Type: application/json" "$CONSOLE_PRECHECK/api/proxy/ops/panic_guard/reset" >/dev/null || true
  exit 1
fi
echo "OK: second trigger 409 with cooldown"

echo "=============================="
echo "Step2: POST /api/proxy/ops/panic_guard/reset 200"
echo "=============================="
reset_resp="$(curl -sS --noproxy '*' -X POST -H "Content-Type: application/json" -w "\n%{http_code}" "$CONSOLE_PRECHECK/api/proxy/ops/panic_guard/reset")"
reset_code="$(echo "$reset_resp" | tail -1)"
if [ "$reset_code" != "200" ]; then
  echo "FAIL_REASON=reset_not_200"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  exit 1
fi
echo "OK: reset 200"

PASS_OR_FAIL=PASS
FAIL_REASON=""
echo "=============================="
echo "MODULE=panic_guard_cooldown_e2e"
echo "PASS_OR_FAIL=$PASS_OR_FAIL"
echo "FAIL_REASON=$FAIL_REASON"
