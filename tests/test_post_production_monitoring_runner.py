import importlib.util
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "run_post_production_monitoring.py"

spec = importlib.util.spec_from_file_location("run_post_production_monitoring", MODULE_PATH)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def _snapshot(**overrides):
    report = {
        "generated_at": "2026-07-30T14:37:42Z",
        "result": "PASS",
        "status": "MONITORING_READY_CONTINUOUS_TRADING_DISABLED",
        "snapshot": {
            "matching_filled_order_count": 1,
            "symbol_order_count_in_window": 1,
            "continuous_runtime_enabled": "NO",
            "automatic_trading_enabled": "NO",
        },
        "boundary": {
            "credential_file_read": "NO",
            "production_signing_executed": "NO",
            "production_http_network_attempted": "NO",
            "new_production_request_sent": "NO",
            "second_production_request_sent": "NO",
            "runtime_modified": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    report.update(overrides)
    return report


class PostProductionMonitoringRunnerTest(unittest.TestCase):
    def test_runner_passes_for_safe_snapshot(self):
        report, exit_code = runner.build_run_report(_snapshot(), 0)

        self.assertEqual(exit_code, 0)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["status"], "POST_PRODUCTION_MONITORING_RUN_READY")
        self.assertEqual(report["boundary"]["credential_file_read"], "NO")
        self.assertEqual(report["boundary"]["new_production_request_sent"], "NO")
        self.assertEqual(report["boundary"]["go_live"], "NO-GO")
        self.assertEqual(report["boundary"]["live_trading"], "NO-GO")
        alert = runner.build_alert_report(report)
        self.assertEqual(alert["result"], "CLEAR")
        self.assertEqual(alert["status"], "POST_PRODUCTION_MONITORING_ALERT_CLEAR")
        self.assertEqual(alert["boundary"]["new_production_request_sent"], "NO")

    def test_runner_blocks_if_snapshot_failed(self):
        report, exit_code = runner.build_run_report(_snapshot(result="BLOCKED"), 1)

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["result"], "BLOCKED")
        failed = {item["name"] for item in report["checks"] if item["result"] == "FAIL"}
        self.assertIn("snapshot_result_pass", failed)
        alert = runner.build_alert_report(report)
        self.assertEqual(alert["result"], "ACTIVE")
        self.assertEqual(alert["status"], "POST_PRODUCTION_MONITORING_ALERT_ACTIVE")
        self.assertEqual(alert["severity"], "page")
        self.assertEqual(len(alert["failed_checks"]), 1)

    def test_runner_blocks_if_snapshot_implies_second_request(self):
        snapshot = _snapshot(
            boundary={
                "credential_file_read": "NO",
                "production_signing_executed": "NO",
                "production_http_network_attempted": "NO",
                "new_production_request_sent": "NO",
                "second_production_request_sent": "YES",
                "runtime_modified": "NO",
                "go_live": "NO-GO",
                "live_trading": "NO-GO",
            }
        )

        report, exit_code = runner.build_run_report(snapshot, 0)

        self.assertEqual(exit_code, 1)
        failed = {item["name"] for item in report["checks"] if item["result"] == "FAIL"}
        self.assertIn("runner_did_not_touch_runtime_boundaries", failed)

    def test_runner_blocks_if_continuous_runtime_enabled(self):
        snapshot = _snapshot(
            snapshot={
                "matching_filled_order_count": 1,
                "symbol_order_count_in_window": 1,
                "continuous_runtime_enabled": "YES",
                "automatic_trading_enabled": "NO",
            }
        )

        report, exit_code = runner.build_run_report(snapshot, 0)

        self.assertEqual(exit_code, 1)
        failed = {item["name"] for item in report["checks"] if item["result"] == "FAIL"}
        self.assertIn("continuous_runtime_disabled", failed)


if __name__ == "__main__":
    unittest.main()
