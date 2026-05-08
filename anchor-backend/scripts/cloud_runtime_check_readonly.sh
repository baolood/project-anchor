#!/usr/bin/env bash
set -u

# Read-only runtime audit for Project Anchor on cloud host.
# This script does not mutate system state.

ROOT_DIR="${ROOT_DIR:-/root/project-anchor/anchor-backend}"
BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-http://127.0.0.1:8000/health}"
OPS_STATE_URL="${OPS_STATE_URL:-http://127.0.0.1:8000/ops/state}"
DOMAIN_COMMAND_ID="${DOMAIN_COMMAND_ID:-}"
DOMAIN_COMMAND_STATUS_QUERY="${DOMAIN_COMMAND_STATUS_QUERY:-}"

CHECK_PASS=0
CHECK_FAIL=0
SYSTEM_RESULT="SYSTEM_NORMAL"

PASS_MARK="PASS"
FAIL_MARK="FAIL"

WORKDIR_OK=1
COMPOSE_PS_OUTPUT=""
HEALTH_RAW=""
OPS_STATE_RAW=""
WORKER_LOGS_RAW=""
DOMAIN_STATUS_RAW=""

mark_pass() {
  CHECK_PASS=$((CHECK_PASS + 1))
}

mark_fail() {
  CHECK_FAIL=$((CHECK_FAIL + 1))
  SYSTEM_RESULT="SYSTEM_NOT_NORMAL"
}

print_check() {
  local name="$1"
  local observed="$2"
  local status="$3"
  echo "${name}"
  echo "Observed: ${observed}"
  echo "Result: ${status}"
  echo
}

if [ ! -d "${ROOT_DIR}" ]; then
  WORKDIR_OK=0
fi

if [ "${WORKDIR_OK}" -eq 1 ]; then
  cd "${ROOT_DIR}" || WORKDIR_OK=0
fi

if [ "${WORKDIR_OK}" -eq 0 ]; then
  print_check "1. workdir" "missing ROOT_DIR=${ROOT_DIR}" "${FAIL_MARK}"
  mark_fail
else
  print_check "1. workdir" "found ROOT_DIR=${ROOT_DIR}" "${PASS_MARK}"
  mark_pass
fi

if [ "${WORKDIR_OK}" -eq 1 ] && COMPOSE_PS_OUTPUT="$(docker compose ps 2>&1)"; then
  compose_status="${PASS_MARK}"
  compose_observed="backend/postgres/redis/worker services found and Up"
  for svc in backend postgres redis worker; do
    if ! printf '%s\n' "${COMPOSE_PS_OUTPUT}" | rg -q "${svc}.*Up"; then
      compose_status="${FAIL_MARK}"
      compose_observed="service ${svc} not Up in docker compose ps"
      break
    fi
  done
  print_check "2. docker compose services" "${compose_observed}" "${compose_status}"
  if [ "${compose_status}" = "${PASS_MARK}" ]; then mark_pass; else mark_fail; fi
else
  print_check "2. docker compose services" "docker compose ps failed" "${FAIL_MARK}"
  mark_fail
fi

ports_status="${FAIL_MARK}"
ports_observed="missing localhost-only bindings"
if [ -n "${COMPOSE_PS_OUTPUT}" ]; then
  need1='127\.0\.0\.1:8000->8000/tcp'
  need2='127\.0\.0\.1:5432->5432/tcp'
  need3='127\.0\.0\.1:6379->6379/tcp'
  bad1='0\.0\.0\.0:8000->8000/tcp'
  bad2='0\.0\.0\.0:5432->5432/tcp'
  bad3='0\.0\.0\.0:6379->6379/tcp'
  bad4='\[::\]:8000->8000/tcp'
  bad5='\[::\]:5432->5432/tcp'
  bad6='\[::\]:6379->6379/tcp'
  if printf '%s\n' "${COMPOSE_PS_OUTPUT}" | rg -q "${need1}" \
    && printf '%s\n' "${COMPOSE_PS_OUTPUT}" | rg -q "${need2}" \
    && printf '%s\n' "${COMPOSE_PS_OUTPUT}" | rg -q "${need3}" \
    && ! printf '%s\n' "${COMPOSE_PS_OUTPUT}" | rg -q "${bad1}|${bad2}|${bad3}|${bad4}|${bad5}|${bad6}"; then
    ports_status="${PASS_MARK}"
    ports_observed="backend/postgres/redis ports bound to 127.0.0.1 only"
  else
    ports_observed="expected localhost bindings not fully met or public bindings still present"
  fi
