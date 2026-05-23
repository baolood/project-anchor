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

    @staticmethod
    def _real_success_tuple():
        return (
            {
                "ok": True,
                "result": {
                    "ok": True,
                    "type": "order",
                    "execution_mode": "testnet",
                    "market": "binance_testnet",
                    "symbol": "BTCUSDT",
                    "side": "BUY",
                    "notional": 4.0,
                    "order_type": "market",
                    "source": "trade_gate_v1",
                    "created_by": "baolood",
                    "stop_price": 68000.0,
                    "idempotency_key": "testnet:trade_gate_v1:BTCUSDT:BUY:4:external",
                    "host_label": "binance_futures_testnet",
                    "external_order_id": "real-testnet-order-1",
                    "external_status": "FILLED",
                    "ts": 456,
                },
                "error": None,
            },
            {
                "type": "ORDER",
                "attempt": 2,
                "execution_mode": "testnet",
                "host_label": "binance_futures_testnet",
                "configured_origin": "https://testnet.binancefuture.com",
                "canonical_path": "ORDER:testnet",
                "external_request_started": True,
            },
            "TESTNET_EXECUTOR_ACCEPTED",
            {
                "type": "ORDER",
                "attempt": 2,
                "execution_mode": "testnet",
                "host_label": "binance_futures_testnet",
                "configured_origin": "https://testnet.binancefuture.com",
                "canonical_path": "ORDER:testnet",
                "external_request_started": True,
                "external_order_id": "real-testnet-order-1",
                "external_status": "FILLED",
            },
        )

    @staticmethod
    def _real_auth_failed_tuple():
        return (
            {
                "ok": False,
                "result": None,
                "error": {
                    "code": "TESTNET_EXECUTOR_AUTH_FAILED",
                    "failure_family": "TESTNET_EXECUTOR_AUTH_FAILED",
                    "failure_reason": "real_auth_failed",
                    "gate": "external_executor",
                    "external_request_started": True,
                    "external_order_id_present": False,
                    "execution_mode": "testnet",
                    "host_label": "binance_futures_testnet",
                    "configured_origin": "https://testnet.binancefuture.com",
                    "canonical_path": "ORDER:testnet",
                },
            },
            {
                "type": "ORDER",
                "attempt": 2,
                "execution_mode": "testnet",
                "host_label": "binance_futures_testnet",
                "configured_origin": "https://testnet.binancefuture.com",
                "canonical_path": "ORDER:testnet",
                "external_request_started": True,
            },
            "TESTNET_EXECUTOR_REJECTED",
            {
                "type": "ORDER",
                "attempt": 2,
                "execution_mode": "testnet",
                "host_label": "binance_futures_testnet",
                "configured_origin": "https://testnet.binancefuture.com",
                "canonical_path": "ORDER:testnet",
                "failure_family": "TESTNET_EXECUTOR_AUTH_FAILED",
                "failure_reason": "real_auth_failed",
                "external_request_started": True,
            },
        )

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

    async def test_runner_emits_mocked_validation_failed_external_chain(self) -> None:
        result, events, mark_done, mark_failed = await self._run_runner(
            {"TESTNET_EXECUTOR_MOCK_OUTCOME": "validation_failed"}
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
        self.assertEqual(events[3]["payload"]["failure_family"], "TESTNET_EXECUTOR_VALIDATION_FAILED")
        self.assertEqual(events[3]["payload"]["failure_reason"], "mock_validation_failed")
        self.assertEqual(events[4]["payload"]["error"]["failure_family"], "TESTNET_EXECUTOR_VALIDATION_FAILED")
        self.assertFalse(events[4]["payload"]["error"]["external_order_id_present"])

    async def test_runner_emits_mocked_network_error_external_chain(self) -> None:
        result, events, mark_done, mark_failed = await self._run_runner(
            {"TESTNET_EXECUTOR_MOCK_OUTCOME": "network_error"}
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
        self.assertEqual(events[3]["payload"]["failure_family"], "TESTNET_EXECUTOR_NETWORK_ERROR")
        self.assertEqual(events[4]["payload"]["error"]["failure_family"], "TESTNET_EXECUTOR_NETWORK_ERROR")
        self.assertTrue(events[4]["payload"]["error"]["external_request_started"])

    async def test_runner_maps_unknown_mock_outcome_to_unexpected_family(self) -> None:
        result, events, mark_done, mark_failed = await self._run_runner(
            {"TESTNET_EXECUTOR_MOCK_OUTCOME": "weird_case"}
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
        self.assertEqual(events[3]["payload"]["failure_family"], "TESTNET_EXECUTOR_UNEXPECTED")
        self.assertEqual(events[3]["payload"]["failure_reason"], "mock_weird_case")
        self.assertEqual(events[4]["payload"]["error"]["failure_family"], "TESTNET_EXECUTOR_UNEXPECTED")
        self.assertEqual(events[4]["payload"]["error"]["gate"], "external_executor")

    async def test_runner_real_mode_stays_disabled_without_explicit_enable_flag(self) -> None:
        result, events, mark_done, mark_failed = await self._run_runner(
            {
                "TESTNET_EXECUTOR_MODE": "real",
                "TESTNET_EXECUTOR_REAL_ENABLE": "",
            }
        )

        self.assertEqual(
            result,
            {"id": "order-external-1", "type": "ORDER", "final_status": "FAILED"},
        )
        mark_done.assert_not_awaited()
        mark_failed.assert_awaited_once()
        event_types = [event["event_type"] for event in events]
        self.assertEqual(event_types, ["PICKED", "KILL_SWITCH_CHECKED", "ACTION_FAIL", "MARK_FAILED"])
        self.assertEqual(events[2]["payload"]["error"]["failure_family"], "TESTNET_REAL_WIRE_DISABLED")
        self.assertFalse(events[2]["payload"]["error"]["external_request_started"])
        self.assertNotIn("TESTNET_EXECUTOR_REQUESTED", event_types)

    async def test_runner_invalid_executor_mode_does_not_silently_go_real(self) -> None:
        result, events, mark_done, mark_failed = await self._run_runner(
            {"TESTNET_EXECUTOR_MODE": "mystery"}
        )

        self.assertEqual(
            result,
            {"id": "order-external-1", "type": "ORDER", "final_status": "FAILED"},
        )
        mark_done.assert_not_awaited()
        mark_failed.assert_awaited_once()
        event_types = [event["event_type"] for event in events]
        self.assertEqual(event_types, ["PICKED", "KILL_SWITCH_CHECKED", "ACTION_FAIL", "MARK_FAILED"])
        self.assertEqual(events[2]["payload"]["error"]["failure_family"], "TESTNET_EXECUTOR_MODE_INVALID")
        self.assertEqual(events[2]["payload"]["error"]["configured_executor_mode"], "mystery")
        self.assertNotIn("TESTNET_EXECUTOR_REQUESTED", event_types)

    async def test_runner_real_mode_can_emit_success_chain_when_helper_is_patched(self) -> None:
        with patch(
            "app.actions.runner.real_testnet_executor.run_real_testnet_order_request",
            return_value=self._real_success_tuple(),
        ):
            result, events, mark_done, mark_failed = await self._run_runner(
                {
                    "TESTNET_EXECUTOR_MODE": "real",
                    "TESTNET_EXECUTOR_REAL_ENABLE": "1",
                }
            )

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
        self.assertEqual(events[3]["payload"]["external_order_id"], "real-testnet-order-1")

    async def test_runner_real_mode_can_emit_rejected_chain_when_helper_is_patched(self) -> None:
        with patch(
            "app.actions.runner.real_testnet_executor.run_real_testnet_order_request",
            return_value=self._real_auth_failed_tuple(),
        ):
            result, events, mark_done, mark_failed = await self._run_runner(
                {
                    "TESTNET_EXECUTOR_MODE": "real",
                    "TESTNET_EXECUTOR_REAL_ENABLE": "1",
                }
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


if __name__ == "__main__":
    unittest.main()
