import dataclasses
import ast
import inspect
import sys
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "anchor-backend" / "app" / "actions" / "alternative_testnet_http_client.py"
sys.path.insert(0, str(PROJECT_ROOT / "anchor-backend"))

from app.actions.alternative_testnet_http_client import (  # noqa: E402
    AlternativeTestnetHttpBuiltRequest,
    AlternativeTestnetHttpClientRequest,
    AlternativeTestnetHttpPipelineResult,
    AlternativeTestnetHttpRuntimeWiringResult,
    AlternativeTestnetHttpSigningInput,
    AlternativeTestnetHttpSigningMaterial,
    AlternativeTestnetHttpSigningResult,
    AlternativeTestnetHttpTransportInput,
    AlternativeTestnetHttpTransportResult,
    NoNetworkAlternativeTestnetHttpClient,
)
from app.actions import runner as domain_runner  # noqa: E402


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


def _signing_material(**overrides):
    payload = {
        "material_id": "mock-signing-material-v1",
        "authorization_header_value": "MockAuth explicit-material",
        "signature_value": "mock-signature-value",
    }
    payload.update(overrides)
    return AlternativeTestnetHttpSigningMaterial(**payload)


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
            "headers",
            "timeout",
            "send(",
            "execute(",
            "hmac",
            "private_key",
        )
        for snippet in forbidden_snippets:
            self.assertNotIn(snippet, source)

    def test_builds_deterministic_transport_input_shape(self):
        built = self.client.build_order_request(_request())
        first = self.client.build_transport_input(built)
        second = self.client.build_transport_input(built)

        self.assertIsInstance(first, AlternativeTestnetHttpTransportInput)
        self.assertEqual(dataclasses.asdict(first), dataclasses.asdict(second))
        self.assertEqual(first.method, built.method)
        self.assertEqual(first.path, built.path)
        self.assertEqual(first.idempotency_key, built.idempotency_key)
        self.assertEqual(first.client_order_ref, built.client_order_ref)
        self.assertEqual(first.body, built.body)

    def test_transport_input_preserves_builder_boundary_without_response_evidence(self):
        transport_input = self.client.build_transport_input(self.client.build_order_request(_request()))
        payload = dataclasses.asdict(transport_input)
        forbidden_fields = {
            "external_order_id",
            "external_order_id_present",
            "network_sent",
            "http_status",
            "request_url",
        }

        self.assertEqual(transport_input.idempotency_key, _request().idempotency_key)
        self.assertTrue(forbidden_fields.isdisjoint(payload))
        self.assertTrue(forbidden_fields.isdisjoint(payload["body"]))

    def test_transport_accepted_result_shape_requires_upstream_order_id(self):
        transport_input = self.client.build_transport_input(self.client.build_order_request(_request()))
        result = self.client.accepted_transport_result(
            transport_input,
            upstream_external_order_id="upstream-order-123",
        )

        self.assertIsInstance(result, AlternativeTestnetHttpTransportResult)
        self.assertEqual(result.status, "ACCEPTED")
        self.assertEqual(result.external_order_id, "upstream-order-123")
        self.assertTrue(result.external_order_id_present)
        self.assertFalse(result.network_sent)
        self.assertIsNone(result.failure_family)
        self.assertIsNone(result.failure_reason)

    def test_transport_rejected_result_shape_has_no_external_order_id(self):
        transport_input = self.client.build_transport_input(self.client.build_order_request(_request()))
        result = self.client.rejected_transport_result(transport_input)

        self.assertEqual(result.status, "REJECTED")
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)
        self.assertFalse(result.network_sent)
        self.assertEqual(result.failure_family, "ALTERNATIVE_TESTNET_HTTP_TRANSPORT_REJECTED")
        self.assertEqual(result.failure_reason, "alternative_testnet_http_transport_rejected")

    def test_transport_not_executed_result_shape_has_no_external_order_id(self):
        transport_input = self.client.build_transport_input(self.client.build_order_request(_request()))
        result = self.client.transport_not_executed_result(transport_input)

        self.assertEqual(result.status, "NOT_EXECUTED")
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)
        self.assertFalse(result.network_sent)
        self.assertEqual(result.failure_family, "ALTERNATIVE_TESTNET_HTTP_TRANSPORT_NOT_EXECUTED")
        self.assertEqual(result.failure_reason, "alternative_testnet_http_transport_not_executed")

    def test_transport_result_preserves_idempotency_and_context(self):
        transport_input = self.client.build_transport_input(
            self.client.build_order_request(
                _request(
                    idempotency_key="alternative:http:transport-context:v1",
                    venue="approved_alternative_testnet_custom",
                )
            )
        )
        results = [
            self.client.accepted_transport_result(transport_input, "upstream-order-123"),
            self.client.rejected_transport_result(transport_input),
            self.client.transport_not_executed_result(transport_input),
        ]

        for result in results:
            self.assertEqual(result.idempotency_key, "alternative:http:transport-context:v1")
            self.assertEqual(result.venue, "approved_alternative_testnet_custom")
            self.assertEqual(result.execution_mode, "testnet")

    def test_transport_shapes_do_not_include_credentials_or_signing_fields(self):
        transport_input = self.client.build_transport_input(self.client.build_order_request(_request()))
        shapes = [
            dataclasses.asdict(transport_input),
            dataclasses.asdict(self.client.accepted_transport_result(transport_input, "upstream-order-123")),
            dataclasses.asdict(self.client.rejected_transport_result(transport_input)),
            dataclasses.asdict(self.client.transport_not_executed_result(transport_input)),
        ]
        forbidden_fragments = (
            "authorization",
            "signature",
            "signed",
            "credential",
            "secret",
            "api_key",
            "api_secret",
            "password",
            "token",
        )

        def assert_no_forbidden(value):
            if isinstance(value, dict):
                for key, nested_value in value.items():
                    self.assertFalse(any(fragment in key.lower() for fragment in forbidden_fragments), key)
                    assert_no_forbidden(nested_value)
                return
            self.assertFalse(any(fragment in str(value).lower() for fragment in forbidden_fragments), value)

        for shape in shapes:
            assert_no_forbidden(shape)

    def test_builds_deterministic_signing_input_shape(self):
        transport_input = self.client.build_transport_input(self.client.build_order_request(_request()))
        material = _signing_material()
        first = self.client.build_signing_input(transport_input, material)
        second = self.client.build_signing_input(transport_input, material)

        self.assertIsInstance(first, AlternativeTestnetHttpSigningInput)
        self.assertEqual(dataclasses.asdict(first), dataclasses.asdict(second))
        self.assertEqual(first.idempotency_key, transport_input.idempotency_key)
        self.assertEqual(first.method, transport_input.method)
        self.assertEqual(first.path, transport_input.path)
        self.assertEqual(first.body, transport_input.body)
        self.assertEqual(first.material_id, material.material_id)

    def test_signed_request_shape_uses_explicit_material_only(self):
        transport_input = self.client.build_transport_input(self.client.build_order_request(_request()))
        material = _signing_material()
        signing_input = self.client.build_signing_input(transport_input, material)
        result = self.client.signed_request_result(signing_input, material)

        self.assertIsInstance(result, AlternativeTestnetHttpSigningResult)
        self.assertEqual(result.status, "SIGNED")
        self.assertEqual(result.material_id, "mock-signing-material-v1")
        self.assertEqual(result.authorization_header_value, "MockAuth explicit-material")
        self.assertEqual(result.signature_value, "mock-signature-value")
        self.assertEqual(result.body, transport_input.body)

    def test_signing_not_executed_shape_has_no_authorization_or_signature(self):
        transport_input = self.client.build_transport_input(self.client.build_order_request(_request()))
        result = self.client.signing_not_executed_result(transport_input)

        self.assertEqual(result.status, "NOT_EXECUTED")
        self.assertIsNone(result.material_id)
        self.assertIsNone(result.authorization_header_value)
        self.assertIsNone(result.signature_value)
        self.assertEqual(result.failure_family, "ALTERNATIVE_TESTNET_HTTP_SIGNING_NOT_EXECUTED")
        self.assertEqual(result.failure_reason, "alternative_testnet_http_signing_not_executed")

    def test_signing_preserves_idempotency_body_and_context(self):
        transport_input = self.client.build_transport_input(
            self.client.build_order_request(
                _request(
                    idempotency_key="alternative:http:signing-context:v1",
                    venue="approved_alternative_testnet_custom",
                )
            )
        )
        material = _signing_material(material_id="mock-material-custom")
        signing_input = self.client.build_signing_input(transport_input, material)
        signed = self.client.signed_request_result(signing_input, material)
        not_executed = self.client.signing_not_executed_result(transport_input)

        for result in (signed, not_executed):
            self.assertEqual(result.idempotency_key, "alternative:http:signing-context:v1")
            self.assertEqual(result.venue, "approved_alternative_testnet_custom")
            self.assertEqual(result.execution_mode, "testnet")
            self.assertEqual(result.body, transport_input.body)

    def test_signing_shapes_do_not_create_external_order_or_network_sent(self):
        transport_input = self.client.build_transport_input(self.client.build_order_request(_request()))
        material = _signing_material()
        signing_input = self.client.build_signing_input(transport_input, material)
        results = [
            self.client.signed_request_result(signing_input, material),
            self.client.signing_not_executed_result(transport_input),
        ]

        for result in results:
            self.assertFalse(result.network_sent)
            self.assertIsNone(result.external_order_id)
            self.assertFalse(result.external_order_id_present)

    def test_signing_shapes_do_not_include_real_credential_fields(self):
        transport_input = self.client.build_transport_input(self.client.build_order_request(_request()))
        material = _signing_material()
        signing_input = self.client.build_signing_input(transport_input, material)
        shapes = [
            dataclasses.asdict(material),
            dataclasses.asdict(signing_input),
            dataclasses.asdict(self.client.signed_request_result(signing_input, material)),
            dataclasses.asdict(self.client.signing_not_executed_result(transport_input)),
        ]
        forbidden_fragments = ("credential", "secret", "api_key", "api_secret", "password", "token")

        def assert_no_forbidden(value):
            if isinstance(value, dict):
                for key, nested_value in value.items():
                    self.assertFalse(any(fragment in key.lower() for fragment in forbidden_fragments), key)
                    assert_no_forbidden(nested_value)
                return
            self.assertFalse(any(fragment in str(value).lower() for fragment in forbidden_fragments), value)

        for shape in shapes:
            assert_no_forbidden(shape)

    def test_composed_pipeline_build_only_shape(self):
        result = self.client.build_only_pipeline_result(_request())

        self.assertIsInstance(result, AlternativeTestnetHttpPipelineResult)
        self.assertEqual(result.status, "BUILT")
        self.assertEqual(result.idempotency_key, _request().idempotency_key)
        self.assertEqual(result.method, "POST")
        self.assertEqual(result.path, "/testnet/orders")
        self.assertEqual(result.body["idempotency_key"], _request().idempotency_key)
        self.assertIsNone(result.material_id)
        self.assertIsNone(result.authorization_header_value)
        self.assertIsNone(result.signature_value)
        self.assertFalse(result.network_sent)
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)

    def test_composed_pipeline_signed_not_sent_shape(self):
        material = _signing_material()
        result = self.client.signed_not_sent_pipeline_result(_request(), material)

        self.assertEqual(result.status, "SIGNED")
        self.assertEqual(result.material_id, material.material_id)
        self.assertEqual(result.authorization_header_value, material.authorization_header_value)
        self.assertEqual(result.signature_value, material.signature_value)
        self.assertEqual(result.idempotency_key, _request().idempotency_key)
        self.assertEqual(result.body["idempotency_key"], _request().idempotency_key)
        self.assertFalse(result.network_sent)
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)

    def test_composed_pipeline_transport_not_executed_shape(self):
        result = self.client.transport_not_executed_pipeline_result(_request(), _signing_material())

        self.assertEqual(result.status, "NOT_EXECUTED")
        self.assertEqual(result.failure_family, "ALTERNATIVE_TESTNET_HTTP_TRANSPORT_NOT_EXECUTED")
        self.assertEqual(result.failure_reason, "alternative_testnet_http_transport_not_executed")
        self.assertFalse(result.network_sent)
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)

    def test_composed_pipeline_accepted_shape_uses_upstream_like_response_only(self):
        result = self.client.accepted_pipeline_result(
            _request(),
            _signing_material(),
            upstream_external_order_id="upstream-order-accepted-1",
        )

        self.assertEqual(result.status, "ACCEPTED")
        self.assertEqual(result.external_order_id, "upstream-order-accepted-1")
        self.assertTrue(result.external_order_id_present)
        self.assertFalse(result.network_sent)
        self.assertIsNone(result.failure_family)
        self.assertIsNone(result.failure_reason)

    def test_composed_pipeline_rejected_shape_has_no_external_order_id(self):
        result = self.client.rejected_pipeline_result(_request(), _signing_material())

        self.assertEqual(result.status, "REJECTED")
        self.assertEqual(result.failure_family, "ALTERNATIVE_TESTNET_HTTP_TRANSPORT_REJECTED")
        self.assertEqual(result.failure_reason, "alternative_testnet_http_transport_rejected")
        self.assertFalse(result.network_sent)
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)

    def test_composed_pipeline_preserves_idempotency_end_to_end(self):
        request = _request(
            idempotency_key="alternative:http:pipeline-context:v1",
            venue="approved_alternative_testnet_custom",
        )
        material = _signing_material(material_id="mock-material-pipeline")
        results = [
            self.client.build_only_pipeline_result(request),
            self.client.signed_not_sent_pipeline_result(request, material),
            self.client.transport_not_executed_pipeline_result(request, material),
            self.client.accepted_pipeline_result(request, material, "upstream-order-pipeline-1"),
            self.client.rejected_pipeline_result(request, material),
        ]

        for result in results:
            self.assertEqual(result.idempotency_key, "alternative:http:pipeline-context:v1")
            self.assertEqual(result.venue, "approved_alternative_testnet_custom")
            self.assertEqual(result.execution_mode, "testnet")
            self.assertEqual(result.body["idempotency_key"], "alternative:http:pipeline-context:v1")

    def test_composed_pipeline_does_not_create_external_order_before_upstream_like_response(self):
        request = _request()
        material = _signing_material()
        pre_response_results = [
            self.client.build_only_pipeline_result(request),
            self.client.signed_not_sent_pipeline_result(request, material),
            self.client.transport_not_executed_pipeline_result(request, material),
            self.client.rejected_pipeline_result(request, material),
        ]

        for result in pre_response_results:
            self.assertIsNone(result.external_order_id)
            self.assertFalse(result.external_order_id_present)

    def test_composed_pipeline_never_marks_network_sent(self):
        request = _request()
        material = _signing_material()
        results = [
            self.client.build_only_pipeline_result(request),
            self.client.signed_not_sent_pipeline_result(request, material),
            self.client.transport_not_executed_pipeline_result(request, material),
            self.client.accepted_pipeline_result(request, material, "upstream-order-accepted-1"),
            self.client.rejected_pipeline_result(request, material),
        ]

        for result in results:
            self.assertFalse(result.network_sent)

    def test_composed_pipeline_shapes_do_not_include_real_credentials(self):
        request = _request()
        material = _signing_material()
        shapes = [
            dataclasses.asdict(self.client.build_only_pipeline_result(request)),
            dataclasses.asdict(self.client.signed_not_sent_pipeline_result(request, material)),
            dataclasses.asdict(self.client.transport_not_executed_pipeline_result(request, material)),
            dataclasses.asdict(self.client.accepted_pipeline_result(request, material, "upstream-order-accepted-1")),
            dataclasses.asdict(self.client.rejected_pipeline_result(request, material)),
        ]
        forbidden_fragments = ("credential", "secret", "api_key", "api_secret", "password", "token")

        def assert_no_forbidden(value):
            if isinstance(value, dict):
                for key, nested_value in value.items():
                    self.assertFalse(any(fragment in key.lower() for fragment in forbidden_fragments), key)
                    assert_no_forbidden(nested_value)
                return
            self.assertFalse(any(fragment in str(value).lower() for fragment in forbidden_fragments), value)

        for shape in shapes:
            assert_no_forbidden(shape)

    def test_future_execution_adapter_contract_input_shape_is_local_pipeline_result(self):
        result = self.client.signed_not_sent_pipeline_result(_request(), _signing_material())
        field_names = {field.name for field in dataclasses.fields(AlternativeTestnetHttpPipelineResult)}

        self.assertIn("idempotency_key", field_names)
        self.assertIn("venue", field_names)
        self.assertIn("execution_mode", field_names)
        self.assertIn("status", field_names)
        self.assertIn("body", field_names)
        self.assertEqual(result.status, "SIGNED")
        self.assertEqual(result.idempotency_key, _request().idempotency_key)
        self.assertEqual(result.venue, _request().venue)
        self.assertEqual(result.execution_mode, _request().execution_mode)

    def test_future_execution_adapter_contract_output_shape_preserves_pipeline_evidence(self):
        accepted = self.client.accepted_pipeline_result(
            _request(),
            _signing_material(),
            upstream_external_order_id="upstream-order-adapter-contract-1",
        )
        rejected = self.client.rejected_pipeline_result(_request(), _signing_material())

        self.assertEqual(accepted.status, "ACCEPTED")
        self.assertEqual(accepted.external_order_id, "upstream-order-adapter-contract-1")
        self.assertTrue(accepted.external_order_id_present)
        self.assertFalse(accepted.network_sent)

        self.assertEqual(rejected.status, "REJECTED")
        self.assertIsNone(rejected.external_order_id)
        self.assertFalse(rejected.external_order_id_present)
        self.assertFalse(rejected.network_sent)
        self.assertEqual(rejected.failure_family, "ALTERNATIVE_TESTNET_HTTP_TRANSPORT_REJECTED")

    def test_future_execution_adapter_boundary_keeps_no_external_order_before_upstream_response(self):
        request = _request()
        material = _signing_material()
        pre_upstream_shapes = [
            self.client.build_only_pipeline_result(request),
            self.client.signed_not_sent_pipeline_result(request, material),
            self.client.transport_not_executed_pipeline_result(request, material),
        ]

        for result in pre_upstream_shapes:
            self.assertIsNone(result.external_order_id)
            self.assertFalse(result.external_order_id_present)
            self.assertFalse(result.network_sent)

    def test_future_execution_adapter_boundary_has_no_runtime_integration_code(self):
        source = self._module_source()
        forbidden_snippets = (
            "commands_domain",
            "domain_command_worker",
            "register_executor",
            "runtime_path_enabled=True",
            "enable_runtime_path",
            "runner.execute",
            "worker.enqueue",
            "risk.check",
        )

        for snippet in forbidden_snippets:
            self.assertNotIn(snippet, source)

    def test_runtime_wiring_gap_review_keeps_http_client_module_disabled(self):
        source = self._module_source()
        forbidden_snippets = (
            "runtime_enabled",
            "runtime_path_enabled=True",
            "enable_runtime_path",
            "register_runtime",
            "CommandWorker",
            "DomainCommand",
            "enqueue_command",
            "dispatch_command",
            "start_worker",
        )

        for snippet in forbidden_snippets:
            self.assertNotIn(snippet, source)

    def test_runtime_wiring_gap_review_requires_disabled_state_evidence(self):
        request = _request(idempotency_key="alternative:http:runtime-gap:v1")
        material = _signing_material(material_id="mock-material-runtime-gap")
        evidence = [
            self.client.signed_not_sent_pipeline_result(request, material),
            self.client.transport_not_executed_pipeline_result(request, material),
            self.client.rejected_pipeline_result(request, material),
        ]

        for result in evidence:
            self.assertEqual(result.idempotency_key, "alternative:http:runtime-gap:v1")
            self.assertFalse(result.network_sent)
            self.assertFalse(result.external_order_id_present)
            self.assertIsNone(result.external_order_id)

    def test_runtime_wiring_gap_review_keeps_canary_and_external_request_fields_absent(self):
        result = dataclasses.asdict(
            self.client.transport_not_executed_pipeline_result(_request(), _signing_material())
        )
        forbidden_fields = {
            "canary_enabled",
            "canary_executed",
            "external_request_sent",
            "external_request_started",
            "runtime_path_enabled",
            "runner_id",
            "worker_id",
        }

        self.assertTrue(forbidden_fields.isdisjoint(result))
        self.assertTrue(forbidden_fields.isdisjoint(result["body"]))

    def test_runtime_wiring_preimplementation_guardrail_blocks_early_wiring_tokens(self):
        source = self._module_source()
        forbidden_snippets = (
            "runner.execute",
            "worker.enqueue",
            "risk.check",
            "enable_runtime_path",
            "runtime_path_enabled=True",
            "external_request_sent=True",
            "canary_executed=True",
            "requests.",
            "httpx.",
            "aiohttp.",
            "urllib.request",
            "socket.socket",
            "os.environ",
            "getenv(",
            "hmac.",
            "private_key",
        )

        for snippet in forbidden_snippets:
            self.assertNotIn(snippet, source)

    def test_runtime_wiring_preimplementation_guardrail_preserves_disabled_state(self):
        request = _request(idempotency_key="alternative:http:preimplementation-guardrail:v1")
        material = _signing_material(material_id="mock-material-preimplementation-guardrail")
        evidence = {
            "signed_not_sent": self.client.signed_not_sent_pipeline_result(request, material),
            "transport_not_executed": self.client.transport_not_executed_pipeline_result(request, material),
            "rejected": self.client.rejected_pipeline_result(request, material),
        }

        for result in evidence.values():
            self.assertEqual(result.idempotency_key, "alternative:http:preimplementation-guardrail:v1")
            self.assertFalse(result.network_sent)
            self.assertFalse(result.external_order_id_present)
            self.assertIsNone(result.external_order_id)

        self.assertEqual(evidence["transport_not_executed"].status, "NOT_EXECUTED")
        self.assertEqual(evidence["rejected"].status, "REJECTED")

    def test_runtime_wiring_preimplementation_guardrail_keeps_runtime_fields_absent(self):
        result = dataclasses.asdict(
            self.client.signed_not_sent_pipeline_result(_request(), _signing_material())
        )
        forbidden_fields = {
            "runtime_enabled",
            "runtime_path_enabled",
            "runner_modified",
            "worker_modified",
            "risk_modified",
            "credential_loaded",
            "env_loaded",
            "real_signing_enabled",
            "network_behavior_enabled",
            "external_request_sent",
            "canary_retried",
        }

        self.assertTrue(forbidden_fields.isdisjoint(result))
        self.assertTrue(forbidden_fields.isdisjoint(result["body"]))

    def test_minimal_runtime_wiring_disabled_result_shape_is_default_disabled(self):
        result = self.client.runtime_disabled_result(
            _request(idempotency_key="alternative:http:runtime-disabled:v1")
        )
        field_names = {field.name for field in dataclasses.fields(AlternativeTestnetHttpRuntimeWiringResult)}

        self.assertIn("runtime_path_enabled", field_names)
        self.assertEqual(result.status, "DISABLED")
        self.assertEqual(result.idempotency_key, "alternative:http:runtime-disabled:v1")
        self.assertEqual(result.venue, "approved_alternative_testnet")
        self.assertEqual(result.execution_mode, "testnet")
        self.assertEqual(result.disabled_reason, "alternative_testnet_http_runtime_disabled")
        self.assertEqual(result.disabled_stage, "runtime_wiring")
        self.assertFalse(result.runtime_path_enabled)
        self.assertFalse(result.composed_pipeline_executed)
        self.assertFalse(result.signing_executed)
        self.assertFalse(result.transport_executed)
        self.assertFalse(result.network_sent)
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)
        self.assertEqual(result.failure_family, "ALTERNATIVE_TESTNET_HTTP_RUNTIME_DISABLED")
        self.assertEqual(result.failure_reason, "alternative_testnet_http_runtime_disabled")

    def test_minimal_runtime_wiring_not_enabled_and_not_wired_shapes_are_terminal_disabled(self):
        not_enabled = self.client.runtime_not_enabled_result(_request())
        not_wired = self.client.runtime_not_wired_result(_request())

        self.assertEqual(not_enabled.status, "NOT_ENABLED")
        self.assertEqual(not_enabled.disabled_reason, "alternative_testnet_http_runtime_not_enabled")
        self.assertEqual(not_enabled.disabled_stage, "runtime_wiring")
        self.assertEqual(not_enabled.failure_family, "ALTERNATIVE_TESTNET_HTTP_RUNTIME_NOT_ENABLED")
        self.assertEqual(not_enabled.failure_reason, "alternative_testnet_http_runtime_not_enabled")

        self.assertEqual(not_wired.status, "NOT_WIRED")
        self.assertEqual(not_wired.disabled_reason, "alternative_testnet_http_runtime_not_wired")
        self.assertEqual(not_wired.disabled_stage, "runtime_wiring")
        self.assertEqual(not_wired.failure_family, "ALTERNATIVE_TESTNET_HTTP_RUNTIME_NOT_WIRED")
        self.assertEqual(not_wired.failure_reason, "alternative_testnet_http_runtime_not_wired")

        for result in (not_enabled, not_wired):
            self.assertFalse(result.runtime_path_enabled)
            self.assertFalse(result.composed_pipeline_executed)
            self.assertFalse(result.signing_executed)
            self.assertFalse(result.transport_executed)
            self.assertFalse(result.network_sent)
            self.assertIsNone(result.external_order_id)
            self.assertFalse(result.external_order_id_present)

    def test_minimal_runtime_wiring_disabled_shapes_do_not_execute_pipeline_signing_or_transport(self):
        results = [
            self.client.runtime_disabled_result(_request()),
            self.client.runtime_not_enabled_result(_request()),
            self.client.runtime_not_wired_result(_request()),
        ]

        for result in results:
            self.assertFalse(result.runtime_path_enabled)
            self.assertFalse(result.composed_pipeline_executed)
            self.assertFalse(result.signing_executed)
            self.assertFalse(result.transport_executed)
            self.assertFalse(result.network_sent)

    def test_minimal_runtime_wiring_disabled_shapes_do_not_include_credentials_or_enabled_runtime(self):
        shapes = [
            dataclasses.asdict(self.client.runtime_disabled_result(_request())),
            dataclasses.asdict(self.client.runtime_not_enabled_result(_request())),
            dataclasses.asdict(self.client.runtime_not_wired_result(_request())),
        ]
        forbidden_fields = {
            "credential_loaded",
            "env_loaded",
            "real_signing_enabled",
            "network_behavior_enabled",
            "external_request_sent",
            "canary_retried",
            "runner_id",
            "worker_id",
            "risk_id",
        }

        for shape in shapes:
            self.assertTrue(forbidden_fields.isdisjoint(shape))
            self.assertFalse(shape["runtime_path_enabled"])
            self.assertFalse(shape["network_sent"])
            self.assertIsNone(shape["external_order_id"])

    def test_disabled_runtime_observability_shape_is_audit_friendly(self):
        result = dataclasses.asdict(
            self.client.runtime_disabled_result(
                _request(idempotency_key="alternative:http:disabled-observability:v1")
            )
        )

        self.assertEqual(result["idempotency_key"], "alternative:http:disabled-observability:v1")
        self.assertEqual(result["status"], "DISABLED")
        self.assertEqual(result["disabled_reason"], "alternative_testnet_http_runtime_disabled")
        self.assertEqual(result["disabled_stage"], "runtime_wiring")
        self.assertFalse(result["runtime_path_enabled"])
        self.assertFalse(result["network_sent"])
        self.assertFalse(result["external_order_id_present"])
        self.assertIsNone(result["external_order_id"])
        self.assertFalse(result["composed_pipeline_executed"])
        self.assertFalse(result["signing_executed"])
        self.assertFalse(result["transport_executed"])

    def test_disabled_runtime_observability_covers_all_disabled_status_reasons(self):
        cases = {
            "DISABLED": self.client.runtime_disabled_result(_request()),
            "NOT_ENABLED": self.client.runtime_not_enabled_result(_request()),
            "NOT_WIRED": self.client.runtime_not_wired_result(_request()),
        }

        for status, result in cases.items():
            self.assertEqual(result.status, status)
            self.assertEqual(result.disabled_stage, "runtime_wiring")
            self.assertTrue(result.disabled_reason.startswith("alternative_testnet_http_runtime_"))
            self.assertEqual(result.disabled_reason, result.failure_reason)
            self.assertFalse(result.runtime_path_enabled)
            self.assertFalse(result.network_sent)
            self.assertFalse(result.external_order_id_present)

    def test_disabled_runtime_observability_does_not_mask_execution_evidence(self):
        result = self.client.runtime_disabled_result(_request())

        self.assertFalse(result.composed_pipeline_executed)
        self.assertFalse(result.signing_executed)
        self.assertFalse(result.transport_executed)
        self.assertEqual(result.disabled_stage, "runtime_wiring")
        self.assertEqual(result.failure_family, "ALTERNATIVE_TESTNET_HTTP_RUNTIME_DISABLED")

    def test_disabled_runtime_guardrail_requires_audit_fields(self):
        field_names = {field.name for field in dataclasses.fields(AlternativeTestnetHttpRuntimeWiringResult)}
        required_fields = {
            "disabled_reason",
            "disabled_stage",
            "network_sent",
            "external_order_id_present",
            "composed_pipeline_executed",
            "signing_executed",
            "transport_executed",
        }

        self.assertTrue(required_fields.issubset(field_names))

    def test_disabled_runtime_guardrail_blocks_execution_regressions(self):
        results = [
            self.client.runtime_disabled_result(_request()),
            self.client.runtime_not_enabled_result(_request()),
            self.client.runtime_not_wired_result(_request()),
        ]

        for result in results:
            self.assertFalse(result.composed_pipeline_executed)
            self.assertFalse(result.signing_executed)
            self.assertFalse(result.transport_executed)
            self.assertFalse(result.runtime_path_enabled)
            self.assertFalse(result.network_sent)

    def test_disabled_runtime_guardrail_blocks_external_order_and_network_regressions(self):
        results = [
            dataclasses.asdict(self.client.runtime_disabled_result(_request())),
            dataclasses.asdict(self.client.runtime_not_enabled_result(_request())),
            dataclasses.asdict(self.client.runtime_not_wired_result(_request())),
        ]

        for result in results:
            self.assertEqual(result["disabled_stage"], "runtime_wiring")
            self.assertTrue(result["disabled_reason"])
            self.assertIsNone(result["external_order_id"])
            self.assertFalse(result["external_order_id_present"])
            self.assertFalse(result["network_sent"])
            self.assertNotIn("network_request_sent", result)
            self.assertNotIn("external_request_sent", result)
            self.assertNotIn("external_request_started", result)

    def test_disabled_runtime_status_surface_marks_skeleton_present_and_runtime_disabled(self):
        result = self.client.runtime_disabled_result(_request())
        status_surface = {
            "skeleton_present": isinstance(self.client, NoNetworkAlternativeTestnetHttpClient),
            "runtime_disabled": not result.runtime_path_enabled,
            "status": result.status,
            "disabled_reason": result.disabled_reason,
            "disabled_stage": result.disabled_stage,
        }

        self.assertTrue(status_surface["skeleton_present"])
        self.assertTrue(status_surface["runtime_disabled"])
        self.assertEqual(status_surface["status"], "DISABLED")
        self.assertEqual(status_surface["disabled_reason"], "alternative_testnet_http_runtime_disabled")
        self.assertEqual(status_surface["disabled_stage"], "runtime_wiring")

    def test_disabled_runtime_status_surface_preserves_non_execution_status(self):
        result = self.client.runtime_disabled_result(_request())
        status_surface = {
            "network_sent": result.network_sent,
            "external_order_id_present": result.external_order_id_present,
            "composed_pipeline_executed": result.composed_pipeline_executed,
            "signing_executed": result.signing_executed,
            "transport_executed": result.transport_executed,
        }

        self.assertFalse(status_surface["network_sent"])
        self.assertFalse(status_surface["external_order_id_present"])
        self.assertFalse(status_surface["composed_pipeline_executed"])
        self.assertFalse(status_surface["signing_executed"])
        self.assertFalse(status_surface["transport_executed"])

    def test_runtime_enablement_minimal_result_defaults_to_not_enabled(self):
        result = self.client.runtime_enablement_minimal_result(
            _request(idempotency_key="alternative:http:minimal-enable-disabled:v1")
        )

        self.assertIsInstance(result, AlternativeTestnetHttpRuntimeWiringResult)
        self.assertEqual(result.status, "NOT_ENABLED")
        self.assertEqual(result.idempotency_key, "alternative:http:minimal-enable-disabled:v1")
        self.assertEqual(result.disabled_reason, "alternative_testnet_http_runtime_not_enabled")
        self.assertEqual(result.disabled_stage, "runtime_wiring")
        self.assertFalse(result.runtime_path_enabled)
        self.assertFalse(result.composed_pipeline_executed)
        self.assertFalse(result.signing_executed)
        self.assertFalse(result.transport_executed)
        self.assertFalse(result.network_sent)
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)

    def test_runtime_enablement_minimal_result_is_deterministic_disabled_shape(self):
        first = self.client.runtime_enablement_minimal_result(_request())
        second = self.client.runtime_enablement_minimal_result(_request())
        not_wired = self.client.runtime_not_wired_result(_request())

        self.assertEqual(dataclasses.asdict(first), dataclasses.asdict(second))
        self.assertEqual(not_wired.status, "NOT_WIRED")
        for result in (first, not_wired):
            self.assertFalse(result.runtime_path_enabled)
            self.assertFalse(result.composed_pipeline_executed)
            self.assertFalse(result.signing_executed)
            self.assertFalse(result.transport_executed)
            self.assertFalse(result.network_sent)
            self.assertIsNone(result.external_order_id)
            self.assertFalse(result.external_order_id_present)

    def test_runtime_enablement_minimal_result_does_not_execute_pipeline_signing_or_transport(self):
        class SpyClient(NoNetworkAlternativeTestnetHttpClient):
            def __init__(self):
                self.calls = []

            def build_only_pipeline_result(self, request):
                self.calls.append("build_only_pipeline_result")
                return super().build_only_pipeline_result(request)

            def signed_not_sent_pipeline_result(self, request, material):
                self.calls.append("signed_not_sent_pipeline_result")
                return super().signed_not_sent_pipeline_result(request, material)

            def transport_not_executed_pipeline_result(self, request, material):
                self.calls.append("transport_not_executed_pipeline_result")
                return super().transport_not_executed_pipeline_result(request, material)

            def build_signing_input(self, transport_input, material):
                self.calls.append("build_signing_input")
                return super().build_signing_input(transport_input, material)

            def signed_request_result(self, signing_input, material):
                self.calls.append("signed_request_result")
                return super().signed_request_result(signing_input, material)

            def transport_not_executed_result(self, transport_input):
                self.calls.append("transport_not_executed_result")
                return super().transport_not_executed_result(transport_input)

        spy = SpyClient()
        result = spy.runtime_enablement_minimal_result(_request())

        self.assertEqual(spy.calls, [])
        self.assertEqual(result.status, "NOT_ENABLED")
        self.assertFalse(result.runtime_path_enabled)
        self.assertFalse(result.composed_pipeline_executed)
        self.assertFalse(result.signing_executed)
        self.assertFalse(result.transport_executed)
        self.assertFalse(result.network_sent)
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)

    def test_disabled_by_default_runtime_enablement_gate_defaults_to_not_enabled(self):
        result = self.client.disabled_by_default_runtime_enablement_result(
            _request(idempotency_key="alternative:http:disabled-by-default-gate:v1")
        )

        self.assertEqual(result.status, "NOT_ENABLED")
        self.assertEqual(result.disabled_reason, "alternative_testnet_http_runtime_not_enabled")
        self.assertEqual(result.disabled_stage, "runtime_wiring")
        self.assertFalse(result.runtime_path_enabled)
        self.assertFalse(result.composed_pipeline_executed)
        self.assertFalse(result.signing_executed)
        self.assertFalse(result.transport_executed)
        self.assertFalse(result.network_sent)
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)

    def test_disabled_by_default_runtime_enablement_gate_accepts_only_disabled_local_states(self):
        cases = [
            ({"state": "disabled"}, "DISABLED", "alternative_testnet_http_runtime_disabled"),
            ({"state": "not_enabled"}, "NOT_ENABLED", "alternative_testnet_http_runtime_not_enabled"),
            ({"state": "not_wired"}, "NOT_WIRED", "alternative_testnet_http_runtime_not_wired"),
            ({"action": "observe_only"}, "DISABLED", "alternative_testnet_http_runtime_disabled"),
        ]

        for enablement_input, expected_status, expected_reason in cases:
            with self.subTest(enablement_input=enablement_input):
                result = self.client.disabled_by_default_runtime_enablement_result(
                    _request(),
                    enablement_input=enablement_input,
                )

                self.assertEqual(result.status, expected_status)
                self.assertEqual(result.disabled_reason, expected_reason)
                self.assertFalse(result.runtime_path_enabled)
                self.assertFalse(result.signing_executed)
                self.assertFalse(result.transport_executed)
                self.assertFalse(result.network_sent)
                self.assertIsNone(result.external_order_id)
                self.assertFalse(result.external_order_id_present)

    def test_disabled_by_default_runtime_enablement_gate_fails_closed_for_malformed_input(self):
        result = self.client.disabled_by_default_runtime_enablement_result(
            _request(idempotency_key="alternative:http:malformed-enable-gate:v1"),
            enablement_input="malformed",
        )

        self.assertEqual(result.status, "DISABLED")
        self.assertEqual(
            result.failure_family,
            "ALTERNATIVE_TESTNET_HTTP_RUNTIME_ENABLEMENT_MALFORMED",
        )
        self.assertEqual(
            result.failure_reason,
            "alternative_testnet_http_runtime_enablement_malformed",
        )
        self.assertFalse(result.runtime_path_enabled)
        self.assertFalse(result.composed_pipeline_executed)
        self.assertFalse(result.signing_executed)
        self.assertFalse(result.transport_executed)
        self.assertFalse(result.network_sent)
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)

    def test_disabled_by_default_runtime_enablement_gate_fails_closed_for_unsupported_input(self):
        result = self.client.disabled_by_default_runtime_enablement_result(
            _request(idempotency_key="alternative:http:unsupported-enable-gate:v1"),
            enablement_input={"state": "requested", "action": "start"},
        )

        self.assertEqual(result.status, "DISABLED")
        self.assertEqual(
            result.failure_family,
            "ALTERNATIVE_TESTNET_HTTP_RUNTIME_ENABLEMENT_UNSUPPORTED",
        )
        self.assertEqual(
            result.failure_reason,
            "alternative_testnet_http_runtime_enablement_unsupported",
        )
        self.assertFalse(result.runtime_path_enabled)
        self.assertFalse(result.composed_pipeline_executed)
        self.assertFalse(result.signing_executed)
        self.assertFalse(result.transport_executed)
        self.assertFalse(result.network_sent)
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)

    def test_disabled_by_default_runtime_enablement_gate_does_not_execute_pipeline_signing_or_transport(self):
        class SpyClient(NoNetworkAlternativeTestnetHttpClient):
            def __init__(self):
                self.calls = []

            def build_only_pipeline_result(self, request):
                self.calls.append("build_only_pipeline_result")
                return super().build_only_pipeline_result(request)

            def signed_not_sent_pipeline_result(self, request, material):
                self.calls.append("signed_not_sent_pipeline_result")
                return super().signed_not_sent_pipeline_result(request, material)

            def transport_not_executed_pipeline_result(self, request, material):
                self.calls.append("transport_not_executed_pipeline_result")
                return super().transport_not_executed_pipeline_result(request, material)

            def build_signing_input(self, transport_input, material):
                self.calls.append("build_signing_input")
                return super().build_signing_input(transport_input, material)

            def signed_request_result(self, signing_input, material):
                self.calls.append("signed_request_result")
                return super().signed_request_result(signing_input, material)

            def transport_not_executed_result(self, transport_input):
                self.calls.append("transport_not_executed_result")
                return super().transport_not_executed_result(transport_input)

        spy = SpyClient()
        results = [
            spy.disabled_by_default_runtime_enablement_result(_request()),
            spy.disabled_by_default_runtime_enablement_result(_request(), {"state": "disabled"}),
            spy.disabled_by_default_runtime_enablement_result(_request(), {"state": "requested"}),
            spy.disabled_by_default_runtime_enablement_result(_request(), "malformed"),
        ]

        self.assertEqual(spy.calls, [])
        for result in results:
            self.assertFalse(result.runtime_path_enabled)
            self.assertFalse(result.composed_pipeline_executed)
            self.assertFalse(result.signing_executed)
            self.assertFalse(result.transport_executed)
            self.assertFalse(result.network_sent)
            self.assertIsNone(result.external_order_id)
            self.assertFalse(result.external_order_id_present)

    def test_runtime_enablement_integration_disabled_result_defaults_to_not_wired(self):
        result = self.client.runtime_enablement_integration_disabled_result(
            _request(idempotency_key="alternative:http:integration-disabled:v1")
        )

        self.assertIsInstance(result, AlternativeTestnetHttpRuntimeWiringResult)
        self.assertEqual(result.status, "NOT_WIRED")
        self.assertEqual(result.idempotency_key, "alternative:http:integration-disabled:v1")
        self.assertEqual(result.disabled_reason, "alternative_testnet_http_runtime_not_wired")
        self.assertEqual(result.disabled_stage, "runtime_wiring")
        self.assertFalse(result.runtime_path_enabled)
        self.assertFalse(result.composed_pipeline_executed)
        self.assertFalse(result.signing_executed)
        self.assertFalse(result.transport_executed)
        self.assertFalse(result.network_sent)
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)

    def test_runtime_enablement_integration_disabled_result_is_deterministic(self):
        first = self.client.runtime_enablement_integration_disabled_result(_request())
        second = self.client.runtime_enablement_integration_disabled_result(_request())

        self.assertEqual(dataclasses.asdict(first), dataclasses.asdict(second))
        self.assertEqual(first.status, "NOT_WIRED")
        self.assertFalse(first.runtime_path_enabled)
        self.assertFalse(first.network_sent)
        self.assertIsNone(first.external_order_id)
        self.assertFalse(first.external_order_id_present)

    def test_runtime_enablement_integration_disabled_result_does_not_execute_pipeline_signing_or_transport(self):
        class SpyClient(NoNetworkAlternativeTestnetHttpClient):
            def __init__(self):
                self.calls = []

            def build_only_pipeline_result(self, request):
                self.calls.append("build_only_pipeline_result")
                return super().build_only_pipeline_result(request)

            def signed_not_sent_pipeline_result(self, request, material):
                self.calls.append("signed_not_sent_pipeline_result")
                return super().signed_not_sent_pipeline_result(request, material)

            def transport_not_executed_pipeline_result(self, request, material):
                self.calls.append("transport_not_executed_pipeline_result")
                return super().transport_not_executed_pipeline_result(request, material)

            def build_signing_input(self, transport_input, material):
                self.calls.append("build_signing_input")
                return super().build_signing_input(transport_input, material)

            def signed_request_result(self, signing_input, material):
                self.calls.append("signed_request_result")
                return super().signed_request_result(signing_input, material)

            def transport_not_executed_result(self, transport_input):
                self.calls.append("transport_not_executed_result")
                return super().transport_not_executed_result(transport_input)

        spy = SpyClient()
        result = spy.runtime_enablement_integration_disabled_result(_request())

        self.assertEqual(spy.calls, [])
        self.assertEqual(result.status, "NOT_WIRED")
        self.assertFalse(result.runtime_path_enabled)
        self.assertFalse(result.composed_pipeline_executed)
        self.assertFalse(result.signing_executed)
        self.assertFalse(result.transport_executed)
        self.assertFalse(result.network_sent)
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)

    def test_runtime_enablement_integration_observability_fields_are_audit_ready(self):
        source = self._module_source()
        imported = self._module_import_names()
        result = dataclasses.asdict(
            self.client.runtime_enablement_integration_disabled_result(
                _request(idempotency_key="alternative:http:integration-observability:v1")
            )
        )
        required_fields = {
            "disabled_reason",
            "disabled_stage",
            "runtime_path_enabled",
            "composed_pipeline_executed",
            "signing_executed",
            "transport_executed",
            "network_sent",
            "external_order_id",
            "external_order_id_present",
            "failure_family",
            "failure_reason",
        }
        forbidden_imports = {
            "app.actions.runner",
            "runner",
            "worker",
            "risk",
            "commands_domain",
            "domain_command_worker",
            "requests",
            "httpx",
            "aiohttp",
            "socket",
            "urllib.request",
            "os",
            "configparser",
            "dotenv",
            "hmac",
        }
        forbidden_snippets = (
            "runner.execute",
            "worker.enqueue",
            "risk.check",
            "runtime_path_enabled=True",
            "external_request_sent=True",
            "network_sent=True",
            "canary_executed=True",
            "os.environ",
            "getenv(",
            "requests.",
            "httpx.",
            "aiohttp.",
            "socket.socket",
            "hmac.",
        )

        self.assertTrue(required_fields.issubset(result))
        self.assertEqual(result["status"], "NOT_WIRED")
        self.assertEqual(result["disabled_reason"], "alternative_testnet_http_runtime_not_wired")
        self.assertEqual(result["disabled_stage"], "runtime_wiring")
        self.assertFalse(result["runtime_path_enabled"])
        self.assertFalse(result["composed_pipeline_executed"])
        self.assertFalse(result["signing_executed"])
        self.assertFalse(result["transport_executed"])
        self.assertFalse(result["network_sent"])
        self.assertIsNone(result["external_order_id"])
        self.assertFalse(result["external_order_id_present"])
        self.assertTrue(forbidden_imports.isdisjoint(imported))
        for snippet in forbidden_snippets:
            self.assertNotIn(snippet, source)

    def test_runtime_enablement_integration_guardrails_remain_closed(self):
        source = self._module_source()
        imported = self._module_import_names()
        result = self.client.runtime_enablement_integration_disabled_result(
            _request(idempotency_key="alternative:http:integration-guardrail:v1")
        )
        guardrail_expectations = {
            "runtime_path_enabled": result.runtime_path_enabled,
            "composed_pipeline_executed": result.composed_pipeline_executed,
            "signing_executed": result.signing_executed,
            "transport_executed": result.transport_executed,
            "network_sent": result.network_sent,
            "external_order_id_present": result.external_order_id_present,
        }
        forbidden_imports = {
            "app.actions.runner",
            "runner",
            "worker",
            "risk",
            "commands_domain",
            "domain_command_worker",
            "requests",
            "httpx",
            "aiohttp",
            "socket",
            "urllib.request",
            "os",
            "configparser",
            "dotenv",
            "hmac",
            "jwt",
            "cryptography",
        }
        forbidden_snippets = (
            "runner.execute",
            "worker.enqueue",
            "risk.check",
            "runtime_path_enabled=True",
            "runtime_path_enabled = True",
            "external_request_sent=True",
            "external_request_sent = True",
            "network_sent=True",
            "network_sent = True",
            "canary_executed=True",
            "canary_executed = True",
            "os.environ",
            "getenv(",
            "requests.",
            "httpx.",
            "aiohttp.",
            "socket.socket",
            "urllib.request",
            "hmac.",
            "real_signing_enabled",
            "network_behavior_enabled",
        )

        self.assertEqual(result.status, "NOT_WIRED")
        self.assertEqual(result.disabled_stage, "runtime_wiring")
        self.assertEqual(result.disabled_reason, "alternative_testnet_http_runtime_not_wired")
        self.assertIsNone(result.external_order_id)
        self.assertTrue(forbidden_imports.isdisjoint(imported))
        for field_name, value in guardrail_expectations.items():
            self.assertFalse(value, field_name)
        for snippet in forbidden_snippets:
            self.assertNotIn(snippet, source)

    def test_blocker_3_runner_worker_risk_boundary_remains_unwired(self):
        source = self._module_source()
        imported = self._module_import_names()
        forbidden_imports = {
            "app.actions.runner",
            "runner",
            "worker",
            "risk",
            "domain_command_worker",
            "commands_domain",
        }
        forbidden_snippets = (
            "from app.actions.runner",
            "import runner",
            "runner.execute",
            "worker.enqueue",
            "risk.check",
            "runner_modified",
            "worker_modified",
            "risk_modified",
            "register_executor",
            "register_runtime",
            "domain_command_worker",
            "commands_domain",
        )
        disabled_shape = dataclasses.asdict(self.client.runtime_disabled_result(_request()))

        self.assertTrue(forbidden_imports.isdisjoint(imported))
        for snippet in forbidden_snippets:
            self.assertNotIn(snippet, source)
            self.assertNotIn(snippet, disabled_shape)

    def test_blocker_4_runtime_path_enablement_guard_remains_disabled(self):
        source = self._module_source()
        disabled_results = [
            self.client.runtime_disabled_result(_request()),
            self.client.runtime_not_enabled_result(_request()),
            self.client.runtime_not_wired_result(_request()),
        ]
        forbidden_snippets = (
            "runtime_path_enabled=True",
            "runtime_path_enabled = True",
            "enable_runtime_path",
            "runtime_enabled = True",
            "runtime_enabled=True",
        )

        for result in disabled_results:
            self.assertFalse(result.runtime_path_enabled)
            self.assertFalse(result.composed_pipeline_executed)
            self.assertFalse(result.signing_executed)
            self.assertFalse(result.transport_executed)
            self.assertFalse(result.network_sent)
            self.assertIsNone(result.external_order_id)
            self.assertFalse(result.external_order_id_present)

        for snippet in forbidden_snippets:
            self.assertNotIn(snippet, source)

    def test_blocker_5_credential_loading_boundary_remains_closed(self):
        source = self._module_source()
        imported = self._module_import_names()
        shapes = [
            dataclasses.asdict(self.client.build_order_request(_request())),
            dataclasses.asdict(self.client.build_only_pipeline_result(_request())),
            dataclasses.asdict(self.client.runtime_disabled_result(_request())),
            dataclasses.asdict(self.client.runtime_not_enabled_result(_request())),
            dataclasses.asdict(self.client.runtime_not_wired_result(_request())),
        ]
        forbidden_imports = {
            "configparser",
            "dotenv",
            "os",
            "pydantic",
        }
        forbidden_snippets = (
            "os.environ",
            "getenv(",
            "dotenv",
            "configparser",
            "open(",
            "Path.home",
            "read_text(",
            "credential_loaded",
            "env_loaded",
        )
        forbidden_fragments = ("credential", "secret", "api_key", "api_secret", "password", "token")

        self.assertTrue(forbidden_imports.isdisjoint(imported))
        for snippet in forbidden_snippets:
            self.assertNotIn(snippet, source)

        def assert_no_forbidden(value):
            if isinstance(value, dict):
                for key, nested_value in value.items():
                    self.assertFalse(any(fragment in key.lower() for fragment in forbidden_fragments), key)
                    assert_no_forbidden(nested_value)
                return
            self.assertFalse(any(fragment in str(value).lower() for fragment in forbidden_fragments), value)

        for shape in shapes:
            assert_no_forbidden(shape)

    def test_blocker_6_real_signing_boundary_remains_mock_only(self):
        source = self._module_source()
        imported = self._module_import_names()
        transport_input = self.client.build_transport_input(self.client.build_order_request(_request()))
        material = _signing_material()
        signing_input = self.client.build_signing_input(transport_input, material)
        signed = self.client.signed_request_result(signing_input, material)
        not_executed = self.client.signing_not_executed_result(transport_input)
        forbidden_imports = {
            "base64",
            "cryptography",
            "hmac",
            "jwt",
            "rsa",
        }
        forbidden_snippets = (
            "hmac.",
            "private_key",
            "public_key",
            "rsa.",
            "cryptography",
            "jwt.",
            "sign(",
            "signature_algorithm",
            "real_signing_enabled",
        )

        self.assertTrue(forbidden_imports.isdisjoint(imported))
        for snippet in forbidden_snippets:
            self.assertNotIn(snippet, source)

        self.assertEqual(signed.status, "SIGNED")
        self.assertEqual(signed.material_id, "mock-signing-material-v1")
        self.assertEqual(signed.authorization_header_value, "MockAuth explicit-material")
        self.assertEqual(signed.signature_value, "mock-signature-value")
        self.assertFalse(signed.network_sent)
        self.assertIsNone(signed.external_order_id)
        self.assertFalse(signed.external_order_id_present)

        self.assertEqual(not_executed.status, "NOT_EXECUTED")
        self.assertIsNone(not_executed.authorization_header_value)
        self.assertIsNone(not_executed.signature_value)
        self.assertFalse(not_executed.network_sent)

    def test_blocker_7_real_http_transport_boundary_remains_no_network(self):
        source = self._module_source()
        imported = self._module_import_names()
        transport_input = self.client.build_transport_input(self.client.build_order_request(_request()))
        transport_results = [
            self.client.accepted_transport_result(transport_input, "upstream-order-transport-boundary"),
            self.client.rejected_transport_result(transport_input),
            self.client.transport_not_executed_result(transport_input),
        ]
        forbidden_imports = {"aiohttp", "http.client", "httpx", "requests", "socket", "urllib.request"}
        forbidden_snippets = (
            "aiohttp.",
            "http.client",
            "httpx.",
            "requests.",
            "import socket",
            "socket.socket",
            "urllib.request",
            "urlopen(",
            ".send(",
            ".request(",
            "network_behavior_enabled",
            "external_request_sent=True",
            "network_sent=True",
        )
        forbidden_fields = {
            "external_request_sent",
            "external_request_started",
            "http_status",
            "network_request_sent",
            "request_url",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imported))
        for snippet in forbidden_snippets:
            self.assertNotIn(snippet, source)

        for result in transport_results:
            payload = dataclasses.asdict(result)
            self.assertFalse(result.network_sent)
            self.assertTrue(forbidden_fields.isdisjoint(payload))

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

    def test_blocker_9_canary_before_runtime_requirements_remain_blocked(self):
        source = self._module_source()
        request = _request()
        built_request = self.client.build_order_request(request)
        material = _signing_material()
        transport_input = self.client.build_transport_input(built_request)
        signing_input = self.client.build_signing_input(transport_input, material)
        signing_result = self.client.signed_request_result(signing_input, material)
        runtime_disabled = self.client.runtime_disabled_result(request)
        pipeline_results = [
            self.client.build_only_pipeline_result(request),
            self.client.signed_not_sent_pipeline_result(request, material),
            self.client.transport_not_executed_pipeline_result(request, material),
            self.client.rejected_pipeline_result(request, material),
        ]
        accepted_pipeline_result = self.client.accepted_pipeline_result(
            request,
            material,
            "upstream-order-canary-guard",
        )

        forbidden_snippets = (
            "canary_enabled",
            "canary_executed",
            "canary_retry",
            "canary_retried",
            "execute_canary",
            "runtime_enablement=True",
            "runtime_path_enabled=True",
            "external_request_sent=True",
            "network_sent=True",
        )
        forbidden_fields = {
            "canary_enabled",
            "canary_executed",
            "canary_retried",
            "canary_retry_authorized",
            "external_request_sent",
            "runtime_enablement",
        }

        for snippet in forbidden_snippets:
            self.assertNotIn(snippet, source)

        self.assertFalse(runtime_disabled.network_sent)
        self.assertFalse(runtime_disabled.runtime_path_enabled)
        self.assertFalse(runtime_disabled.external_order_id_present)
        self.assertEqual(runtime_disabled.disabled_stage, "runtime_wiring")
        self.assertEqual(runtime_disabled.disabled_reason, "alternative_testnet_http_runtime_disabled")
        self.assertTrue(forbidden_fields.isdisjoint(dataclasses.asdict(runtime_disabled)))

        self.assertEqual(signing_result.material_id, "mock-signing-material-v1")
        self.assertFalse(signing_result.network_sent)
        self.assertTrue(forbidden_fields.isdisjoint(dataclasses.asdict(transport_input)))
        for result in pipeline_results:
            payload = dataclasses.asdict(result)
            self.assertFalse(result.network_sent)
            self.assertFalse(result.external_order_id_present)
            self.assertTrue(forbidden_fields.isdisjoint(payload))

        self.assertFalse(accepted_pipeline_result.network_sent)
        self.assertTrue(forbidden_fields.isdisjoint(dataclasses.asdict(accepted_pipeline_result)))

    def test_disabled_only_runner_integration_status_surface_remains_disabled(self):
        first = domain_runner.disabled_only_runner_integration_status_surface()
        second = domain_runner.disabled_only_runner_integration_status_surface()
        function_source = inspect.getsource(domain_runner.disabled_only_runner_integration_status_surface)
        forbidden_snippets = (
            "os.getenv",
            "os.environ",
            "run_action_with_pipeline",
            "default_pipeline_steps",
            "domain_command_worker",
            "risk_gate",
            "risk_state",
            "requests.",
            "httpx.",
            "aiohttp.",
            "socket.",
            "urllib.request",
            "external_request_sent=True",
            "network_sent=True",
            "canary_executed=True",
            "runtime_path_enabled=True",
        )

        self.assertEqual(first, second)
        self.assertEqual(first["surface"], "alternative_testnet_http_client_runner_integration")
        self.assertEqual(first["status"], "DISABLED")
        self.assertEqual(first["mode"], "disabled_status_surface_only")
        self.assertEqual(first["stage"], "runner_integration_disabled_status_surface")
        self.assertEqual(first["reason"], "runtime_enablement_not_authorized")
        self.assertFalse(first["runtime_path_enabled"])
        self.assertFalse(first["runner_pipeline_invoked"])
        self.assertFalse(first["worker_invoked"])
        self.assertFalse(first["risk_modified"])
        self.assertFalse(first["credentials_read"])
        self.assertFalse(first["env_config_read"])
        self.assertFalse(first["real_signing_enabled"])
        self.assertFalse(first["real_http_network_enabled"])
        self.assertFalse(first["network_sent"])
        self.assertFalse(first["external_request_sent"])
        self.assertIsNone(first["external_order_id"])
        self.assertFalse(first["external_order_id_present"])
        self.assertFalse(first["canary_executed"])
        self.assertEqual(first["go_live"], "NO-GO")
        self.assertEqual(first["live_trading"], "NO-GO")
        for snippet in forbidden_snippets:
            self.assertNotIn(snippet, function_source)


if __name__ == "__main__":
    unittest.main()
