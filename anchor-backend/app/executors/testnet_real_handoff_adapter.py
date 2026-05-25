from __future__ import annotations

import os
from typing import Any, Dict, Mapping, Optional


_CANONICAL_KEYS = (
    "TESTNET_EXCHANGE_BASE_URL",
    "TESTNET_EXCHANGE_API_KEY",
    "TESTNET_EXCHANGE_API_SECRET",
    "TESTNET_EXCHANGE_KEY_ID",
    "TESTNET_EXECUTOR_MODE",
    "TESTNET_EXECUTOR_REAL_ENABLE",
)


def _env_value(env: Mapping[str, str], key: str) -> str:
    return str(env.get(key) or "").strip()


def _is_present(value: str) -> bool:
    return bool(value)


def build_real_handoff_runtime_snapshot(
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    source_env = env or os.environ
    base_url = _env_value(source_env, "TESTNET_EXCHANGE_BASE_URL")
    executor_mode = _env_value(source_env, "TESTNET_EXECUTOR_MODE").lower()
    real_enable = _env_value(source_env, "TESTNET_EXECUTOR_REAL_ENABLE")
    api_key = _env_value(source_env, "TESTNET_EXCHANGE_API_KEY")
    api_secret = _env_value(source_env, "TESTNET_EXCHANGE_API_SECRET")
    key_id = _env_value(source_env, "TESTNET_EXCHANGE_KEY_ID")

    blocked_reasons = []
    if not base_url:
        blocked_reasons.append("base_url_missing")
    if executor_mode != "mock":
        blocked_reasons.append("executor_mode_not_mock")
    if real_enable != "0":
        blocked_reasons.append("real_enable_not_zero")

    return {
        "type": "real_credential_handoff_runtime_snapshot",
        "canonical_keys": list(_CANONICAL_KEYS),
        "configured_origin": base_url,
        "executor_mode": executor_mode,
        "real_enable": real_enable,
        "api_key_present": _is_present(api_key),
        "api_secret_present": _is_present(api_secret),
        "key_id_present": _is_present(key_id),
        "credential_free_mock_posture": (
            executor_mode == "mock"
            and real_enable == "0"
            and not api_key
            and not api_secret
            and not key_id
        ),
        "blocked_reasons": blocked_reasons,
    }


def build_real_handoff_adapter_skeleton(
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    snapshot = build_real_handoff_runtime_snapshot(env)
    return {
        "type": "real_credential_handoff_adapter_skeleton",
        "phase": "planning_ready_runtime_slice",
        "allows_runtime_mutation": False,
        "allows_external_request": False,
        "allows_live_trading": False,
        "future_handoff_keys": [
            "TESTNET_EXCHANGE_API_KEY",
            "TESTNET_EXCHANGE_API_SECRET",
            "TESTNET_EXCHANGE_KEY_ID",
        ],
        "current_runtime": snapshot,
        "task_opening_allowed": bool(snapshot["credential_free_mock_posture"]),
    }
