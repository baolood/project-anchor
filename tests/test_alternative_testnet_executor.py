import dataclasses
import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "anchor-backend"))

from app.actions.alternative_testnet_executor import (  # noqa: E402
    AlternativeTestnetOrderRequest,
    AlternativeTestnetVenueResponse,
    map_alternative_testnet_response,
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

    def _assert_validation_failure(self, **overrides):
        result = run_alternative_testnet_order_stub(_request(**overrides))

        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.failure_family, "ALTERNATIVE_TESTNET_REQUEST_INVALID")
        self.assertIsNotNone(result.failure_reason)
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)
        return dataclasses.asdict(result)

    def test_unknown_scenario_does_not_silently_become_accepted(self):
        result = self._assert_validation_failure(scenario="UNKNOWN")

        self.assertEqual(result["failure_reason"], "scenario_invalid")

    def test_missing_idempotency_key_fails_local_validation(self):
        result = self._assert_validation_failure(idempotency_key="")

        self.assertEqual(result["failure_reason"], "idempotency_key_missing")

    def test_invalid_side_fails_local_validation(self):
        result = self._assert_validation_failure(side="HOLD")

        self.assertEqual(result["failure_reason"], "side_invalid")

    def test_zero_and_negative_notional_fail_local_validation(self):
        zero = self._assert_validation_failure(notional=0)
        negative = self._assert_validation_failure(notional=-4)

        self.assertEqual(zero["failure_reason"], "notional_invalid")
        self.assertEqual(negative["failure_reason"], "notional_invalid")

    def test_missing_required_fields_fail_local_validation(self):
        self.assertEqual(self._assert_validation_failure(venue="")["failure_reason"], "venue_missing")
        self.assertEqual(
            self._assert_validation_failure(execution_mode="")["failure_reason"],
            "execution_mode_missing",
        )
        self.assertEqual(
            self._assert_validation_failure(execution_mode="live")["failure_reason"],
            "execution_mode_not_testnet",
        )
        self.assertEqual(self._assert_validation_failure(symbol="")["failure_reason"], "symbol_missing")

    def test_validation_failures_do_not_imply_network_request(self):
        result = self._assert_validation_failure(side="INVALID")

        self.assertNotIn("network_request_sent", result)
        self.assertNotIn("http_status", result)
        self.assertNotIn("request_url", result)
        self.assertNotIn("external_request_sent", result)
        self.assertNotIn("external_request_started", result)

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

    def test_accepted_response_mapping_with_external_order_id(self):
        result = map_alternative_testnet_response(
            _request(command_id="mapped-accepted"),
            AlternativeTestnetVenueResponse(
                status="ACCEPTED",
                external_order_id="venue-order-123",
            ),
        )

        self.assertEqual(result.command_id, "mapped-accepted")
        self.assertEqual(result.idempotency_key, "alternative:ops_manual:BTCUSDT:BUY:4:first-skeleton:v1")
        self.assertEqual(result.execution_mode, "testnet")
        self.assertEqual(result.venue, "approved_alternative_testnet")
        self.assertEqual(result.status, "ACCEPTED")
        self.assertIsNone(result.failure_family)
        self.assertIsNone(result.failure_reason)
        self.assertEqual(result.external_order_id, "venue-order-123")
        self.assertTrue(result.external_order_id_present)

    def test_accepted_response_mapping_without_external_order_id(self):
        result = map_alternative_testnet_response(
            _request(),
            AlternativeTestnetVenueResponse(status="ACCEPTED"),
        )

        self.assertEqual(result.status, "ACCEPTED")
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)

    def test_rejected_response_mapping_never_invents_external_order_id(self):
        result = map_alternative_testnet_response(
            _request(),
            AlternativeTestnetVenueResponse(
                status="REJECTED",
                external_order_id="ignored-venue-order",
                failure_family="ALTERNATIVE_TESTNET_VENUE_REJECTED",
                failure_reason="venue_rejected",
            ),
        )

        self.assertEqual(result.status, "REJECTED")
        self.assertEqual(result.failure_family, "ALTERNATIVE_TESTNET_VENUE_REJECTED")
        self.assertEqual(result.failure_reason, "venue_rejected")
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)

    def test_failed_response_mapping_never_invents_external_order_id(self):
        result = map_alternative_testnet_response(
            _request(),
            AlternativeTestnetVenueResponse(
                status="FAILED",
                external_order_id="ignored-venue-order",
                failure_family="ALTERNATIVE_TESTNET_VENUE_FAILED",
                failure_reason="venue_failed",
            ),
        )

        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.failure_family, "ALTERNATIVE_TESTNET_VENUE_FAILED")
        self.assertEqual(result.failure_reason, "venue_failed")
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)

    def test_unknown_response_maps_to_explicit_failure(self):
        result = map_alternative_testnet_response(
            _request(),
            AlternativeTestnetVenueResponse(status="PARTIAL"),
        )

        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.failure_family, "ALTERNATIVE_TESTNET_RESPONSE_UNKNOWN")
        self.assertEqual(result.failure_reason, "alternative_testnet_response_unknown")
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)

    def test_response_mapping_does_not_include_credentials_or_secret_values(self):
        result = dataclasses.asdict(
            map_alternative_testnet_response(
                _request(),
                AlternativeTestnetVenueResponse(
                    status="FAILED",
                    failure_family="ALTERNATIVE_TESTNET_VENUE_FAILED",
                    failure_reason="venue_failed",
                ),
            )
        )

        forbidden_fragments = ("credential", "secret", "api_key", "api_secret", "password", "token")
        for key, value in result.items():
            self.assertFalse(any(fragment in key.lower() for fragment in forbidden_fragments), key)
            self.assertFalse(any(fragment in str(value).lower() for fragment in forbidden_fragments), value)

    def test_response_mapping_does_not_imply_network_request_was_sent(self):
        result = dataclasses.asdict(
            map_alternative_testnet_response(
                _request(),
                AlternativeTestnetVenueResponse(status="ACCEPTED", external_order_id="venue-order-123"),
            )
        )

        self.assertNotIn("network_request_sent", result)
        self.assertNotIn("http_status", result)
        self.assertNotIn("request_url", result)
        self.assertNotIn("external_request_sent", result)
        self.assertNotIn("external_request_started", result)


if __name__ == "__main__":
    unittest.main()
