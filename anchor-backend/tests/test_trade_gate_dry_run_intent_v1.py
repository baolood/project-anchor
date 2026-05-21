import unittest
from unittest.mock import AsyncMock, patch

from app.main import (
    _build_trade_gate_dry_run_payload,
    _validate_trade_gate_dry_run_request,
    create_trade_gate_dry_run_intent,
)


class TradeGateDryRunIntentV1Test(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.valid_body = {
            "asset": "BTC",
            "direction": "BUY",
            "hypothetical_notional": 150,
            "entry_reason": "Breakout retest with defined invalidation.",
            "exit_plan": "If BTC breaks below 68500, or loss reaches 3%, exit simulation.",
            "emotional_state": "calm",
            "gate_decision": "SIMULATE_ONLY",
            "gate_evaluated_at": "2026-05-21T04:00:00Z",
            "source": "trade_gate_v1",
            "stop_loss": 68500,
        }

    def test_validate_pause_rejected(self) -> None:
        ok, reason = _validate_trade_gate_dry_run_request(
            {**self.valid_body, "gate_decision": "PAUSE"}
        )

        self.assertFalse(ok)
        self.assertEqual(reason, "GATE_PAUSE")

    def test_build_payload_enforces_dry_run(self) -> None:
        payload = _build_trade_gate_dry_run_payload(
            {**self.valid_body, "execution_mode": "live"}
        )

        self.assertEqual(payload["symbol"], "BTCUSDT")
        self.assertEqual(payload["side"], "BUY")
        self.assertEqual(payload["execution_mode"], "dry_run")
        self.assertEqual(payload["gate_decision"], "SIMULATE_ONLY")
        self.assertEqual(payload["notional"], 150.0)
        self.assertEqual(payload["notional_usd"], 150.0)
        self.assertNotIn("api_key", payload)

    def test_forbidden_api_key_rejected(self) -> None:
        ok, reason = _validate_trade_gate_dry_run_request(
            {**self.valid_body, "api_key": "should-not-be-here"}
        )

        self.assertFalse(ok)
        self.assertEqual(reason, "FORBIDDEN_FIELD:api_key")

    async def test_pause_returns_error_without_enqueue(self) -> None:
        with patch("app.main._create_domain_command", new_callable=AsyncMock) as create_mock:
            response = await create_trade_gate_dry_run_intent(
                {**self.valid_body, "gate_decision": "PAUSE"}
            )

        self.assertEqual(response, {"status": "error", "error": "GATE_PAUSE"})
        create_mock.assert_not_awaited()

    async def test_simulate_only_creates_order_command(self) -> None:
        with patch(
            "app.main._create_domain_command",
            new=AsyncMock(return_value={"id": "order-123", "status": "PENDING"}),
        ) as create_mock:
            response = await create_trade_gate_dry_run_intent(self.valid_body)

        self.assertEqual(response, {"status": "ok", "command_id": "order-123"})
        create_mock.assert_awaited_once()
        args = create_mock.await_args.args
        self.assertEqual(args[0], "order")
        self.assertEqual(args[1], "ORDER")
        self.assertEqual(args[2]["execution_mode"], "dry_run")
        self.assertEqual(args[2]["gate_decision"], "SIMULATE_ONLY")
        self.assertEqual(args[2]["symbol"], "BTCUSDT")
        self.assertEqual(args[2]["stop_loss"], 68500.0)


if __name__ == "__main__":
    unittest.main()
