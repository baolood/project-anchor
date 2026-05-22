# Real testnet host safety rule V1

**Status:** host-safety rule only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Security lead, interim).

**Date:** 2026-05-22

**Scope:** resolve the host-safety question for the future canonical real testnet path:

```text
Command.type = ORDER
payload.execution_mode = testnet
TESTNET_EXCHANGE_BASE_URL
```

This document does not implement host validation. It defines the rule that future implementation must follow before any signed HTTP request is allowed.

## 1. Decision

The canonical host-safety rule for future real testnet execution is:

```text
explicit named venue map + exact HTTPS origin allowlist
```

Not accepted as the primary rule:

```text
generic suffix matching alone
free-form host input
implicit fallback from blank config
legacy QUOTE path host behavior
```

## 2. Why this rule wins

This rule is chosen because it gives the strongest practical safety with the least ambiguity.

It is better than a plain suffix rule because:

- some suffixes can be ambiguous or overly broad
- exact named origins are easier to audit
- reviewers can tell clearly whether a host is approved
- accidental live-host drift becomes easier to reject

## 3. Canonical model

Future implementation should validate `TESTNET_EXCHANGE_BASE_URL` in two steps:

1. map `market` to a named testnet venue profile
2. require the configured base URL to match one exact allowed origin for that profile

Canonical example:

```text
market = binance_testnet
-> allowed origins = { https://testnet.binancefuture.com }
```

The exact list may expand later, but the model remains:

```text
named venue
-> explicit allowlist
-> exact origin match
```

## 4. Minimum required checks

Before any signed HTTP request, the future boundary must verify all of these:

- `TESTNET_EXCHANGE_BASE_URL` is present
- URL parses successfully
- scheme is `https`
- host is non-empty
- URL origin exactly matches one allowed origin for the chosen testnet venue
- URL is not a production/live origin
- URL is not a loopback/local dev host for the real external path
- URL does not rely on implicit defaulting

If any check fails:

```text
no signed HTTP
command becomes FAILED
failure family = TESTNET_BASE_URL_INVALID
```

## 5. Allowed matching rule

Allowed matching must be:

```text
exact origin equality after normalization
```

Normalization may include:

- lowercasing scheme and host
- removing default port when equivalent
- preserving path/query exclusion from origin comparison

The safe comparison target is:

```text
scheme + host + effective port
```

not a raw string prefix.

## 6. Disallowed matching rules

The future implementation must reject these strategies as primary validation:

- `contains("testnet")`
- host suffix only, without venue mapping
- regex that accepts multiple unknown hosts
- blank host falling back to production default
- environment guess from payload text alone

These are too weak for a boundary that must protect against accidental live contact.

## 7. Named venue profile rule

Each canonical testnet venue should eventually have a small profile that defines:

- market label
- allowed origin set
- optional host label for review evidence
- optional expected product scope

Minimum conceptual shape:

```text
binance_testnet
-> origins: { https://testnet.binancefuture.com }
-> host_label: binance_futures_testnet
```

If the market does not map to a known profile:

```text
no signed HTTP
failure family = TESTNET_BASE_URL_INVALID or TESTNET_CONTRACT_REJECTED
```

depending on where the validation is placed.

## 8. Live-host rejection rule

The validator must explicitly reject origins known to be live/production, even if the rest of the payload says `testnet`.

Reason:

```text
execution_mode=testnet must not be able to override a live host by wording alone
```

This is a hard safety rule, not a soft warning.

## 9. Loopback and local-host rule

For the future real external path, these must be rejected as real testnet upstreams:

- `127.0.0.1`
- `localhost`
- private dev aliases meant for local simulation

Why:

- local hosts can be valid for proxying or dev tools
- they are not proof of real external testnet contact
- accepting them would blur stub/proxy/real-boundary evidence

## 10. Failure semantics

When host safety fails, review should see:

- final state: `FAILED`
- family: `TESTNET_BASE_URL_INVALID`
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

If implementation emits more detail, it must still preserve the same review meaning.

## 11. Review evidence

The command detail review should let the operator answer:

- what market profile was selected?
- what host label was expected?
- what origin was configured?
- did the configured origin exactly match an allowed origin?
- was any live or ambiguous host rejected before signed HTTP?

Non-secret host metadata is acceptable in review output if it helps prove the decision.

## 12. Adapter and migration rule

If migration temporarily bridges old and new config names:

```text
TESTNET_EXCHANGE_BASE_URL first
legacy BINANCE_FUTURES_BASE second
```

But the resulting value must still pass the canonical host-safety rule.

Legacy naming does not weaken host validation.

## 13. What not to do

- Do not accept “looks like testnet” as proof.
- Do not silently default a blank URL.
- Do not allow production hosts when `execution_mode=testnet`.
- Do not treat loopback as real external proof.
- Do not rely on the legacy QUOTE path to define future host validation.

## 14. Recommended next bounded round

After this rule, the natural next round is:

```text
Real Testnet Kill Switch Source Rule V1
```

Scope:

```text
docs-only
resolve which runtime source is authoritative for kill switch proof at boundary time
no real key
no live trading
```

## 15. Acceptance for this rule

```text
host safety rule resolved with named venue map + exact origin allowlist: PASS
generic suffix-only validation rejected: PASS
live-host rejection rule stated: PASS
loopback/local-host rejection stated: PASS
failure family fixed to TESTNET_BASE_URL_INVALID: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```
