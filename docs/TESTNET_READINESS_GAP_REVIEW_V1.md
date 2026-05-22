# Testnet readiness gap review V1

**Status:** gap review only — not a testnet enablement, not live trading approval.

**Owner:** **baolood** (Release / Engineering / Operations lead, interim).

**Date:** 2026-05-22

**Current posture:** dry-run main chain is validated and repeatable, but testnet and live trading remain **NO-GO**.

```text
/trade-gate
-> Next same-origin proxy
-> SSH tunnel
-> cloud backend
-> commands_domain
-> domain_command_worker
-> risk
-> DONE / FAILED
```

## 1. Decision

Project Anchor is ready for **testnet readiness planning**, but not ready to connect testnet credentials or execute testnet orders.

The next safe phase is:

```text
dry-run repeatability
-> testnet contract/design review
-> testnet credential custody plan
-> testnet-only executor implementation
-> testnet smoke with kill switch ON/OFF evidence
-> tiny-live go/no-go review
```

Do not skip from dry-run to live trading.

## 2. What is already strong enough

| Area | Current evidence | Readiness |
|------|------------------|-----------|
| Trade Gate frontend | `/trade-gate` submits dry-run intent through same-origin proxy | PASS for dry-run |
| Backend intake | `POST /trade-gate/dry-run-intents` returns `command_id` | PASS for dry-run |
| Command chain | `commands_domain` -> worker -> risk produces `DONE` / `FAILED` | PASS for dry-run |
| Risk hard limits | Unsafe notional blocked with `RISK_HARD_LIMITS` | PASS |
| Repeatability | `scripts/checklist_trade_gate_dry_run_e2e.sh` and `docs/DRY_RUN_SMOKE_RUNBOOK_V1.md` | PASS |
| Command detail review | `/ops -> /commands -> /commands/[id]` review path exists | PASS for dry-run |
| CI guardrail | `local-box-baseline` green on latest dry-run docs/scripts | PASS |

## 3. Hard blockers before testnet

| Blocker | Why it matters | Minimum next action |
|---------|----------------|---------------------|
| No approved testnet execution contract | Current execution-service code is archived draft and `execute_testnet` is `TESTNET-MOCK` | Write a new testnet command contract before code |
| No credential custody plan | Testnet API keys still need least-privilege storage, rotation, and no-plaintext rules | Complete a testnet-only row in `docs/SECRETS_AND_ROTATION.md` or a linked design |
| Kill switch not tied to testnet path | Testnet must prove commands stop before any external call | Run or extend kill-switch smoke against the planned executor boundary |
| Stage/prod-like target not locked | Go-live checklist says the shared target host is the convergence point | Record target facts in `docs/ENVIRONMENT_PARITY_CHECKLIST.md` §5 |
| R-001 remains OPEN | Admin bypass can push to `main` without PR-only discipline | Decide and apply `enforce_admins` + PR-only, or keep NO-GO |
| R-002 remains OPEN | Local Python drift means local claims are weaker than CI | Align local Python to CI 3.11+ and rerun baseline/smokes |

## 4. Design gaps to close before code

### 4.1 Command contract

Define a testnet command that cannot be confused with dry-run or live:

```text
execution_mode: testnet
market: <exchange-testnet-name>
asset: BTCUSDT
side: BUY | SELL
notional: decimal string
order_type: market | limit
risk_snapshot_id: optional
source: trade_gate_v1 | ops_manual
idempotency_key: required
```

Acceptance:

- `execution_mode=testnet` is required.
- `execution_mode=live` is rejected until a separate go-live review closes.
- Missing `idempotency_key` is rejected.
- Commands remain inspectable through `/commands/[id]`.

### 4.2 Executor boundary

Testnet execution must be a separate boundary from dry-run command intake.

Minimum expected behavior:

- Worker validates risk before executor call.
- Kill switch is checked immediately before executor call.
- External client is testnet-only by configuration.
- Response is persisted as command events.
- Any network/API failure marks command `FAILED` with a useful error.

### 4.3 Secrets and permissions

Before any testnet key is used:

- Store it outside git.
- Scope it to testnet only.
- Disable withdrawal permissions.
- Record owner, storage location, and rotation path.
- Add a no-plaintext scan step to the testnet smoke evidence.

### 4.4 Observability

Testnet smoke must produce enough evidence to answer:

- Was the command picked?
- Did risk allow or block it?
- Was kill switch checked?
- Was a testnet-only executor called?
- Was the external response recorded?
- Did the command end in `DONE` or `FAILED` with a clear reason?

## 5. Proposed next implementation sequence

Do these as separate bounded rounds:

1. **Testnet Command Contract V1** — docs only, define payload, rejection rules, command events, and no-live guarantee.
2. **Testnet Secrets Custody V1** — docs only, define where testnet keys live and how they rotate.
3. **Testnet Executor Stub V1** — code, but no external API call; prove worker boundary and eventing.
4. **Testnet Client Wiring V1** — code, testnet-only client with environment guardrails and no withdrawal scope.
5. **Testnet Smoke Script V1** — script proves `DONE`/`FAILED`, kill switch behavior, and command detail evidence.
6. **Tiny Live Readiness Review V1** — docs only; live remains `NO-GO` unless hard gates close.

## 6. What not to do

- Do not put testnet or live API keys in `.env` files committed to git.
- Do not reuse archived `execution_service` draft as production code without a new contract.
- Do not remap order commands to quote commands to make worker status look green.
- Do not weaken risk hard limits to force `DONE`.
- Do not expose the cloud backend publicly just for convenience.
- Do not close R-001 or R-002 without the evidence required in `docs/GO_LIVE_CHECKLIST.md` §6 / §9.
- Do not interpret CI green as live approval.

## 7. Acceptance for this review

This document is accepted when:

```text
dry-run main chain acknowledged: PASS
testnet remains NO-GO: PASS
live trading remains NO-GO: PASS
hard blockers listed: PASS
next bounded rounds listed: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
```

## 8. Next single task

Recommended next task:

```text
Testnet Command Contract V1
```

Scope:

- docs only
- define command payload and event contract
- explicitly reject `execution_mode=live`
- no API key
- no backend / worker / risk implementation yet

Exit criteria:

```text
contract file created: PASS
testnet-only semantics: PASS
live rejected by contract: PASS
idempotency defined: PASS
command detail evidence path defined: PASS
live trading: NO-GO
```
