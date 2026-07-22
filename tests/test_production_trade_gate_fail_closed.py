import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "anchor-backend"))

from app.trade_gate_production import (  # noqa: E402
    PRODUCTION_COMMAND_TYPE,
    PRODUCTION_EXECUTION_GATE_REQUIRED_VERDICT,
    PRODUCTION_IDEMPOTENCY_KEY,
    PRODUCTION_REQUEST_SEND_GATE_REQUIRED_VERDICT,
    production_order_command_creation_candidate_response,
    production_order_command_creation_payload,
    production_order_send_decision_response,
    production_execution_gate_decision,
    production_order_blocked_response,
    production_request_send_gate_decision,
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
        self.assertFalse(payload["command_creation_candidate"])
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

    def test_request_send_gate_defaults_closed(self):
        decision = production_request_send_gate_decision(
            now=datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc)
        )

        self.assertFalse(decision["authorized"])
        self.assertEqual(decision["reason"], "PRODUCTION_REQUEST_SEND_GATE_CLOSED")
        self.assertFalse(decision["checks"]["request_send_authorized"])
        self.assertFalse(decision["go_live_allowed"])
        self.assertFalse(decision["live_trading_allowed"])

    def test_request_send_gate_accepts_exactly_one_window_without_go_live(self):
        decision = production_request_send_gate_decision(
            {
                "AUTHORIZED_PRODUCTION_REQUEST_SEND": "YES",
                "AUTHORIZED_PRODUCTION_CREDENTIAL_ACCESS": "YES",
                "AUTHORIZED_PRODUCTION_SIGNING": "YES",
                "AUTHORIZED_PRODUCTION_HTTP_NETWORK": "YES",
                "AUTHORIZED_GO_LIVE": "NO",
                "AUTHORIZED_LIVE_TRADING": "NO",
                "PRODUCTION_REQUEST_SEND_WINDOW_OPEN": True,
                "PRODUCTION_REQUEST_SEND_WINDOW_EXPIRES_AT": "2026-07-22T09:00:00Z",
                "PRODUCTION_REQUEST_SEND_NO_RETRY": True,
                "PRODUCTION_REQUEST_SEND_IDEMPOTENCY_KEY": PRODUCTION_IDEMPOTENCY_KEY,
                "FINAL_PRODUCTION_REQUEST_SEND_OPERATOR_VERDICT": (
                    PRODUCTION_REQUEST_SEND_GATE_REQUIRED_VERDICT
                ),
            },
            now=datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc),
        )

        self.assertTrue(decision["authorized"])
        self.assertEqual(decision["reason"], "AUTHORIZED")
        self.assertTrue(decision["checks"]["production_http_network_authorized"])
        self.assertTrue(decision["checks"]["go_live_not_authorized"])
        self.assertTrue(decision["checks"]["live_trading_not_authorized"])
        self.assertFalse(decision["go_live_allowed"])
        self.assertFalse(decision["live_trading_allowed"])

    def test_request_send_gate_rejects_expired_window(self):
        decision = production_request_send_gate_decision(
            {
                "AUTHORIZED_PRODUCTION_REQUEST_SEND": "YES",
                "AUTHORIZED_PRODUCTION_CREDENTIAL_ACCESS": "YES",
                "AUTHORIZED_PRODUCTION_SIGNING": "YES",
                "AUTHORIZED_PRODUCTION_HTTP_NETWORK": "YES",
                "AUTHORIZED_GO_LIVE": "NO",
                "AUTHORIZED_LIVE_TRADING": "NO",
                "PRODUCTION_REQUEST_SEND_WINDOW_OPEN": True,
                "PRODUCTION_REQUEST_SEND_WINDOW_EXPIRES_AT": "2026-07-22T07:59:59Z",
                "PRODUCTION_REQUEST_SEND_NO_RETRY": True,
                "PRODUCTION_REQUEST_SEND_IDEMPOTENCY_KEY": PRODUCTION_IDEMPOTENCY_KEY,
                "FINAL_PRODUCTION_REQUEST_SEND_OPERATOR_VERDICT": (
                    PRODUCTION_REQUEST_SEND_GATE_REQUIRED_VERDICT
                ),
            },
            now=datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc),
        )

        self.assertFalse(decision["authorized"])
        self.assertFalse(decision["checks"]["window_not_expired"])

    def test_request_send_gate_rejects_go_live_or_live_trading(self):
        decision = production_request_send_gate_decision(
            {
                "AUTHORIZED_PRODUCTION_REQUEST_SEND": "YES",
                "AUTHORIZED_PRODUCTION_CREDENTIAL_ACCESS": "YES",
                "AUTHORIZED_PRODUCTION_SIGNING": "YES",
                "AUTHORIZED_PRODUCTION_HTTP_NETWORK": "YES",
                "AUTHORIZED_GO_LIVE": "YES",
                "AUTHORIZED_LIVE_TRADING": "YES",
                "PRODUCTION_REQUEST_SEND_WINDOW_OPEN": True,
                "PRODUCTION_REQUEST_SEND_WINDOW_EXPIRES_AT": "2026-07-22T09:00:00Z",
                "PRODUCTION_REQUEST_SEND_NO_RETRY": True,
                "PRODUCTION_REQUEST_SEND_IDEMPOTENCY_KEY": PRODUCTION_IDEMPOTENCY_KEY,
                "FINAL_PRODUCTION_REQUEST_SEND_OPERATOR_VERDICT": (
                    PRODUCTION_REQUEST_SEND_GATE_REQUIRED_VERDICT
                ),
            },
            now=datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc),
        )

        self.assertFalse(decision["authorized"])
        self.assertFalse(decision["checks"]["go_live_not_authorized"])
        self.assertFalse(decision["checks"]["live_trading_not_authorized"])

    def test_send_decision_response_blocks_when_gate_closed(self):
        response = production_order_send_decision_response(
            _valid_production_body(),
            production_request_send_gate_decision(
                now=datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc)
            ),
        )

        self.assertEqual(response["status"], "blocked")
        self.assertFalse(response["ready_for_exactly_one_send"])
        self.assertFalse(response["request_send_gate_authorized"])
        self.assertFalse(response["production_request_sent"])
        self.assertFalse(response["production_signing_executed"])
        self.assertFalse(response["production_http_network_executed"])

    def test_send_decision_response_ready_never_sends_by_itself(self):
        gate = production_request_send_gate_decision(
            {
                "AUTHORIZED_PRODUCTION_REQUEST_SEND": "YES",
                "AUTHORIZED_PRODUCTION_CREDENTIAL_ACCESS": "YES",
                "AUTHORIZED_PRODUCTION_SIGNING": "YES",
                "AUTHORIZED_PRODUCTION_HTTP_NETWORK": "YES",
                "AUTHORIZED_GO_LIVE": "NO",
                "AUTHORIZED_LIVE_TRADING": "NO",
                "PRODUCTION_REQUEST_SEND_WINDOW_OPEN": True,
                "PRODUCTION_REQUEST_SEND_WINDOW_EXPIRES_AT": "2026-07-22T09:00:00Z",
                "PRODUCTION_REQUEST_SEND_NO_RETRY": True,
                "PRODUCTION_REQUEST_SEND_IDEMPOTENCY_KEY": PRODUCTION_IDEMPOTENCY_KEY,
                "FINAL_PRODUCTION_REQUEST_SEND_OPERATOR_VERDICT": (
                    PRODUCTION_REQUEST_SEND_GATE_REQUIRED_VERDICT
                ),
            },
            now=datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc),
        )

        response = production_order_send_decision_response(_valid_production_body(), gate)

        self.assertEqual(response["status"], "ready_for_exactly_one_send")
        self.assertTrue(response["ready_for_exactly_one_send"])
        self.assertTrue(response["request_send_gate_authorized"])
        self.assertFalse(response["production_request_sent"])
        self.assertFalse(response["production_signing_executed"])
        self.assertFalse(response["production_http_network_executed"])
        self.assertFalse(response["go_live_allowed"])
        self.assertFalse(response["live_trading_allowed"])
        self.assertNotIn("api_key", str(response))
        self.assertNotIn("api_secret", str(response))

    def test_command_creation_payload_is_non_secret_and_not_sendable(self):
        payload = production_order_command_creation_payload(_valid_production_body())

        self.assertEqual(payload["command_type"], PRODUCTION_COMMAND_TYPE)
        self.assertEqual(payload["execution_mode"], "production")
        self.assertEqual(payload["market"], "binance_spot")
        self.assertEqual(payload["symbol"], "BTCUSDT")
        self.assertEqual(payload["side"], "BUY")
        self.assertEqual(payload["notional"], 4.0)
        self.assertTrue(payload["command_creation_only"])
        self.assertFalse(payload["production_signing_executed"])
        self.assertFalse(payload["production_http_network_executed"])
        self.assertFalse(payload["production_request_sent"])
        self.assertNotIn("api_key", payload)
        self.assertNotIn("api_secret", payload)
        self.assertNotIn("secret", payload)

    def test_authorized_gate_only_produces_command_creation_candidate(self):
        response = production_order_command_creation_candidate_response(
            _valid_production_body(),
            production_execution_gate_decision(
                {
                    "PRODUCTION_EXECUTION_GATE_ENABLED": True,
                    "PRODUCTION_EXACTLY_ONE_COMMAND_CREATION": True,
                    "PRODUCTION_NO_RETRY": True,
                    "PRODUCTION_IDEMPOTENCY_KEY": PRODUCTION_IDEMPOTENCY_KEY,
                    "FINAL_OPERATOR_VERDICT": PRODUCTION_EXECUTION_GATE_REQUIRED_VERDICT,
                }
            ),
        )

        self.assertEqual(response["status"], "ready_to_create_command")
        self.assertEqual(response["command_type"], PRODUCTION_COMMAND_TYPE)
        self.assertTrue(response["command_creation_candidate"])
        self.assertFalse(response["command_created"])
        self.assertFalse(response["production_request_sent"])
        self.assertTrue(response["execution_gate_authorized"])
        self.assertNotIn("command_id", response)
        self.assertEqual(response["payload"]["idempotency_key"], PRODUCTION_IDEMPOTENCY_KEY)

    def test_closed_gate_does_not_produce_command_creation_candidate(self):
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
