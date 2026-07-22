import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "anchor-backend"))

from app.executors.production_send_runner import run_final_production_send  # noqa: E402
from app.trade_gate_production import (  # noqa: E402
    PRODUCTION_IDEMPOTENCY_KEY,
    PRODUCTION_REQUEST_SEND_GATE_REQUIRED_VERDICT,
)


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


def _body():
    return {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "notional": 4,
        "order_type": "market",
        "execution_mode": "production",
        "market": "binance_spot",
        "source": "ops_manual",
        "idempotency_key": PRODUCTION_IDEMPOTENCY_KEY,
    }


def _gate_config():
    return {
        "AUTHORIZED_PRODUCTION_REQUEST_SEND": "YES",
        "AUTHORIZED_PRODUCTION_CREDENTIAL_ACCESS": "YES",
        "AUTHORIZED_PRODUCTION_SIGNING": "YES",
        "AUTHORIZED_PRODUCTION_HTTP_NETWORK": "YES",
        "AUTHORIZED_GO_LIVE": "NO",
        "AUTHORIZED_LIVE_TRADING": "NO",
        "PRODUCTION_REQUEST_SEND_WINDOW_OPEN": True,
        "PRODUCTION_REQUEST_SEND_WINDOW_EXPIRES_AT": "2026-07-22T09:00:00Z",
        "PRODUCTION_REQUEST_SEND_NO_RETRY": True,
        "PRODUCTION_REQUEST_SEND_IDEMPOTENCY_KEY": PRODUCTION_IDEMPOTENCY_KEY,
        "FINAL_PRODUCTION_REQUEST_SEND_OPERATOR_VERDICT": (
            PRODUCTION_REQUEST_SEND_GATE_REQUIRED_VERDICT
        ),
    }


def _fixture_env():
    return "\n".join(
        [
            "PRODUCTION_EXCHANGE_BASE_URL=https://api.binance.com",
            "PRODUCTION_EXCHANGE_API_KEY=fixture-production-key",
            "PRODUCTION_EXCHANGE_API_SECRET=fixture-production-secret",
            "PRODUCTION_EXCHANGE_KEY_ID=fixture-production-key-id",
        ]
    )


class ProductionSendRunnerTest(unittest.TestCase):
    def test_runner_defaults_to_credential_read_not_authorized(self):
        outcome, requested_payload, terminal_type, terminal_payload = run_final_production_send(
            _body(),
            _gate_config(),
            "/tmp/not-read.env",
            1234567890,
        )

        self.assertFalse(outcome["ok"])
        self.assertEqual(outcome["error"]["code"], "PRODUCTION_CREDENTIAL_READ_NOT_AUTHORIZED")
        self.assertFalse(outcome["error"]["external_request_started"])
        self.assertIsNone(requested_payload)
        self.assertIsNone(terminal_type)
        self.assertIsNone(terminal_payload)

    def test_runner_with_fixture_credentials_still_requires_execute_flag(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as tmp:
            tmp.write(_fixture_env())
            tmp.flush()

            outcome, requested_payload, terminal_type, terminal_payload = (
                run_final_production_send(
                    _body(),
                    _gate_config(),
                    tmp.name,
                    1234567890,
                    now=datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc),
                    credential_read_enabled=True,
                )
            )

        self.assertFalse(outcome["ok"])
        self.assertEqual(outcome["error"]["code"], "PRODUCTION_SEND_EXECUTION_NOT_AUTHORIZED")
        self.assertTrue(outcome["error"]["credential_shape"]["loaded"])
        self.assertFalse(outcome["error"]["external_request_started"])
        self.assertIsNone(requested_payload)
        self.assertIsNone(terminal_type)
        self.assertIsNone(terminal_payload)

    def test_runner_ready_fixture_with_fake_transport_parses_response(self):
        fake_opener = _FakeOpener()
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as tmp:
            tmp.write(_fixture_env())
            tmp.flush()

            outcome, requested_payload, terminal_type, terminal_payload = (
                run_final_production_send(
                    _body(),
                    _gate_config(),
                    tmp.name,
                    1234567890,
                    now=datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc),
                    execute=True,
                    credential_read_enabled=True,
                    opener=fake_opener,
                )
            )

        self.assertTrue(outcome["ok"])
        self.assertEqual(len(fake_opener.calls), 1)
        self.assertEqual(terminal_type, "PRODUCTION_HTTP_RESPONSE")
        self.assertEqual(terminal_payload["external_status"], "FILLED")
        self.assertTrue(terminal_payload["external_order_id_present"])
        self.assertTrue(requested_payload["signature_present"])
        self.assertTrue(outcome["result"]["credential_shape"]["loaded"])
        self.assertNotIn("fixture-production-key", str(outcome))
        self.assertNotIn("fixture-production-secret", str(outcome))
        self.assertNotIn("fixture-production-key-id", str(outcome))
        self.assertNotIn("signature=", str(outcome))


if __name__ == "__main__":
    unittest.main()
