# Annotation: historical monitoring snapshot check names

`reports/post_production_monitoring_snapshot.json` and `reports/post_production_monitoring_snapshot.md` are unchanged historical output from `2026-07-31T04:09:17Z`.

Those files still contain checks named `exactly_one_order_confirmed` and `no_new_or_second_request` with result `PASS`. Those checks counted orders and boundary flags stored in repository reports. They were not a fresh exchange reconciliation.

Current code labels those counts as repo-recorded. Exchange confirmation stays a separate field and is `UNKNOWN` unless an offline reconciliation file is supplied. When the repo-recorded checks pass and exchange confirmation is `UNKNOWN`, the snapshot top-level `result` is `PASS_REPO_RECORDED_ONLY` and `status` is `MONITORING_REPO_RECORDED_ONLY_CONTINUOUS_TRADING_DISABLED`. That is not a plain `PASS`. The process exit code stays 0, and the monitoring runner keeps its alert `CLEAR` with severity `none` so this state does not page.

A plain snapshot `result` of `PASS` with status `MONITORING_READY_CONTINUOUS_TRADING_DISABLED` is used only when the offline reconciliation file confirms the exchange checks. Exchange disagreement or an unreadable supplied file is `BLOCKED` and does page.

The read-only MCP observation projection renames the historical check names, reports `exchange_confirmed_order_status: UNKNOWN` for this snapshot, and projects the observation `result` as `PASS_REPO_RECORDED_ONLY` even though the historical file still says `PASS`. `run_readonly_healthcheck` treats `PASS_REPO_RECORDED_ONLY` as a healthy observation. It does not alert.

`scripts/review_post_production_24h_stability.py` (also used for the 48h and 72h windows) treats both `PASS` and `PASS_REPO_RECORDED_ONLY` as a repo-level `monitoring_snapshot_pass`. Exchange confirmation is a separate evidence field, `exchange_confirmed_order_status`, and stays `UNKNOWN` unless that snapshot records an offline reconciliation file. `UNKNOWN` does not block the review. `FAIL` does. Historical check names `exactly_one_order_confirmed` and `no_new_or_second_request` are not read as exchange confirmation. Regenerating the snapshot on the host is a separate deploy step. The historical JSON and Markdown files in this directory stay byte-unchanged.
