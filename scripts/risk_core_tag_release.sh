#!/usr/bin/env bash
set -euo pipefail

TAG="${TAG:-risk-core-v2}"

echo "HEAD=$(git rev-parse HEAD)"
echo "TAG=$TAG"

# 1) 确保 release 先全绿（默认 EXTREME SKIPPED）
./scripts/release_up_and_verify.sh | tee /tmp/anchor_e2e_release_before_tag_last.out

# 2) 若 tag 已存在，先删本地 + 远端（可重复运行）
if git rev-parse "$TAG" >/dev/null 2>&1; then
  git tag -d "$TAG" >/dev/null 2>&1 || true
fi
git push origin ":refs/tags/$TAG" >/dev/null 2>&1 || true

# 3) 创建并推送 tag
git tag -a "$TAG" -m "Risk Core v2: daily default env + release green + extreme optional"
git push origin "$TAG"

# 4) 证据
{
  echo "TAG=$TAG"
  echo "TAG_POINTS_TO=$(git rev-list -n 1 "$TAG")"
  echo "HEAD=$(git rev-parse HEAD)"
} | tee /tmp/anchor_risk_core_tag_release_last.out

echo "DONE."
echo "/tmp/anchor_e2e_release_before_tag_last.out"
echo "/tmp/anchor_risk_core_tag_release_last.out"
