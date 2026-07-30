import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "decide_post_production_operations.py"

spec = importlib.util.spec_from_file_location("decide_post_production_operations", MODULE_PATH)
decision = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(decision)


def _send():
    return {
        "result": "PASS",
        "success": True,
        "terminal": {
            "http_status": 200,
            "external_status": "FILLED",
            "external_order_id_present": True,
        },
        "boundary": {
            "secret_value_disclosed": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }


def _post_recon():
    return {
        "result": "PASS",
        "boundary": {
            "second_production_request_sent": "NO",
        },
    }


def _readonly_recon():
    return {
        "result": "PASS",
        "order_reconciliation": {
            "matching_filled_order_count": 1,
            "symbol_order_count_in_window": 1,
        },
        "account_reconciliation": {
            "usdt_balance_row_present": True,
            "btc_balance_row_present": True,
        },
        "boundary": {
            "secret_value_disclosed": "NO",
            "second_production_request_sent": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }


def _readiness():
    return {
        "result": "BLOCKED",
        "blockers": [
            "go-live not authorized",
            "live trading not authorized",
        ],
    }


def _risk_limits(**overrides):
    data = {
        "AUTHORIZED_PRODUCTION_SYMBOLS": "BTCUSDT",
        "AUTHORIZED_PRODUCTION_SIDES": "BUY_ONLY",
        "AUTHORIZED_MAX_NOTIONAL": "10",
        "AUTHORIZED_MAX_ORDER_COUNT": "1",
    }
    data.update(overrides)
    return data


class PostProductionOperationsDecisionTest(unittest.TestCase):
    def _run(self, *, send=None, post_recon=None, readonly_recon=None, readiness=None, risk=None):
        values = {
            decision.SEND_RESULT: (send or _send(), None),
            decision.POST_SEND_RECONCILIATION: (post_recon or _post_recon(), None),
            decision.READONLY_RECONCILIATION: (readonly_recon or _readonly_recon(), None),
            decision.EXECUTION_READINESS: (readiness or _readiness(), None),
            decision.RISK_LIMITS: (risk or _risk_limits(), None),
        }

        def fake_read_json(path):
            return values[path]

        with patch.object(decision, "read_json", side_effect=fake_read_json):
            return decision.build_report()

    def test_operations_decision_passes_after_exactly_one_filled_send(self):
        report, exit_code = self._run()

        self.assertEqual(exit_code, 0)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(
            report["decision"],
            "FIRST_PRODUCTION_VALIDATION_COMPLETE_CONTINUOUS_TRADING_DISABLED",
        )
        self.assertEqual(report["summary"]["production_request_sent"], "YES")
        self.assertEqual(report["summary"]["continuous_runtime_enabled"], "NO")
        self.assertEqual(report["boundary"]["new_production_request_sent"], "NO")
        self.assertEqual(report["boundary"]["go_live"], "NO-GO")
        self.assertEqual(report["boundary"]["live_trading"], "NO-GO")

    def test_blocks_if_readonly_reconciliation_missing_exactly_one_order(self):
        readonly = _readonly_recon()
        readonly["order_reconciliation"] = {
            "matching_filled_order_count": 2,
            "symbol_order_count_in_window": 2,
        }

        report, exit_code = self._run(readonly_recon=readonly)

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["result"], "BLOCKED")
        failed = {item["name"] for item in report["checks"] if item["result"] == "FAIL"}
        self.assertIn("exactly_one_matching_order", failed)

    def test_blocks_if_go_live_or_live_trading_was_authorized(self):
        readiness = {"result": "PASS", "blockers": []}

        report, exit_code = self._run(readiness=readiness)

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["result"], "BLOCKED")
        failed = {item["name"] for item in report["checks"] if item["result"] == "FAIL"}
        self.assertIn("execution_readiness_not_go_live", failed)

    def test_blocks_if_risk_limits_drift(self):
        report, exit_code = self._run(risk=_risk_limits(AUTHORIZED_MAX_ORDER_COUNT="2"))

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["result"], "BLOCKED")
        failed = {item["name"] for item in report["checks"] if item["result"] == "FAIL"}
        self.assertIn("risk_limits_remain_bounded", failed)


if __name__ == "__main__":
    unittest.main()
