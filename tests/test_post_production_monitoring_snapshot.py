import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "generate_post_production_monitoring_snapshot.py"

spec = importlib.util.spec_from_file_location("generate_post_production_monitoring_snapshot", MODULE_PATH)
snapshot = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(snapshot)


def _send():
    return {
        "result": "PASS",
        "success": True,
        "terminal": {"external_status": "FILLED"},
        "boundary": {"secret_value_disclosed": "NO"},
    }


def _readonly_reconciliation(**overrides):
    data = {
        "result": "PASS",
        "order_reconciliation": {
            "matching_filled_order_count": 1,
            "symbol_order_count_in_window": 1,
        },
        "account_reconciliation": {
            "usdt_balance_row_present": True,
            "btc_balance_row_present": True,
            "balance_amounts_recorded": "NO",
        },
        "boundary": {
            "secret_value_disclosed": "NO",
            "second_production_request_sent": "NO",
        },
    }
    data.update(overrides)
    return data


def _decision(**overrides):
    data = {
        "result": "PASS",
        "decision": "FIRST_PRODUCTION_VALIDATION_COMPLETE_CONTINUOUS_TRADING_DISABLED",
        "summary": {
            "continuous_runtime_enabled": "NO",
            "automatic_trading_enabled": "NO",
        },
        "boundary": {
            "new_production_request_sent": "NO",
            "second_production_request_sent": "NO",
            "secret_value_disclosed": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    data.update(overrides)
    return data


def _readiness(**overrides):
    data = {
        "blockers": [
            "go-live not authorized",
            "live trading not authorized",
        ]
    }
    data.update(overrides)
    return data


def _risk_limits(**overrides):
    data = {
        "AUTHORIZED_PRODUCTION_SYMBOLS": "BTCUSDT",
        "AUTHORIZED_PRODUCTION_SIDES": "BUY_ONLY",
        "AUTHORIZED_MAX_NOTIONAL": "10",
        "AUTHORIZED_MAX_ORDER_COUNT": "1",
    }
    data.update(overrides)
    return data


class PostProductionMonitoringSnapshotTest(unittest.TestCase):
    def _run(self, *, send=None, readonly=None, decision=None, readiness=None, risk=None):
        values = {
            snapshot.SEND_RESULT: (send or _send(), None),
            snapshot.READONLY_RECONCILIATION: (readonly or _readonly_reconciliation(), None),
            snapshot.OPERATIONS_DECISION: (decision or _decision(), None),
            snapshot.EXECUTION_READINESS: (readiness or _readiness(), None),
            snapshot.RISK_LIMITS: (risk or _risk_limits(), None),
        }

        def fake_read_json(path):
            return values[path]

        with patch.object(snapshot, "read_json", side_effect=fake_read_json):
            return snapshot.build_report()

    def test_monitoring_snapshot_passes_after_first_production_validation(self):
        report, exit_code = self._run()

        self.assertEqual(exit_code, 0)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["status"], "MONITORING_READY_CONTINUOUS_TRADING_DISABLED")
        self.assertEqual(report["snapshot"]["production_request_sent"], "YES")
        self.assertEqual(report["snapshot"]["continuous_runtime_enabled"], "NO")
        self.assertEqual(report["boundary"]["new_production_request_sent"], "NO")
        self.assertEqual(report["boundary"]["go_live"], "NO-GO")
        self.assertEqual(report["boundary"]["live_trading"], "NO-GO")

    def test_blocks_if_duplicate_order_evidence_appears(self):
        readonly = _readonly_reconciliation(
            order_reconciliation={
                "matching_filled_order_count": 2,
                "symbol_order_count_in_window": 2,
            }
        )

        report, exit_code = self._run(readonly=readonly)

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["result"], "BLOCKED")
        failed = {item["name"] for item in report["checks"] if item["result"] == "FAIL"}
        self.assertIn("exactly_one_order_confirmed", failed)

    def test_blocks_if_continuous_trading_is_enabled(self):
        decision = _decision(
            summary={
                "continuous_runtime_enabled": "YES",
                "automatic_trading_enabled": "NO",
            }
        )

        report, exit_code = self._run(decision=decision)

        self.assertEqual(exit_code, 1)
        failed = {item["name"] for item in report["checks"] if item["result"] == "FAIL"}
        self.assertIn("continuous_trading_disabled", failed)

    def test_blocks_if_risk_limits_drift(self):
        report, exit_code = self._run(risk=_risk_limits(AUTHORIZED_MAX_ORDER_COUNT="2"))

        self.assertEqual(exit_code, 1)
        failed = {item["name"] for item in report["checks"] if item["result"] == "FAIL"}
        self.assertIn("risk_limits_still_bounded", failed)


if __name__ == "__main__":
    unittest.main()
