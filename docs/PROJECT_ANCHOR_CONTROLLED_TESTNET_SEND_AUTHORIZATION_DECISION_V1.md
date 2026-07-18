# Project Anchor Controlled Testnet Send Authorization Decision V1

## Baseline

- Baseline HEAD: `880e536 Merge pull request #303 from baolood/codex/project-anchor-one-shot-testnet-dry-run-evidence`
- Prior state: `ONE_SHOT_TESTNET_DRY_RUN_EVIDENCE_MERGED_RUNTIME_DISABLED`
- Trigger: operator asked to continue after the one-shot ORDER:testnet dry-run evidence merged

## Decision Result

- controlled testnet send decision reviewed: YES
- second bounded preflight PASS evidence available: YES
- one-shot dry-run evidence available: YES
- controlled send runbook available: YES
- readiness evidence sufficient to request a fresh bounded send window: YES
- generic continuation wording accepted as exactly-one send authorization: NO
- fresh bounded operator authorization window required before any POST: YES

## Required Fresh Send Authorization Shape

A future controlled testnet send authorization must explicitly include all of the following:

- authorized action: exactly one controlled ORDER:testnet send
- authorized execution window: fresh, current, and bounded
- authorized idempotency key: explicit
- allowed command surface: explicit
- POST authorization: YES_FOR_EXACTLY_ONE_CONTROLLED_TESTNET_SEND_ONLY
- secret disclosure: NO
- automatic retry: NO
- canary: NO
- go-live/live trading: NO-GO
- final operator verdict: explicit approval for exactly one controlled testnet send

If any required field is missing, ambiguous, expired, or reused, execution remains blocked.

## Boundary

- POST executed in this task: NO
- real external request sent: NO
- canary executed: NO
- runtime path enabled by this decision: NO
- real signing executed: NO
- real HTTP/network attempted: NO
- secret values read/disclosed: NO
- go-live: NO-GO
- live trading: NO-GO

## Final State

```text
CONTROLLED_TESTNET_SEND_AUTHORIZATION_DECISION_RECORDED_RUNTIME_DISABLED
```

## Next Safe State

```text
WAITING_FOR_FRESH_BOUNDED_CONTROLLED_TESTNET_SEND_AUTHORIZATION_WINDOW
```
