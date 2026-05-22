# Real testnet credential handoff rule V1

**Status:** credential-handoff rule only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Security lead, interim).

**Date:** 2026-05-22

**Scope:** define how canonical `TESTNET_EXCHANGE_*` credentials are allowed to arrive at runtime for the future canonical real testnet path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not provision or use credentials. It fixes the first allowed runtime handoff model.

## 1. Decision

The first canonical credential handoff model is:

```text
runtime process environment only,
fed from an approved secret store or operator-controlled runtime injection,
never from repository files
```

Allowed high-level flow:

```text
approved secret store or operator-local secure source
-> runtime environment injection
-> process reads TESTNET_EXCHANGE_* env vars
```

Not approved as canonical first model:

```text
committed .env files
hardcoded config files
payload-carried secrets
generic EXCHANGE_API_KEY aliases
```

## 2. Why this rule wins

This rule is chosen because it is the smallest runtime model that stays aligned with the existing docs and keeps secrets out of git.

It is better than file-based handoff because:

- it avoids repo file leakage
- it matches the canonical env contract already defined
- it is easier to reason about in stage/testnet runtime

The goal is:

```text
simple, explicit, reviewable handoff
before any more complex secret-distribution design
```

## 3. Canonical variable family

Only these names are approved for first real testnet runtime handoff:

```text
TESTNET_EXCHANGE_API_KEY
TESTNET_EXCHANGE_API_SECRET
TESTNET_EXCHANGE_BASE_URL
TESTNET_EXCHANGE_KEY_ID
```

Rules:

- values must arrive outside git
- runtime may read them from environment only
- names must not be remapped to a generic live-looking family

## 4. Approved sources

For the first runtime model, approved source classes are:

- secret manager materialized into runtime env
- operator-local secure store materialized into runtime env
- deployment/runtime configuration layer that injects env vars without writing them into repo files

All approved source classes must satisfy:

- values remain outside git
- values are rotatable
- values are deletable
- operator can identify which secret id and key id suffix were active

## 5. Disallowed sources

These are not approved as canonical first handoff:

- `.env` committed to repo
- plaintext config files under repo tree
- shell scripts in git containing real values
- request payload carrying key/secret
- logs or screenshots used as credential transport
- live exchange key repurposed as “temporary testnet”

## 6. Runtime injection rule

The executor boundary may read credentials only after:

- canonical path confirmed
- host safety passed
- kill switch passed
- risk/policy passed

That means:

```text
credential presence is a late boundary prerequisite,
not an early shortcut that bypasses other gates
```

If credentials are missing or malformed:

```text
no signed HTTP
failure family = TESTNET_CREDENTIALS_MISSING
```

## 7. File-system rule

The first canonical handoff must not depend on runtime reading secret values from repo-managed files.

Not allowed:

- `./.env`
- `./anchor-backend/.env`
- checked-in JSON/YAML secret blobs
- “temporary” text files under the repo

If a platform internally mounts secrets into files outside the repo, that is a different model and must be explicitly approved in a later round. It is not the default V1 rule.

## 8. Environment precedence rule

If temporary compatibility with legacy names exists, precedence must remain:

```text
TESTNET_EXCHANGE_* first
legacy BINANCE_* second
```

But the first approved handoff model still expects operators to provide the canonical `TESTNET_EXCHANGE_*` family.

Legacy names do not become the preferred handoff channel.

## 9. Runtime review evidence

Review should be able to answer, without exposing secrets:

- which secret family was expected?
- was the canonical env family present?
- what key id suffix or safe identifier was active?
- did handoff succeed before external request?
- if handoff failed, was it classified as `TESTNET_CREDENTIALS_MISSING`?

Review should not need to see raw credential material.

## 10. Secret-safe identifier rule

Runtime may expose a non-secret identifier such as:

```text
TESTNET_EXCHANGE_KEY_ID
```

or key-id suffix only, if that helps operations.

Rules:

- identifier must not be a usable secret
- identifier is for audit/review only
- identifier must not replace actual credential presence checks

## 11. Failure semantics

If the canonical env family is not present or not usable, review should see:

- final state: `FAILED`
- family: `TESTNET_CREDENTIALS_MISSING`
- external request status: `no`
- no `TESTNET_EXECUTOR_ACCEPTED`
- no `external_order_id`

Recommended event family:

```text
PICKED
POLICY_ALLOW
KILL_SWITCH_CHECKED
ACTION_FAIL
MARK_FAILED
```

If implementation adds more detail later, it must still preserve the same review meaning.

## 12. Relationship to host safety and kill switch

Credential handoff is not stronger than other boundary rules.

This means:

- having credentials does not weaken host-safety validation
- having credentials does not weaken kill switch
- credentials must not be read in a way that bypasses safe-fail posture

The safe sequence stays:

```text
contract / policy / risk
-> kill switch
-> host safety
-> credential presence
-> external request
```

## 13. What not to do

- Do not commit testnet secret values to repo files.
- Do not let payloads carry key/secret.
- Do not invent generic live-looking env names for first handoff.
- Do not treat credential presence as permission to skip host-safety or kill-switch checks.
- Do not make legacy BINANCE_* the preferred new handoff path.

## 14. Recommended next bounded round

After this rule, the natural next round is:

```text
Real Testnet First Implementation Slice Decision V1
```

Scope:

```text
docs-only
choose the safest first code slice after the current readiness docs stack
no real key
no live trading
```

## 15. Acceptance for this rule

```text
canonical runtime handoff fixed to env-only TESTNET_EXCHANGE_* model: PASS
repo-file secret handoff rejected: PASS
payload-carried secret handoff rejected: PASS
legacy BINANCE_* downgraded to compatibility-only: PASS
TESTNET_CREDENTIALS_MISSING failure semantics preserved: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```
