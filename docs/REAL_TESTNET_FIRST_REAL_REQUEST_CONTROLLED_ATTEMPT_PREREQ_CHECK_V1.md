# Real Testnet first real request controlled attempt prereq check V1

**Status:** prereq check only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** compress the final explicit prerequisites that must all be true before Project Anchor is allowed to schedule the first bounded real external testnet request on the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not authorize the request by itself.
It defines the last blocking gate between a complete docs-and-review stack and an actual scheduled controlled attempt.

## 1. Decision

The first real testnet request remains blocked unless every prerequisite in this document is explicitly satisfied at the same time.

If any one prerequisite is:

- missing
- ambiguous
- contradicted by runtime observation
- contradicted by `/commands/[id]` evidence expectations

then result is:

```text
BLOCKED - do not schedule the controlled attempt
```

This is intentionally stricter than “probably ready.”

## 2. Fixed applicability

This prereq check applies only to:

```text
ORDER + execution_mode=testnet
```

It must not be reused for:

- legacy `QUOTE + BINANCE_TESTNET`
- `TESTNET_EXECUTOR_STUB`
- mocked external executor as proof of real send
- live trading

## 3. Canonical path prerequisites

All of these must already be true:

- canonical path remains `ORDER + execution_mode=testnet`
- legacy `QUOTE + BINANCE_TESTNET` is not being used as proof or fallback
- `/commands/[id]` can already distinguish:
  - preflight refusal
  - mocked external attempt
  - guarded real-boundary refusal
  - real external attempt evidence
- the current project interpretation still is:

```text
dry-run: proven
mocked external executor: proven
guarded real transport helper: implemented
live trading: NO-GO
```

If these path statements are not stable, do not schedule the attempt.

## 4. Runtime posture prerequisites

Before scheduling the attempt, all of these must be explicitly nameable:

- which cloud host will be used
- which operator owns the window
- which reviewer owns the window
- which revision/runtime posture is expected
- whether the host is in:
  - `mock`
  - `real-but-disabled`
  - `real-enabled-for-bounded-window`

And all of these must already be understood:

- `TESTNET_EXECUTOR_MODE` is explicit
- `TESTNET_EXECUTOR_REAL_ENABLE` is explicit
- `mock` remains the primary retreat posture
- fail-closed remains reachable immediately

If runtime posture cannot be named in one sentence, the attempt is not schedulable.

## 5. Safety prerequisites

All of these must already be true before the attempt can be scheduled:

- host safety still uses exact allowlisted HTTPS origin only
- canonical env family remains `TESTNET_EXCHANGE_*`
- credential presence can be proven without exposing secret values
- kill switch merged state can be checked during the runtime window
- ingress freeze posture remains intact
- domain/public-ingress work is still deferred
- retreat to `mock` or fail-closed does not depend on improvisation

This means the project must still know how to say “stop” more confidently than it says “send once.”

## 6. Review-surface prerequisites

The controlled attempt must remain blocked unless the reviewer can rely on all of these surfaces:

```text
/ops
-> /commands
-> /commands/[id]
```

That requires all of these to be true:

- operator review path is reachable enough to inspect state
- commands list is reachable enough to locate the bounded attempt
- command detail is reachable enough to validate event family, explanation, and outcome
- logs are treated as supporting evidence only, not as the primary verdict surface

If the project can send but not review, the project is not ready.

## 7. Rehearsal prerequisites

The first real request should not be scheduled unless the following rehearsals are already complete and still credible:

- dry activation drill logic is understood
- cloud host retreat drill logic is understood
- runtime verification checklist is usable
- minimal log review rule is usable
- first-anomaly retreat posture is explicit:
  - stop additional sends
  - preserve exact command evidence
  - retreat before second attempt

The project should not discover its retreat posture during the first anomaly.

## 8. Documentation and record prerequisites

Before scheduling the attempt, all of these artifacts must already exist and be accepted as the record shape:

- signoff record
- runtime-window execution record
- review closeout
- real-testnet review artifact home
- `BLOCKED / PASS / FAIL` artifact examples
- first-request evidence bundle index

This prerequisite is satisfied only if the project can answer:

```text
where will the attempt be approved,
where will it be recorded,
where will it be reviewed,
where will it be closed out
```

without inventing new templates mid-window.

## 9. Controlled-attempt command prerequisites

The first real request command must already be narrow enough to survive review:

- one command only
- one explicit `idempotency_key`
- one explicit `created_by`
- one explicit `source`
- one intentionally small notional
- one explicit order type
- one positive `stop_price`
- one explicit venue/host label
- no concurrent “also try this” command
- no automatic retry

If the planned command is not deliberately narrow, the attempt should stay blocked.

## 10. Hard stop prerequisites

The team must already agree that any of the following blocks scheduling:

- unclear executor mode ownership
- unclear host/origin identity
- uncertain credential-presence proof
- uncertain kill switch visibility
- uncertain review-surface reachability
- uncertain retreat path
- any desire to “just retry quickly” if the first result looks odd
- any plan to change ingress, env, deploy, or runtime shape in the same window

A controlled attempt is only valid if the attempt window is bounded, not overloaded.

## 11. Minimum prereq check template

Use this minimal scheduling gate template:

```text
timestamp:
operator:
reviewer:
host_identity:
expected_revision:

canonical_path_confirmed: yes/no
legacy_path_not_used: yes/no
runtime_posture_nameable: yes/no
real_mode_intent_explicit: yes/no
mock_retreat_available: yes/no
fail_closed_available: yes/no

host_safety_confirmed: yes/no
canonical_env_family_confirmed: yes/no
credential_presence_confirmed: yes/no
kill_switch_visibility_confirmed: yes/no
ingress_freeze_intact: yes/no
domain_work_deferred: yes/no

ops_surface_reachable: yes/no
commands_surface_reachable: yes/no
command_detail_surface_reachable: yes/no
log_review_rule_understood: yes/no

dry_activation_rehearsed: yes/no
retreat_drill_understood: yes/no
execution_record_ready: yes/no
review_closeout_ready: yes/no
artifact_home_ready: yes/no

bounded_command_shape_ready: yes/no
automatic_retry_absent: yes/no
second_attempt_not_preauthorized: yes/no

verdict: PASS/BLOCKED
notes:
```

## 12. PASS criteria

This prereq check is `PASS` only if:

- the canonical path is stable
- runtime posture is explicit
- safety boundary is explicit
- review surfaces are reachable
- rehearsal posture is credible
- recording/closeout artifacts are already in place
- the first command is deliberately narrow
- no hard stop condition is present
- live trading remains `NO-GO`

## 13. BLOCKED criteria

This prereq check is `BLOCKED` if:

- any prerequisite is unknown
- any prerequisite depends on a same-window config mutation
- reviewability is weaker than sendability
- retreat is weaker than enablement
- the team is relying on confidence instead of explicit proof

`BLOCKED` here is a healthy gate, not a failure.

## 14. Stable status statement

At this point the correct prereq summary is:

```text
the docs-and-review stack is ready,
but the first real request remains blocked
until canonical path, runtime posture, safety, review reachability,
retreat credibility, and bounded command shape are all simultaneously explicit
```

## 15. Minimal next bounded round

After this prereq check, the next natural bounded round is:

```text
Real Testnet First Real Request Scheduling Packet V1
```

Scope:

```text
docs-only
assemble the exact bounded packet that would be reviewed
immediately before deciding whether to open the actual first-request window
```
