# Project Anchor Controlled Testnet Send Success Closeout V1

## Baseline

- Baseline HEAD: `9d8c2a0 Merge pull request #304 from baolood/codex/project-anchor-controlled-testnet-send-authorization-decision`
- Prior state: `CONTROLLED_TESTNET_SEND_AUTHORIZATION_DECISION_MERGED_RUNTIME_DISABLED`
- Authorization: `FINAL_OPERATOR_VERDICT=APPROVED_FOR_EXACTLY_ONE_CONTROLLED_TESTNET_SEND_ONLY`
- Authorized idempotency key: `testnet:ops_manual:BTCUSDT:BUY:4:first-bounded-request:v1`
- Fresh window: `2026-07-18T15:39:00Z` to `2026-07-18T16:39:00Z`

## Execution

- command: `scripts/one_shot_order_testnet_invocation.sh --execute`
- execution count: exactly one
- window time check: PASS
- guarded post branch: EXECUTE
- local POST attempted: YES
- local POST executed: YES
- automatic retry: NO
- command id: `order-a06eed8f-cd60-4a4f-b3e9-84c540b98e6f`

## Result

- command status: DONE
- attempt: 1
- execution mode: testnet
- market: binance_testnet
- host label: binance_futures_testnet
- external request started: YES
- external status: FILLED
- external order id present: YES
- external order id: `22553435057`
- error: null

## Event Chain

- PICKED
- POLICY_ALLOW
- KILL_SWITCH_CHECKED
- TESTNET_EXECUTOR_REQUESTED
- TESTNET_EXECUTOR_ACCEPTED
- ACTION_OK
- MARK_DONE

## Post-Execution Safety State

- kill switch enabled: false
- worker heartbeat alive after execution: YES
- secret values printed/disclosed: NO
- secret lengths/prefixes/suffixes/hashes printed: NO
- second send executed: NO
- automatic retry executed: NO
- canary executed: NO
- go-live: NO-GO
- live trading: NO-GO

## Final State

```text
CONTROLLED_TESTNET_SEND_SUCCESS_CLOSEOUT_RECORDED_TESTNET_FILLED_CANARY_NOT_EXECUTED
```

## Next Safe State

```text
READY_FOR_POST_CONTROLLED_TESTNET_SEND_RESULT_REVIEW
```