fi
print_check "3. runtime ports" "${ports_observed}" "${ports_status}"
if [ "${ports_status}" = "${PASS_MARK}" ]; then mark_pass; else mark_fail; fi

health_status="${FAIL_MARK}"
health_observed="backend /health unreachable"
if HEALTH_RAW="$(curl -fsS "${BACKEND_HEALTH_URL}" 2>&1)"; then
  if printf '%s' "${HEALTH_RAW}" | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if (d.get("ok") is True or d.get("status")=="ok") else 1)'; then
    health_status="${PASS_MARK}"
    health_observed="${HEALTH_RAW}"
  else
    health_observed="JSON returned but missing ok=true/status=ok: ${HEALTH_RAW}"
  fi
fi
print_check "4. backend health" "${health_observed}" "${health_status}"
if [ "${health_status}" = "${PASS_MARK}" ]; then mark_pass; else mark_fail; fi

ops_status="${FAIL_MARK}"
ops_observed="/ops/state unreachable or invalid"
if OPS_STATE_RAW="$(curl -fsS "${OPS_STATE_URL}" 2>&1)"; then
  if printf '%s' "${OPS_STATE_RAW}" | python3 -c '
import json,sys
obj=json.load(sys.stdin)
required=["kill_switch","worker_heartbeat","worker_panic"]
ok=all(k in obj for k in required)
sys.exit(0 if ok else 1)
'; then
    ops_status="${PASS_MARK}"
    ops_observed="JSON reachable with kill_switch/worker_heartbeat/worker_panic"
  else
    ops_observed="JSON reachable but required keys missing"
  fi
fi
print_check "5. /ops/state" "${ops_observed}" "${ops_status}"
if [ "${ops_status}" = "${PASS_MARK}" ]; then mark_pass; else mark_fail; fi

logs_status="${PASS_MARK}"
logs_observed="worker logs do not show all-ERROR in last 50 lines"
if WORKER_LOGS_RAW="$(docker compose logs --tail=50 worker 2>&1)"; then
  non_empty_count="$(printf '%s\n' "${WORKER_LOGS_RAW}" | python3 -c 'import sys; print(sum(1 for l in sys.stdin if l.strip()))')"
  error_count="$(printf '%s\n' "${WORKER_LOGS_RAW}" | rg -i -c 'error|exception|traceback' || true)"
  if [ "${non_empty_count}" -gt 0 ] && [ "${error_count}" -ge "${non_empty_count}" ]; then
    logs_status="${FAIL_MARK}"
    logs_observed="last 50 worker log lines are continuous error-like lines"
  fi
else
  logs_status="${FAIL_MARK}"
  logs_observed="failed to read worker logs"
fi
print_check "6. worker logs" "${logs_observed}" "${logs_status}"
if [ "${logs_status}" = "${PASS_MARK}" ]; then mark_pass; else mark_fail; fi

domain_status="${PASS_MARK}"
domain_observed="SKIPPED (set DOMAIN_COMMAND_ID and DOMAIN_COMMAND_STATUS_QUERY to enforce)"
if [ -n "${DOMAIN_COMMAND_ID}" ] && [ -n "${DOMAIN_COMMAND_STATUS_QUERY}" ]; then
  if DOMAIN_STATUS_RAW="$(psql ${DOMAIN_COMMAND_STATUS_QUERY} 2>&1)"; then
    if printf '%s\n' "${DOMAIN_STATUS_RAW}" | rg -q "${DOMAIN_COMMAND_ID}.*(DONE|FAILED)"; then
      domain_observed="domain command transitioned to DONE/FAILED"
      domain_status="${PASS_MARK}"
    else
      domain_observed="domain command not DONE/FAILED (or query mismatch)"
      domain_status="${FAIL_MARK}"
    fi
  else
    domain_observed="domain command query failed"
    domain_status="${FAIL_MARK}"
  fi
fi
print_check "7. domain command mainline" "${domain_observed}" "${domain_status}"
if [ "${domain_status}" = "${PASS_MARK}" ]; then mark_pass; else mark_fail; fi

echo "Final: ${SYSTEM_RESULT}"
echo "PASS checks: ${CHECK_PASS}"
echo "FAIL checks: ${CHECK_FAIL}"

if [ "${SYSTEM_RESULT}" = "SYSTEM_NORMAL" ]; then
  exit 0
fi

exit 1
