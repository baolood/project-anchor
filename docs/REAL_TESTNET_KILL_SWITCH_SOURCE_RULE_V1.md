# Real testnet kill switch source rule V1

**Status:** source-of-truth rule only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Security lead, interim).

**Date:** 2026-05-22

**Scope:** resolve which runtime source is authoritative for kill switch proof at the future canonical real testnet executor boundary:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not implement the boundary check. It defines which source future implementation must trust when deciding whether signed HTTP may proceed.

## 1. Decision

The authoritative kill switch source at executor-boundary time is:

```text
merged runtime state from app.ops.kill_switch.get_kill_switch_state()
```

which currently resolves into:

```text
enabled: bool
source: string
```

and already merges:

- env override
- Redis runtime state

This merged result is the canonical decision input.

## 2. Why this rule wins

This rule is chosen because it matches existing runtime behavior while still giving one reviewable answer at the boundary.

It is better than picking only env or only Redis because:

- env override exists as an emergency hard stop
- Redis state exists as the normal operator control path
- reviewers need one final authoritative answer, not two competing reads

The rule is:

```text
implementation may have multiple underlying sources,
but boundary-time decision must consume one merged authoritative result
```

## 3. Canonical source contract

At boundary time, future real testnet implementation must read:

```text
enabled, source = get_kill_switch_state()
```

Decision rule:

- if `enabled == true` -> block external request
- if `enabled == false` -> boundary may continue to later checks

The boundary must not independently re-interpret lower-level inputs once this merged result is returned.

## 4. Why lower-level re-checks are disallowed

The future executor boundary must not do things like:

- read raw env itself and ignore merged state
- read Redis separately and override merged state locally
- derive its own “best guess” from unrelated ops pages

Why:

- creates split-brain decisions
- weakens auditability
- makes `KILL_SWITCH_ON` evidence ambiguous

## 5. Underlying precedence rule

The authoritative merged function may internally preserve precedence.

Current expected precedence shape:

```text
env emergency override first
Redis runtime state second
default OFF only when neither source enables kill switch
```

Future implementation must not invent a different precedence at the executor boundary.

If precedence ever changes, it must change in the shared source function, not in executor-specific code.

## 6. Boundary usage rule

The future real testnet executor boundary must perform the kill switch decision:

```text
after contract / policy / risk checks
before any signed HTTP request
```

and it must use exactly one authoritative read for that decision point.

Required review meaning:

```text
KILL_SWITCH_CHECKED
means the boundary consumed the authoritative merged kill-switch state
at the last safe point before external request
```

## 7. Required review evidence

When refusal happens, review should be able to see:

- final state: `FAILED`
- family: `KILL_SWITCH_ON`
- event family including `KILL_SWITCH_CHECKED`
- no external request evidence after refusal
- non-secret indication of the merged source label

The source label is important because reviewers should know whether the refusal came from:

- env emergency override
- Redis/operator control
- another explicitly documented merged source label in the future

## 8. Source label rule

The merged source function should expose a stable, reviewable source label.

Minimum expected labels:

```text
env
redis
default
```

or equivalent explicit names with the same meaning.

The operator review does not need raw backend internals, but it should be able to answer:

```text
why was kill switch considered ON at boundary time?
```

## 9. Failure semantics

If the authoritative merged read says kill switch is ON:

```text
no signed HTTP
failure family = KILL_SWITCH_ON
external request status = no
```

Recommended event family:

```text
PICKED
POLICY_ALLOW
KILL_SWITCH_CHECKED
ACTION_FAIL
MARK_FAILED
```

If the source read itself fails unexpectedly, implementation should not continue optimistically into external execution. It should fail closed.

Recommended normalization for source-read failure:

```text
KILL_SWITCH_ON
or a future dedicated safe-fail family if explicitly introduced
```

but never “assume OFF and continue”.

## 10. Safe-fail rule

The boundary must be fail-closed with respect to kill switch state.

That means:

- unknown source state must not allow execution
- read errors must not silently degrade into OFF
- missing Redis alone does not justify bypass if higher-precedence source says ON

The safety posture is:

```text
uncertain stop-state => stop
```

not:

```text
uncertain stop-state => continue
```

## 11. Relationship to current repo behavior

This rule aligns with existing repository behavior that already exposes merged kill-switch state through shared helpers and APIs.

It intentionally avoids creating:

- one source rule for API ingestion
- another source rule for worker loop
- a third source rule for future executor boundary

There must be one canonical runtime answer at decision time.

## 12. What not to do

- Do not let executor code read raw env directly as its own authority.
- Do not let executor code read Redis directly as its own authority.
- Do not continue when source state is ambiguous.
- Do not treat terminal logs as stronger than merged runtime state.
- Do not let legacy QUOTE path define the new source-of-truth rule.

## 13. Recommended next bounded round

After this rule, the natural next round is:

```text
Real Testnet Event Payload Schema V1
```

Scope:

```text
docs-only
resolve which non-secret fields must accompany TESTNET_EXECUTOR_REQUESTED / ACCEPTED / REJECTED
no real key
no live trading
```

## 14. Acceptance for this rule

```text
authoritative kill-switch source fixed to merged get_kill_switch_state(): PASS
boundary-time split-brain reads disallowed: PASS
fail-closed behavior stated: PASS
source label review requirement stated: PASS
KILL_SWITCH_ON refusal semantics preserved: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```
