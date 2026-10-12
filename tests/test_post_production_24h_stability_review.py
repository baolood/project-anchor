import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "review_post_production_24h_stability.py"

spec = importlib.util.spec_from_file_location("review_post_production_24h_stability", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def write_json(path: Path, data: str) -> None:
    path.write_text(data, encoding="utf-8")


class PostProduction24hStabilityReviewTest(unittest.TestCase):
    def test_review_passes_with_monitoring_timer_and_boundary_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            write_json(
                report_dir / "post_production_monitoring_run.json",
                """
                {
                  "generated_at": "2026-08-03T02:36:37Z",
                  "result": "PASS",
                  "status": "POST_PRODUCTION_MONITORING_RUN_READY",
                  "boundary": {
                    "new_production_request_sent": "NO",
                    "second_production_request_sent": "NO",
                    "canary_rerun": "NO",
                    "go_live": "NO-GO",
                    "live_trading": "NO-GO"
                  }
                }
                """,
            )
            write_json(
                report_dir / "post_production_monitoring_snapshot.json",
                """
                {
                  "generated_at": "2026-08-03T02:36:37Z",
                  "result": "PASS",
                  "snapshot": {"worker": {"last_heartbeat_at": "2026-08-03T02:36:00Z"}},
                  "boundary": {
                    "new_production_request_sent": "NO",
                    "second_production_request_sent": "NO",
                    "canary_rerun": "NO",
                    "go_live": "NO-GO",
                    "live_trading": "NO-GO"
                  }
                }
                """,
            )
            write_json(
                report_dir / "post_production_monitoring_alert.json",
                '{"result":"CLEAR","status":"POST_PRODUCTION_MONITORING_ALERT_CLEAR"}',
            )
            write_json(
                report_dir / "post_production_monitoring_alert_notification.json",
                '{"result":"SUPPRESSED","status":"POST_PRODUCTION_MONITORING_NOTIFICATION_SUPPRESSED"}',
            )
            write_json(
                report_dir / "post_production_monitoring_timer_runtime_validation.json",
                '{"result":"PASS"}',
            )
            write_json(
                report_dir / "post_production_monitoring_timer_stability_validation.json",
                '{"result":"PASS","latest_consecutive_success_count":96}',
            )

            with mock.patch.object(module, "systemctl_active", return_value="active"), mock.patch.object(
                module, "systemctl_enabled", return_value="enabled"
            ), mock.patch.object(module, "journal_success_count", return_value=(96, None)):
                report = module.build_review(report_dir, "24 hours ago", 12)

        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["checks"]["monitoring_snapshot_pass"], "PASS")
        self.assertEqual(report["checks"]["minimum_24h_successes_observed"], "PASS")
        self.assertEqual(report["evidence"]["exchange_confirmed_order_status"], "UNKNOWN")
        self.assertEqual(report["evidence"]["exchange_reconciliation_supplied"], "NO")
        self.assertNotEqual(report["evidence"]["exchange_confirmed_order_status"], "PASS")
        self.assertEqual(report["status"], "POST_PRODUCTION_24H_STABILITY_REVIEW_PASS")
        self.assertEqual(report["boundary"]["credential_file_read"], "NO")
        self.assertEqual(report["boundary"]["new_production_request_sent"], "NO")
        self.assertEqual(report["boundary"]["go_live"], "NO-GO")

    def test_review_blocks_when_success_count_is_too_low(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            write_json(
                report_dir / "post_production_monitoring_run.json",
                """
                {
                  "result": "PASS",
                  "boundary": {
                    "new_production_request_sent": "NO",
                    "second_production_request_sent": "NO",
                    "canary_rerun": "NO",
                    "go_live": "NO-GO",
                    "live_trading": "NO-GO"
                  }
                }
                """,
            )
            write_json(report_dir / "post_production_monitoring_snapshot.json", '{"result":"PASS"}')
            write_json(report_dir / "post_production_monitoring_alert.json", '{"result":"CLEAR"}')
            write_json(report_dir / "post_production_monitoring_alert_notification.json", "{}")
            write_json(report_dir / "post_production_monitoring_timer_runtime_validation.json", '{"result":"PASS"}')
            write_json(report_dir / "post_production_monitoring_timer_stability_validation.json", '{"result":"PASS"}')

            with mock.patch.object(module, "systemctl_active", return_value="active"), mock.patch.object(
                module, "systemctl_enabled", return_value="enabled"
            ), mock.patch.object(module, "journal_success_count", return_value=(4, None)):
                report = module.build_review(report_dir, "24 hours ago", 12)

        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["checks"]["minimum_24h_successes_observed"], "FAIL")
        self.assertEqual(report["boundary"]["second_production_request_sent"], "NO")

    def test_review_blocks_when_timer_is_inactive(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            write_json(
                report_dir / "post_production_monitoring_run.json",
                """
                {
                  "result": "PASS",
                  "boundary": {
                    "new_production_request_sent": "NO",
                    "second_production_request_sent": "NO",
                    "canary_rerun": "NO",
                    "go_live": "NO-GO",
                    "live_trading": "NO-GO"
                  }
                }
                """,
            )
            write_json(report_dir / "post_production_monitoring_snapshot.json", '{"result":"PASS"}')
            write_json(report_dir / "post_production_monitoring_alert.json", '{"result":"CLEAR"}')
            write_json(report_dir / "post_production_monitoring_alert_notification.json", "{}")
            write_json(report_dir / "post_production_monitoring_timer_runtime_validation.json", '{"result":"PASS"}')
            write_json(report_dir / "post_production_monitoring_timer_stability_validation.json", '{"result":"PASS"}')

            with mock.patch.object(module, "systemctl_active", return_value="inactive"), mock.patch.object(
                module, "systemctl_enabled", return_value="enabled"
            ), mock.patch.object(module, "journal_success_count", return_value=(96, None)):
                report = module.build_review(report_dir, "24 hours ago", 12)

        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["checks"]["timer_active"], "FAIL")

    def test_review_uses_custom_window_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            write_json(
                report_dir / "post_production_monitoring_run.json",
                """
                {
                  "result": "PASS",
                  "boundary": {
                    "new_production_request_sent": "NO",
                    "second_production_request_sent": "NO",
                    "canary_rerun": "NO",
                    "go_live": "NO-GO",
                    "live_trading": "NO-GO"
                  }
                }
                """,
            )
            write_json(report_dir / "post_production_monitoring_snapshot.json", '{"result":"PASS"}')
            write_json(report_dir / "post_production_monitoring_alert.json", '{"result":"CLEAR"}')
            write_json(report_dir / "post_production_monitoring_alert_notification.json", "{}")
            write_json(report_dir / "post_production_monitoring_timer_runtime_validation.json", '{"result":"PASS"}')
            write_json(report_dir / "post_production_monitoring_timer_stability_validation.json", '{"result":"PASS"}')

            with mock.patch.object(module, "systemctl_active", return_value="active"), mock.patch.object(
                module, "systemctl_enabled", return_value="enabled"
            ), mock.patch.object(module, "journal_success_count", return_value=(191, None)):
                report = module.build_review(report_dir, "48 hours ago", 24, "48h")

        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["status"], "POST_PRODUCTION_48H_STABILITY_REVIEW_PASS")
        self.assertEqual(report["review_window"]["label"], "48h")
        self.assertEqual(report["checks"]["minimum_48h_successes_observed"], "PASS")
        self.assertEqual(report["next_single_task"], "continue_to_72h_read_only_observation")

    def test_repo_recorded_only_snapshot_is_repo_level_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            write_json(
                report_dir / "post_production_monitoring_run.json",
                """
                {
                  "result": "PASS",
                  "boundary": {
                    "new_production_request_sent": "NO",
                    "second_production_request_sent": "NO",
                    "canary_rerun": "NO",
                    "go_live": "NO-GO",
                    "live_trading": "NO-GO"
                  }
                }
                """,
            )
            write_json(
                report_dir / "post_production_monitoring_snapshot.json",
                """
                {
                  "result": "PASS_REPO_RECORDED_ONLY",
                  "status": "MONITORING_REPO_RECORDED_ONLY_CONTINUOUS_TRADING_DISABLED",
                  "checks": [
                    {"name": "repo_recorded_exactly_one_order", "result": "PASS"},
                    {"name": "exchange_confirmed_exactly_one_order", "result": "UNKNOWN"}
                  ],
                  "snapshot": {
                    "exchange_reconciliation_supplied": "NO",
                    "exchange_confirmed_order_status": "UNKNOWN"
                  },
                  "boundary": {
                    "new_production_request_sent": "NO",
                    "second_production_request_sent": "NO",
                    "canary_rerun": "NO",
                    "go_live": "NO-GO",
                    "live_trading": "NO-GO"
                  }
                }
                """,
            )
            write_json(report_dir / "post_production_monitoring_alert.json", '{"result":"CLEAR"}')
            write_json(report_dir / "post_production_monitoring_alert_notification.json", "{}")
            write_json(report_dir / "post_production_monitoring_timer_runtime_validation.json", '{"result":"PASS"}')
            write_json(report_dir / "post_production_monitoring_timer_stability_validation.json", '{"result":"PASS"}')

            with mock.patch.object(module, "systemctl_active", return_value="active"), mock.patch.object(
                module, "systemctl_enabled", return_value="enabled"
            ), mock.patch.object(module, "journal_success_count", return_value=(96, None)):
                report = module.build_review(report_dir, "24 hours ago", 12)

        self.assertEqual(report["checks"]["monitoring_snapshot_pass"], "PASS")
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["evidence"]["snapshot_result"], "PASS_REPO_RECORDED_ONLY")
        self.assertNotEqual(report["evidence"]["snapshot_result"], "PASS")
        self.assertEqual(report["evidence"]["exchange_confirmed_order_status"], "UNKNOWN")
        self.assertNotEqual(report["evidence"]["exchange_confirmed_order_status"], "PASS")

    def test_historical_order_check_names_are_not_exchange_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            write_json(
                report_dir / "post_production_monitoring_run.json",
                """
                {
                  "result": "PASS",
                  "boundary": {
                    "new_production_request_sent": "NO",
                    "second_production_request_sent": "NO",
                    "canary_rerun": "NO",
                    "go_live": "NO-GO",
                    "live_trading": "NO-GO"
                  }
                }
                """,
            )
            write_json(
                report_dir / "post_production_monitoring_snapshot.json",
                """
                {
                  "result": "PASS",
                  "checks": [
                    {"name": "exactly_one_order_confirmed", "result": "PASS"},
                    {"name": "no_new_or_second_request", "result": "PASS"}
                  ]
                }
                """,
            )
            write_json(report_dir / "post_production_monitoring_alert.json", '{"result":"CLEAR"}')
            write_json(report_dir / "post_production_monitoring_alert_notification.json", "{}")
            write_json(report_dir / "post_production_monitoring_timer_runtime_validation.json", '{"result":"PASS"}')
            write_json(report_dir / "post_production_monitoring_timer_stability_validation.json", '{"result":"PASS"}')

            with mock.patch.object(module, "systemctl_active", return_value="active"), mock.patch.object(
                module, "systemctl_enabled", return_value="enabled"
            ), mock.patch.object(module, "journal_success_count", return_value=(96, None)):
                report = module.build_review(report_dir, "24 hours ago", 12)

        self.assertEqual(report["checks"]["monitoring_snapshot_pass"], "PASS")
        self.assertEqual(report["evidence"]["exchange_confirmed_order_status"], "UNKNOWN")
        self.assertNotEqual(report["evidence"]["exchange_confirmed_order_status"], "PASS")

    def test_reconciled_exchange_confirmation_is_reported_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            write_json(
                report_dir / "post_production_monitoring_run.json",
                """
                {
                  "result": "PASS",
                  "boundary": {
                    "new_production_request_sent": "NO",
                    "second_production_request_sent": "NO",
                    "canary_rerun": "NO",
                    "go_live": "NO-GO",
                    "live_trading": "NO-GO"
                  }
                }
                """,
            )
            write_json(
                report_dir / "post_production_monitoring_snapshot.json",
                """
                {
                  "result": "PASS",
                  "snapshot": {
                    "exchange_reconciliation_supplied": "YES",
                    "exchange_confirmed_order_status": "PASS"
                  }
                }
                """,
            )
            write_json(report_dir / "post_production_monitoring_alert.json", '{"result":"CLEAR"}')
            write_json(report_dir / "post_production_monitoring_alert_notification.json", "{}")
            write_json(report_dir / "post_production_monitoring_timer_runtime_validation.json", '{"result":"PASS"}')
            write_json(report_dir / "post_production_monitoring_timer_stability_validation.json", '{"result":"PASS"}')

            with mock.patch.object(module, "systemctl_active", return_value="active"), mock.patch.object(
                module, "systemctl_enabled", return_value="enabled"
            ), mock.patch.object(module, "journal_success_count", return_value=(96, None)):
                report = module.build_review(report_dir, "24 hours ago", 12)

        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["checks"]["monitoring_snapshot_pass"], "PASS")
        self.assertEqual(report["evidence"]["exchange_reconciliation_supplied"], "YES")
        self.assertEqual(report["evidence"]["exchange_confirmed_order_status"], "PASS")

    def test_blocked_snapshot_fails_repo_level_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            write_json(
                report_dir / "post_production_monitoring_run.json",
                """
                {
                  "result": "PASS",
                  "boundary": {
                    "new_production_request_sent": "NO",
                    "second_production_request_sent": "NO",
                    "canary_rerun": "NO",
                    "go_live": "NO-GO",
                    "live_trading": "NO-GO"
                  }
                }
                """,
            )
            write_json(
                report_dir / "post_production_monitoring_snapshot.json",
                """
                {
                  "result": "BLOCKED",
                  "snapshot": {
                    "exchange_reconciliation_supplied": "YES",
                    "exchange_confirmed_order_status": "FAIL"
                  }
                }
                """,
            )
            write_json(report_dir / "post_production_monitoring_alert.json", '{"result":"CLEAR"}')
            write_json(report_dir / "post_production_monitoring_alert_notification.json", "{}")
            write_json(report_dir / "post_production_monitoring_timer_runtime_validation.json", '{"result":"PASS"}')
            write_json(report_dir / "post_production_monitoring_timer_stability_validation.json", '{"result":"PASS"}')

            with mock.patch.object(module, "systemctl_active", return_value="active"), mock.patch.object(
                module, "systemctl_enabled", return_value="enabled"
            ), mock.patch.object(module, "journal_success_count", return_value=(96, None)):
                report = module.build_review(report_dir, "24 hours ago", 12)

        self.assertEqual(report["checks"]["monitoring_snapshot_pass"], "FAIL")
        self.assertEqual(report["evidence"]["exchange_confirmed_order_status"], "FAIL")
        self.assertEqual(report["result"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
