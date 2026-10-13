# Same-hour Official V2 ledger runs

Do not add `OnSuccess=anchor-official-ledger.service` to `project-anchor-jev-forward-shadow-v2.service`.

`anchor-official-ledger.service` is `Type=oneshot`. Its hourly timer also starts it at minute :10. A second start in that same hour appends another `PENDING_NEXT_BAR` row for an observation whose fill bar is still open. It is not a no-op, and it does not replace the row the first run wrote.

`BLOCKED.json` on the ledger root is a risk. A blocked run is not a clean retry: leaving that file in place can stop a later run, and deleting ledger bytes to clear it would rewrite history. Do not `chmod` or `setfacl` the StateDirectory.

The sealed entry point `/var/lib/anchor-official-ledger-20261010/cloud_official_once.py` is not in this checkout and is not edited. The run index below is the host `events.jsonl` shape this repository reads.

## Where the append time lives

Live ledger rows have no write-time field. `event_time`, `written_at`, and `recorded_at` on a ledger row are not the time the run appended it. A row names its id `ledger_event_id`, its hash `row_hash`, and its signal time `signal_available_at`.

`<ledger root>/events.jsonl` is one JSON object per line. A committed line is:

```json
{"at":"2026-10-12T23:10:01.432083+00:00","commits":366,"event":"committed","ledger_events":1015,"run_seq":70,"source_lines":370}
```

The run number is `run_seq`. `ledger_events` is the cumulative ledger-row count after that run. Run N owns ledger lines `(ledger_events of run N-1, ledger_events of run N]`. Run 1 owns `(0, ledger_events]`. A committed series that does not start at `run_seq` 1, or that skips a number, does not label pending rows. The matching directory is `runs/run-NNNNNN` (six digits). Its before-snapshot is `runs/run-NNNNNN/before/affl-v2-official-ledger/out/anchor_fake_fill_ledger_v2_official.jsonl`. The mirror reads that snapshot's last line only as a cross-check and does not copy it. `committed_at` in `run-boundaries.jsonl` is the `at` text from the matching committed line.

The fill bar is the next 1h bar after `signal_available_at`: the first hour that opens strictly after that timestamp. `10:05` opens `11:00` and closes `12:00`. `BAR_NOT_YET_CLOSED` means a later row resolves that bar and the earliest committed time is before the close. `DATA_GAP` means the pending was committed at or after that close, or the bar has closed and was never resolved. `IN_FLIGHT` means the observation is still unresolved and that close is still after the read clock.

`runs_waited` is the number of distinct runs that appended a `PENDING_NEXT_BAR` row, summed across observations. When a pending row cannot be placed in a run, the summary omits `BAR_NOT_YET_CLOSED`, `DATA_GAP`, and `IN_FLIGHT`, and `runs_waited` is the raw pending-row count.

`IN_FLIGHT` is an unresolved observation whose fill bar close (the first 1h open strictly after `signal_available_at`, plus one hour) is still after the read clock. That observation is not `DATA_GAP`.
