# Reconciliation: 2026-08-05 BLOCKED attempt and 2026-08-06 FILLED attempt

The second manual low-frequency production request ran twice. The reports that were already committed are the earlier attempt. The later fill was left uncommitted until this archive.

## Committed reports are the 2026-08-05 attempt

These files are unchanged. This note does not edit them, so their hashes stay the hashes of the copies already in git:

- `reports/next_manual_low_frequency_production_send_result.json`
- `reports/next_manual_low_frequency_production_send_result.md`
- `reports/next_manual_operation_eligibility.json`
- `reports/next_manual_operation_eligibility.md`

The send result was generated at `2026-08-05T11:00:56Z` on Darwin. Result `BLOCKED`. Failure code `NEXT_MANUAL_PRODUCTION_SEND_EXECUTION_NOT_REQUESTED`. The execution-host contract was not compliant because that machine was not the whitelisted host. The eligibility report beside it was generated at `2026-08-05T09:48:59Z`.

A pointer with the same statement sits next to those reports: `reports/next_manual_low_frequency_2026-08-05_blocked_attempt.md`.

## 2026-08-06 cloud run returned PASS / FILLED

A second run at `2026-08-06T03:26:55Z` on the cloud host returned `PASS` / `FILLED` for the same idempotency key:

`production:ops_manual:BTCUSDT:BUY:10:next-manual-low-frequency-request:v1`

Redacted copies of that worktree bundle are in `pass-reports/`. The send result records a Binance spot market buy, quote quantity 10, external status `FILLED`, HTTP 200. The redacted exchange note records the fill as 0.00015 BTC at 64530 (quote 9.67950000) at `2026-08-06T03:26:55.385Z`. Order and trade identifiers stay placeholders (`<ORDER_2>`, `<CLIENT_ORDER_2>`, `<TRADE_2>`). The same note records the earlier 2026-07-30 fill (0.00015 BTC at 65038.72) as the other BTCUSDT order under that key. This archive does not replace `reports/production_exactly_one_send_result.json`.

The 2026-08-06 eligibility report differs from the committed 2026-08-05 eligibility report in `generated_at` (`2026-08-06T03:26:55Z`) and `hours_since_last_production_request` (`157.57` versus `139.93`).

`exchange-facts-binance-BTCUSDT.json` keeps placeholders in place and is not strict JSON. `guardian-excerpt-2026-08-06T0325-0327Z.redacted.json` is the guardian window `2026-08-06T03:25:00Z` through `2026-08-06T03:27:30Z`.

## Authorization chain is only partially verified

The guardian excerpt is important evidence. It records approval requests and guardian `allow` outcomes for a pre-send eligibility check and for one capped BTCUSDT BUY with no retry and no second request. The original user authorization message has not been found. The authorization chain is only partially verified. This note does not claim that the chain is fully verified.

## Hashes

Unredacted originals stay off-repo. Their SHA-256 values are in `UNREDACTED_ORIGINAL_SHA256.txt`. SHA-256 of the redacted files committed here:

| Redacted file | SHA-256 |
| --- | --- |
| `pass-reports/next_manual_low_frequency_production_send_result.json` | `74b2090d24081d60a17c3a3d119735d01187e79774bb9cfbffb382b04f8c1fef` |
| `pass-reports/next_manual_low_frequency_production_send_result.md` | `aa8ebe045d6f018f695e635eac21f53265c1953f49c58bce1d9b5e9a6c91e519` |
| `pass-reports/next_manual_operation_eligibility.json` | `c63507aa8c92583058955d8ba568a68cda9d090ff3f31f19a18832db72d4f4ed` (same as the unredacted original) |
| `pass-reports/next_manual_operation_eligibility.md` | `aeb2908849fd26d88f3ffd775bd74e60257ee21df686b7fb7b68636ea01b54ea` (same as the unredacted original) |
| `guardian-excerpt-2026-08-06T0325-0327Z.redacted.json` | `af85f69d5021afde20373e2f930b45e3bc3df4cb721f8c0fa864dcac630ce6b1` |
| `exchange-facts-binance-BTCUSDT.json` | `62751ae7dd003f21d087d68906277b4b823ad2c9ccea07ecd911792b5cb700fc` |

The committed guardian file also replaces a local working-directory path with `<ADMIN_HOME>`. That is why its hash differs from both the unredacted original and the earlier redacted stage copy. Placeholders are not restored.
