# Equity v2.1 dual-write

**Default: OFF.** **DEPLOY=NO.**

Helper: `eval_recording/equity_v21_dual_write.py`.

## File

| File | Role |
|------|------|
| `anchor_fake_fill_equity_v2_1_official.csv` | Only write target, and only when the flag is on |
| `anchor_fake_fill_equity_v2_official.csv` | Legacy. Tagged `LEGACY_HEADER_MISMATCH`. Never opened for write |

The helper also refuses any path whose parts include `affl-v2-official-ledger`, and it refuses a symlink that resolves to the legacy filename. An existing file with the new name but an old header is left unchanged.

## Flag

| Input | Result |
|-------|--------|
| Caller passes `enabled=False` | Off, even if the env var or CLI flag is set |
| `AFFL_EQUITY_V21_DUAL_WRITE` unset, empty, or not `1` | Off |
| `AFFL_EQUITY_V21_DUAL_WRITE=1` | On |
| argv contains `--equity-v21-dual-write` | On, when the caller passes that argv |

Off does not create the new file. Nothing in `local_box`, `anchor-backend`, `scripts`, `risk_engine`, `shared`, or `eval_scoring` calls the helper.

## 13-column header

Genesis uses the same columns as every later row. There is no 6-column seed.

```text
schema_version,timestamp_utc,observation_id,position,realized_pnl,unrealized_pnl,net_liquidation_equity,drawdown,exposure,cash_reserve,active_notional,mark_rule_id,sample_class
```

| Column | Rule |
|--------|------|
| `schema_version` | `equity_v2_1` on every row |
| `mark_rule_id` | `MARK_RULE_C7_V1` when that rule is bound. Otherwise `UNBOUND` or empty. The helper does not default this to `MARK_RULE_C7_V1` |
| `sample_class` | Caller-supplied. Synthetic rows in tests use `NON_SCORING` |
| Genesis | `observation_id=LEDGER_GENESIS`, `position=FLAT` |

A new file is born with the header plus one genesis row. Later calls append. A second genesis row is refused. Header width and body width are both 13.

## Scoring view

`eval_recording/equity_schema.py` reads this 13-column file. `project_scoring_view` adds `trade_id`, `equity_at_open`, `mark_kind`, and `mark_honesty_label` in memory. The view id is `equity_v2_1_view`. Those fields are not written into `anchor_fake_fill_equity_v2_1_official.csv`.

This helper does not score drawdown and does not rewrite historical Line A rows into the new file. Host enablement stays off.
