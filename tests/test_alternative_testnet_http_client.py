import dataclasses
import sys
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "anchor-backend" / "app" / "actions" / "alternative_testnet_http_client.py"
sys.path.insert(0, str(PROJECT_ROOT / "anchor-backend"))

from app.actions.alternative_testnet_http_client import (  # noqa: E402
    AlternativeTestnetHttpClientRequest,
    NoNetworkAlternativeTestnetHttpClient,
)


def _request(**overrides):
    payload = {
        "idempotency_key": "alternative:http:BTCUSDT:BUY:4:first-skeleton:v1",
        "venue": "approved_alternative_testnet",
        "execution_mode": "testnet",
    }
    payload.update(overrides)
    return AlternativeTestnetHttpClientRequest(**payload)


class AlternativeTestnetHttpClientSkeletonTest(unittest.TestCase):
    def setUp(self):
        self.client = NoNetworkAlternativeTestnetHttpClient()

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

    def test_failed_fixture_response_has_no_external_order_id(self):
        result = self.client.failed_fixture_response(_request())

        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.failure_family, "ALTERNATIVE_TESTNET_HTTP_FAILED")
        self.assertEqual(result.failure_reason, "alternative_testnet_http_failed")
        self.assertIsNone(result.external_order_id)
        self.assertFalse(result.external_order_id_present)

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

    def test_responses_do_not_imply_external_request(self):
        result = dataclasses.asdict(self.client.accepted_fixture_response(_request()))

        self.assertNotIn("network_request_sent", result)
        self.assertNotIn("http_status", result)
        self.assertNotIn("request_url", result)
        self.assertNotIn("external_request_sent", result)
        self.assertNotIn("external_request_started", result)

    def test_module_does_not_import_real_http_or_socket_libraries(self):
        source = MODULE_PATH.read_text(encoding="utf-8")

        forbidden_snippets = (
            "import requests",
            "from requests",
            "import httpx",
            "from httpx",
            "import aiohttp",
            "from aiohttp",
            "import socket",
            "from socket",
            "urllib.request",
        )
        for snippet in forbidden_snippets:
            self.assertNotIn(snippet, source)

    def test_module_does_not_read_env_or_config(self):
        source = MODULE_PATH.read_text(encoding="utf-8")

        forbidden_snippets = (
            "os.environ",
            "getenv(",
            "dotenv",
            "configparser",
            "pydantic",
        )
        for snippet in forbidden_snippets:
            self.assertNotIn(snippet, source)


if __name__ == "__main__":
    unittest.main()
