# Cloud host readonly status command pack V1

**Status:** docs-only readonly command pack - no key use, no deploy, no runtime mutation, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-25

**Scope:** provide one bounded copy/paste command pack that the operator can run on the cloud host to collect real runtime posture before first controlled send preparation.

This document does not authorize a real testnet request.
It does not change runtime state.
It only standardizes how readonly evidence should be collected and pasted back for review.

## 1. Purpose

Use this command pack to collect readonly cloud-host evidence only.

The goal is to answer:

```text
what host is this
what project path is real
what revision appears deployed
what containers appear up
what local backend/ops surfaces respond
```

If those basics are unclear, the correct result is `BLOCKED`.

## 2. Hard boundary

This command pack must remain readonly.

It must not:

- restart backend
- restart worker
- deploy anything
- edit `.env`
- edit config
- mutate docker state
- perform migrations
- trigger a real testnet request
- touch live trading
- call external exchange endpoints

If any command suggestion crosses those lines, stop and do not run it.

## 3. Required operator inputs

Before running the pack, the operator must know or provide:

1. the actual cloud project path
2. the command output pasted back into review verbatim

If the project path is unknown, do not guess and do not improvise.
Result is `BLOCKED`.

## 4. Copy/paste readonly command block

Run this block exactly as readonly evidence collection:

```bash
hostname
pwd
git -C /root/project-anchor log -1 --oneline || true
git -C /opt/project-anchor log -1 --oneline || true
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
curl -sS http://127.0.0.1:8000/health || true
curl -sS http://127.0.0.1:8000/ops/state || true
```

These commands are intentionally limited to:

- host identity
- working directory
- common candidate repo paths
- running containers
- local backend health
- local ops state

No command in this block should mutate runtime state.

## 5. Optional path-specific block

If the actual project path is known and differs from the two common guesses above, replace `PROJECT_PATH` and run:

```bash
PROJECT_PATH="/actual/project/path"
pwd
git -C "$PROJECT_PATH" log -1 --oneline || true
git -C "$PROJECT_PATH" status --short || true
```

Use this section only after the operator knows the real project path.

If `PROJECT_PATH` is unknown, stop instead of guessing.

## 6. STOP conditions

Stop immediately if any of these happens:

1. a command asks for a secret
2. a command would mutate runtime
3. `health` or `ops/state` result is unclear
4. docker services appear missing or contradictory
5. project path is unknown

Also stop if:

- shell access is not the expected cloud host
- output appears to come from the wrong revision or wrong machine
- any command result suggests public exposure changed unexpectedly

## 7. Paste-back template

Paste the results back using this exact structure:

```text
[Cloud Host Readonly Status Pasteback V1]
timestamp:
operator:
expected_host:
actual_project_path:

hostname:
pwd:

git_root_project_anchor:
git_opt_project_anchor:
git_actual_project_path:
git_status_actual_project_path:

docker_ps:
backend_health:
ops_state:

path_unknown: yes/no
health_unclear: yes/no
ops_state_unclear: yes/no
docker_services_missing: yes/no
unexpected_change_observed: yes/no

verdict: PASS / BLOCKED / NO-GO
notes:
```

If a field was not collected, write:

```text
not_collected: <reason>
```

Do not replace missing data with memory or guesses.

## 8. PASS / BLOCKED / NO-GO interpretation

### `PASS`

Use only if all are true:

- host identity is clear
- actual project path is known
- at least one git path result is coherent
- docker process posture is understandable
- local backend health is readable
- local ops state is readable
- no mutation was performed

`PASS` does not mean live trading is approved.
It only means readonly posture collection succeeded.

### `BLOCKED`

Use if any of these are true:

- project path unknown
- health unclear
- ops state unclear
- docker posture unclear
- wrong host suspected
- output contradictory

`BLOCKED` means do not proceed to first controlled send preparation yet.

### `NO-GO`

Use if evidence indicates the cloud host should not be used for higher-risk work at all in its current state.

Examples:

- services missing in a way that breaks the review path
- host/revision mismatch cannot be reconciled
- unexpected exposure or runtime drift is suspected
- readonly collection itself reveals an unsafe or non-reviewable posture

`NO-GO` here is stronger than `BLOCKED`.
It means stop and route to technical review before any next step.

## 9. Rollback note

This round is docs-only.

If the document itself needs to be removed later:

```bash
cd /Users/baolood/Projects/project-anchor
git revert <commit>
git push origin main
```

If it has not been committed yet:

```bash
cd /Users/baolood/Projects/project-anchor
git restore docs/CLOUD_HOST_READONLY_STATUS_COMMAND_PACK_V1.md
git status --short
```
