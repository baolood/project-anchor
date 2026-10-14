# ANCHOR_EVAL_RECORDING_INFRA_SPEC_V1

**Doc ID:** `ANCHOR_EVAL_RECORDING_INFRA_SPEC_V1`  
**Gate:** **B** — parallel recording infrastructure. **Not** the scoring chain.  
**Status:** spec + scaffolding only. `FORMAL_SCORING_CHAIN=NOT_ON_FORMAL_SCORING_CHAIN` until the Founder says so.  
**Scaffolding:** `eval_recording/` (no HTTP, no Official ledger writes).

This document does **not** freeze T0, does **not** score Official PnL / profit factor / drawdown, does **not** modify legacy Official ledger files, does **not** deploy production, does **not** enable live trading, and does **not** change PASS LINE C1–C10 thresholds.

Wire-up into the Official writer is a later **Founder EXECUTE**. Until that order, readers keep `NET_PNL_STATUS=EX_FUNDING` wherever funding is absent, and they keep the legacy equity CSV as a historical artifact.

## 1. Coordination with the C6 risk-boundary PR

C6 Protective Risk Boundary work is a **separate branch and a separate PR**. It owns ex-ante stop fields and any future edits under `affl-causal-successor/affl_v2/`.

This Gate B change does **not** create or edit those files (`EDITS_AFFL_V2_TYPES=NO`).

| Name | Owner | Rule |
|------|--------|------|
| `preset_stop_price`, `stop_rule_id`, `risk_amount`, `risk_pct`, `HARD_STOP_EXIT` | C6 | Not defined and not invented here |
| `trade_id` (`tr_` + entry `ledger_event_id`) | Gate B scheme | If C6 also touches a shared struct, add `trade_id` as an **optional** field (default unset) behind version gate `recording_v1` |
| `equity_at_open` | Gate B column on the **new** equity file | C6 may copy the same semantic onto an entry event. That copy must not rewrite the legacy equity CSV or this v2.1 header |
| Funding completeness, `MARK_RULE_C7_V1`, C9 source paths | Gate B | Stay out of the C6 stop struct |

`eval_recording.trade_id.RecordingOptionalFields` is the typed additive carrier (`recording_schema_version`, `trade_id`, `trade_id_hash`). It is not `LedgerEvent` and it is not a risk struct. Older schema versions ignore a stray `trade_id`.

## 2. Real funding ingest

### 2.1 Source

Official Fake-Fill stays on public market data. The design target for `PF_XBTUSD` is:

```text
GET https://futures.kraken.com/derivatives/api/v3/historicalfundingrates?symbol=PF_XBTUSD
```

Auth: **none**. Private account funding and private fills stay forbidden while trading locks remain NO. Invented or constant funding is forbidden.

Public docs currently describe the same payload under the hyphenated slug `historical-funding-rates` (`HistoricalFundingRateJson`: `timestamp`, `fundingRate`, `relativeFundingRate`). Founder EXECUTE must record which live URL returned that object before any cache is appended. This package's request plan has `execute=NO` and performs no fetch.

`fundingRate` is the absolute rate (Kraken: the amount a one-contract short receives for that period). `relativeFundingRate` is the absolute rate relative to spot at calculation time. They are not interchangeable. This spec does **not** lock which one becomes the scored series.

### 2.2 Status, never zero-fill

For each closed hold, the expected set is every funding-period timestamp in `(entry_fill_time, exit_fill_time]`.

| `FUNDING_DATA_STATUS` | Meaning | `funding_pnl` | `NET_PNL_STATUS` |
|------------------------|---------|---------------|------------------|
| `NO_INTERVAL` | Expected set is empty | null | `EX_FUNDING` |
| `MISSING` | No expected timestamp was retrieved | null | `EX_FUNDING` |
| `PARTIAL` | Some expected timestamps were retrieved | null | `EX_FUNDING` |
| `PRESENT` | Every expected timestamp has both rate fields | null while `OFFICIAL_SIGN_LOCK=NO` | `EX_FUNDING` until the sign lock |

