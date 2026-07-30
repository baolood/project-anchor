#!/usr/bin/env bash
set -euo pipefail

RUNTIME_USER="project_anchor_runtime"
RUNTIME_GROUP="project_anchor_runtime"
ENV_DIR="/etc/project-anchor"
ENV_FILE="/etc/project-anchor/production.env"

find_free_id() {
  local kind="$1"
  local candidate_id
  for candidate_id in $(seq 499 -1 401); do
    if [ "$kind" = "user" ]; then
      if ! dscl . -list /Users UniqueID | awk '{print $2}' | grep -qx "$candidate_id"; then
        echo "$candidate_id"
        return 0
      fi
    else
      if ! dscl . -list /Groups PrimaryGroupID | awk '{print $2}' | grep -qx "$candidate_id"; then
        echo "$candidate_id"
        return 0
      fi
    fi
  done
  return 1
}

if [ "$(id -u)" != "0" ]; then
  echo "ERROR: run with sudo: sudo bash scripts/provision_production_runtime_identity_macos.sh" >&2
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: missing $ENV_FILE" >&2
  exit 1
fi

if ! dscl . -read "/Groups/$RUNTIME_GROUP" >/dev/null 2>&1; then
  echo "CREATE_RUNTIME_GROUP"
  runtime_gid="$(find_free_id group)"
  dscl . -create "/Groups/$RUNTIME_GROUP"
  dscl . -create "/Groups/$RUNTIME_GROUP" PrimaryGroupID "$runtime_gid"
  dscl . -create "/Groups/$RUNTIME_GROUP" RealName "Project Anchor Runtime"
else
  echo "CREATE_RUNTIME_GROUP_SKIPPED_EXISTS"
fi

runtime_gid="$(dscl . -read "/Groups/$RUNTIME_GROUP" PrimaryGroupID | awk '{print $2}')"
if [ -z "$runtime_gid" ]; then
  echo "ERROR: unable to resolve runtime group id" >&2
  exit 1
fi

if ! dscl . -read "/Users/$RUNTIME_USER" >/dev/null 2>&1; then
  echo "CREATE_RUNTIME_USER"
  runtime_uid="$(find_free_id user)"
  dscl . -create "/Users/$RUNTIME_USER"
  dscl . -create "/Users/$RUNTIME_USER" UserShell /usr/bin/false
  dscl . -create "/Users/$RUNTIME_USER" RealName "Project Anchor Runtime"
  dscl . -create "/Users/$RUNTIME_USER" UniqueID "$runtime_uid"
  dscl . -create "/Users/$RUNTIME_USER" PrimaryGroupID "$runtime_gid"
  dscl . -create "/Users/$RUNTIME_USER" NFSHomeDirectory /var/empty
  dscl . -create "/Users/$RUNTIME_USER" GeneratedUID "$(uuidgen)"
else
  echo "CREATE_RUNTIME_USER_SKIPPED_EXISTS"
fi

id "$RUNTIME_USER" >/dev/null

echo "ALIGN_ENV_FILE"
chown "$RUNTIME_USER:$RUNTIME_GROUP" "$ENV_FILE"
chmod 600 "$ENV_FILE"

echo "ALIGN_ENV_DIR"
chgrp "$RUNTIME_GROUP" "$ENV_DIR"
chmod 710 "$ENV_DIR"

echo "RUNTIME_USER_CHECK"
id "$RUNTIME_USER"

echo "ENV_FILE_CHECK"
stat -f 'OWNER=%Su GROUP=%Sg MODE=%Lp PATH=%N' "$ENV_FILE"

echo "ENV_DIR_CHECK"
stat -f 'OWNER=%Su GROUP=%Sg MODE=%Lp PATH=%N' "$ENV_DIR"

echo "PROVISIONING_RESULT=PASS"
