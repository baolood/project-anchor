# Official evaluation recording status

**DEPLOY=NO.** This package does not deploy, does not change Vultr, and does not move money.

It adds default-off helpers for a later recording series. It is not a score, not a signature, and not a freeze.

## Freeze

PASS LINE V1.1 is already frozen in `docs/PROJECT_ANCHOR_PASS_LINE_V1_1_FREEZE_RECORD.md` (`T0_FROZEN=YES`, T0 `2026-10-22T20:27:21+08:00`). This change does not edit that record, the sign-off page, or the final draft.

This package does **not** freeze PASS LINE. It does not sign §9 again and it does not open a new freeze. Host wire, equity dual-write enablement, and live funding ingest stay unauthorized. Those gates remain blocked.

## What landed

| Piece | Where | State |
|-------|--------|--------|
| Equity v2.1 dual-write | `eval_recording/equity_v21_dual_write.py` | **OFF** unless `AFFL_EQUITY_V21_DUAL_WRITE=1` or `--equity-v21-dual-write` |
| Relative-rate accrual candidate | `eval_recording/funding/accrual.py` plus fixtures | Computes `PRESENT` only when the hold is complete. Not selected for scoring |
| Writer adapter | `eval_recording/funding/recording.py` | `funding_pnl` stays null. `NET_PNL_STATUS` stays `EX_FUNDING` |
| Public fetch script | `eval_recording/funding/fetch_pf_xbtusd_funding.py` | Manual only. No private API |
| Gap map from the 2026-10-23 public fetch | `eval_recording/funding/cache/PF_XBTUSD_gaps_summary.json` | 7 gap spans, 8 missing hours. Not a rate cache |
| C9 template | `docs/pass-line/templates/C9_INCIDENT_REGISTER.jsonl` | Empty. Not read by `eval_scoring` |

## Intentionally off

- No host EXECUTE and no `--c6-local-root` change.
- No rewrite of Line A, sealed ledger StateDirectory, or `anchor_fake_fill_equity_v2_official.csv`.
- No live `funding_pnl` on the writer. No zero-fill of missing prints.
- No PASS LINE freeze and no C1–C10 threshold edit.
- No carry/basis work.
- Gate A PR #417 and Gate B PR #416 are not merged here.

## Header note

The on-disk equity file stays the 13-column header in `EQUITY_V21_DUAL_WRITE.md`. The 17 names from the Gate B draft (`trade_id`, `equity_at_open`, `mark_kind`, `mark_honesty_label`, and the shared columns) are the in-memory view `equity_v2_1_view` in `eval_recording/equity_schema.py`. That view is not a second file and not a second `schema_version`. Host enablement stays unauthorized. `DEPLOY=NO`.

## Scoring note

`eval_scoring/public_funding.py` remains the locked Official funding reader (`EXTERNAL_PUBLIC_FUNDING_V1`, absolute `fundingRate` per contract). The accrual module here is a separate relative-rate candidate (`relativeFundingRate` times notional). It is not imported by the scorer.

*DEPLOY=NO. No scores.*
