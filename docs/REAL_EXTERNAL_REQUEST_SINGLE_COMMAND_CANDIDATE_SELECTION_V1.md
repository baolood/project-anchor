# Real External Request Single Command Candidate Selection V1

## 1. Purpose

This artifact selects exactly one candidate command family for any future
bounded real external request.

It does not approve a final execution command. It only narrows the repo to one
candidate family so that a later implementation packet can fix one endpoint,
one payload, one command_id rule, and one evidence shape.

## 2. Current status

- candidate selection prepared: YES
- selected candidate family fixed: YES
- final execution command approved now: NO
- real external request authorized now: NO
- real external request sent now: NO
- canary executed now: NO
- go-live: NO-GO
- live trading: NO-GO

## 3. Selection result

The only selected candidate family is:

```text
canonical ORDER + execution_mode=testnet runtime-owned path
```

The candidate family is anchored to these repo-tracked surfaces:

- backend intake: `POST /trade-gate/dry-run-intents`
- backend command creation: `_create_domain_command("order", "ORDER", payload)`
- runtime boundary owner: `anchor-backend/app/actions/runner.py`
- executor boundary: `anchor-backend/app/executors/testnet_order_executor.py`
- canonical event family:
  - `TESTNET_EXECUTOR_REQUESTED`
  - `TESTNET_EXECUTOR_ACCEPTED`
  - `TESTNET_EXECUTOR_REJECTED`

## 4. Why this family was selected

This family is selected because repo evidence repeatedly fixes the canonical
future path as:

```text
ORDER + execution_mode=testnet
```

The selection is supported by:

- `docs/REAL_TESTNET_FIRST_EXTERNAL_EXECUTOR_PLAN_V1.md`
- `docs/REAL_TESTNET_FIRST_IMPLEMENTATION_SLICE_DECISION_V1.md`
- `docs/LEGACY_TESTNET_PATH_DECISION_V1.md`
- `anchor-backend/app/main.py`
- `anchor-console/app/api/trade-gate/dry-run-intents/route.ts`
- `anchor-backend/app/actions/runner.py`

This family preserves the properties that the blocked window exposed as
mandatory:

- runtime-owned evidence
- canonical command_id creation
- canonical `REQUESTED / ACCEPTED / REJECTED` event chain
- policy / kill switch / host-safety gating before any upstream request
- reviewable separation between preflight refusal and upstream attempt

## 5. Explicit rejections

### Rejected candidate A. Direct Binance shell scripts

Rejected examples:

- `binance_testnet_place_limit_ioc.sh`
- `place_test_order.sh`

These are rejected because they:

- call Binance testnet directly
- depend on direct shell secret access
- bypass canonical runtime evidence
- bypass canonical `ORDER:testnet` eventing
- bypass command creation and command review surfaces

They may remain as historical exploration artifacts, but they are not the
approved candidate family for the first bounded real external request.

### Rejected candidate B. Legacy QUOTE path

Rejected examples:

- `POST /domain-commands/quote`
- `anchor-console/app/api/proxy/commands/quote/route.ts`

This family is rejected because repo docs explicitly mark legacy
`QUOTE + BINANCE_TESTNET` as non-canonical for the future real request path.

It must not be reused as the main implementation for the first bounded real
external request.

### Rejected candidate C. Generic POST /commands as the final operator entry

`POST /commands` remains a valid repo surface for generic command intake and
audit work, but it is not selected here as the final bounded operator command.

Reason:

- this packet is choosing the canonical family for the first bounded real
  external request
- repo evidence for that family is fixed to `ORDER + execution_mode=testnet`
- the selected family already has a more specific runtime-owned intake path via
  `/trade-gate/dry-run-intents`

## 6. What is still intentionally not decided

This packet still does **not** approve:

- one final operator command string
- one final payload body
- one final command_id naming rule
- one final success evidence record
- one final blocked evidence record
- one final rollback or retreat command

Those must be fixed by a later implementation packet.

## 7. Required next artifact

The next required artifact is:

```text
Real External Request Single Command Implementation Packet
```

That packet must define exactly one:

- endpoint or script
- payload
- command_id rule
- success evidence shape
- blocked evidence shape
- rollback or retreat action

Until that packet exists, execution must remain blocked.

## 8. Explicit non-claims

- This packet does not approve a final execution command.
- This packet does not authorize a real external request.
- This packet does not send a real external request.
- This packet does not authorize canary execution.
- This packet does not authorize go-live.
- This packet does not authorize live trading.
