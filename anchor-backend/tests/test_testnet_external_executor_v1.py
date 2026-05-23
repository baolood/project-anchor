import os
import unittest
from unittest.mock import AsyncMock, patch

from app.actions.runner import DomainCommandRunner
from app.workers.domain_command_worker import OrderAction


def _testnet_payload(**overrides):
    payload = {
        "execution_mode": "testnet",
        "market": "binance_testnet",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "notional": "4",
        "stop_price": "68000",
        "order_type": "market",
        "idempotency_key": "testnet:trade_gate_v1:BTCUSDT:BUY:4:external",
        "source": "trade_gate_v1",
        "created_by": "baolood",
    }
    payload.update(overrides)
    return payload


class TestnetExternalExecutorV1Test(unittest.IsolatedAsyncioTestCase):
    async def _run_runner(self, env):
        picked = {
            "id": "order-external-1",
            "type": "ORDER",
            "attempt": 2,
            "payload": _testnet_payload(),
        }
        events = []

        async def pick_one():
            return picked

        async def append_event(command_id, event_type, attempt, event_payload):
            events.append(
                {
                    "command_id": command_id,
                    "event_type": event_type,
                    "attempt": attempt,
                    "payload": event_payload,
                }
            )

        mark_done = AsyncMock(return_value=1)
        mark_failed = AsyncMock(return_value=0)
        runner = DomainCommandRunner(
            pick_one,
            lambda command_type: OrderAction() if command_type == "ORDER" else None,
            mark_done,
            mark_failed,
            now_ts_fn=lambda: 456,
            append_event_fn=append_event,
        )
        env_patch = {
            "ANCHOR_KILL_SWITCH": "",
            "TESTNET_EXCHANGE_BASE_URL": "https://testnet.binancefuture.com",
            "TESTNET_EXCHANGE_API_KEY": "k",
            "TESTNET_EXCHANGE_API_SECRET": "s",
            "TESTNET_EXCHANGE_KEY_ID": "kid-1",
            "TESTNET_EXECUTOR_MODE": "mock",
            "TESTNET_EXECUTOR_MOCK_OUTCOME": "success",
        }
        env_patch.update(env)
        with patch.dict(os.environ, env_patch, clear=False):
            result = await runner.run_one()
        return result, events, mark_done, mark_failed

    async def test_runner_emits_mocked_success_external_chain(self) -> None:
        result, events, mark_done, mark_failed = await self._run_runner({})

        self.assertEqual(
            result,
            {"id": "order-external-1", "type": "ORDER", "final_status": "DONE"},
        )
        mark_done.assert_awaited_once()
        mark_failed.assert_not_awaited()
        event_types = [event["event_type"] for event in events]
        self.assertEqual(
            event_types,
            [
                "PICKED",
                "KILL_SWITCH_CHECKED",
                "TESTNET_EXECUTOR_REQUESTED",
                "TESTNET_EXECUTOR_ACCEPTED",
                "ACTION_OK",
                "MARK_DONE",
            ],
        )
        self.assertEqual(events[2]["payload"]["canonical_path"], "ORDER:testnet")
        self.assertTrue(events[2]["payload"]["external_request_started"])
        self.assertEqual(events[3]["payload"]["external_status"], "MOCK_ACCEPTED")
        self.assertTrue(events[3]["payload"]["external_order_id"].startswith("mock-testnet-order-"))

    async def test_runner_emits_mocked_auth_failed_external_chain(self) -> None:
        result, events, mark_done, mark_failed = await self._run_runner(
            {"TESTNET_EXECUTOR_MOCK_OUTCOME": "auth_failed"}
        )

        self.assertEqual(
            result,
            {"id": "order-external-1", "type": "ORDER", "final_status": "FAILED"},
        )
        mark_done.assert_not_awaited()
        mark_failed.assert_awaited_once()
        event_types = [event["event_type"] for event in events]
        self.assertEqual(
            event_types,
            [
                "PICKED",
                "KILL_SWITCH_CHECKED",
                "TESTNET_EXECUTOR_REQUESTED",
                "TESTNET_EXECUTOR_REJECTED",
                "ACTION_FAIL",
                "MARK_FAILED",
            ],
        )
        self.assertEqual(events[3]["payload"]["failure_family"], "TESTNET_EXECUTOR_AUTH_FAILED")
        self.assertEqual(events[4]["payload"]["error"]["failure_family"], "TESTNET_EXECUTOR_AUTH_FAILED")
        self.assertTrue(events[4]["payload"]["error"]["external_request_started"])

    async def test_runner_emits_mocked_timeout_external_chain(self) -> None:
        result, events, mark_done, mark_failed = await self._run_runner(
            {"TESTNET_EXECUTOR_MOCK_OUTCOME": "timeout"}
        )

        self.assertEqual(
            result,
            {"id": "order-external-1", "type": "ORDER", "final_status": "FAILED"},
        )
        mark_done.assert_not_awaited()
        mark_failed.assert_awaited_once()
        event_types = [event["event_type"] for event in events]
        self.assertEqual(event_types[2], "TESTNET_EXECUTOR_REQUESTED")
        self.assertEqual(event_types[3], "TESTNET_EXECUTOR_REJECTED")
        self.assertEqual(events[3]["payload"]["failure_family"], "TESTNET_EXECUTOR_TIMEOUT")
        self.assertEqual(events[4]["payload"]["error"]["failure_family"], "TESTNET_EXECUTOR_TIMEOUT")


if __name__ == "__main__":
    unittest.main()