A retrieved rate of `0` is a real zero and counts as retrieved. A missing row, a null field, or a gap is **not** stored as `0`. Partial covers are not summed into a claimed net. `NET_PNL_EX_FUNDING` stays as the parallel diagnostic and is not deleted.

`NET_PNL_INCL_FUNDING` is produced only by `resolve_recorded_net` when `FUNDING_DATA_STATUS=PRESENT` **and** `sign_lock=YES`, as `NET_PNL_EX_FUNDING + funding_pnl`. That function still labels the result `not_a_score=True` and `formal_scoring_chain=NOT_ON_FORMAL_SCORING_CHAIN`. Gate B ships `OFFICIAL_SIGN_LOCK=NO`, so the Official path remains `EX_FUNDING`.

### 2.3 Candidate accrual (not selected)

When coverage is `PRESENT`, scaffolding may attach two **unselected** candidates. `selected_for_net_pnl` stays null.

1. `ABSOLUTE_PER_CONTRACT_SHORT_RECEIVES` — short adds `fundingRate * quantity_contracts`; long adds the negation.
2. `RELATIVE_RATE_TIMES_NOTIONAL_LONG_PAYS_WHEN_POSITIVE` — long adds `-relativeFundingRate * position_notional`; short adds the negation. This matches the readiness sketch and is still not the scored series.

Future cache (not created here), append-only, with fetch time and response hash:

```text
affl-v2-official-ledger/funding/PF_XBTUSD_historicalfundingrates.jsonl
```

Field list: `eval_recording/schemas/funding_rate_cache.SCHEMA.json`.

## 3. Equity file `equity_v2_1`

### 3.1 Leave the legacy file alone

| Artifact | Role |
|----------|------|
| `anchor_fake_fill_equity_v2_official.csv` | Legacy. Header/body mismatch (6-column header, 6-column genesis, 10-column engine rows). **Do not rewrite.** |
| `anchor_fake_fill_equity_v2_1_official.csv` | New file. One header width for genesis and every later row. |

Legacy headers, rejected by the v2.1 reader:

```text
timestamp_utc,equity,realized_pnl,unrealized_pnl,position,event
timestamp_utc,observation_id,position,realized_pnl,unrealized_pnl,net_liquidation_equity,drawdown,exposure,cash_reserve,active_notional
```

The scaffolding writer refuses that legacy filename and refuses any path that contains `affl-v2-official-ledger`. Dual-write of a new file under the Official tree is Founder EXECUTE, not this PR.

### 3.2 Header

`schema_version` is `equity_v2_1` on every row. Companion description: `eval_recording/schemas/anchor_fake_fill_equity_v2_1_official.SCHEMA.json`.

<!-- EQUITY_V2_1_HEADER_BEGIN -->
schema_version,timestamp_utc,observation_id,trade_id,position,realized_pnl,unrealized_pnl,net_liquidation_equity,equity_at_open,drawdown,exposure,cash_reserve,active_notional,mark_rule_id,mark_kind,mark_honesty_label,sample_class
<!-- EQUITY_V2_1_HEADER_END -->

| Column | Rule |
|--------|------|
| `schema_version` | Constant `equity_v2_1` |
| `timestamp_utc` | ISO-8601 UTC |
| `observation_id` | Linked sample; genesis uses `LEDGER_GENESIS` |
| `trade_id` | `tr_` + entry `ledger_event_id` while a leg is referenced; empty when no leg |
| `position` | `FLAT` / `LONG` / `SHORT` |
| `realized_pnl` … `active_notional` | Same economics as today's `EquityPoint`, carried as text. This spec does not grade them |
| `equity_at_open` | Net liquidation equity at the entry fill of `trade_id`. **Required when `trade_id` is set. Empty when `trade_id` is empty.** Not a stop and not `risk_amount` |
| `mark_rule_id` | `MARK_RULE_C7_V1` |
| `mark_kind` | `GENESIS`, `BAR_1H`, `FILL`, or `OHLC_ADVERSE_PROXY` |
| `mark_honesty_label` | `RECORDED_MARK`, or `NOT_TICK_LOW` on the OHLC proxy only |
| `sample_class` | `FORWARD_LIVE_SHADOW` |

