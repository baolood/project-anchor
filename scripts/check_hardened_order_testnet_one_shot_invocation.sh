#!/usr/bin/env bash
# Verifies the hardened one-shot ORDER:testnet invocation script remains
# fail-closed before any future operator-authorized window can execute it.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_hardened_order_testnet_one_shot_invocation.sh

Checks scripts/one_shot_order_testnet_invocation.sh with offline fixtures only.

It verifies:
- before-window exits non-zero before POST
- expired-window exits non-zero before POST
- missing-env exits non-zero before POST
- valid-window-dry exits zero but remains dry-run
- no fixture sends a POST or requires credentials

This script does not authorize real external requests, canary, go-live, or
live trading.
EOF
}

if (($# > 0)); then
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "HARDENED_ORDER_TESTNET_ONE_SHOT_INVOCATION_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

TARGET="${ROOT}/scripts/one_shot_order_testnet_invocation.sh"
TMPDIR_CREATED="$(mktemp -d)"
trap 'rm -rf "${TMPDIR_CREATED}"' EXIT

fail() {
  echo "HARDENED_ORDER_TESTNET_ONE_SHOT_INVOCATION_CHECK FAIL: $1" >&2
  exit 1
}

[[ -f "${TARGET}" ]] || fail "missing target script ${TARGET}"

cat >"${TMPDIR_CREATED}/date" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -eq 6 && "$1" == "-u" && "$2" == "-j" && "$3" == "-f" && "$4" == "%Y-%m-%dT%H:%M:%SZ" && "$6" == "+%s" ]]; then
  python3 - "$5" <<'PY'
import datetime
import sys

value = sys.argv[1]
dt = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
print(int(dt.timestamp()))
PY
  exit 0
fi

exec /bin/date "$@"
EOF
chmod +x "${TMPDIR_CREATED}/date"

run_target() {
  PATH="${TMPDIR_CREATED}:${PATH}" bash "${TARGET}" "$@"
}

run_expect_blocked() {
  local fixture="$1"
  local expected_reason="$2"
  local output
  local status=0

  output="$(run_target --fixture "${fixture}" 2>&1)" || status=$?

  [[ "${status}" -ne 0 ]] || fail "${fixture} unexpectedly exited zero"
  grep -Fq "${expected_reason}" <<<"${output}" || fail "${fixture} did not print ${expected_reason}"
  grep -Fq "WINDOW_TIME_CHECK=BLOCKED" <<<"${output}" || fail "${fixture} did not block window time check"
  grep -Fq "POST_ATTEMPTED=NO" <<<"${output}" || fail "${fixture} attempted POST"
  grep -Fq "POST_EXECUTED=NO" <<<"${output}" || fail "${fixture} executed POST"
}

run_expect_dry_pass() {
  local fixture="$1"
  local output

  output="$(run_target --fixture "${fixture}" 2>&1)" || fail "${fixture} exited non-zero"

  grep -Fq "WINDOW_TIME_CHECK=PASS" <<<"${output}" || fail "${fixture} did not pass time check"
  grep -Fq "GUARDED_POST_BRANCH=DRY_RUN" <<<"${output}" || fail "${fixture} did not stay dry-run"
  grep -Fq "POST_ATTEMPTED=NO" <<<"${output}" || fail "${fixture} attempted POST"
  grep -Fq "POST_EXECUTED=NO" <<<"${output}" || fail "${fixture} executed POST"
  grep -Fq "testnet:ops_manual:BTCUSDT:BUY:4:first-bounded-request:v1" <<<"${output}" \
    || fail "${fixture} lost fixed idempotency key"
}

run_expect_blocked "before-window" "WINDOW_NOT_OPEN_YET"
run_expect_blocked "expired-window" "WINDOW_EXPIRED"
run_expect_blocked "missing-env" "MISSING_REQUIRED_WINDOW_ENV"
run_expect_dry_pass "valid-window-dry"

echo "HARDENED_ORDER_TESTNET_ONE_SHOT_INVOCATION=PASS"
echo "TARGET_SCRIPT=scripts/one_shot_order_testnet_invocation.sh"
echo "WINDOW_NOT_OPEN_YET_EXITS_1=yes"
echo "WINDOW_EXPIRED_EXITS_1=yes"
echo "MISSING_ENV_EXITS_1=yes"
echo "VALID_WINDOW_DRY_RUN_POST_ATTEMPTED=false"
echo "REAL_EXTERNAL_REQUEST_SENT=false"
echo "CANARY_EXECUTED=false"
echo "GO_LIVE=NO-GO"
echo "LIVE_TRADING=NO-GO"
echo "HARDENED_ORDER_TESTNET_ONE_SHOT_INVOCATION_CHECK PASS: fail-closed fixtures verified"
