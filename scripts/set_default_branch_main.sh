#!/usr/bin/env bash
# 使用 GitHub API 将默认分支设为 main
# 1) 打开 https://github.com/settings/tokens/new 创建 token（勾选 repo）
# 2) export TOKEN=ghp_xxxx
# 3) ./scripts/set_default_branch_main.sh
set -e

TOKEN="${TOKEN:?请设置 TOKEN，例如: export TOKEN=ghp_xxxx}"
OWNER="baolood"
REPO="project-anchor"

echo "Setting default_branch to main..."
curl -sS -X PATCH \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO" \
  -d '{"default_branch":"main"}' | python3 -c "
import json,sys
d=json.load(sys.stdin)
if 'default_branch' in d:
  print('OK: default_branch=', d['default_branch'])
else:
  print('Response:', d, file=sys.stderr)
  sys.exit(1)
"

echo ""
echo "Terminal cleanup..."
cd "$(dirname "$0")/.."
git remote set-head origin -a
git remote show origin | head -10
git push origin --delete feature/ops-console-minimal
git branch -r
echo ""
echo "Done."
