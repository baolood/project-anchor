import json
import os
import socket
import unittest
import urllib.error
from unittest.mock import patch

from app.executors.testnet_order_executor import run_real_testnet_order_request


def _transport_input(**overrides):
    payload = {
        "command_id": "order-real-wire-1",
        "attempt": 1,
        "execution_mode": "testnet",
        "market": "binance_testnet",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "notional": 4.0,
        "order_type": "market",
        "source": "ops_manual",
        "created_by": "baolood",
        "stop_price": 68000.0,
        "idempotency_key": "testnet:ops_manual:BTCUSDT:BUY:4:real-wire",
        "host_label": "binance_futures_testnet",
        "configured_origin": "https://testnet.binancefuture.com",
        "canonical_path": "ORDER:testnet",
        "key_id_present": True,
    }
    payload.update(overrides)
    return payload


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestnetRealWireV1Test(unittest.TestCase):
    def test_helper_stays_disabled_without_explicit_enable(self):
        with patch.dict(os.environ, {}, clear=False):
            out, requested, terminal_type, terminal_payload = run_real_testnet_order_request(
                _transport_input(),
                456,
            )

        self.assertFalse(out["ok"])
        self.assertEqual(out["error"]["failure_family"], "TESTNET_REAL_WIRE_DISABLED")
        self.assertIsNone(requested)
        self.assertIsNone(terminal_type)
        self.assertIsNone(terminal_payload)

    def test_helper_emits_real_success_with_signed_request(self):
        seen = {}

        def _fake_urlopen(request, timeout=0):
            if request.full_url.endswith("/fapi/v1/time"):
                seen["time_url"] = request.full_url
                return _FakeResponse({"serverTime": 999999})
            seen["url"] = request.full_url
            seen["timeout"] = timeout
            seen["api_key"] = request.get_header("X-mbx-apikey")
            return _FakeResponse({"orderId": 12345, "status": "FILLED"})

        with patch.dict(
            os.environ,
            {
                "TESTNET_EXECUTOR_REAL_ENABLE": "1",
                "TESTNET_EXCHANGE_API_KEY": "real-key",
                "TESTNET_EXCHANGE_API_SECRET": "real-secret",
            },
            clear=False,
        ), patch("app.executors.testnet_order_executor.urllib.request.urlopen", side_effect=_fake_urlopen):
            out, requested, terminal_type, terminal_payload = run_real_testnet_order_request(
                _transport_input(),
                456,
            )

        self.assertTrue(out["ok"])
        self.assertEqual(out["result"]["external_order_id"], "12345")
        self.assertEqual(out["result"]["external_status"], "FILLED")
        self.assertEqual(requested["executor_mode_label"], "real")
        self.assertEqual(requested["external_request_started"], True)
        self.assertEqual(terminal_type, "TESTNET_EXECUTOR_ACCEPTED")
        self.assertEqual(terminal_payload["external_order_id"], "12345")
        self.assertTrue(seen["time_url"].endswith("/fapi/v1/time"))
        self.assertIn("/fapi/v1/order?", seen["url"])
        self.assertIn("signature=", seen["url"])
        self.assertIn("timestamp=999999", seen["url"])
        self.assertEqual(seen["timeout"], 10)
        self.assertEqual(seen["api_key"], "real-key")

    def test_helper_maps_http_400_to_validation_failed(self):
        http_error = urllib.error.HTTPError(
            url="https://testnet.binancefuture.com/fapi/v1/order",
            code=400,
            msg="bad request",
            hdrs=None,
            fp=None,
        )
        http_error.read = lambda: b'{"code":-1102,"msg":"bad input"}'

        def _fake_urlopen(request, timeout=0):
            if request.full_url.endswith("/fapi/v1/time"):
                return _FakeResponse({"serverTime": 999999})
            raise http_error

        with patch.dict(
            os.environ,
            {
                "TESTNET_EXECUTOR_REAL_ENABLE": "1",
                "TESTNET_EXCHANGE_API_KEY": "real-key",
                "TESTNET_EXCHANGE_API_SECRET": "real-secret",
            },
            clear=False,
        ), patch("app.executors.testnet_order_executor.urllib.request.urlopen", side_effect=_fake_urlopen):
            out, requested, terminal_type, terminal_payload = run_real_testnet_order_request(
                _transport_input(),
                456,
            )

        self.assertFalse(out["ok"])
        self.assertEqual(out["error"]["failure_family"], "TESTNET_EXECUTOR_VALIDATION_FAILED")
        self.assertEqual(out["error"]["exchange_error_code"], -1102)
        self.assertEqual(out["error"]["exchange_error_msg"], "bad input")
        self.assertIn("bad input", out["error"]["http_body_excerpt"])
        self.assertEqual(terminal_type, "TESTNET_EXECUTOR_REJECTED")
        self.assertEqual(terminal_payload["failure_family"], "TESTNET_EXECUTOR_VALIDATION_FAILED")
        self.assertEqual(terminal_payload["exchange_error_code"], -1102)
        self.assertEqual(terminal_payload["exchange_error_msg"], "bad input")
        self.assertTrue(requested["external_request_started"])

    def test_helper_maps_timeout_to_timeout_family(self):
        def _fake_urlopen(request, timeout=0):
            if request.full_url.endswith("/fapi/v1/time"):
                return _FakeResponse({"serverTime": 999999})
            raise socket.timeout("timed out")

        with patch.dict(
            os.environ,
            {
                "TESTNET_EXECUTOR_REAL_ENABLE": "1",
                "TESTNET_EXCHANGE_API_KEY": "real-key",
                "TESTNET_EXCHANGE_API_SECRET": "real-secret",
            },
            clear=False,
        ), patch(
            "app.executors.testnet_order_executor.urllib.request.urlopen",
            side_effect=_fake_urlopen,
        ):
            out, requested, terminal_type, terminal_payload = run_real_testnet_order_request(
                _transport_input(),
                456,
            )

        self.assertFalse(out["ok"])
        self.assertEqual(out["error"]["failure_family"], "TESTNET_EXECUTOR_TIMEOUT")
        self.assertEqual(terminal_type, "TESTNET_EXECUTOR_REJECTED")
        self.assertEqual(terminal_payload["failure_family"], "TESTNET_EXECUTOR_TIMEOUT")
        self.assertTrue(requested["external_request_started"])

    def test_helper_maps_url_error_to_network_family(self):
        def _fake_urlopen(request, timeout=0):
            if request.full_url.endswith("/fapi/v1/time"):
                return _FakeResponse({"serverTime": 999999})
            raise urllib.error.URLError("network down")

        with patch.dict(
            os.environ,
            {
                "TESTNET_EXECUTOR_REAL_ENABLE": "1",
                "TESTNET_EXCHANGE_API_KEY": "real-key",
                "TESTNET_EXCHANGE_API_SECRET": "real-secret",
            },
            clear=False,
        ), patch(
            "app.executors.testnet_order_executor.urllib.request.urlopen",
            side_effect=_fake_urlopen,
        ):
            out, requested, terminal_type, terminal_payload = run_real_testnet_order_request(
                _transport_input(),
                456,
            )

        self.assertFalse(out["ok"])
        self.assertEqual(out["error"]["failure_family"], "TESTNET_EXECUTOR_NETWORK_ERROR")
        self.assertEqual(terminal_type, "TESTNET_EXECUTOR_REJECTED")
        self.assertEqual(terminal_payload["failure_family"], "TESTNET_EXECUTOR_NETWORK_ERROR")
        self.assertTrue(requested["external_request_started"])


if __name__ == "__main__":
    unittest.main()