`equity_at_open` is the additive column the preflight found missing as a literal. The readiness 13-column draft did not name it; v2.1 does, and also names `trade_id`, `mark_kind`, and `mark_honesty_label` so C7 can label the optional proxy without overloading an old column.

Genesis uses this same header. It does not use a 6-column seed. `equity_at_open` and `trade_id` are empty on genesis. The starting `net_liquidation_equity` is copied from ledger genesis at Founder EXECUTE; the helper does not hard-code it.

## 4. `trade_id`

```text
trade_id = "tr_" + entry_ledger_event_id
```

Example shape: entry `ledger_event_id=le-000007` ⇒ `trade_id=tr_le-000007`.

1. `OPEN` and `REVERSE_ENTRY` set `trade_id` from **that** event's `ledger_event_id` and hold it on the open leg.
2. `FLAT_EXIT` and `REVERSE_EXIT` copy the held id. They do not mint.
3. `REVERSE_ENTRY` is valid only after the previous leg has been cleared by its exit. The new leg gets a new id.
4. Other event types do not mint and do not clear the held id.
5. Do not key the id on `observation_id` or on array index. Exit observation is not entry observation.
6. Optional `trade_id_hash = sha256(LEDGER_GENESIS_ID + "|" + entry_ledger_event_id)` sits beside the id. The id itself stays the `tr_` form.
7. Readers treat `trade_id` as authoritative only when `recording_schema_version=recording_v1`.

Future C2 counting of distinct `trade_id` is out of scope here. This spec does not count trades and does not score.

## 5. MARK_RULE_C7_V1

Canonical text (also `eval_recording.mark_rule.MARK_RULE_C7_V1_TEXT`):

<!-- MARK_RULE_C7_V1_BEGIN -->
MARK_RULE_C7_V1 (honest sampling). For Official equity used in C5/C7: (1) Required marks: at least 1 equity sample per completed 1h bar while the Official account is open or flat-after-genesis, and one mark at each Official fill (OPEN, FLAT_EXIT, REVERSE_EXIT, REVERSE_ENTRY). (2) Primary day_low is the minimum of recorded Official equity marks on that CST day. T0 and partial-day rules stay as already written in the pass line; this rule does not change them. (3) Optional conservative intrabar proxy, labeled: if the Founder enables it, for each 1h bar while a position is open, also emit a mark using that bar's OHLC adverse extreme (LONG uses the bar low, SHORT uses the bar high) converted with the same unrealized formula. Those rows use mark_kind=OHLC_ADVERSE_PROXY and mark_honesty_label=NOT_TICK_LOW, and they are not tick-low and not an exchange mark-price low. (4) Forbidden claim: calling an OHLC adverse extreme or a 1h close the true intraday tick minimum. (5) Until this rule is implemented and equity v2.1 is the scoring path, C7 stays CONDITIONAL. This text is not on the formal scoring chain until the Founder says so.
<!-- MARK_RULE_C7_V1_END -->

Cadence helpers in `eval_recording.mark_rule` report missing bar ids and missing fill ids. An `OHLC_ADVERSE_PROXY` row does **not** satisfy the required bar or fill mark. The helpers do not compute day-low percentages.

## 6. C9 authoritative sources

C9 counters (unauthorized privilege, live-order attempt, ledger tamper, risk-gate bypass) are **not** columns on the trade ledger. The binding list is paths. `in_trade_ledger` is false on every entry in `eval_recording.c9_sources`.

Repo paths below exist in this checkout. Host paths are operational locations from the readiness inventory; this PR does not read or write them. The pass-line document is listed as the future authorization source and is **not** edited here, so its C1–C10 threshold text stays untouched.

### 6.1 Audit

