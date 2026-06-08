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
        "idempotency_key": "testnet:trade_gate_v1:BTCUSDT:BUY:4:preflight",
        "source": "trade_gate_v1",
        "created_by": "baolood",
    }
    payload.update(overrides)
    return payload


class TestnetBoundaryPreflightV1Test(unittest.IsolatedAsyncioTestCase):
    async def _run_runner(self, payload, env):
        picked = {
            "id": "order-preflight-1",
            "type": "ORDER",
            "attempt": 1,
            "payload": payload,
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
        env_patch = {
            "ANCHOR_KILL_SWITCH": "",
            "TESTNET_EXCHANGE_BASE_URL": "",
            "TESTNET_EXCHANGE_API_KEY": "",
            "TESTNET_EXCHANGE_API_SECRET": "",
            "TESTNET_EXCHANGE_KEY_ID": "",
        }
        env_patch.update(env)
        with patch.dict(os.environ, env_patch, clear=False):
            result = await runner.run_one()
        return result, events, mark_done, mark_failed

    async def test_runner_blocks_testnet_order_when_kill_switch_on(self) -> None:
        result, events, mark_done, mark_failed = await self._run_runner(
            _testnet_payload(),
            {
                "ANCHOR_KILL_SWITCH": "1",
                "TESTNET_EXCHANGE_BASE_URL": "https://demo-fapi.binance.com",
                "TESTNET_EXCHANGE_API_KEY": "k",
                "TESTNET_EXCHANGE_API_SECRET": "s",
                "TESTNET_EXCHANGE_KEY_ID": "kid-1",
            },
        )

        self.assertEqual(
            result,
            {"id": "order-preflight-1", "type": "ORDER", "final_status": "FAILED"},
        )
        mark_done.assert_not_awaited()
        mark_failed.assert_awaited_once()
        event_types = [event["event_type"] for event in events]
        self.assertEqual(event_types, ["PICKED", "KILL_SWITCH_CHECKED", "ACTION_FAIL", "MARK_FAILED"])
        self.assertEqual(events[1]["payload"]["source"], "env")
        self.assertTrue(events[1]["payload"]["enabled"])
        self.assertEqual(events[1]["payload"]["gate"], "kill_switch")
        self.assertEqual(events[2]["payload"]["error"]["code"], "KILL_SWITCH_ON")
        self.assertEqual(events[2]["payload"]["error"]["failure_family"], "KILL_SWITCH_ON")
        self.assertEqual(events[2]["payload"]["error"]["gate"], "kill_switch")
        self.assertFalse(events[2]["payload"]["error"]["external_request_started"])
        self.assertFalse(events[2]["payload"]["error"]["external_order_id_present"])

    async def test_runner_rejects_invalid_testnet_base_url_before_external_request(self) -> None:
        result, events, mark_done, mark_failed = await self._run_runner(
            _testnet_payload(),
            {
                "TESTNET_EXCHANGE_BASE_URL": "http://127.0.0.1:18000",
                "TESTNET_EXCHANGE_API_KEY": "k",
                "TESTNET_EXCHANGE_API_SECRET": "s",
                "TESTNET_EXCHANGE_KEY_ID": "kid-1",
            },
        )

        self.assertEqual(
            result,
            {"id": "order-preflight-1", "type": "ORDER", "final_status": "FAILED"},
        )
        mark_done.assert_not_awaited()
        mark_failed.assert_awaited_once()
        event_types = [event["event_type"] for event in events]
        self.assertEqual(event_types, ["PICKED", "KILL_SWITCH_CHECKED", "ACTION_FAIL", "MARK_FAILED"])
        self.assertFalse(events[1]["payload"]["enabled"])
        self.assertEqual(events[2]["payload"]["error"]["code"], "TESTNET_BASE_URL_INVALID")
        self.assertEqual(events[2]["payload"]["error"]["failure_family"], "TESTNET_BASE_URL_INVALID")
        self.assertEqual(events[2]["payload"]["error"]["gate"], "host_safety")
        self.assertNotIn("TESTNET_EXECUTOR_STUB", event_types)

    async def test_runner_rejects_missing_testnet_credentials_before_external_request(self) -> None:
        result, events, mark_done, mark_failed = await self._run_runner(
            _testnet_payload(),
            {
                "TESTNET_EXCHANGE_BASE_URL": "https://demo-fapi.binance.com",
            },
        )

        self.assertEqual(
            result,
            {"id": "order-preflight-1", "type": "ORDER", "final_status": "FAILED"},
        )
        mark_done.assert_not_awaited()
        mark_failed.assert_awaited_once()
        event_types = [event["event_type"] for event in events]
        self.assertEqual(event_types, ["PICKED", "KILL_SWITCH_CHECKED", "ACTION_FAIL", "MARK_FAILED"])
        self.assertEqual(events[2]["payload"]["error"]["code"], "TESTNET_CREDENTIALS_MISSING")
        self.assertEqual(events[2]["payload"]["error"]["failure_family"], "TESTNET_CREDENTIALS_MISSING")
        self.assertEqual(events[2]["payload"]["error"]["gate"], "credential_presence")
        self.assertEqual(events[2]["payload"]["error"]["host_label"], "binance_futures_testnet")
        self.assertNotIn("TESTNET_EXECUTOR_STUB", event_types)
        self.assertNotIn("ACTION_OK", event_types)
        self.assertNotIn("MARK_DONE", event_types)

    async def test_runner_accepts_demo_fapi_origin_in_testnet_host_safety_profile(self) -> None:
        result, events, mark_done, mark_failed = await self._run_runner(
            _testnet_payload(),
            {
                "TESTNET_EXCHANGE_BASE_URL": "https://demo-fapi.binance.com",
                "TESTNET_EXCHANGE_API_KEY": "k",
                "TESTNET_EXCHANGE_API_SECRET": "s",
                "TESTNET_EXCHANGE_KEY_ID": "kid-1",
                "TESTNET_EXECUTOR_MODE": "mystery",
            },
        )

        self.assertEqual(
            result,
            {"id": "order-preflight-1", "type": "ORDER", "final_status": "FAILED"},
        )
        mark_done.assert_not_awaited()
        mark_failed.assert_awaited_once()
        event_types = [event["event_type"] for event in events]
        self.assertEqual(event_types, ["PICKED", "KILL_SWITCH_CHECKED", "ACTION_FAIL", "MARK_FAILED"])
        self.assertEqual(events[2]["payload"]["error"]["code"], "TESTNET_EXECUTOR_MODE_INVALID")
        self.assertEqual(events[2]["payload"]["error"]["failure_family"], "TESTNET_EXECUTOR_MODE_INVALID")
        self.assertEqual(events[2]["payload"]["error"]["gate"], "executor_boundary")


if __name__ == "__main__":
    unittest.main()
