import dataclasses
import ast
import sys
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "anchor-backend" / "app" / "actions" / "alternative_testnet_http_client.py"
sys.path.insert(0, str(PROJECT_ROOT / "anchor-backend"))

from app.actions.alternative_testnet_http_client import (  # noqa: E402
    AlternativeTestnetHttpBuiltRequest,
    AlternativeTestnetHttpClientRequest,
    NoNetworkAlternativeTestnetHttpClient,
)


def _request(**overrides):
    payload = {
        "idempotency_key": "alternative:http:BTCUSDT:BUY:4:first-skeleton:v1",
        "venue": "approved_alternative_testnet",
        "execution_mode": "testnet",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "notional": "4",
    }
    payload.update(overrides)
    return AlternativeTestnetHttpClientRequest(**payload)


class AlternativeTestnetHttpClientSkeletonTest(unittest.TestCase):
    def setUp(self):
        self.client = NoNetworkAlternativeTestnetHttpClient()

    def _module_source(self):
        return MODULE_PATH.read_text(encoding="utf-8")

    def _module_import_names(self):
        tree = ast.parse(self._module_source())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        return imported

    def test_accepted_fixture_response_is_deterministic(self):
        first = self.client.accepted_fixture_response(_request())
        second = self.client.accepted_fixture_response(_request())

        self.assertEqual(first.status, "ACCEPTED")
        self.assertIsNone(first.failure_family)
        self.assertIsNone(first.failure_reason)
        self.assertEqual(first.external_order_id, second.external_order_id)
        self.assertTrue(first.external_order_id_present)
        self.assertTrue(first.external_order_id.startswith("alt-testnet-http-fixture-"))

    def test_rejected_fixture_response_has_no_external_order_id(self):
        result = self.client.rejected_fixture_response(_request())

        self.assertEqual(result.status, "REJECTED")
        self.assertEqual(result.failure_family, "ALTERNATIVE_TESTNET_HTTP_REJECTED")
        self.assertEqual(result.failure_reason, "alternative_testnet_http_rejected")
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)

    def test_rejected_fixture_response_is_deterministic(self):
        first = self.client.rejected_fixture_response(_request())
        second = self.client.rejected_fixture_response(_request())

        self.assertEqual(dataclasses.asdict(first), dataclasses.asdict(second))

    def test_failed_fixture_response_has_no_external_order_id(self):
        result = self.client.failed_fixture_response(_request())

        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.failure_family, "ALTERNATIVE_TESTNET_HTTP_FAILED")
        self.assertEqual(result.failure_reason, "alternative_testnet_http_failed")
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)

    def test_failed_and_unexpected_fixture_responses_are_deterministic(self):
        first_failed = self.client.failed_fixture_response(_request())
        second_failed = self.client.failed_fixture_response(_request())
        first_unexpected = self.client.unexpected_fixture_response(_request())
        second_unexpected = self.client.unexpected_fixture_response(_request())

        self.assertEqual(dataclasses.asdict(first_failed), dataclasses.asdict(second_failed))
        self.assertEqual(dataclasses.asdict(first_unexpected), dataclasses.asdict(second_unexpected))

    def test_unexpected_fixture_response_is_explicit_failed_result(self):
        result = self.client.unexpected_fixture_response(_request())

        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.failure_family, "ALTERNATIVE_TESTNET_HTTP_UNEXPECTED")
        self.assertEqual(result.failure_reason, "alternative_testnet_http_unexpected")
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)

    def test_fixture_responses_preserve_evidence_fields(self):
        result = self.client.accepted_fixture_response(
            _request(
                idempotency_key="alternative:http:custom:v1",
                venue="approved_alternative_testnet_custom",
            )
        )

        self.assertEqual(result.idempotency_key, "alternative:http:custom:v1")
        self.assertEqual(result.venue, "approved_alternative_testnet_custom")
        self.assertEqual(result.execution_mode, "testnet")

    def test_builds_deterministic_buy_request_object(self):
        first = self.client.build_order_request(_request())
        second = self.client.build_order_request(_request())

        self.assertIsInstance(first, AlternativeTestnetHttpBuiltRequest)
        self.assertEqual(dataclasses.asdict(first), dataclasses.asdict(second))
        self.assertEqual(first.method, "POST")
        self.assertEqual(first.path, "/testnet/orders")
        self.assertEqual(first.symbol, "BTCUSDT")
        self.assertEqual(first.side, "BUY")
        self.assertEqual(first.notional, "4")
        self.assertTrue(first.client_order_ref.startswith("alt-testnet-local-"))

    def test_builds_deterministic_sell_request_object(self):
        first = self.client.build_order_request(
            _request(
                idempotency_key="alternative:http:BTCUSDT:SELL:4:first-builder:v1",
                side="SELL",
            )
        )
        second = self.client.build_order_request(
            _request(
                idempotency_key="alternative:http:BTCUSDT:SELL:4:first-builder:v1",
                side="SELL",
            )
        )

        self.assertEqual(dataclasses.asdict(first), dataclasses.asdict(second))
        self.assertEqual(first.side, "SELL")
        self.assertEqual(first.body["side"], "SELL")

    def test_built_request_preserves_idempotency_and_evidence_fields(self):
        result = self.client.build_order_request(
            _request(
                idempotency_key="alternative:http:custom-builder:v1",
                venue="approved_alternative_testnet_custom",
                execution_mode="testnet",
            )
        )

        self.assertEqual(result.idempotency_key, "alternative:http:custom-builder:v1")
        self.assertEqual(result.body["idempotency_key"], "alternative:http:custom-builder:v1")
        self.assertEqual(result.venue, "approved_alternative_testnet_custom")
        self.assertEqual(result.execution_mode, "testnet")
        self.assertEqual(result.body["venue"], "approved_alternative_testnet_custom")
        self.assertEqual(result.body["execution_mode"], "testnet")

    def test_built_request_excludes_credentials_and_secret_fields(self):
        built = dataclasses.asdict(self.client.build_order_request(_request()))
        forbidden_fragments = ("credential", "secret", "api_key", "api_secret", "password", "token")

        def assert_no_forbidden(value):
            if isinstance(value, dict):
                for key, nested_value in value.items():
                    self.assertFalse(any(fragment in key.lower() for fragment in forbidden_fragments), key)
                    assert_no_forbidden(nested_value)
                return
            self.assertFalse(any(fragment in str(value).lower() for fragment in forbidden_fragments), value)

        assert_no_forbidden(built)

    def test_built_request_excludes_authorization_and_signature_fields(self):
        built = dataclasses.asdict(self.client.build_order_request(_request()))
        forbidden_fragments = ("authorization", "signature", "signed", "bearer")

        def assert_no_forbidden(value):
            if isinstance(value, dict):
                for key, nested_value in value.items():
                    self.assertFalse(any(fragment in key.lower() for fragment in forbidden_fragments), key)
                    assert_no_forbidden(nested_value)
                return
            self.assertFalse(any(fragment in str(value).lower() for fragment in forbidden_fragments), value)

        assert_no_forbidden(built)

    def test_built_request_does_not_include_full_or_live_url(self):
        built = dataclasses.asdict(self.client.build_order_request(_request()))
        flattened = " ".join(str(value) for value in built.values())
        flattened = f"{flattened} {' '.join(str(value) for value in built['body'].values())}"

        self.assertNotIn("http://", flattened)
        self.assertNotIn("https://", flattened)
        self.assertNotIn("api.", flattened)
        self.assertNotIn("live", flattened.lower())
        self.assertTrue(built["path"].startswith("/"))

    def test_built_request_does_not_imply_network_request_was_sent(self):
        built = dataclasses.asdict(self.client.build_order_request(_request()))
        forbidden_fields = {
            "external_order_id",
            "external_order_id_present",
            "external_request_sent",
            "external_request_started",
            "network_request_sent",
            "network_sent",
            "request_url",
        }

        self.assertTrue(forbidden_fields.isdisjoint(built))
        self.assertTrue(forbidden_fields.isdisjoint(built["body"]))

    def test_built_request_preserves_pre_signing_transport_gap(self):
        built = dataclasses.asdict(self.client.build_order_request(_request()))
        forbidden_fields = {
            "authorization",
            "headers",
            "signature",
            "signed_payload",
            "timeout",
            "transport",
            "url",
        }

        self.assertTrue(forbidden_fields.isdisjoint(built))
        self.assertTrue(forbidden_fields.isdisjoint(built["body"]))

    def test_module_does_not_implement_signing_or_transport_execution(self):
        source = self._module_source()

        forbidden_snippets = (
            "Authorization",
            "signature",
            "signed_payload",
            "headers",
            "timeout",
            "transport",
            "network_sent",
            "send(",
            "execute(",
        )
        for snippet in forbidden_snippets:
            self.assertNotIn(snippet, source)

    def test_responses_do_not_include_credentials_or_secret_values(self):
        results = [
            self.client.accepted_fixture_response(_request()),
            self.client.rejected_fixture_response(_request()),
            self.client.failed_fixture_response(_request()),
            self.client.unexpected_fixture_response(_request()),
        ]

        forbidden_fragments = ("credential", "secret", "api_key", "api_secret", "password", "token")
        for result in results:
            for key, value in dataclasses.asdict(result).items():
                self.assertFalse(any(fragment in key.lower() for fragment in forbidden_fragments), key)
                self.assertFalse(any(fragment in str(value).lower() for fragment in forbidden_fragments), value)

    def test_request_and_response_shapes_do_not_include_credential_fields(self):
        request_fields = {field.name for field in dataclasses.fields(AlternativeTestnetHttpClientRequest)}
        built_request_fields = {field.name for field in dataclasses.fields(AlternativeTestnetHttpBuiltRequest)}
        response_fields = {
            field.name
            for field in dataclasses.fields(
                self.client.accepted_fixture_response(_request()).__class__,
            )
        }

        forbidden_fragments = ("credential", "secret", "api_key", "api_secret", "password", "token")
        for field_name in request_fields | built_request_fields | response_fields:
            self.assertFalse(
                any(fragment in field_name.lower() for fragment in forbidden_fragments),
                field_name,
            )

    def test_responses_do_not_imply_external_request(self):
        result = dataclasses.asdict(self.client.accepted_fixture_response(_request()))

        self.assertNotIn("network_request_sent", result)
        self.assertNotIn("http_status", result)
        self.assertNotIn("request_url", result)
        self.assertNotIn("external_request_sent", result)
        self.assertNotIn("external_request_started", result)

    def test_all_fixture_responses_avoid_external_request_evidence_fields(self):
        results = [
            self.client.accepted_fixture_response(_request()),
            self.client.rejected_fixture_response(_request()),
            self.client.failed_fixture_response(_request()),
            self.client.unexpected_fixture_response(_request()),
        ]
        forbidden_fields = {
            "network_request_sent",
            "http_status",
            "request_url",
            "external_request_sent",
            "external_request_started",
        }

        for result in results:
            self.assertTrue(forbidden_fields.isdisjoint(dataclasses.asdict(result)))

    def test_module_does_not_import_real_http_or_socket_libraries(self):
        imported = self._module_import_names()

        forbidden_imports = {"requests", "httpx", "aiohttp", "socket", "urllib.request"}
        self.assertTrue(forbidden_imports.isdisjoint(imported))

    def test_module_does_not_read_env_or_config(self):
        source = self._module_source()

        forbidden_snippets = (
            "os.environ",
            "getenv(",
            "dotenv",
            "configparser",
            "pydantic",
            "open(",
            "Path.home",
            "read_text(",
        )
        for snippet in forbidden_snippets:
            self.assertNotIn(snippet, source)

    def test_evidence_semantics_are_explicit_for_all_fixture_outcomes(self):
        accepted = self.client.accepted_fixture_response(_request())
        rejected = self.client.rejected_fixture_response(_request())
        failed = self.client.failed_fixture_response(_request())
        unexpected = self.client.unexpected_fixture_response(_request())

        self.assertEqual(accepted.status, "ACCEPTED")
        self.assertIsNotNone(accepted.external_order_id)
        self.assertTrue(accepted.external_order_id_present)

        for result in (rejected, failed, unexpected):
            self.assertIn(result.status, {"REJECTED", "FAILED"})
            self.assertIsNotNone(result.failure_family)
            self.assertIsNotNone(result.failure_reason)
            self.assertIsNone(result.external_order_id)
            self.assertFalse(result.external_order_id_present)


if __name__ == "__main__":
    unittest.main()
