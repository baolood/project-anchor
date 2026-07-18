# Project Anchor One-Shot Testnet Dry-Run Evidence V1

## Baseline

- Baseline HEAD: `8f78520 Merge pull request #302 from baolood/codex/project-anchor-post-preflight-result-review`
- Prior state: `POST_PREFLIGHT_RESULT_REVIEW_MERGED_RUNTIME_DISABLED`
- Purpose: record one guarded ORDER:testnet dry-run evidence item after second bounded preflight PASS

## Command

```text
bash scripts/one_shot_order_testnet_invocation.sh --fixture valid-window-dry
```

## Result

```text
WINDOW_TIME_CHECK=PASS
INVOCATION_SURFACE=POST http://127.0.0.1:8000/trade-gate/testnet-order-intents
POST_ATTEMPTED=NO
GUARDED_POST_BRANCH=DRY_RUN
POST_EXECUTED=NO
```

## Boundary

- POST executed: NO
- external request sent: NO
- canary executed: NO
- runtime path enabled by this evidence: NO
- real signing executed: NO
- real HTTP/network attempted: NO
- secret values read/disclosed: NO
- go-live: NO-GO
- live trading: NO-GO

## Final State

```text
ONE_SHOT_TESTNET_DRY_RUN_EVIDENCE_RECORDED_RUNTIME_DISABLED
```

## Next Safe State

```text
READY_FOR_EXPLICIT_CONTROLLED_TESTNET_SEND_AUTHORIZATION_DECISION
```
