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
        self.assertEqual(report["checks"]["minimum_24h_successes_observed"], "PASS")
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


if __name__ == "__main__":
    unittest.main()
