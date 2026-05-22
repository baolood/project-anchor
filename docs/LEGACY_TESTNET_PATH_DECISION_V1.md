# Legacy testnet path decision V1

**Status:** decision record only - no code change, no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Release / Engineering lead, interim).

**Date:** 2026-05-22

**Scope:** decide the disposition of the existing legacy path:

```text
EXECUTION_MODE=BINANCE_TESTNET
and cmd_type=QUOTE
```

This document does not execute that path. It only decides what Project Anchor should do with it.

## 1. Decision

The legacy real-testnet path should **not** be treated as the canonical future testnet path.

Decision:

```text
canonical future path = ORDER + execution_mode=testnet
legacy QUOTE + BINANCE_TESTNET path = isolate, label as legacy, and plan migration/removal
```

That means:

- do not extend new testnet work on top of the legacy `QUOTE` branch
- do not call it the official testnet path in docs or review
- do not wire real credentials into it as the long-term solution

## 2. Why this decision is necessary

The repository currently has two different “testnet” shapes:

### Newer path

```text
Command.type: ORDER
payload.execution_mode: testnet
source / created_by / stop_price enforced
testnet_stub: true
external_call: false
```

### Older path

```text
EXECUTION_MODE=BINANCE_TESTNET
cmd_type=QUOTE
BINANCE_API_KEY / BINANCE_API_SECRET
signed REST call to Binance Futures Testnet
```

If both remain “active” without a decision:

- reviewers cannot tell which path is authoritative
- env naming remains inconsistent
- event semantics remain split
- future real testnet work will be harder to audit

## 3. Why the legacy path should not be the canonical one

The legacy path is useful as evidence that signed testnet HTTP was explored, but it is a weak fit for the current direction.

Problems:

- it is `QUOTE`-shaped, while the current contract is `ORDER`-shaped
- it is keyed off global env mode instead of `payload.execution_mode`
- it uses older env names:
  - `BINANCE_API_KEY`
  - `BINANCE_API_SECRET`
  - `BINANCE_FUTURES_BASE`
- it bypasses the newer stub review semantics
- it was not designed around the newer `source / created_by / stop_price` audit fields

So the old branch is better treated as:

```text
legacy exploration code
not the future contract authority
```

## 4. Chosen disposition

Chosen disposition:

```text
Isolate now
Migrate later
Remove only after replacement is proven
```

Interpretation:

1. **Isolate now**
   The team should explicitly label the `QUOTE + BINANCE_TESTNET` path as legacy in docs and review language.

2. **Migrate later**
   If real testnet execution is pursued, it should move under:

   ```text
   ORDER + execution_mode=testnet
   ```

   with canonical env naming and clearer event evidence.

3. **Remove only after replacement is proven**
   Do not delete the legacy code blindly before the replacement path exists and is testable.

## 5. What “isolate” means in practice

For upcoming rounds, “isolate” means:

- do not add new features to the legacy path
- do not add new docs that present it as preferred
- do not add new smoke scripts around the legacy path as if it were the mainline
- do not route Trade Gate or new testnet flows through it
- do not bind long-term credential naming to it

It may remain in the tree temporarily, but it should be treated as:

```text
legacy
non-canonical
subject to migration/removal
```

## 6. Migration target

The intended replacement target is:

```text
ORDER command
payload.execution_mode=testnet
canonical testnet env names
explicit kill switch boundary
real-testnet smoke evidence
command detail review path
```

Minimum characteristics of the replacement:

- `execution_mode=testnet` drives the path
- env names are clearly testnet-only
- no generic `BINANCE_API_KEY` ambiguity
- event chain remains reviewable through `/commands/[id]`
- kill switch proof exists before signed HTTP
- auth/network failures normalize into command errors

## 7. What not to do

- Do not declare the legacy path “good enough” just because it can sign HTTP.
- Do not wire production-like secrets into the legacy path.
- Do not rename the newer `ORDER` contract back toward `QUOTE` just to match old code.
- Do not delete the legacy path until the replacement path exists and is proven.
- Do not call CI green a real testnet approval.

## 8. Recommended next bounded rounds

After this decision, the next useful rounds are:

1. **Canonical Testnet Env Contract V1**
   Choose exact env names for future real testnet path.

2. **ORDER Testnet Executor Boundary V1**
   Define or implement the real executor boundary under `ORDER`.

3. **Real Testnet Smoke Spec V1**
   Specify PASS/FAIL evidence before any real key is used.

4. **Legacy Testnet Path Isolation Note V1**
   If needed, add a brief inline code/doc note marking the old branch as legacy.

## 9. Acceptance for this decision

```text
canonical future path chosen: PASS
legacy QUOTE path marked non-canonical: PASS
remove-now rejected: PASS
migrate-later stated: PASS
env naming conflict acknowledged: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```
