# Annotation: these reports are the 2026-08-05 BLOCKED attempt

The four reports below are unchanged. Do not rewrite them; their hashes are the hashes of the copies already in git.

- `reports/next_manual_low_frequency_production_send_result.json` (`b99226eee3434545bf1b7f4f93de924c639be3a4ff1e7665ad281e93347c9a3e`)
- `reports/next_manual_low_frequency_production_send_result.md` (`08c5f45bfb4b83f5295fe16efc27d4fdc937d07908c5d268fb2fc7b119302591`)
- `reports/next_manual_operation_eligibility.json` (`0392322c674f9d5f3c3e4378cad9a02d6531521daf4459a0145197726d0a1b4f`)
- `reports/next_manual_operation_eligibility.md` (`8f878bc0488ddfb360bce28d5f39c25e9617ba04b369406a6cc37b970af8df76`)

They correspond to the earlier attempt, not the 2026-08-06 fill:

- send result generated at `2026-08-05T11:00:56Z` on Darwin, result `BLOCKED`, because that host was not whitelisted
- eligibility generated at `2026-08-05T09:48:59Z`

The later cloud run at `2026-08-06T03:26:55Z` returned `PASS` / `FILLED` and was not committed with these files. Redacted copies and the reconciliation, including the unredacted-original SHA-256 values, are in `evidence/archive/2026-08-06-binance-btc-fill/`.

The guardian approval log for that later run is important evidence, and the original user authorization message has not been found. The authorization chain is only partially verified.
