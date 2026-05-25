#!/usr/bin/env bash
# Validates one filled first-controlled-send artifact against the repo's
# actual-artifact storage/naming/clarity guardrails.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_first_controlled_send_actual_artifact.sh <artifact-path>

Validates one candidate first-controlled-send filled artifact.

Checks:
- file is under docs/reviews/real_testnet/
- filename matches FIRST_CONTROLLED_SEND_<date>_<order-id-or-not-sent>.md
- required identity fields are present
- example / placeholder wording is absent
- obvious secret-bearing markers are absent

This script validates artifact form only.
It does not authorize a real controlled send or live trading.
EOF
}

if (($# != 1)); then
  usage >&2
  exit 2
fi

if [[ "$1" == "-h" || "$1" == "--help" ]]; then
  usage
  exit 0
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "FIRST_CONTROLLED_SEND_ARTIFACT_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

artifact_input="$1"
case "$artifact_input" in
  /*) ARTIFACT="$artifact_input" ;;
  *) ARTIFACT="${ROOT}/${artifact_input}" ;;
esac

if [[ ! -f "$ARTIFACT" ]]; then
  echo "FIRST_CONTROLLED_SEND_ARTIFACT_CHECK FAIL: missing file: $ARTIFACT" >&2
  exit 1
fi

expected_dir="${ROOT}/docs/reviews/real_testnet"
case "$ARTIFACT" in
  "${expected_dir}/"*) ;;
  *)
    echo "FIRST_CONTROLLED_SEND_ARTIFACT_CHECK FAIL: file must live under docs/reviews/real_testnet/" >&2
    exit 1
    ;;
esac

base="$(basename "$ARTIFACT")"
if [[ ! "$base" =~ ^FIRST_CONTROLLED_SEND_([0-9]{4}-[0-9]{2}-[0-9]{2})_(order-[A-Za-z0-9-]+|not-sent-[A-Za-z0-9-]+)\.md$ ]]; then
  echo "FIRST_CONTROLLED_SEND_ARTIFACT_CHECK FAIL: bad filename: $base" >&2
  exit 1
fi

review_date="${BASH_REMATCH[1]}"
identity_suffix="${BASH_REMATCH[2]}"

content="$(cat "$ARTIFACT")"

fail() {
  echo "FIRST_CONTROLLED_SEND_ARTIFACT_CHECK FAIL: $1" >&2
  exit 1
}

line_has_value() {
  local key="$1"
  grep -Eq "^${key}:[[:space:]]*[^[:space:]].*$" "$ARTIFACT"
}

line_matches() {
  local regex="$1"
  grep -Eq "$regex" "$ARTIFACT"
}

line_has_value "review_date" || fail "missing review_date"
line_matches "^review_date:[[:space:]]*${review_date}$" || fail "review_date does not match filename date"
line_has_value "reviewer" || fail "missing reviewer"
line_has_value "operator" || fail "missing operator"
line_has_value "host_label" || fail "missing host_label"
line_has_value "configured_origin" || fail "missing configured_origin"

if ! line_has_value "runtime_posture" && ! line_has_value "executor_mode"; then
  fail "missing runtime posture marker (runtime_posture or executor_mode)"
fi

if [[ "$identity_suffix" == order-* ]]; then
  line_matches "^command_id:[[:space:]]*${identity_suffix}$" || fail "command_id does not match filename identity"
else
  if ! grep -Eq "not-sent" "$ARTIFACT"; then
    fail "not-sent artifact must explicitly say not-sent"
  fi
fi

if ! line_has_value "final_result_label" && ! line_has_value "result_label"; then
  fail "missing final result label"
fi

if ! line_has_value "idempotency_key"; then
  fail "missing idempotency_key"
fi

if grep -Eqi 'example-(pass|fail|blocked)|synthetic example|example only|placeholder|<[^>]+>' "$ARTIFACT"; then
  fail "file still contains synthetic/example/placeholder wording"
fi

if grep -Eqi 'api key|api secret|raw auth header|request signature|plaintext credential|secret:' "$ARTIFACT"; then
  fail "file appears to contain secret-bearing material"
fi

echo "FIRST_CONTROLLED_SEND_ARTIFACT_CHECK PASS: ${base}"
