# Same-hour Official V2 ledger runs

Do not add `OnSuccess=anchor-official-ledger.service` to `project-anchor-jev-forward-shadow-v2.service`.

`anchor-official-ledger.service` is `Type=oneshot`. Its hourly timer also starts it at minute :10. A second start in that same hour appends another `PENDING_NEXT_BAR` row for an observation whose fill bar is still open. It is not a no-op, and it does not replace the row the first run wrote.

`BLOCKED.json` on the ledger root is a risk. A blocked run is not a clean retry: leaving that file in place can stop a later run, and deleting ledger bytes to clear it would rewrite history. Do not `chmod` or `setfacl` the StateDirectory.

The sealed entry point `/var/lib/anchor-official-ledger-20261010/cloud_official_once.py` is not in this checkout and is not edited. The run index below is the structure this repository can actually read.

## Where the append time lives

Live ledger rows have no write-time field. `event_time`, `written_at`, and `recorded_at` on a ledger row are not the time the run appended it.

`simulation/d5/original/cloud-package/cloud_loop.py` function `event()` appends one JSON object per line to `<root>/events.jsonl` (`json.dumps(..., sort_keys=True)`). A finished generation is:

```python
event(root, "committed", round_index=index, round_id=ids[-1],
      next_due=control["next_due"], status=control["status"])
```

That line has `event` = `committed`, timestamp `at`, and integer `round_index`. `run_index` is accepted the same way when a line uses that key instead. The Official V2 root names the matching directory `runs/run-NNNNNN` (six digits). Host snapshots already live at `runs/<name>/before/anchor_fake_fill_ledger_v2_official.jsonl`. The mirror reads the last line of that before-snapshot and does not copy the snapshot. `committed_at` in `run-boundaries.jsonl` is the `at` text from the matching committed line.

`runs_waited` is the number of distinct runs that appended a `PENDING_NEXT_BAR` row, summed across observations. When a pending row cannot be placed in a run, the summary omits `BAR_NOT_YET_CLOSED`, `DATA_GAP`, and `IN_FLIGHT`, and `runs_waited` is the raw pending-row count.

`IN_FLIGHT` is an unresolved observation whose fill bar close (the first 1h open strictly after `signal_available_at`, plus one hour) is still after the read clock. That observation is not `DATA_GAP`.
