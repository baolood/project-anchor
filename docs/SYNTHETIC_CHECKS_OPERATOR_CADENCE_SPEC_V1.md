# Synthetic Checks Operator Cadence Spec V1

## Status

- Spec type: operator-run cadence specification
- Current accepted activation path: operator-run cadence
- Cron / scheduler required now: NO
- Real external request authorized: NO
- Live trading: NO-GO

## Operator

- Primary operator: `baolood`
- Qualification: `solo internal review mode`

## Cadence

Current accepted minimum cadence:

- once per day during the active pre-go-live preparation window

Additional required trigger:

- re-run after any bounded stage action that may materially affect the observed
  runtime posture for:
  - backend health
  - ops state visibility
  - worker heartbeat
  - parent guardrail checks

Examples include:

- controlled deploy validation
- controlled rollback validation
- explicit stage runtime posture changes that are separately authorized

## Execution scope

Each cadence run must execute the already agreed synthetic check set:

- `SC-HEALTH`
- `SC-OPS`
- `SC-WORKER`
- `SC-PARENT`

No new probe surfaces are introduced by this spec.

## Evidence location

Evidence must be written under:

- **`artifacts/synthetic-checks/`**

Naming rule:

- one file per run
- UTC timestamp included in the filename
- enough context in the filename to identify the cadence run

Example pattern:

- `YYYY-MM-DDThh-mm-ssZ-operator-run-cadence-<label>.md`

## Minimum evidence payload

Each run must record at least:

- execution timestamp
- operator identity
- host identity
- repo path
- git revision
- git dirty state
- docker runtime visibility
- `SC-HEALTH` result
- `SC-OPS` result
- `SC-WORKER` classification
- `SC-PARENT` result
- boundary confirmation
- final PASS / FAIL decision

## PASS rule for cadence run

A cadence run is PASS only if all are true:

- `/health` returns success
- `/ops/state` is reachable
- worker heartbeat is visible
- worker heartbeat freshness is within `<= 60s`
- `PYTHON=python3.11 bash scripts/check_local_box_baseline.sh` passes
- `bash scripts/check_go_live_rules.sh` passes
- no deploy or restart occurs as part of the run
- no credential or kill switch mutation occurs
- real external request remains NOT AUTHORIZED
- live trading remains NO-GO

## Failure handling

If any cadence run fails:

1. stop the run
2. record the failing check
3. record visible runtime posture
4. do not repair runtime unless separately authorized
5. do not close the Week 3 row

## Final spec result

- Operator-run cadence explicit: YES
- Evidence location explicit: YES
- Minimum payload explicit: YES
- Accepted current activation path fixed: YES
- Cron / scheduler required now: NO
