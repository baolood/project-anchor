import io
import sys
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "anchor-backend"))

from app.executors.production_order_executor import (  # noqa: E402
    DEFAULT_PRODUCTION_ORDER_PATH,
    build_signed_order_request,
    build_spot_market_order_params,
    redacted_request_shape,
    run_gated_production_order_request,
    run_production_order_request,
    sign_query,
)


def _transport_input(**overrides):
    data = {
        "execution_mode": "production",
        "market": "binance_spot",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "notional": 4,
        "order_type": "market",
        "idempotency_key": "production:ops_manual:BTCUSDT:BUY:4:first-bounded-production-request:v1",
    }
    data.update(overrides)
    return data


def _authorized_gate_config(**overrides):
    data = {
        "AUTHORIZED_PRODUCTION_REQUEST_SEND": "YES",
        "AUTHORIZED_PRODUCTION_CREDENTIAL_ACCESS": "YES",
        "AUTHORIZED_PRODUCTION_SIGNING": "YES",
        "AUTHORIZED_PRODUCTION_HTTP_NETWORK": "YES",
        "AUTHORIZED_GO_LIVE": "NO",
        "AUTHORIZED_LIVE_TRADING": "NO",
        "PRODUCTION_REQUEST_SEND_WINDOW_OPEN": True,
        "PRODUCTION_REQUEST_SEND_WINDOW_EXPIRES_AT": "2026-07-22T09:00:00Z",
        "PRODUCTION_REQUEST_SEND_NO_RETRY": True,
        "PRODUCTION_REQUEST_SEND_IDEMPOTENCY_KEY": (
            "production:ops_manual:BTCUSDT:BUY:4:first-bounded-production-request:v1"
        ),
        "FINAL_PRODUCTION_REQUEST_SEND_OPERATOR_VERDICT": (
            "APPROVED_FOR_EXACTLY_ONE_PRODUCTION_REQUEST_SEND_ONLY"
        ),
    }
    data.update(overrides)
    return data


class _FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return (
            b'{"symbol":"BTCUSDT","orderId":12345,"clientOrderId":"fixture-client",'
            b'"transactTime":1234567890,"status":"FILLED"}'
        )


class _FakeOpener:
    def __init__(self):
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append({"request": request, "timeout": timeout})
        return _FakeResponse()


