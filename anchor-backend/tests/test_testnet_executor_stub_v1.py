import unittest
from unittest.mock import AsyncMock

from app.actions.runner import DomainCommandRunner
from app.workers.domain_command_worker import OrderAction


def _testnet_payload(**overrides):
    payload = {
        "execution_mode": "testnet",
        "market": "binance_testnet",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "notional": "4",
        "order_type": "market",
        "idempotency_key": "testnet:trade_gate_v1:BTCUSDT:BUY:4:test",
        "source": "trade_gate_v1",
    }
    payload.update(overrides)
    return payload


class TestnetExecutorStubV1Test(unittest.IsolatedAsyncioTestCase):
    def test_order_action_returns_testnet_stub_without_external_call(self) -> None:
        output = OrderAction().run(
            {"id": "order-testnet-1", "type": "ORDER", "payload": _testnet_payload()}
        )

        self.assertTrue(output["ok"])
        result = output["result"]
        self.assertEqual(result["execution_mode"], "testnet")
        self.assertEqual(result["market"], "binance_testnet")
        self.assertEqual(result["symbol"], "BTCUSDT")
        self.assertEqual(result["side"], "BUY")
        self.assertEqual(result["notional"], 4.0)
        self.assertTrue(result["testnet_stub"])
        self.assertFalse(result["external_call"])
        self.assertEqual(result["testnet_order_id"], "testnet-stub-order-testnet-1")
        self.assertTrue(result["kill_switch_required_before_real_executor"])

    def test_order_action_rejects_live_execution_mode(self) -> None:
        output = OrderAction().run(
            {
                "id": "order-live-1",
                "type": "ORDER",
                "payload": _testnet_payload(execution_mode="live"),
            }
        )

        self.assertFalse(output["ok"])
        self.assertEqual(output["error"], {"code": "LIVE_EXECUTION_DISABLED"})

    def test_order_action_rejects_testnet_secret_fields(self) -> None:
        output = OrderAction().run(
            {
                "id": "order-secret-1",
                "type": "ORDER",
                "payload": _testnet_payload(api_key="should-not-be-here"),
            }
        )

        self.assertFalse(output["ok"])
        self.assertEqual(output["error"]["code"], "TESTNET_CONTRACT_REJECTED")
        self.assertEqual(output["error"]["reason"], "forbidden_secret_field:api_key")

    async def test_runner_emits_testnet_stub_events_and_marks_done(self) -> None:
        picked = {
            "id": "order-testnet-2",
            "type": "ORDER",
            "attempt": 1,
            "payload": _testnet_payload(),
        }
        events = []

        async def pick_one():
            return picked

        async def append_event(command_id, event_type, attempt, payload):
            events.append(
                {
                    "command_id": command_id,
                    "event_type": event_type,
                    "attempt": attempt,
                    "payload": payload,
                }
            )

        mark_done = AsyncMock(return_value=1)
        mark_failed = AsyncMock(return_value=0)
        runner = DomainCommandRunner(
            pick_one,
            lambda command_type: OrderAction() if command_type == "ORDER" else None,
            mark_done,
            mark_failed,
            now_ts_fn=lambda: 123,
            append_event_fn=append_event,
        )

        result = await runner.run_one()

        self.assertEqual(
            result,
            {"id": "order-testnet-2", "type": "ORDER", "final_status": "DONE"},
        )
        mark_done.assert_awaited_once()
        mark_failed.assert_not_awaited()
        event_types = [event["event_type"] for event in events]
        self.assertEqual(
            event_types,
            ["PICKED", "TESTNET_EXECUTOR_STUB", "ACTION_OK", "MARK_DONE"],
        )
        self.assertEqual(events[1]["payload"]["execution_mode"], "testnet")
        self.assertFalse(events[1]["payload"]["external_call"])

    async def test_runner_does_not_emit_testnet_stub_event_on_rejected_payload(self) -> None:
        picked = {
            "id": "order-testnet-3",
            "type": "ORDER",
            "attempt": 1,
            "payload": _testnet_payload(idempotency_key=""),
        }
        events = []

        async def pick_one():
            return picked

        async def append_event(command_id, event_type, attempt, payload):
            events.append(
                {
                    "command_id": command_id,
                    "event_type": event_type,
                    "attempt": attempt,
                    "payload": payload,
                }
            )

        mark_done = AsyncMock(return_value=0)
        mark_failed = AsyncMock(return_value=1)
        runner = DomainCommandRunner(
            pick_one,
            lambda command_type: OrderAction() if command_type == "ORDER" else None,
            mark_done,
            mark_failed,
            now_ts_fn=lambda: 123,
            append_event_fn=append_event,
        )

        result = await runner.run_one()

        self.assertEqual(
            result,
            {"id": "order-testnet-3", "type": "ORDER", "final_status": "FAILED"},
        )
        mark_done.assert_not_awaited()
        mark_failed.assert_awaited_once()
        event_types = [event["event_type"] for event in events]
        self.assertEqual(event_types, ["PICKED", "ACTION_FAIL", "MARK_FAILED"])
        self.assertNotIn("TESTNET_EXECUTOR_STUB", event_types)


if __name__ == "__main__":
    unittest.main()
