# PF_XBTUSD funding accrual candidate

**DEPLOY=NO.** Live writer ingest is **off**. `official_sign_lock` stays `NO`.

This is a recording candidate for later use. It is not `eval_scoring.public_funding`, and it does not change that module.

## Two formulas, one of them locked

| Path | Formula | Used for C3 |
|------|---------|-------------|
| `eval_scoring/public_funding.py` | Absolute `fundingRate` times quantity times recorded contract size. Hold overlap is `[entry, exit)` against `[timestamp, timestamp+1h)`, prorated. `relativeFundingRate` is audit-only | Yes. This stays the Official reader |
| `eval_recording/funding/accrual.py` | `funding_pnl = -side_sign * position_notional_usd * Σ relativeFundingRate` for stamps `entry < T <= exit`. Long pays when the relative rate is positive | **No.** `selected_for_scoring=NO` |

Do not mix the two amounts. Do not average them.

## Status

| Status | When | Candidate amount | Writer `funding_pnl` |
|--------|------|------------------|----------------------|
| `PRESENT` | Every expected hour in the window is in the map | Sum, including a retrieved `0` | **null** (`live_funding_ingest=OFF`) |
| `PARTIAL` | At least one expected hour is missing | null | null |
| `MISSING` | None of the expected hours are present, or the window is empty | null | null |

`NET_PNL_STATUS` on the writer record stays `EX_FUNDING`. `NET_PNL_INCL_FUNDING` stays null. `NET_PNL_EX_FUNDING` is copied through only when the caller already has it.

`recording_funding_fields` is the entry a later writer can call. It has no environment switch. `LIVE_FUNDING_INGEST_ENABLED` is the constant `False`.

A missing hour is not stored as rate `0`. A rate that was actually `0` is `PRESENT` on the candidate and still null on the writer record.

## Public fetch

Manual script, public GET, no key:

```text
GET https://futures.kraken.com/derivatives/api/v3/historical-funding-rates?symbol=PF_XBTUSD
```

The unhyphenated `historicalfundingrates` path returned HTTP 404 on the 2026-10-23 check. The script does not invent prints for gaps. It writes `GAP` rows and a gap summary. The Official writer does not import the script.

```bash
cd /path/to/project-anchor
python3 -I eval_recording/funding/fetch_pf_xbtusd_funding.py --dry-run
```

`--out-dir` defaults to the script directory. A full JSONL from that command is a local cache, not a committed scoring book. The committed `eval_recording/funding/cache/PF_XBTUSD_gaps_summary.json` is only the gap map from the 2026-10-23 public response (8951 hourly prints, 8 missing hours, coverage `2025-10-15T08:00:00Z` through `2026-10-23T14:00:00Z`). Response SHA-256 `2d0cb86b817d66df60211a898968f6a55b9ea1144b05fdb20d216beb6cdd4dc1`.

## Tests

```bash
cd /path/to/project-anchor
export PYTHONPATH=.
python3 -m unittest tests.test_funding_accrual tests.test_equity_v21_dual_write tests.test_pass_line_recording_off
```

Fixtures: `eval_recording/funding/fixtures/accrual_present_12h.json`, `accrual_partial_gap_synthetic.json`, `accrual_missing_empty.json`.
