import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "reconcile_production_post_send_readonly.py"

spec = importlib.util.spec_from_file_location("reconcile_production_post_send_readonly", MODULE_PATH)
reconcile = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.path.insert(0, str(PROJECT_ROOT / "anchor-backend"))
spec.loader.exec_module(reconcile)


class _FakeResponse:
    status = 200

    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._body


class _FakeOpener:
    def __init__(self, order_body: bytes, account_body: bytes):
        self.order_body = order_body
        self.account_body = account_body
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append({"url": request.full_url, "method": request.get_method(), "timeout": timeout})
        if "/api/v3/allOrders" in request.full_url:
            return _FakeResponse(self.order_body)
        if "/api/v3/account" in request.full_url:
            return _FakeResponse(self.account_body)
        raise AssertionError(request.full_url)


def _window():
    return {
        "planned_window": {
            "not_before": "2026-07-30T13:52:57Z",
            "expires_at": "2026-07-30T14:52:57Z",
        }
    }


def _send():
    return {
        "result": "PASS",
        "success": True,
        "request": {"symbol": "BTCUSDT", "side": "BUY", "max_notional": "10"},
        "terminal": {"external_status": "FILLED"},
    }


def _risk():
    return {"AUTHORIZED_MAX_NOTIONAL": "10", "AUTHORIZED_PRODUCTION_SYMBOLS": "BTCUSDT"}


def _credentials():
    return {
        "base_url": "https://api.binance.com",
        "api_key": "fixture-key",
        "api_secret": "fixture-secret",
        "key_id": "fixture-key-id",
    }


def _credential_report():
    return {
        "ok": True,
        "code": "PRODUCTION_CREDENTIALS_LOADED",
        "field_status": {
            "PRODUCTION_EXCHANGE_BASE_URL": "PRESENT_VALID",
            "PRODUCTION_EXCHANGE_API_KEY": "PRESENT_VALID",
            "PRODUCTION_EXCHANGE_API_SECRET": "PRESENT_VALID",
            "PRODUCTION_EXCHANGE_KEY_ID": "PRESENT_VALID",
        },
        "secret_value_disclosed": False,
    }


class ProductionPostSendReadonlyReconciliationTest(unittest.TestCase):
    def _run(self, opener, *, send=None, window=None, risk=None, execute=True):
        values = {
            reconcile.WINDOW_PLAN: (window or _window(), None),
            reconcile.SEND_RESULT: (send or _send(), None),
            reconcile.RISK_LIMITS: (risk or _risk(), None),
        }

        def fake_read_json(path):
            return values[path]

        with patch.object(reconcile, "read_json", side_effect=fake_read_json), patch.object(
            reconcile, "load_production_credentials", return_value=(_credentials(), _credential_report())
        ):
            return reconcile.build_report(
                execute_readonly=execute,
                credential_path=Path("/etc/project-anchor/production.env"),
                now=datetime(2026, 7, 30, 14, 0, tzinfo=timezone.utc),
                opener=opener,
            )

    def test_readonly_reconciliation_passes_for_one_matching_filled_order(self):
        opener = _FakeOpener(
            b'[{"symbol":"BTCUSDT","side":"BUY","type":"MARKET","status":"FILLED",'
            b'"orderId":123,"clientOrderId":"abc","time":1,"updateTime":2,'
            b'"cummulativeQuoteQty":"9.99","executedQty":"0.0001"}]',
            b'{"balances":[{"asset":"USDT","free":"17","locked":"0"},{"asset":"BTC","free":"0.0001","locked":"0"}]}',
        )

        report, exit_code = self._run(opener)

        self.assertEqual(exit_code, 0)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["order_reconciliation"]["matching_filled_order_count"], 1)
        self.assertEqual(report["order_reconciliation"]["symbol_order_count_in_window"], 1)
        self.assertTrue(report["account_reconciliation"]["usdt_balance_row_present"])
        self.assertTrue(report["account_reconciliation"]["btc_balance_row_present"])
        self.assertEqual(report["boundary"]["production_order_sent"], "NO")
        self.assertEqual(len(opener.calls), 2)
        rendered = str(report)
        self.assertNotIn("fixture-secret", rendered)
        self.assertNotIn("fixture-key", rendered)

    def test_readonly_reconciliation_blocks_without_authorization_flag(self):
        opener = _FakeOpener(b"[]", b"{}")

        report, exit_code = self._run(opener, execute=False)

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["boundary"]["credential_file_read"], "NO")
        self.assertEqual(len(opener.calls), 0)

    def test_readonly_reconciliation_blocks_duplicate_symbol_order(self):
        opener = _FakeOpener(
            b'[{"symbol":"BTCUSDT","side":"BUY","type":"MARKET","status":"FILLED",'
            b'"orderId":123,"cummulativeQuoteQty":"10","executedQty":"0.0001"},'
            b'{"symbol":"BTCUSDT","side":"BUY","type":"MARKET","status":"FILLED",'
            b'"orderId":124,"cummulativeQuoteQty":"10","executedQty":"0.0001"}]',
            b'{"balances":[{"asset":"USDT","free":"17","locked":"0"},{"asset":"BTC","free":"0.0001","locked":"0"}]}',
        )

        report, exit_code = self._run(opener)

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["result"], "BLOCKED")
        failed = {item["name"] for item in report["checks"] if item["result"] == "FAIL"}
        self.assertIn("matching_filled_order_count_one", failed)
        self.assertIn("no_second_symbol_order_in_window", failed)

    def test_readonly_reconciliation_blocks_missing_balance_rows(self):
        opener = _FakeOpener(
            b'[{"symbol":"BTCUSDT","side":"BUY","type":"MARKET","status":"FILLED",'
            b'"orderId":123,"cummulativeQuoteQty":"10","executedQty":"0.0001"}]',
            b'{"balances":[{"asset":"ETH","free":"0","locked":"0"}]}',
        )

        report, exit_code = self._run(opener)

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["result"], "BLOCKED")
        failed = {item["name"] for item in report["checks"] if item["result"] == "FAIL"}
        self.assertIn("usdt_balance_visible", failed)
        self.assertIn("btc_balance_visible", failed)


if __name__ == "__main__":
    unittest.main()
