# Go-live daily snapshots

Local standup evidence from [`scripts/go_live_status_report.sh`](../../scripts/go_live_status_report.sh).

- **Naming:** `go_live_daily_status_YYYY-MM-DD.out`
- **Process:** [`docs/GO_LIVE_CHECKLIST.md`](../../docs/GO_LIVE_CHECKLIST.md) §7
- **`*.out` files** are gitignored at the repo root; this file is the tracked pointer for the directory.
- **`--out` paths:** the reporter runs `mkdir -p` on the parent directory of `--out` before writing (you may still `mkdir -p artifacts/go-live` explicitly).
- **CI:** the reporter runs as a smoke step in [`local-box-baseline.yml`](../../.github/workflows/local-box-baseline.yml) (job **check**); each job declares **`timeout-minutes`** caps in that workflow.
