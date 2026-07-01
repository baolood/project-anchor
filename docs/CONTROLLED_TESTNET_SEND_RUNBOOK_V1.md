# Controlled Testnet Send Runbook V1

## 1. Purpose

This runbook reduces waiting, rework, and repeated prompt reconstruction for controlled real external testnet sends.

It does not reduce safety checks. It fixes the order of work so readiness is proven before any fresh execution window is opened.

Fixed flow:

READINESS_GREEN -> FRESH_AUTH_WINDOW -> EXACTLY_ONE_SEND -> CLOSEOUT_PR -> MERGE

## 2. Preconditions For READINESS_GREEN

READINESS_GREEN is true only when all of the following are true:

- main clean
- `scripts/check_hardened_order_testnet_one_shot_invocation.sh` PASS
- `scripts/check_go_live_rules.sh` PASS
- `scripts/check_local_box_baseline.sh` PASS
- backend `/health` PASS
- `/ops/state` PASS
- kill switch `enabled=false`
- worker available and heartbeat fresh
- testnet credentials runtime ready
- canary NOT EXECUTED
- live trading NO-GO
- go-live NO-GO

If any item is not green, do not open an authorization window.

## 3. Four Fixed Phases

### Diagnosis

Read-only only.

Use this phase to identify the blocker, expected runtime source, failing gate, and next required authorization. Do not mutate files, runtime, env, secrets, backend, worker, risk, or deploy state.

### Configuration

Separately authorized runtime/env repair only.

Use this phase only after the operator explicitly authorizes the bounded configuration action. Do not send POST, do not run the one-shot send path, and do not treat configuration authorization as execution authorization.

### Verification

Confirm READINESS_GREEN.

Run the baseline, guardrail, runtime, kill-switch, worker, and credential-runtime checks. This phase must still avoid POST and external exchange requests.

### Execution

Fresh bounded window plus exactly-one send only.

Execution may start only after READINESS_GREEN is true and a fresh operator authorization window has been granted.

## 4. Fresh Authorization Window Rule

- Do not open a window until READINESS_GREEN is true.
- Use a 45-60 minute bounded authorization window.
- The window is for execution, not environment repair.
- Expired windows must not be reused.
- Used windows must not be reused.
- If the window closes before execution, stop and create a new authorization record later.

## 5. Exactly-One Send Rule

- Execute inside the authorized window only.
- Use the fixed idempotency key already approved for the bounded send.
- Do not retry automatically.
- Stop on any failed preflight.
- Stop if git status is not clean.
- Stop if kill switch is enabled.
- Stop if runtime, worker, or credentials checks fail.
- Closeout is required for DONE, FAILED, or UNKNOWN.

## 6. Closeout Rule

Every execution attempt closeout must record:

- command_id
- idempotency key
- result: DONE / FAILED / UNKNOWN
- external_order_id if present
- whether upstream external exchange request started
- event chain
- canary remains NOT EXECUTED
- live trading remains NO-GO
- go-live remains NO-GO

Closeout must happen before credentials repair, retry, canary, or any new execution window.

## 7. Current Known State

- main currently at 9866c93c78d0ec179ed6dfc54ec76c48c7fb2a08 or later
- previous local intent endpoint POST was SENT
- previous local request was exactly one request
- upstream external exchange request was NOT STARTED
- historical blocker: TESTNET_CREDENTIALS_MISSING_AFTER_BOUNDED_LOCAL_SEND
- runtime repair result: TESTNET_CREDENTIALS_RUNTIME_READY
- no retry occurred after credential runtime repair
- no upstream external exchange request started after credential runtime repair
- current execution status: READY_FOR_READINESS_GREEN_VERIFICATION
- next step is READINESS_GREEN verification before the next fresh authorization window
- reconciliation evidence: `docs/TESTNET_CREDENTIALS_RUNTIME_RECONCILIATION_V1.md`
- canary: NOT EXECUTED
- live trading: NO-GO
- go-live: NO-GO

## 8. Boundary

This runbook does not authorize:

- POST
- retry
- one-shot live/send mode
- real external exchange request
- canary
- live trading
- go-live
- runtime/env/secrets mutation
- backend/worker/risk/deploy changes

The next execution may happen only through a separate fresh bounded operator authorization window.
