import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "anchor-backend"))

from app.trade_gate_production import (  # noqa: E402
    PRODUCTION_COMMAND_CREATED_STATUS,
    PRODUCTION_COMMAND_TYPE,
    PRODUCTION_EXECUTION_GATE_REQUIRED_VERDICT,
    PRODUCTION_IDEMPOTENCY_KEY,
    is_worker_executable_command_status,
    production_order_command_creation_candidate_response,
    production_execution_gate_decision,
)


def _valid_production_body(**overrides):
    body = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "notional": 4,
        "order_type": "market",
        "execution_mode": "production",
        "market": "binance_spot",
        "source": "ops_manual",
        "idempotency_key": PRODUCTION_IDEMPOTENCY_KEY,
    }
    body.update(overrides)
    return body


def _authorized_gate_decision():
    return production_execution_gate_decision(
        {
            "PRODUCTION_EXECUTION_GATE_ENABLED": True,
            "PRODUCTION_EXACTLY_ONE_COMMAND_CREATION": True,
            "PRODUCTION_NO_RETRY": True,
            "PRODUCTION_IDEMPOTENCY_KEY": PRODUCTION_IDEMPOTENCY_KEY,
            "FINAL_OPERATOR_VERDICT": PRODUCTION_EXECUTION_GATE_REQUIRED_VERDICT,
        }
    )


class ProductionCommandCreationPersistenceTest(unittest.TestCase):
    def test_created_status_is_not_worker_executable(self):
        self.assertFalse(
            is_worker_executable_command_status(PRODUCTION_COMMAND_CREATED_STATUS)
        )
        self.assertTrue(is_worker_executable_command_status("PENDING"))
        self.assertTrue(is_worker_executable_command_status("RUNNING"))

    def test_authorized_candidate_is_ready_for_non_executable_persistence(self):
        response = production_order_command_creation_candidate_response(
            _valid_production_body(),
            _authorized_gate_decision(),
        )

        self.assertEqual(response["status"], "ready_to_create_command")
        self.assertEqual(response["command_type"], PRODUCTION_COMMAND_TYPE)
        self.assertTrue(response["command_creation_candidate"])
        self.assertFalse(response["command_created"])
        self.assertFalse(response["production_request_sent"])
        self.assertFalse(
            is_worker_executable_command_status(PRODUCTION_COMMAND_CREATED_STATUS)
        )
        self.assertTrue(response["payload"]["command_creation_only"])
        self.assertFalse(response["payload"]["production_request_sent"])
        self.assertNotIn("api_key", response["payload"])
        self.assertNotIn("api_secret", response["payload"])

    def test_closed_gate_is_not_ready_for_persistence(self):
        response = production_order_command_creation_candidate_response(
            _valid_production_body(),
            production_execution_gate_decision(),
        )

        self.assertEqual(response["status"], "blocked")
        self.assertFalse(response["command_creation_candidate"])
        self.assertFalse(response["command_created"])
        self.assertFalse(response["production_request_sent"])
        self.assertNotIn("command_id", response)


if __name__ == "__main__":
    unittest.main()
