# Stage Python minor parity decision V1

**Status:** decision record only — does **not** change the stage host, does **not** authorize deploy, and does **not** close **`docs/GO_LIVE_CHECKLIST.md`** Week 1 **Prod-like environment parity check**.

**Owner:** **baolood** (Operations / Engineering lead, interim).

**Date:** 2026-05-31

**Related:** **`docs/ENVIRONMENT_PARITY_CHECKLIST.md`**, **`docs/STAGE_ENVIRONMENT_FACTS_V1.md`**, **`docs/STAGE_DEPLOY_RUNBOOK.md`**, **`docs/GO_LIVE_CHECKLIST.md`** Week 1 + Week 2.

---

## 1) Decision

For the current shared stage / prod-like target, the preferred path is:

```text
align the stage host to Python 3.11
```

The team does **not** accept **`Python 3.10.12`** as a permanent intentional delta for the parent repo parity line at this time.

---

## 2) Facts behind the decision

Current recorded facts:

- local parent baseline evidence runs on **`Python 3.11.15`**
- CI parent baseline runs on **`Python 3.11`**
- current stage / prod-like target (`vultr`, `45.76.190.109`) reports **`Python 3.10.12`**
- read-only host check on 2026-05-31 found no preinstalled **`python3.11`** binary on the target host

These facts are already reflected across:

- **`docs/STAGE_ENVIRONMENT_FACTS_V1.md`**
- **`docs/ENVIRONMENT_PARITY_CHECKLIST.md`**

---

## 3) Why not sign off 3.10.12 as an accepted delta

This is a parent-repo parity issue, not the already-closed local drift issue tracked by **R-002**.

Accepting the host at **`3.10.12`** right now would leave us with:

- local parent validation on **`3.11.15`**
- CI parent validation on **`3.11`**
- stage / prod-like parent validation on **`3.10.12`**

That split is still workable for exploratory reads, but it is too loose for calling the Week 1 parity item complete because:

1. Week 2 deploy / rollback / observability runbooks are expected to converge on the shared target host.
2. The parent repo already treats CI as the source of truth for Python-sensitive smokes.
3. A permanent stage lag would make future parent-only failures harder to classify as “host-specific” vs “real parity drift”.

So the right posture is:

```text
host locked
parity blocker explicit
parity not yet closed
```

---

## 4) What this decision does unlock

This decision removes ambiguity about the next action.

The remaining Week 1 parity blocker is now:

```text
stage host Python minor alignment to 3.11
```

Not:

- target host identity
- whether a stage host exists
- whether the parent repo can be inspected on the host

That gives the downstream Week 2-6 lines a cleaner dependency:

- **before**: “stage / prod-like target still vague”
- **after**: “stage target is fixed; Python minor alignment remains”

---

## 5) Next allowed move

The next bounded task should be one of these:

1. **Stage Python 3.11 alignment plan** — docs / ops plan only
2. **Stage Python 3.11 installation / selection change** — explicit host change task, separately authorized
3. **Parity close decision after alignment evidence** — only after the target host actually reports **`Python 3.11`**

Until one of those happens:

- **`docs/GO_LIVE_CHECKLIST.md`** Week 1 parity row stays **`IN_PROGRESS`**
- Week 2 deploy / rollback docs may continue to improve, but they do not become fully validated
- **go-live remains `NO-GO`**
- **real external request remains `NOT AUTHORIZED`**
- **live trading remains `NO-GO`**

---

## 6) Non-goals

This decision does **not**:

- install Python on the host
- change the host runtime
- perform deploys
- authorize real external request
- authorize live trading

