# Cloud host minimal log review rule V1

**Status:** log review rule only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** define the smallest cloud-host log review standard required to distinguish preflight refusal, guarded real-boundary refusal, and real external-attempt evidence during the first bounded real testnet request window.

This rule does not require a full observability platform.
It standardizes what “enough logging to decide safely” means for the current guarded stage.

## 1. Decision

The operator does not need every log line.
The operator does need enough log evidence to answer one question reliably:

```text
did this command stop before external request,
stop at the guarded real boundary,
or actually cross into external-attempt evidence?
```

If the available host-side logs cannot answer that question, result is:

```text
BLOCKED - do not continue beyond current posture
```

## 2. What this rule is for

This rule exists because the first real request window is still narrow and operator-mediated.

The goal is not deep observability.
The goal is to avoid these failure modes:

- reading too much log noise and guessing
- treating terminal output as enough proof
- confusing preflight refusal with real-attempt refusal
- confusing guarded real-boundary refusal with upstream rejection

## 3. Minimum log-review objective

The smallest acceptable log review should help the operator distinguish these three classes:

### A. Pre-external refusal

Examples:

- `KILL_SWITCH_ON`
- `TESTNET_BASE_URL_INVALID`
- `TESTNET_CREDENTIALS_MISSING`
- `TESTNET_CONTRACT_REJECTED`
- `POLICY_BLOCK`
- `RISK_HARD_LIMITS_...`

Interpretation:

```text
the command never crossed into external-attempt evidence
```

### B. Guarded real-boundary refusal

Examples:

- `TESTNET_REAL_WIRE_DISABLED`
- `TESTNET_REAL_TRANSPORT_INPUT_INVALID`

Interpretation:

```text
the canonical path reached the real helper boundary,
but still did not complete a real upstream attempt
```

### C. Real external-attempt evidence

Examples:

- `TESTNET_EXECUTOR_REQUESTED`
- `TESTNET_EXECUTOR_ACCEPTED`
- `TESTNET_EXECUTOR_REJECTED`
- `TESTNET_EXECUTOR_AUTH_FAILED`
- `TESTNET_EXECUTOR_TIMEOUT`
- `TESTNET_EXECUTOR_NETWORK_ERROR`

Interpretation:

```text
the command crossed into external-attempt territory
and must be reviewed as such
```

## 4. Minimum acceptable evidence sources

The operator may use a combination of:

- minimal host-side logs
- `/commands`
- `/commands/[id]`
- review artifact notes

But the rule is:

```text
host logs should support the interpretation,
not replace the command-detail review path
```

If logs and `/commands/[id]` disagree, treat that as an anomaly requiring retreat or technical review.

## 5. What “minimum log review” means

Minimum log review means the operator can answer all of these:

1. Did the command reach worker/action processing at all?
2. Did the command stop before external request evidence?
3. Did it stop at the guarded real boundary?
4. Did it emit external-attempt evidence?
5. Is the final command state consistent with the log interpretation?

If even one answer is unclear, the log review is not sufficient.

## 6. What not to do

During the request window, the operator must not:

- grep endlessly until a preferred answer appears
- use raw logs as a substitute for `/commands/[id]`
- treat absence of logs as proof of success
- treat presence of generic errors as proof of external attempt
- interpret a single detached line as global system truth

This rule exists to reduce over-reading and false certainty.

## 7. Minimum review posture by evidence family

### For pre-external refusal

Minimum acceptable interpretation:

- no true external-attempt evidence should be claimed
- final state should align with refusal
- `/commands/[id]` should not imply accepted upstream behavior

### For guarded real-boundary refusal

Minimum acceptable interpretation:

- command reached the real helper boundary
- command did not successfully complete a real upstream acceptance
- operator should verify whether retreat is required before any second attempt

### For real external-attempt evidence

Minimum acceptable interpretation:

- command crossed the external-attempt boundary
- operator must classify the result as accepted or rejected/failed
- any second attempt requires explicit review of the first command evidence

## 8. Minimal log-review checklist

Use this short checklist during the request window:

```text
timestamp:
command_id:
log_source_identified: yes/no
worker_or_backend_processing_seen: yes/no
pre_external_refusal_seen: yes/no
guarded_boundary_refusal_seen: yes/no
external_attempt_evidence_seen: yes/no
final_state_matches_logs: yes/no
command_detail_matches_logs: yes/no
contradiction_present: yes/no
verdict: PASS/BLOCKED
notes:
```

## 9. PASS criteria

This log review rule is `PASS` only if:

- the operator can distinguish refusal vs boundary vs external attempt
- `/commands/[id]` and log interpretation agree
- no contradiction is present
- the operator can explain whether retreat is required

## 10. BLOCKED criteria

This log review rule is `BLOCKED` if:

- logs are too weak or too noisy to classify the path
- command detail and logs disagree
- external-attempt status is ambiguous
- final state does not align with available evidence
- operator would need to guess between refusal and external attempt

This should be treated as a healthy stop condition, not a nuisance.

## 11. Stable status statement

At this point the correct log-review summary is:

```text
minimal logs must support, not replace, command-detail review
the key distinction is refusal vs guarded-boundary vs external-attempt
ambiguity should produce BLOCKED or technical review
domain: still not required
live trading: NO-GO
```

## 12. Minimal next bounded round

After this rule, the next natural host-related bounded round is:

```text
Cloud Host Ingress Freeze Rule V1
```

Scope:

```text
docs-only
fix what ingress or exposure changes are explicitly forbidden
during the first-real-request preparation and review window
```
