import dataclasses
import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "anchor-backend"))

from app.actions.alternative_testnet_executor import (  # noqa: E402
    AlternativeTestnetOrderRequest,
    run_alternative_testnet_order_stub,
)


def _request(**overrides):
    payload = {
        "command_id": "alt-testnet-1",
        "idempotency_key": "alternative:ops_manual:BTCUSDT:BUY:4:first-skeleton:v1",
        "venue": "approved_alternative_testnet",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "notional": 4.0,
        "scenario": "ACCEPTED",
    }
    payload.update(overrides)
    return AlternativeTestnetOrderRequest(**payload)


def _result_dict(**overrides):
    result = run_alternative_testnet_order_stub(_request(**overrides))
    return dataclasses.asdict(result)


class AlternativeTestnetExecutorSkeletonTest(unittest.TestCase):
    def test_accepted_result_shape(self):
        result = run_alternative_testnet_order_stub(_request(scenario="ACCEPTED"))

        self.assertEqual(result.execution_mode, "testnet")
        self.assertEqual(result.venue, "approved_alternative_testnet")
        self.assertEqual(result.status, "ACCEPTED")
        self.assertIsNone(result.failure_family)
        self.assertIsNone(result.failure_reason)
        self.assertTrue(result.external_order_id_present)
        self.assertTrue(result.external_order_id.startswith("alt-testnet-order-"))

    def test_accepted_contract_preserves_request_evidence(self):
        result = run_alternative_testnet_order_stub(
            _request(
                command_id="alt-testnet-accepted-contract",
                idempotency_key="alternative:contract:accepted:v1",
                venue="approved_alternative_testnet_contract",
                scenario="ACCEPTED",
            )
        )

        self.assertEqual(result.command_id, "alt-testnet-accepted-contract")
        self.assertEqual(result.idempotency_key, "alternative:contract:accepted:v1")
        self.assertEqual(result.execution_mode, "testnet")
        self.assertEqual(result.venue, "approved_alternative_testnet_contract")
        self.assertEqual(result.status, "ACCEPTED")
        self.assertTrue(result.external_order_id_present)
        self.assertIsNotNone(result.external_order_id)

    def test_rejected_result_shape(self):
        result = run_alternative_testnet_order_stub(_request(scenario="REJECTED"))

        self.assertEqual(result.status, "REJECTED")
        self.assertEqual(result.failure_family, "ALTERNATIVE_TESTNET_EXECUTOR_REJECTED")
        self.assertEqual(result.failure_reason, "alternative_testnet_rejected")
        self.assertFalse(result.external_order_id_present)

    def test_rejected_contract_is_terminal_without_retry_evidence(self):
        result = _result_dict(scenario="REJECTED")

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["failure_family"], "ALTERNATIVE_TESTNET_EXECUTOR_REJECTED")
        self.assertEqual(result["failure_reason"], "alternative_testnet_rejected")
        self.assertIsNone(result["external_order_id"])
        self.assertFalse(result["external_order_id_present"])
        self.assertNotIn("retry", result)
        self.assertNotIn("retry_count", result)

    def test_failed_result_shape(self):
        result = run_alternative_testnet_order_stub(_request(scenario="FAILED"))

        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.failure_family, "ALTERNATIVE_TESTNET_EXECUTOR_FAILED")
        self.assertEqual(result.failure_reason, "alternative_testnet_failed")
        self.assertFalse(result.external_order_id_present)

    def test_failed_contract_preserves_deterministic_evidence_shape(self):
        first = _result_dict(command_id="failed-a", scenario="FAILED")
        second = _result_dict(command_id="failed-b", scenario="FAILED")

        self.assertEqual(first["idempotency_key"], second["idempotency_key"])
        self.assertEqual(first["execution_mode"], "testnet")
        self.assertEqual(second["execution_mode"], "testnet")
        self.assertEqual(first["venue"], second["venue"])
        self.assertEqual(first["status"], "FAILED")
        self.assertEqual(second["status"], "FAILED")
        self.assertEqual(first["failure_family"], "ALTERNATIVE_TESTNET_EXECUTOR_FAILED")
        self.assertEqual(second["failure_family"], "ALTERNATIVE_TESTNET_EXECUTOR_FAILED")
        self.assertIsNone(first["external_order_id"])
        self.assertIsNone(second["external_order_id"])

    def test_rejected_and_failed_have_no_external_order_id(self):
        rejected = run_alternative_testnet_order_stub(_request(scenario="REJECTED"))
        failed = run_alternative_testnet_order_stub(_request(scenario="FAILED"))

        self.assertIsNone(rejected.external_order_id)
        self.assertIsNone(failed.external_order_id)
        self.assertFalse(rejected.external_order_id_present)
        self.assertFalse(failed.external_order_id_present)

    def test_idempotency_and_evidence_fields_are_deterministic(self):
        first = run_alternative_testnet_order_stub(_request(scenario="ACCEPTED"))
        second = run_alternative_testnet_order_stub(
            _request(command_id="alt-testnet-2", scenario="ACCEPTED")
        )

        self.assertEqual(first.idempotency_key, second.idempotency_key)
        self.assertEqual(first.external_order_id, second.external_order_id)
        self.assertEqual(first.execution_mode, "testnet")
        self.assertEqual(first.venue, "approved_alternative_testnet")

    def test_unknown_scenario_does_not_silently_become_accepted(self):
        with self.assertRaises(ValueError):
            run_alternative_testnet_order_stub(_request(scenario="UNKNOWN"))

    def test_result_shape_does_not_include_credentials_or_secret_values(self):
        result = _result_dict(scenario="ACCEPTED")

        forbidden_fragments = ("credential", "secret", "api_key", "api_secret", "password", "token")
        for key, value in result.items():
            self.assertFalse(any(fragment in key.lower() for fragment in forbidden_fragments), key)
            self.assertFalse(any(fragment in str(value).lower() for fragment in forbidden_fragments), value)

    def test_result_shape_does_not_imply_network_request_was_sent(self):
        result = _result_dict(scenario="ACCEPTED")

        self.assertNotIn("network_request_sent", result)
        self.assertNotIn("http_status", result)
        self.assertNotIn("request_url", result)
        self.assertNotIn("external_request_sent", result)
        self.assertNotIn("external_request_started", result)


if __name__ == "__main__":
    unittest.main()
