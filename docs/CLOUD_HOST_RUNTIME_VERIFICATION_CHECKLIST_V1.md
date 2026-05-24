# Cloud host runtime verification checklist V1

**Status:** runtime checklist only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** compress the exact runtime values, mode checks, host signals, and review-surface confirmations an operator should verify during the bounded first-real-request window on the cloud host.

This checklist does not authorize the first real request by itself.
It exists so the request window is verified by explicit runtime observation rather than memory or assumption.

## 1. Decision

During the bounded first-real-request window, the cloud host should be treated as:

```text
verify first
attempt second
retreat immediately on ambiguity
```

If the operator cannot complete this checklist with clear answers, result is:

```text
BLOCKED - remain on mock or fail-closed posture
```

## 2. Fixed applicability

This checklist applies only to:

```text
ORDER + execution_mode=testnet
```

It must not be reused for:

- legacy `QUOTE + BINANCE_TESTNET`
- `TESTNET_EXECUTOR_STUB`
- live trading

## 3. Runtime identity checks

Before or during the request window, confirm all of these:

- intended cloud host identity is explicit
- intended revision / deployed state is explicit
- operator identity for this window is explicit
- reviewer identity for this window is explicit
- the host is still being treated as an engineering-controlled node, not a public customer ingress

If any identity is unclear, stop before checking deeper runtime values.

## 4. Mode and toggle checks

Confirm all of these runtime facts explicitly:

- `TESTNET_EXECUTOR_MODE` current value is known
- if `real` is being considered, it is intentional and not inherited accidentally
- `TESTNET_EXECUTOR_REAL_ENABLE` current state is known
- `mock` remains available as a retreat posture
- fail-closed remains reachable if real wire is not explicitly allowed

The operator should be able to state plainly which of these postures the host is in:

```text
mock
real-but-disabled
real-enabled-for-bounded-window
invalid / blocked
```

If the posture cannot be named, do not attempt the request.

## 5. Canonical env and host-safety checks

Confirm all of these:

- canonical env family is `TESTNET_EXCHANGE_*`
- no legacy `BINANCE_*` naming is being treated as canonical
- configured origin is the expected exact HTTPS origin
- host label matches the expected venue mapping
- kill switch merged state can be checked now
- credential presence can be proven without exposing secrets

If any one of these is uncertain, the runtime window is `BLOCKED`.

## 6. Process and review-surface checks

Confirm all of these are still true:

- backend process/container is up
- worker process/container is up
- expected review surfaces are reachable through the current controlled access path
- `/ops` is reachable enough for operator review
- `/commands` is reachable enough to locate the command
- `/commands/[id]` is reachable enough to validate evidence and explanation

The checklist is incomplete if the operator can send but cannot review.

## 7. Evidence-family expectation checks

Before the request, confirm the operator still understands and can distinguish:

- preflight refusal
- mocked external attempt
- guarded real boundary refusal
- real external attempt accepted
- real external attempt rejected

At minimum, the operator should know what it means if they see:

- `KILL_SWITCH_ON`
- `TESTNET_BASE_URL_INVALID`
- `TESTNET_CREDENTIALS_MISSING`
- `TESTNET_REAL_WIRE_DISABLED`
- `TESTNET_REAL_TRANSPORT_INPUT_INVALID`
- `TESTNET_EXECUTOR_REQUESTED`
- `TESTNET_EXECUTOR_ACCEPTED`
- `TESTNET_EXECUTOR_REJECTED`

If the evidence family interpretation is fuzzy, do not proceed.

## 8. Real-attempt stop checks

Before any real attempt, explicitly re-confirm these stop conditions:

- any contradictory mode evidence
- host label / origin mismatch
- missing review surfaces
- missing or unclear kill switch state
- inability to preserve evidence
- uncertainty about whether a second request would be allowed

If any stop condition is present, retreat before attempt.

## 9. Minimum request-window checklist template

Use this minimal runtime verification template:

```text
timestamp:
host_identity_confirmed: yes/no
revision_confirmed: yes/no
operator_identity_confirmed: yes/no
reviewer_identity_confirmed: yes/no

executor_mode_value:
real_enable_value:
runtime_posture_label:
mock_retreat_available: yes/no
fail_closed_available: yes/no

canonical_env_family_confirmed: yes/no
legacy_env_not_canonical: yes/no
configured_origin_confirmed: yes/no
host_label_confirmed: yes/no
kill_switch_state_confirmed: yes/no
credential_presence_confirmed: yes/no

backend_up: yes/no
worker_up: yes/no
ops_reachable: yes/no
commands_reachable: yes/no
command_detail_reachable: yes/no

evidence_family_interpretation_clear: yes/no
stop_conditions_present: yes/no
verdict: PASS/BLOCKED
notes:
```

## 10. PASS criteria

This runtime checklist is `PASS` only if:

- runtime posture is explicit
- canonical env and host-safety checks are explicit
- review surfaces are reachable
- evidence-family interpretation is clear
- no stop condition is currently present
- retreat remains immediately available
- live trading remains `NO-GO`

## 11. BLOCKED criteria

This runtime checklist is `BLOCKED` if:

- mode or enablement state is ambiguous
- canonical env source is unclear
- host identity or origin is unclear
- review surfaces are unavailable
- evidence interpretation is uncertain
- retreat path is not immediate

This should be treated as a healthy stop, not as a failure to be “pushed through.”

## 12. Stable status statement

At this point the correct runtime verification summary is:

```text
request-window runtime posture must be explicitly verified
mode, host, evidence, and review reachability all matter before send
ambiguity should produce BLOCKED, not “try once anyway”
domain: still not required
live trading: NO-GO
```

## 13. Minimal next bounded round

After this checklist, the next natural bounded round is:

```text
Cloud Host Minimal Log Review Rule V1
```

Scope:

```text
docs-only
define the smallest cloud-host log review standard needed to distinguish
preflight refusal, guarded boundary refusal, and real external-attempt evidence
```
