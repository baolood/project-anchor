# Synthetic Checks Activation Path Decision V1

## Status

- Decision type: activation path decision only
- Chosen activation path: operator-run cadence
- Cron / scheduler required now: NO
- Cron / scheduler forbidden forever: NO
- Week 3 synthetic checks row closed by this document: NO
- Real external request authorized: NO
- Live trading: NO-GO

## Question

What repeatable activation path will the project accept for the Week 3
**`Synthetic checks for critical endpoints`** row, given that:

- the synthetic checks are already defined;
- first controlled execution has already passed; and
- the current blocker is activation, not executability?

## Current baseline

The project has already established:

1. **Definition baseline**
   - **`docs/SYNTHETIC_CHECKS_CRITICAL_ENDPOINTS_V1.md`**
2. **Execution authorization**
   - **`docs/SYNTHETIC_CHECKS_EXECUTION_AUTHORIZATION_REVIEW_V1.md`**
3. **First controlled execution evidence**
   - **`docs/SYNTHETIC_CHECKS_FIRST_CONTROLLED_EXECUTION_CLOSEOUT_V1.md`**
4. **Activation threshold decision**
   - **`docs/SYNTHETIC_CHECKS_ACTIVATION_DECISION_V1.md`**

Those layers already prove:

- synthetic checks are explicit;
- synthetic checks are executable;
- synthetic checks are not yet active in an operationally durable sense.

## Decision

Decision: adopt an **operator-run cadence** as the current accepted activation
path for Week 3.

This means:

- the project does **not** need cron or another scheduler **right now**
- the project **does** need an explicit, repeatable, operator-run cadence
- each execution under that cadence must produce an evidence bundle

## Why this path is preferred now

The project is still in the go-live preparation phase.

The smallest controllable path is:

- human-triggered
- fixed-frequency
- explicitly reviewable
- bounded by evidence capture

This avoids introducing a new failure surface too early, such as:

- cron misfire
- scheduler drift
- hidden retries
- silent non-execution
- extra debugging surface unrelated to the synthetic checks themselves

In short:

- **manual once** is too weak
- **operator-run cadence** is strong enough for the current phase
- **cron / scheduler** is optional future hardening, not current necessity

## Accepted activation path (current phase)

The accepted activation path for now is:

- **operator-run cadence**
- fixed trigger / frequency
- fixed evidence bundle format
- repeatable use of the already defined synthetic probes

This path is considered acceptable only if all of the following are explicit:

1. who runs it
2. how often it runs
3. what commands/check set are run
4. where evidence is recorded
5. what counts as PASS / FAIL

## Cadence expectation

Current accepted minimum cadence:

- one named operator
- one fixed review frequency
- one bounded evidence capture path per run

This document does **not** lock the exact interval yet, but it does require the
next activation artifact to name it explicitly.

Examples of acceptable future cadence statements:

- once per day during pre-go-live window
- once per release-candidate change
- once before each controlled operational milestone

The exact cadence can be chosen later, but it must be explicit and repeatable.

## Evidence location

Chosen evidence location:

- **`artifacts/synthetic-checks/`**

Expected use:

- one evidence bundle per activation run
- timestamped or clearly named records
- sufficient content to classify:
  - `SC-HEALTH`
  - `SC-OPS`
  - `SC-WORKER`
  - `SC-PARENT`

This decision fixes the location at the policy level even before the first
cadence-based run is recorded there.

## DONE threshold for Week 3 row

The Week 3 row may move from **`IN_PROGRESS`** to **`DONE`** only when both are
true:

1. the operator-run cadence is explicitly defined and accepted as the current
   activation path
2. at least one successful execution under that cadence is recorded in
   **`artifacts/synthetic-checks/`**

This means:

- first controlled execution alone is **not enough**
- one future run under the accepted activation path **can be enough**
- cron / scheduler is **not** required for this row to close

## What this decision does not do

This decision does **not**:

- execute synthetic checks
- create cadence evidence by itself
- install cron
- introduce a scheduler
- integrate PagerDuty / Slack / Telegram / email
- close the Week 3 row immediately

It only fixes the currently accepted path to activation.

## Relationship to alerting

This decision is intentionally narrower than alerting.

The following remains separate:

- **`Alert rules + routing implemented`**
- **`G2 — P0/P1 alerting verified (test alert acked)`**

So the project may accept:

- synthetic checks active under operator-run cadence

before it accepts:

- full alert tooling integration
- alert ack evidence

That separation is deliberate and keeps the Week 3 lines honest.

## Recommended next task

Recommended next task:

- **`Synthetic Checks Operator Cadence Spec`**

That task should define:

- operator identity / role
- explicit cadence
- exact evidence file naming pattern under
  **`artifacts/synthetic-checks/`**
- minimum required payload in each bundle

## Final decision result

- Activation standard exists: YES
- Operator-run cadence acceptable: YES
- Cron / scheduler required now: NO
- Evidence location required: YES
- Evidence location chosen: **`artifacts/synthetic-checks/`**
- Week 3 row ready for DONE now: NO
- Real external request authorized: NO
- Live trading: NO-GO
