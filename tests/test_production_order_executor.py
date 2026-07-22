import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "anchor-backend"))

from app.executors.production_order_executor import (  # noqa: E402
    DEFAULT_PRODUCTION_ORDER_PATH,
    build_signed_order_request,
    build_spot_market_order_params,
    redacted_request_shape,
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

    def test_run_execute_stops_before_http_transport(self):
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
        self.assertEqual(outcome["error"]["code"], "PRODUCTION_HTTP_TRANSPORT_NOT_WIRED")
        self.assertFalse(outcome["error"]["external_request_started"])
        self.assertIsNone(requested_payload)
        self.assertIsNone(terminal_type)
        self.assertIsNone(terminal_payload)
        self.assertTrue(outcome["error"]["signed_request_shape"]["signature_present"])


if __name__ == "__main__":
    unittest.main()
