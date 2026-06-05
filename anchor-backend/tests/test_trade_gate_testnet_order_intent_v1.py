import unittest
from unittest.mock import AsyncMock, patch

from app.main import (
    _build_trade_gate_testnet_order_payload,
    _validate_trade_gate_testnet_order_request,
    create_trade_gate_testnet_order_intent,
)


class TradeGateTestnetOrderIntentV1Test(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.valid_body = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "notional": 4,
            "stop_price": 68000,
            "order_type": "market",
            "created_by": "baolood",
            "idempotency_key": "testnet:ops_manual:BTCUSDT:BUY:4:endpoint",
        }

    def test_build_payload_enforces_testnet_contract(self) -> None:
        payload = _build_trade_gate_testnet_order_payload(
            {
                **self.valid_body,
                "execution_mode": "live",
                "market": "binance_prod",
                "source": "trade_gate_v1",
            }
        )

        self.assertEqual(payload["execution_mode"], "testnet")
        self.assertEqual(payload["market"], "binance_testnet")
        self.assertEqual(payload["source"], "ops_manual")
        self.assertEqual(payload["created_by"], "baolood")
        self.assertEqual(payload["symbol"], "BTCUSDT")
        self.assertEqual(payload["notional"], 4.0)
        self.assertEqual(payload["stop_price"], 68000.0)

    def test_rejects_live_execution_mode(self) -> None:
        ok, reason = _validate_trade_gate_testnet_order_request(
            {**self.valid_body, "execution_mode": "live"}
        )

        self.assertFalse(ok)
        self.assertEqual(reason, "TESTNET_EXECUTION_MODE_INVALID")

    def test_rejects_non_ops_manual_source(self) -> None:
        ok, reason = _validate_trade_gate_testnet_order_request(
            {**self.valid_body, "source": "trade_gate_v1"}
        )

        self.assertFalse(ok)
        self.assertEqual(reason, "TESTNET_SOURCE_INVALID")

    def test_rejects_missing_stop_price(self) -> None:
        ok, reason = _validate_trade_gate_testnet_order_request(
            {k: v for k, v in self.valid_body.items() if k != "stop_price"}
        )

        self.assertFalse(ok)
        self.assertEqual(reason, "TESTNET_STOP_PRICE_REQUIRED")

    async def test_rejection_returns_error_without_enqueue(self) -> None:
        with patch("app.main._create_domain_command", new_callable=AsyncMock) as create_mock:
            response = await create_trade_gate_testnet_order_intent(
                {**self.valid_body, "execution_mode": "live"}
            )

        self.assertEqual(response, {"status": "error", "error": "TESTNET_EXECUTION_MODE_INVALID"})
        create_mock.assert_not_awaited()

    async def test_acceptance_creates_order_command(self) -> None:
        with patch(
            "app.main._create_domain_command",
            new=AsyncMock(return_value={"id": "order-456", "status": "PENDING"}),
        ) as create_mock:
            response = await create_trade_gate_testnet_order_intent(self.valid_body)

        self.assertEqual(response, {"status": "ok", "command_id": "order-456"})
        create_mock.assert_awaited_once()
        args = create_mock.await_args.args
        self.assertEqual(args[0], "order")
        self.assertEqual(args[1], "ORDER")
        self.assertEqual(args[2]["execution_mode"], "testnet")
        self.assertEqual(args[2]["market"], "binance_testnet")
        self.assertEqual(args[2]["source"], "ops_manual")
        self.assertEqual(args[2]["created_by"], "baolood")
        self.assertEqual(args[2]["idempotency_key"], "testnet:ops_manual:BTCUSDT:BUY:4:endpoint")


if __name__ == "__main__":
    unittest.main()
