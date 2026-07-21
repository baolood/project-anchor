import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "anchor-backend"))

from app.trade_gate_production import (  # noqa: E402
    PRODUCTION_EXECUTION_GATE_REQUIRED_VERDICT,
    PRODUCTION_IDEMPOTENCY_KEY,
    production_execution_gate_decision,
    production_order_blocked_response,
    validate_production_order_request,
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


class ProductionTradeGateFailClosedTest(unittest.TestCase):
    def test_valid_production_shape_is_accepted_by_validator(self):
        ok, reason = validate_production_order_request(_valid_production_body())

        self.assertTrue(ok)
        self.assertIsNone(reason)

    def test_production_validator_rejects_unbounded_notional(self):
        ok, reason = validate_production_order_request(
            _valid_production_body(notional=5)
        )

        self.assertFalse(ok)
        self.assertEqual(reason, "PRODUCTION_NOTIONAL_INVALID")

    def test_production_validator_rejects_wrong_idempotency_key(self):
        ok, reason = validate_production_order_request(
            _valid_production_body(idempotency_key="production:unexpected")
        )

        self.assertFalse(ok)
        self.assertEqual(reason, "PRODUCTION_IDEMPOTENCY_KEY_INVALID")

    def test_production_validator_rejects_secret_fields(self):
        ok, reason = validate_production_order_request(
            _valid_production_body(api_secret="do-not-log")
        )

        self.assertFalse(ok)
        self.assertEqual(reason, "FORBIDDEN_FIELD:api_secret")

    def test_blocked_response_never_contains_command_id(self):
        payload = production_order_blocked_response()

        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["error"], "PRODUCTION_EXECUTION_GATE_CLOSED")
        self.assertFalse(payload["command_created"])
        self.assertFalse(payload["production_request_sent"])
        self.assertTrue(payload["requires_explicit_execution_gate"])
        self.assertFalse(payload["execution_gate_authorized"])
        self.assertEqual(payload["idempotency_key"], PRODUCTION_IDEMPOTENCY_KEY)
        self.assertNotIn("command_id", payload)

    def test_execution_gate_defaults_closed(self):
        decision = production_execution_gate_decision()

        self.assertFalse(decision["authorized"])
        self.assertEqual(decision["reason"], "PRODUCTION_EXECUTION_GATE_CLOSED")
        self.assertFalse(decision["checks"]["gate_enabled"])

    def test_execution_gate_rejects_partial_config(self):
        decision = production_execution_gate_decision(
            {
                "PRODUCTION_EXECUTION_GATE_ENABLED": True,
                "PRODUCTION_IDEMPOTENCY_KEY": PRODUCTION_IDEMPOTENCY_KEY,
            }
        )

        self.assertFalse(decision["authorized"])
        self.assertFalse(decision["checks"]["exactly_one_command_creation"])
        self.assertFalse(decision["checks"]["operator_verdict_matches"])

    def test_execution_gate_accepts_complete_non_send_command_creation_config(self):
        decision = production_execution_gate_decision(
            {
                "PRODUCTION_EXECUTION_GATE_ENABLED": True,
                "PRODUCTION_EXACTLY_ONE_COMMAND_CREATION": True,
                "PRODUCTION_NO_RETRY": True,
                "PRODUCTION_IDEMPOTENCY_KEY": PRODUCTION_IDEMPOTENCY_KEY,
                "FINAL_OPERATOR_VERDICT": PRODUCTION_EXECUTION_GATE_REQUIRED_VERDICT,
            }
        )

        self.assertTrue(decision["authorized"])
        self.assertEqual(decision["reason"], "AUTHORIZED")


if __name__ == "__main__":
    unittest.main()