class ProductionOrderExecutorTest(unittest.TestCase):
    def test_builds_spot_market_order_params_with_quote_order_qty(self):
        params = build_spot_market_order_params(_transport_input(), 1234567890)

        self.assertEqual(params["symbol"], "BTCUSDT")
        self.assertEqual(params["side"], "BUY")
        self.assertEqual(params["type"], "MARKET")
        self.assertEqual(params["quoteOrderQty"], "4")
        self.assertEqual(params["newOrderRespType"], "FULL")
        self.assertEqual(params["timestamp"], 1234567890)

    def test_rejects_non_production_market_shape(self):
        with self.assertRaises(ValueError) as ctx:
            build_spot_market_order_params(
                _transport_input(market="binance_testnet"),
                1234567890,
            )

        self.assertEqual(str(ctx.exception), "PRODUCTION_MARKET_UNSUPPORTED")

    def test_sign_query_is_deterministic(self):
        signature = sign_query("fixture-secret", "symbol=BTCUSDT&side=BUY")

        self.assertEqual(
            signature,
            "07ffb3c6c598c1c2942ec45c67bd99151cf8526aba438ab7366ddaabebe3917b",
        )

    def test_build_signed_order_request_uses_allowlisted_origin(self):
        request = build_signed_order_request(
            _transport_input(),
            {
                "base_url": "https://api.binance.com",
                "api_key": "fixture-key",
                "api_secret": "fixture-secret",
            },
            1234567890,
        )

        self.assertEqual(request["method"], "POST")
        self.assertIn(DEFAULT_PRODUCTION_ORDER_PATH, request["url"])
        self.assertIn("signature=", request["url"])
        self.assertEqual(request["headers"]["X-MBX-APIKEY"], "fixture-key")
        self.assertTrue(request["signature_present"])
        self.assertTrue(request["sendable"])

    def test_rejects_non_allowlisted_origin(self):
        with self.assertRaises(ValueError) as ctx:
            build_signed_order_request(
                _transport_input(),
                {
                    "base_url": "https://example.com",
                    "api_key": "fixture-key",
                    "api_secret": "fixture-secret",
                },
                1234567890,
            )

        self.assertEqual(str(ctx.exception), "PRODUCTION_BASE_URL_NOT_ALLOWLISTED")

    def test_redacted_shape_does_not_include_secrets_or_signature_value(self):
        request = build_signed_order_request(
            _transport_input(),
            {
                "base_url": "https://api.binance.com",
                "api_key": "fixture-key",
                "api_secret": "fixture-secret",
            },
            1234567890,
        )
        shape = redacted_request_shape(request)

        self.assertTrue(shape["signature_present"])
        self.assertTrue(shape["api_key_present"])
        self.assertNotIn("fixture-key", str(shape))
        self.assertNotIn("fixture-secret", str(shape))
        self.assertNotIn("signature=", str(shape))

    def test_run_fails_closed_without_execute_authorization(self):
        outcome, requested_payload, terminal_type, terminal_payload = (
            run_production_order_request(_transport_input(), None, 1234567890)
        )

        self.assertFalse(outcome["ok"])
        self.assertEqual(
            outcome["error"]["code"],
            "PRODUCTION_SEND_EXECUTION_NOT_AUTHORIZED",
        )
        self.assertFalse(outcome["error"]["external_request_started"])
        self.assertIsNone(requested_payload)
        self.assertIsNone(terminal_type)
        self.assertIsNone(terminal_payload)

    def test_run_execute_stops_before_http_transport_when_not_enabled(self):
        outcome, requested_payload, terminal_type, terminal_payload = (
            run_production_order_request(
                _transport_input(),
                {
                    "base_url": "https://api.binance.com",
                    "api_key": "fixture-key",
                    "api_secret": "fixture-secret",
                },
                1234567890,
                execute=True,
            )
        )

        self.assertFalse(outcome["ok"])
        self.assertEqual(outcome["error"]["code"], "PRODUCTION_HTTP_TRANSPORT_NOT_AUTHORIZED")
        self.assertFalse(outcome["error"]["external_request_started"])
        self.assertIsNone(requested_payload)
        self.assertIsNone(terminal_type)
        self.assertIsNone(terminal_payload)
        self.assertTrue(outcome["error"]["signed_request_shape"]["signature_present"])

    def test_run_uses_injected_transport_once_when_transport_enabled(self):
        fake_opener = _FakeOpener()

        outcome, requested_payload, terminal_type, terminal_payload = (
            run_production_order_request(
                _transport_input(),
                {
                    "base_url": "https://api.binance.com",
                    "api_key": "fixture-key",
                    "api_secret": "fixture-secret",
                },
                1234567890,
                execute=True,
                transport_enabled=True,
                opener=fake_opener,
            )
        )

        self.assertTrue(outcome["ok"])
        self.assertEqual(len(fake_opener.calls), 1)
        self.assertEqual(terminal_type, "PRODUCTION_HTTP_RESPONSE")
        self.assertTrue(requested_payload["signature_present"])
        self.assertTrue(requested_payload["api_key_present"])
        self.assertEqual(terminal_payload["external_status"], "FILLED")
        self.assertTrue(terminal_payload["external_order_id_present"])
        self.assertNotIn("fixture-key", str(outcome))
        self.assertNotIn("fixture-secret", str(outcome))
        self.assertNotIn("signature=", str(outcome))

    def test_injected_http_error_fails_closed_without_secret_disclosure(self):
        def failing_opener(request, timeout):
            raise urllib.error.HTTPError(
                request.full_url,
                401,
                "Unauthorized",
                hdrs=None,
                fp=io.BytesIO(b'{"code":-2015,"msg":"redacted"}'),
            )

        outcome, requested_payload, terminal_type, terminal_payload = (
            run_production_order_request(
                _transport_input(),
                {
                    "base_url": "https://api.binance.com",
                    "api_key": "fixture-key",
                    "api_secret": "fixture-secret",
                },
                1234567890,
                execute=True,
                transport_enabled=True,
                opener=failing_opener,
            )
        )

        self.assertFalse(outcome["ok"])
        self.assertEqual(outcome["error"]["code"], "PRODUCTION_HTTP_AUTH_REJECTED")
        self.assertTrue(outcome["error"]["external_request_started"])
        self.assertTrue(requested_payload["signature_present"])
        self.assertEqual(terminal_type, "PRODUCTION_HTTP_AUTH_REJECTED")
        self.assertEqual(terminal_payload["http_status"], 401)
        self.assertNotIn("fixture-key", str(outcome))
        self.assertNotIn("fixture-secret", str(outcome))
        self.assertNotIn("signature=", str(outcome))

    def test_gated_run_stops_before_executor_when_send_gate_closed(self):
        fake_opener = _FakeOpener()

        outcome, requested_payload, terminal_type, terminal_payload = (
            run_gated_production_order_request(
                _transport_input(source="ops_manual"),
                {},
                {
                    "base_url": "https://api.binance.com",
                    "api_key": "fixture-key",
                    "api_secret": "fixture-secret",
                },
                1234567890,
                now=datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc),
                execute=True,
                opener=fake_opener,
            )
        )

        self.assertFalse(outcome["ok"])
        self.assertEqual(outcome["error"]["code"], "PRODUCTION_REQUEST_SEND_GATE_CLOSED")
        self.assertEqual(len(fake_opener.calls), 0)
        self.assertIsNone(requested_payload)
        self.assertIsNone(terminal_type)
        self.assertIsNone(terminal_payload)
        self.assertFalse(outcome["error"]["external_request_started"])

    def test_gated_run_ready_but_execute_false_still_fails_closed(self):
        outcome, requested_payload, terminal_type, terminal_payload = (
            run_gated_production_order_request(
                _transport_input(source="ops_manual"),
                _authorized_gate_config(),
                {
                    "base_url": "https://api.binance.com",
                    "api_key": "fixture-key",
                    "api_secret": "fixture-secret",
                },
                1234567890,
                now=datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc),
            )
        )

        self.assertFalse(outcome["ok"])
        self.assertEqual(outcome["error"]["code"], "PRODUCTION_SEND_EXECUTION_NOT_AUTHORIZED")
        self.assertFalse(outcome["error"]["external_request_started"])
        self.assertIsNone(requested_payload)
        self.assertIsNone(terminal_type)
        self.assertIsNone(terminal_payload)

    def test_gated_run_ready_with_fake_transport_parses_response(self):
        fake_opener = _FakeOpener()

        outcome, requested_payload, terminal_type, terminal_payload = (
            run_gated_production_order_request(
                _transport_input(source="ops_manual"),
                _authorized_gate_config(),
                {
                    "base_url": "https://api.binance.com",
                    "api_key": "fixture-key",
                    "api_secret": "fixture-secret",
                },
                1234567890,
                now=datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc),
                execute=True,
                opener=fake_opener,
            )
        )

        self.assertTrue(outcome["ok"])
        self.assertEqual(len(fake_opener.calls), 1)
        self.assertEqual(terminal_type, "PRODUCTION_HTTP_RESPONSE")
        self.assertEqual(terminal_payload["external_status"], "FILLED")
        self.assertTrue(terminal_payload["external_order_id_present"])
        self.assertTrue(requested_payload["signature_present"])
        self.assertNotIn("fixture-key", str(outcome))
        self.assertNotIn("fixture-secret", str(outcome))
        self.assertNotIn("signature=", str(outcome))


if __name__ == "__main__":
    unittest.main()
