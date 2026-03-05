#!/usr/bin/env bash
set -e

echo "phase313 verify start"

# Ensure policy_limits do not block phase311 step 5 (same key, different body → 409)
docker compose exec -T backend python -m app.system.risk_state_cli set policy_limits '{"max_single_trade_risk_usd":100}' 2>/dev/null || true
docker compose exec -T backend python -m app.system.risk_state_cli set risk_gate_global '{"enabled": false}' 2>/dev/null || true

bash ops/verify_phase311_idempotency_audit.sh
bash ops/verify_observability_loop.sh

echo "PASS: phase313 no regression"
