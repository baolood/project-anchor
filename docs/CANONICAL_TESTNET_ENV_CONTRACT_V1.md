# Canonical testnet env contract V1

**Status:** naming contract only - no code change, no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Security lead, interim).

**Date:** 2026-05-22

**Scope:** choose the canonical environment-variable names for future real testnet execution.

This document does not populate any env values. It only fixes the naming contract.

## 1. Decision

The canonical env naming for future real testnet execution is:

```text
TESTNET_EXCHANGE_API_KEY
TESTNET_EXCHANGE_API_SECRET
TESTNET_EXCHANGE_BASE_URL
TESTNET_EXCHANGE_KEY_ID
```

These names replace the older generic/legacy names as the **future authoritative contract**.

Legacy names:

```text
BINANCE_API_KEY
BINANCE_API_SECRET
BINANCE_FUTURES_BASE
```

are now classified as:

```text
legacy compatibility names
not canonical
not for new design work
```

## 2. Why these names win

The chosen names are better because they:

- clearly say `TESTNET`
- do not look like live or generic exchange credentials
- match the newer testnet custody docs
- are compatible with the newer `ORDER + execution_mode=testnet` contract
- reduce the chance of wiring a live key by mistake

## 3. Canonical variable meanings

| Variable | Meaning | Notes |
|----------|---------|-------|
| `TESTNET_EXCHANGE_API_KEY` | testnet API key | must be testnet-only |
| `TESTNET_EXCHANGE_API_SECRET` | testnet API secret | must be testnet-only |
| `TESTNET_EXCHANGE_BASE_URL` | base URL for the chosen testnet venue | must resolve to testnet hostname only |
| `TESTNET_EXCHANGE_KEY_ID` | optional review/audit identifier for the key | use non-secret identifier only |

Rules:

- values must live outside git
- names may be documented in git
- values must never be documented in git

## 4. Legacy variable disposition

The older names:

```text
BINANCE_API_KEY
BINANCE_API_SECRET
BINANCE_FUTURES_BASE
```

may still exist in legacy code paths for now, but they should be treated as temporary compatibility names only.

That means:

- do not add new docs that present them as preferred
- do not introduce new features that depend on them
- do not use them as the long-term naming basis for `ORDER + execution_mode=testnet`

## 5. Migration rule

Going forward:

```text
new testnet design work -> TESTNET_EXCHANGE_* names
legacy compatibility review -> may mention BINANCE_* names
```

Do not mix both sets in the same new design without an explicit adapter/migration note.

## 6. Runtime intent rule

Canonical testnet env names must be interpreted with these safety rules:

- they are valid only for testnet execution
- they must not point to live hosts
- they must not be reused for live trading later
- any future live path must use a separate naming family

Recommended future split:

```text
TESTNET_EXCHANGE_*
LIVE_EXCHANGE_*
```

Do not use a generic name like `EXCHANGE_API_KEY` for both.

## 7. Base URL rule

`TESTNET_EXCHANGE_BASE_URL` must point to a known testnet endpoint only.

Examples of acceptable intent:

```text
testnet hostname
paper sandbox hostname
exchange-provided simulation endpoint
```

Examples of unacceptable intent:

```text
production exchange hostname
blank value falling back to production by accident
generic hostname with unclear environment
```

## 8. Adapter rule for future implementation

If code must temporarily support both old and new names during migration, use this precedence:

```text
TESTNET_EXCHANGE_* first
legacy BINANCE_* second
```

and mark the fallback as temporary.

Do not do the reverse, or the old names will remain sticky forever.

## 9. What not to do

- Do not keep designing new testnet features around `BINANCE_*` names.
- Do not use the same env names for both testnet and live.
- Do not introduce a generic `EXCHANGE_API_KEY` alias now.
- Do not store values in repo files.
- Do not treat this naming decision as approval to add real credentials.

## 10. Recommended next bounded round

After this naming contract, the natural next round is:

```text
ORDER Testnet Executor Boundary V1
```

Scope:

- code and/or docs
- define the future real executor boundary under `ORDER`
- use canonical `TESTNET_EXCHANGE_*` names only
- no real key value
- no live trading

## 11. Acceptance for this contract

```text
canonical env names chosen: PASS
legacy BINANCE_* names downgraded to compatibility-only: PASS
mixing rule stated: PASS
testnet-only intent stated: PASS
base URL safety rule stated: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```