| Source id | Path |
|-----------|------|
| `audit_go_live_checklist` | `docs/GO_LIVE_CHECKLIST.md` |
| `audit_recording_spec` | `docs/ANCHOR_EVAL_RECORDING_INFRA_SPEC_V1.md` |
| `audit_host_reports` | `/var/lib/project-anchor/reports/` |
| `audit_evidence_reporter` | `/var/lib/project-anchor/evidence-reporter-v1/` |
| `audit_jev_authoritative_samples` | `/var/lib/project-anchor/jev-forward-shadow-v2/jev-forward-authoritative-v2.jsonl` |

### 6.2 Kill-switch

| Source id | Path |
|-----------|------|
| `kill_switch_boundary_doc` | `docs/KILL_SWITCH_REAL_BOUNDARY_CHECK_V1.md` |
| `kill_switch_mcp_doc` | `anchor-backend/docs/ANCHOR_CONTROL_MCP_V1.md` |
| `kill_switch_host_sidecar_doc` | `anchor-backend/docs/ANCHOR_CONTROL_MCP_HOST_SIDECAR_V1.md` |

### 6.3 Deploy

| Source id | Path |
|-----------|------|
| `deploy_host_checkout` | `/opt/project-anchor/project-anchor` |
| `deploy_mcp_systemd_unit` | `/etc/systemd/system/anchor-control-mcp.service` |
| `deploy_mcp_nginx_snippet` | `/etc/nginx/snippets/anchor-control-mcp.conf` |

### 6.4 Authorization

| Source id | Path |
|-----------|------|
| `authorization_ledger_genesis` | `affl-v2-official-ledger/genesis/LEDGER_GENESIS.json` |
| `authorization_ledger_state` | `AFFL_V2_OFFICIAL_LEDGER_STATE.json` |
| `authorization_mcp_deploy_report` | `ANCHOR_CONTROL_MCP_V1_DEPLOY_REPORT.md` |
| `authorization_mcp_inventory` | `ANCHOR_CONTROL_MCP_V1_Production_Deployment_Inventory.md` |
| `authorization_pass_line_doc` | `PROJECT_ANCHOR_OFFICIAL_EVALUATION_PASS_LINE_V1.md` |

### 6.5 Proposed register (not created)

```text
affl-v2-official-ledger/governance/C9_INCIDENT_REGISTER.jsonl
```

Append-only incident rows, including a future daily `ATTEST_ZERO`, belong in that register after Founder EXECUTE. They do not belong on trade events. This PR does not create the file.

## 7. Founder EXECUTE, still later

1. Confirm the live public funding URL and lock one sign convention against a known public row. Until that lock, scored net stays `EX_FUNDING`.
2. Append the funding cache. Do not zero-fill gaps. Switch a **future** scorer to `NET_PNL_INCL_FUNDING` only for `PRESENT` windows after the lock.
3. Dual-write `anchor_fake_fill_equity_v2_1_official.csv` going forward. Do not rewrite the legacy 6/10-column CSV.
4. Persist optional `trade_id` on entry and exit events behind `recording_v1`, without taking ownership of C6 stop fields.
5. Enforce `MARK_RULE_C7_V1` in the writer. Keep the OHLC proxy labeled `NOT_TICK_LOW`.
6. Sample the C9 paths into the incident register. Do not add those counters to the trade ledger.
7. Only a separate Founder order can put any of the above on the formal scoring chain.

## 8. What this PR ships

| Path | Role |
|------|------|
| `docs/ANCHOR_EVAL_RECORDING_INFRA_SPEC_V1.md` | This spec |
| `eval_recording/` | Pure contracts, schemas, one synthetic funding fixture |
| `tests/test_eval_recording_infra_v1.py` | Locks the contracts, including the refusal to score |

Runtime packages (`local_box`, `anchor-backend`, `scripts`, `risk_engine`, `shared`) do not import `eval_recording`. No production service changes. `LIVE_TRADING=NO`. `PRODUCTION_DEPLOY=NO`. `T0_FROZEN=NO`. `PASS_LINE_THRESHOLDS_CHANGED=NO`.
