# feat(ops): Ops Dashboard UI + list_retry E2E fix

## Summary

- Ops Dashboard: `/ops` page, state proxy, heartbeat/panic/kill_switch display, 5s auto-refresh
- E2E: `ops_dashboard_ui_e2e` (SSR/CSR compatible via API checks), `checklist_ops_dashboard_ui_e2e`
- Fix: `list_retry_ui_e2e` FINAL_NOT_DONE — relax pass condition when worker is fast (PASS when `FINAL_STATUS_AFTER_RETRY=DONE`)

## E2E Evidence (bb1f990)

```
./scripts/release_up_and_verify.sh exit 0
PASS_OR_FAIL=PASS
OPS_DASHBOARD_UI_E2E_PASS=YES
LIST_RETRY_UI_E2E_PASS=YES
CHECKLIST_OPS_DASHBOARD_UI_OUT=/tmp/anchor_e2e_checklist_ops_dashboard_ui_e2e_last.out
CHECKLIST_LIST_RETRY_UI_OUT=/tmp/anchor_e2e_checklist_list_retry_ui_e2e_last.out
```

### Full template (from /tmp/anchor_e2e_merge_summary.out)

```
==== E2E EVIDENCE ====
DATE=2026-02-12T20:59:23+08:00
PARENT_HEAD=bb1f990
---- release ----
MODULE=verify_all_e2e
LIST_RETRY_UI_E2E_PASS=YES
OPS_DASHBOARD_UI_E2E_PASS=YES
PASS_OR_FAIL=PASS
FAIL_REASON=
---- index ----
CHECKLIST_LIST_RETRY_UI_OUT=/tmp/anchor_e2e_checklist_list_retry_ui_e2e_last.out
CHECKLIST_OPS_DASHBOARD_UI_OUT=/tmp/anchor_e2e_checklist_ops_dashboard_ui_e2e_last.out
```

## Base / Compare

- **base:** main (or master)
- **compare:** feature/ops-console-minimal
