# CLOUD_AUTOMATION_GUARDRAIL_PLAN_V1

## 1) Goal And Scope

This plan defines the minimum guardrails required before enabling limited production automation support for Codex/Cursor on Project Anchor.

Scope of this document:

- Define rollout in 5 isolated rounds
- Define acceptance criteria and rollback for each round
- Define allowed and forbidden automation boundaries

Out of scope in this round:

- No cloud host changes
- No compose/nginx/env updates
- No service restart/reboot
- No code deployment

Target state is not "full automation". Target state is:

- Low-privilege operator account
- Script-only guarded execution
- Dry-run before apply
- Mandatory verify after apply
- Rollback path always available

---

## 2) Timeline Estimate

- Fast usable baseline: 2 days
- Stable closeout: 3-5 days
- Not recommended: compress all rounds into 1 day

Reason:

- Main risk is permission and safety boundary design, not coding complexity.
- Production control changes must be isolated, auditable, and reversible.

---

## 3) Round Plan (One Round, One Deliverable)

### Round 1 - Guardrail Specification Document

Expected effort: 30-60 minutes

Deliverable:

- `anchor-backend/docs/CLOUD_AUTOMATION_GUARDRAIL_PLAN_V1.md`

Acceptance:

- Rules are written and reviewable
- No runtime or host changes

Rollback:

- Remove this document

### Round 2 - Read-Only Runtime Check Script

Expected effort: 1-2 hours

Deliverable:

- `anchor-backend/scripts/cloud_runtime_check_readonly.sh`

Minimum checks:

- `docker compose ps`
- `/health`
- `/ops/state` (if enabled in current environment)
- worker logs summary
- final PASS/FAIL output

Acceptance:

- Script performs checks only (no mutation)
- Script exit code and output are deterministic

Rollback:

- Remove read-only script

### Round 3 - Low-Privilege Deploy User

Expected effort: 1-2 hours

Deliverable:

- Dedicated `deploy` user and controlled SSH entry path

Acceptance:

- Automation no longer depends on direct root login
- Access path is documented and testable

Rollback:

- Disable deploy user and return to manual root-only workflow

### Round 4 - Whitelisted Sudo Entry

Expected effort: 2-4 hours

Deliverable:

- `/etc/sudoers.d/project-anchor-deploy`
- Whitelisted script entry points only

Security rules:

- No unrestricted `sudo`
- No arbitrary `docker` or shell access
- No `git reset --hard` / `git clean -fd` style destructive operations in automation path

Acceptance:

- Deploy user can run only approved scripts
- Unapproved privileged commands are denied

Rollback:

- Remove sudoers whitelist file and disable privileged entry

### Round 5 - Dry-Run / Apply / Verify / Rollback Loop

Expected effort: 0.5-1 day

Deliverables:

- dry-run script
- apply script
- verify script
- rollback script

Required flow:

1. Dry-run
2. Human confirmation
3. Apply
4. Verify
5. Rollback (if needed) must be executable and validated

Acceptance:

- End-to-end loop works consistently
- Failure path is recoverable via rollback

Rollback:

- Remove guarded automation scripts and return to manual operations

---

## 4) Program-Level Acceptance Template

Use this template to track progress:

```text
[Production Automation Guardrail Timeline]

1. Guardrail specification document
Expected: 30-60 min
Status: TODO

2. Read-only check script
Expected: 1-2 h
Status: TODO

3. Low-privilege deploy user
Expected: 1-2 h
Status: TODO

4. Sudo whitelist
Expected: 2-4 h
Status: TODO

5. Dry-run / apply / rollback loop
Expected: 0.5-1 day
Status: TODO

Estimated total:
2-5 days

Final target:
READY_FOR_LIMITED_AUTOMATION
```

---

## 5) Automation Policy Boundary

When this plan is complete:

- Allowed: limited, guarded, script-only automation
- Not allowed: direct root production operation by Codex/Cursor

Hard boundary:

- No direct arbitrary production commands from assistant context
- No bypass of dry-run/human confirmation/verify/rollback sequence

---

## 6) Risk Control Notes

- Do not compress 5 rounds into a single mixed execution batch.
- Each round must be independently verifiable and independently reversible.
- Priority is operational safety and auditability, not speed.

Current recommendation:

- Today: complete Round 1 only (this document)
- Next rounds: implement read-only checks first, then access control, then guarded apply loop
