# Project Anchor — Risk Core Runbook

## Daily Mode (default)

### Start (backend + worker)

With `docker-compose.override.yml` present, worker picks up daily defaults; no manual env needed:
```bash
cd /Users/baolood/Projects/project-anchor/anchor-backend
docker compose up -d --build
docker compose stop worker 2>/dev/null || true
sleep 2
docker compose up -d worker
```

Without override, use explicit env (see Extreme Mode for override bypass):
```bash
CAPITAL_USD=1000 MAX_SINGLE_TRADE_RISK_PCT=0.5 MAX_NET_EXPOSURE_PCT=30 MAX_LEVERAGE=5 MAX_DAILY_DRAWDOWN_PCT=3 \
RISK_HARD_LIMITS_DISABLE=0 RISK_EXPOSURE_ATOMIC=1 docker compose up -d worker
```

## Extreme Mode (stress test)

### Enter extreme
```bash
cd /Users/baolood/Projects/project-anchor
BASE="http://127.0.0.1:8000" CAPITAL_USD=1000 ./scripts/extreme_mode_run.sh
```

### Or step-by-step
```bash
cd anchor-backend
docker compose stop worker
sleep 2
CAPITAL_USD=1000 MAX_SINGLE_TRADE_RISK_PCT=100 MAX_NET_EXPOSURE_PCT=30 \
RISK_HARD_LIMITS_DISABLE=0 RISK_EXPOSURE_ATOMIC=1 \
docker compose up -d worker
```

## Parent repo — `local_box` (Python + SQLite)

For the **parent repository** `local_box` audit stack (not Docker `anchor-backend`):

1. **Install Python deps** (from repo root):

   ```bash
   cd /path/to/project-anchor
   python3 -m pip install -r requirements.txt
   ```

2. **SQLite path** (`local_box/audit/event_store.py`):

   - **Default:** `<repo-root>/anchor.db` (resolved from `local_box/audit/event_store.py`, not machine-specific).
   - **Override:** set **`LOCAL_BOX_DB_PATH`** to an absolute path or `~`-expanded path if the default location is not writable.

   ```bash
   export LOCAL_BOX_DB_PATH="$PWD/tmp/local_box_ci.db"
   mkdir -p tmp
   ```

3. **Import smoke** (optional, after `pip install`):

   ```bash
   export PYTHONPATH=.
   python3 -c "from local_box.audit import event_store; event_store.init_db(); print('ok', event_store.DB_PATH)"
   python3 -c "import local_box.runner; print('runner import ok')"
   ```

4. **CI:** workflow **`.github/workflows/local-box-baseline.yml`** runs `pip install -r requirements.txt`, `./scripts/check_local_box_baseline.sh`, then SQLite **`init_db()`** smoke, then **`import local_box.runner`** (covers **`shared`**, **`risk_engine.client`**, **`local_box.gate.ticket_signature`**).

## Verify

### Full E2E (default: EXTREME skipped)
```bash
cd /Users/baolood/Projects/project-anchor
./scripts/release_up_and_verify.sh
```

### With EXTREME gate
```bash
EXTREME_MODE_E2E=1 ./scripts/release_up_and_verify.sh
```

### Risk hard limits only
```bash
./scripts/checklist_risk_hard_limits_e2e.sh
```

## Reset

### Reset exposure + clean pending
```bash
curl -s -X POST http://127.0.0.1:8000/ops/dev/reset-pending-domain-commands
cd /Users/baolood/Projects/project-anchor/anchor-backend
docker compose exec -T postgres psql -U anchor -d anchor -c \
  "UPDATE risk_state SET current_exposure_usd=0, updated_at=NOW() WHERE id=1;"
```

## Tag Release (固化 daily env + 验证 + 打 tag)

```bash
cd /Users/baolood/Projects/project-anchor
./scripts/risk_core_tag_release.sh
```

生成 `docker-compose.override.yml`，执行 release 验证，打 `risk-core-v2` 并推送。

## Evidence (paths)

- `/tmp/anchor_risk_core_tag_head.out`
- `/tmp/anchor_e2e_release_after_daily_default_env.out`
- `/tmp/anchor_e2e_release_up_and_verify_last.out`
- `/tmp/anchor_e2e_verify_all_release.out`
- `/tmp/anchor_e2e_index_last.out`
- `/tmp/anchor_e2e_checklist_extreme_mode_e2e_last.out`
- `/tmp/anchor_extreme_outcome_last.out`
- `/tmp/anchor_extreme_risk_state_last.json`
- `/tmp/anchor_extreme_daily_smoke_last.out`
- `/tmp/anchor_e2e_checklist_risk_hard_limits_e2e_last.out`
