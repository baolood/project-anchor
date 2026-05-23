import os
from typing import Any, Dict, Optional, Tuple


def run_real_testnet_order_request(
    transport_input: Dict[str, Any],
    now_ts: int,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], Optional[str], Optional[Dict[str, Any]]]:
    host_label = str(transport_input.get("host_label") or "")
    configured_origin = str(transport_input.get("configured_origin") or "")
    canonical_path = str(transport_input.get("canonical_path") or "ORDER:testnet")
    common = {
        "type": "ORDER",
        "attempt": int(transport_input.get("attempt") or 0),
        "execution_mode": "testnet",
        "host_label": host_label,
        "configured_origin": configured_origin,
        "canonical_path": canonical_path,
        "executor_mode_label": "real",
        "timeout_policy_label": "single_attempt_v1",
    }
    real_wire_enabled = (str(os.getenv("TESTNET_EXECUTOR_REAL_ENABLE") or "").strip() == "1")
    if not real_wire_enabled:
        return (
            {
                "ok": False,
                "result": None,
                "error": {
                    "code": "TESTNET_REAL_WIRE_DISABLED",
                    "failure_family": "TESTNET_REAL_WIRE_DISABLED",
                    "gate": "executor_boundary",
                    "external_request_started": False,
                    "external_order_id_present": False,
                    "execution_mode": "testnet",
                    "host_label": host_label,
                    "configured_origin": configured_origin,
                    "canonical_path": canonical_path,
                    "executor_mode_label": "real",
                    "timeout_policy_label": "single_attempt_v1",
                },
            },
            None,
            None,
            None,
        )

    return (
        {
            "ok": False,
            "result": None,
            "error": {
                "code": "TESTNET_REAL_WIRE_NOT_IMPLEMENTED",
                "failure_family": "TESTNET_REAL_WIRE_NOT_IMPLEMENTED",
                "gate": "executor_boundary",
                "external_request_started": False,
                "external_order_id_present": False,
                "execution_mode": "testnet",
                "host_label": host_label,
                "configured_origin": configured_origin,
                "canonical_path": canonical_path,
                "executor_mode_label": "real",
                "timeout_policy_label": "single_attempt_v1",
                "ts": now_ts,
            },
        },
        None,
        None,
        None,
    )
