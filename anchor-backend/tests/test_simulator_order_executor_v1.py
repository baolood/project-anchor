import unittest

from app.executors.simulator_order_executor import run_simulator_order_request


def _transport_input(**overrides):
    payload = {
        "command_id": "order-simulator-1",
        "attempt": 1,
        "execution_mode": "testnet",
        "market": "binance_testnet",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "notional": "4",
        "stop_price": "68000",
        "order_type": "market",
        "idempotency_key": "testnet:ops_manual:BTCUSDT:BUY:4:first-bounded-request:v1",
        "source": "ops_manual",
        "created_by": "baolood",
        "host_label": "local_exchange_simulator",
        "configured_origin": "simulator://local",
        "canonical_path": "ORDER:testnet",
    }
    payload.update(overrides)
    return payload


class SimulatorOrderExecutorV1Test(unittest.TestCase):
    def test_accepted_returns_deterministic_simulator_order_id(self) -> None:
        out, requested, terminal_type, terminal_payload = run_simulator_order_request(
            _transport_input(simulator_scenario="accepted"),
            100,
        )

        self.assertTrue(out["ok"])
        self.assertTrue(requested["external_request_started"])
        self.assertEqual(terminal_type, "TESTNET_EXECUTOR_ACCEPTED")
        simulator_order_id = out["result"]["simulator_order_id"]
        self.assertTrue(simulator_order_id.startswith("mock-testnet-order-"))
        self.assertEqual(out["result"]["external_order_id"], simulator_order_id)
        self.assertEqual(terminal_payload["simulator_order_id"], simulator_order_id)
        self.assertEqual(terminal_payload["external_order_id"], simulator_order_id)

    def test_rejected_returns_no_order_id(self) -> None:
        out, requested, terminal_type, terminal_payload = run_simulator_order_request(
            _transport_input(simulator_scenario="rejected"),
            101,
        )

        self.assertFalse(out["ok"])
        self.assertTrue(requested["external_request_started"])
        self.assertEqual(terminal_type, "TESTNET_EXECUTOR_REJECTED")
        self.assertEqual(out["error"]["failure_family"], "TESTNET_EXECUTOR_REJECTED")
        self.assertFalse(out["error"]["external_order_id_present"])
        self.assertNotIn("simulator_order_id", terminal_payload)
        self.assertNotIn("external_order_id", terminal_payload)

    def test_failed_returns_failure_family_without_order_id(self) -> None:
        out, requested, terminal_type, terminal_payload = run_simulator_order_request(
            _transport_input(simulator_scenario="failed"),
            102,
        )

        self.assertFalse(out["ok"])
        self.assertTrue(requested["external_request_started"])
        self.assertEqual(terminal_type, "TESTNET_EXECUTOR_FAILED")
        self.assertEqual(out["error"]["failure_family"], "TESTNET_EXECUTOR_SIMULATOR_FAILED")
        self.assertEqual(terminal_payload["failure_family"], "TESTNET_EXECUTOR_SIMULATOR_FAILED")
        self.assertFalse(out["error"]["external_order_id_present"])
        self.assertNotIn("simulator_order_id", terminal_payload)
        self.assertNotIn("external_order_id", terminal_payload)

    def test_duplicate_idempotency_key_does_not_create_second_order_id(self) -> None:
        first, _, _, _ = run_simulator_order_request(
            _transport_input(command_id="order-a", simulator_scenario="accepted"),
            103,
        )
        second, _, _, _ = run_simulator_order_request(
            _transport_input(command_id="order-b", simulator_scenario="accepted"),
            104,
        )

        self.assertEqual(first["result"]["simulator_order_id"], second["result"]["simulator_order_id"])
        self.assertEqual(first["result"]["external_order_id"], second["result"]["external_order_id"])

    def test_invalid_input_fails_before_accepted_outcome(self) -> None:
        out, requested, terminal_type, terminal_payload = run_simulator_order_request(
            _transport_input(notional="0", simulator_scenario="accepted"),
            105,
        )

        self.assertFalse(out["ok"])
        self.assertEqual(requested["simulator_scenario"], "accepted")
        self.assertEqual(terminal_type, "TESTNET_EXECUTOR_FAILED")
        self.assertEqual(out["error"]["failure_family"], "TESTNET_SIMULATOR_INPUT_INVALID")
        self.assertEqual(out["error"]["failure_reason"], "notional_invalid")
        self.assertFalse(out["error"]["external_request_started"])
        self.assertFalse(out["error"]["external_order_id_present"])
        self.assertFalse(terminal_payload["external_request_started"])


if __name__ == "__main__":
    unittest.main()
