# Synthetic Checks Activation Decision V1

## Status

- Decision type: activation threshold decision only
- Synthetic checks executable: YES
- Synthetic checks active: NO
- Week 3 synthetic checks row closed by this document: NO
- Scheduled automation authorized by this document: NO
- External alerting platform integration authorized by this document: NO
- Real external request authorized: NO
- Live trading: NO-GO

## Question

What must be true before the Week 3 checklist row
**`Synthetic checks for critical endpoints`** may honestly move from
**`IN_PROGRESS`** to **`DONE`**?

## Current evidence

The repository now has three relevant layers of evidence:

1. **Definition baseline**
   - **`docs/SYNTHETIC_CHECKS_CRITICAL_ENDPOINTS_V1.md`**
   - Critical endpoint set, probe methods, PASS/FAIL rules, and SLI/alert
     linkage are explicit.

2. **Execution authorization**
   - **`docs/SYNTHETIC_CHECKS_EXECUTION_AUTHORIZATION_REVIEW_V1.md`**
   - First controlled synthetic check execution was explicitly authorized with
     bounded stop conditions.

3. **First controlled execution evidence**
   - **`docs/SYNTHETIC_CHECKS_FIRST_CONTROLLED_EXECUTION_CLOSEOUT_V1.md`**
   - The first controlled synthetic execution passed on the stage host.

These three layers prove that the synthetic checks are defined, reviewable, and
executable.

They do **not** yet prove that the synthetic checks are active in an
operationally durable sense.

## Decision

Decision: do **not** accept one manual execution record by itself as enough to
mark the Week 3 synthetic checks row **`DONE`**.

Reason:

- a single bounded execution proves **executability**
- it does not prove **activation**
- the checklist wording says:
  - **`Basic probes + dependency checks active`**
- “active” must mean more than “ran once successfully under supervision”

## Agreed threshold for `DONE`

The Week 3 row may move to **`DONE`** only when both are true:

1. A **concrete scheduled or otherwise repeatable activation path** exists for
   the agreed synthetic check set.
2. At least **one successful evidence bundle** exists for that activation path.

This means the project needs both:

- a real activation mechanism or operating cadence that is explicit and
  repeatable; and
- at least one successful execution record against that mechanism or cadence.

## What does count as activation?

The following can count as activation if explicitly documented and exercised:

- a concrete scheduler / cron path
- a concrete repeatable operator-run cadence with named trigger, timing, and
  evidence capture path
- another explicit mechanism that makes the checks operationally repeatable

The key requirement is not the specific technology. The key requirement is:

- repeatable
- reviewable
- bounded
- evidenced

## What does not count as activation?

The following do **not** count as sufficient by themselves:

- one manual SSH execution
- one successful probe run without a repeatable path
- one-time evidence detached from a future operating cadence
- a draft statement that the checks “could be scheduled later”

## Alerting relationship

This decision does **not** require alerting platform integration to close the
synthetic checks row itself.

That remains a separate Week 3 line:

- **`Alert rules + routing implemented`**

However, the synthetic activation path must remain compatible with:

- **`docs/SERVICE_SLI_SLO.md`**
- **`docs/ALERTING_ROUTING.md`**

In other words:

- synthetic checks can become **active** before alerting is fully wired
- but synthetic checks cannot be considered **active** if they have no
  repeatable operating path at all

## Checklist impact

Current checklist result:

- `Synthetic checks for critical endpoints`: remain **`IN_PROGRESS`**

Current reasoning:

- executable: YES
- first controlled execution: PASS
- scheduled / repeatable path: NO
- active status: NO
- row ready for DONE: NO

## Recommended next task

Recommended next task:

- **`Synthetic Checks Activation Path Decision`**

That task should answer:

- what repeatable path the project will accept
- who runs it
- how often it runs
- where evidence is recorded
- whether that path is manual cadence, scheduler-based, or another bounded
  mechanism

## Final decision result

- Synthetic checks executable: YES
- Synthetic checks active: NO
- Week 3 row ready for DONE now: NO
- Scheduled automation required specifically: not necessarily
- Concrete scheduled or repeatable path required: YES
- At least one successful evidence bundle for that path required: YES
- Real external request authorized: NO
- Live trading: NO-GO
