import importlib.util
import os
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

        with patch.object(snapshot, "read_json", side_effect=fake_read_json), patch.dict(
            os.environ, {snapshot.EXCHANGE_RECONCILIATION_ENV: ""}, clear=False
        ):
            return snapshot.build_report()

    def test_monitoring_snapshot_passes_after_first_production_validation(self):
        report, exit_code = self._run()

        self.assertEqual(exit_code, 0)
        self.assertEqual(report["result"], "PASS_REPO_RECORDED_ONLY")
        self.assertNotEqual(report["result"], "PASS")
        self.assertEqual(report["status"], "MONITORING_REPO_RECORDED_ONLY_CONTINUOUS_TRADING_DISABLED")
        self.assertEqual(report["snapshot"]["production_request_sent"], "YES")
        self.assertEqual(report["snapshot"]["continuous_runtime_enabled"], "NO")
        self.assertEqual(report["boundary"]["new_production_request_sent"], "NO")
        self.assertEqual(report["boundary"]["go_live"], "NO-GO")
        self.assertEqual(report["boundary"]["live_trading"], "NO-GO")
        self.assertEqual(report["boundary"]["exchange_api_called"], "NO")
        self.assertEqual(report["result_scope"], "repo_recorded_evidence")
        names = {item["name"]: item["result"] for item in report["checks"]}
        self.assertEqual(names["repo_recorded_exactly_one_order"], "PASS")
        self.assertEqual(names["repo_recorded_no_new_or_second_request"], "PASS")
        self.assertNotIn("exactly_one_order_confirmed", names)
        self.assertNotIn("no_new_or_second_request", names)
        self.assertEqual(names["exchange_confirmed_exactly_one_order"], "UNKNOWN")
        self.assertEqual(names["exchange_confirmed_no_new_or_second_request"], "UNKNOWN")
        self.assertEqual(report["snapshot"]["exchange_confirmed_order_status"], "UNKNOWN")
        self.assertEqual(report["snapshot"]["exchange_reconciliation_supplied"], "NO")
        self.assertNotEqual(report["snapshot"]["exchange_confirmed_order_status"], "PASS")

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
        self.assertIn("repo_recorded_exactly_one_order", failed)
        exchange = {item["name"]: item["result"] for item in report["checks"]}
        self.assertEqual(exchange["exchange_confirmed_exactly_one_order"], "UNKNOWN")

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

    def test_offline_reconciliation_can_confirm_exchange_counts(self):
        import json
        import tempfile

        payload = {
            "kind": "offline_exchange_reconciliation",
            "matching_filled_order_count": 1,
            "symbol_order_count": 1,
            "new_or_second_request_observed": False,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "recon.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            report, exit_code = self._run_with_exchange(path)

        self.assertEqual(exit_code, 0)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["status"], "MONITORING_READY_CONTINUOUS_TRADING_DISABLED")
        self.assertEqual(report["snapshot"]["exchange_reconciliation_supplied"], "YES")
        self.assertEqual(report["snapshot"]["exchange_confirmed_order_status"], "PASS")
        self.assertEqual(report["snapshot"]["exchange_confirmed_exactly_one_order"], "PASS")
        self.assertEqual(report["boundary"]["exchange_api_called"], "NO")

    def test_offline_reconciliation_disagreement_is_not_pass(self):
        import json
        import tempfile

        payload = {
            "kind": "offline_exchange_reconciliation",
            "matching_filled_order_count": 2,
            "symbol_order_count": 2,
            "new_or_second_request_observed": True,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "recon.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            report, exit_code = self._run_with_exchange(path)

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["result"], "BLOCKED")
        names = {item["name"]: item["result"] for item in report["checks"]}
        self.assertEqual(names["repo_recorded_exactly_one_order"], "PASS")
        self.assertEqual(names["exchange_confirmed_exactly_one_order"], "FAIL")
        self.assertEqual(names["exchange_confirmed_no_new_or_second_request"], "FAIL")
        self.assertNotEqual(report["snapshot"]["exchange_confirmed_order_status"], "PASS")

    def test_invalid_offline_reconciliation_does_not_pass(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "recon.json"
            path.write_text("{", encoding="utf-8")
            report, exit_code = self._run_with_exchange(path)

        self.assertEqual(exit_code, 1)
        names = {item["name"]: item["result"] for item in report["checks"]}
        self.assertEqual(names["exchange_confirmed_exactly_one_order"], "FAIL")
        self.assertNotEqual(names["exchange_confirmed_exactly_one_order"], "PASS")

    def _run_with_exchange(self, path: Path):
        values = {
            snapshot.SEND_RESULT: (_send(), None),
            snapshot.READONLY_RECONCILIATION: (_readonly_reconciliation(), None),
            snapshot.OPERATIONS_DECISION: (_decision(), None),
            snapshot.EXECUTION_READINESS: (_readiness(), None),
            snapshot.RISK_LIMITS: (_risk_limits(), None),
        }
        original_read_json = snapshot.read_json

        def fake_read_json(candidate):
            if candidate == path:
                return original_read_json(candidate)
            return values[candidate]

        with patch.object(snapshot, "read_json", side_effect=fake_read_json):
            return snapshot.build_report(path)


if __name__ == "__main__":
    unittest.main()
