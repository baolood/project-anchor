import importlib.util
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "validate_post_production_monitoring_timer_stability_linux.py"

spec = importlib.util.spec_from_file_location(
    "validate_post_production_monitoring_timer_stability_linux", MODULE_PATH
)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


SAMPLE_SUCCESS_LOG = """
Jul 31 03:54:16 vultr systemd[1]: Starting Project Anchor read-only post-production monitoring refresh...
Jul 31 03:54:16 vultr bash[1]: POST_PRODUCTION_MONITORING_ONCE_RESULT=PASS
Jul 31 03:54:16 vultr bash[1]: RUN_STATUS=POST_PRODUCTION_MONITORING_RUN_READY
Jul 31 03:54:16 vultr bash[1]: TELEGRAM_SEND_STATUS=POST_PRODUCTION_MONITORING_TELEGRAM_SEND_SUPPRESSED
Jul 31 03:54:16 vultr bash[1]: TELEGRAM_SEND_ATTEMPTED=NO
Jul 31 03:54:16 vultr bash[1]: NEW_PRODUCTION_REQUEST_SENT=NO
Jul 31 03:54:16 vultr bash[1]: SECOND_PRODUCTION_REQUEST_SENT=NO
Jul 31 03:54:16 vultr bash[1]: GO_LIVE=NO-GO
Jul 31 03:54:16 vultr bash[1]: LIVE_TRADING=NO-GO
Jul 31 03:54:16 vultr systemd[1]: Finished Project Anchor read-only post-production monitoring refresh.
Jul 31 04:09:17 vultr systemd[1]: Starting Project Anchor read-only post-production monitoring refresh...
Jul 31 04:09:17 vultr bash[2]: POST_PRODUCTION_MONITORING_ONCE_RESULT=PASS
Jul 31 04:09:17 vultr bash[2]: RUN_STATUS=POST_PRODUCTION_MONITORING_RUN_READY
Jul 31 04:09:17 vultr bash[2]: TELEGRAM_SEND_STATUS=POST_PRODUCTION_MONITORING_TELEGRAM_SEND_SUPPRESSED
Jul 31 04:09:17 vultr bash[2]: TELEGRAM_SEND_ATTEMPTED=NO
Jul 31 04:09:17 vultr bash[2]: NEW_PRODUCTION_REQUEST_SENT=NO
Jul 31 04:09:17 vultr bash[2]: SECOND_PRODUCTION_REQUEST_SENT=NO
Jul 31 04:09:17 vultr bash[2]: GO_LIVE=NO-GO
Jul 31 04:09:17 vultr bash[2]: LIVE_TRADING=NO-GO
Jul 31 04:09:17 vultr systemd[1]: Finished Project Anchor read-only post-production monitoring refresh.
Jul 31 04:24:19 vultr systemd[1]: Starting Project Anchor read-only post-production monitoring refresh...
Jul 31 04:24:19 vultr bash[3]: POST_PRODUCTION_MONITORING_ONCE_RESULT=PASS
Jul 31 04:24:19 vultr bash[3]: RUN_STATUS=POST_PRODUCTION_MONITORING_RUN_READY
Jul 31 04:24:19 vultr bash[3]: TELEGRAM_SEND_STATUS=POST_PRODUCTION_MONITORING_TELEGRAM_SEND_SUPPRESSED
Jul 31 04:24:19 vultr bash[3]: TELEGRAM_SEND_ATTEMPTED=NO
Jul 31 04:24:19 vultr bash[3]: NEW_PRODUCTION_REQUEST_SENT=NO
Jul 31 04:24:19 vultr bash[3]: SECOND_PRODUCTION_REQUEST_SENT=NO
Jul 31 04:24:19 vultr bash[3]: GO_LIVE=NO-GO
Jul 31 04:24:19 vultr bash[3]: LIVE_TRADING=NO-GO
Jul 31 04:24:19 vultr systemd[1]: Finished Project Anchor read-only post-production monitoring refresh.
"""


class PostProductionMonitoringTimerStabilityTest(unittest.TestCase):
    def test_parse_runs_and_consecutive_successes(self):
        runs = module.parse_runs(SAMPLE_SUCCESS_LOG.strip().splitlines())

        self.assertEqual(len(runs), 3)
        self.assertTrue(all(module.run_passed(run) for run in runs))
        self.assertEqual(len(module.latest_consecutive_successes(runs)), 3)

    def test_build_report_passes_when_minimum_successes_are_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            (report_dir / "post_production_monitoring_timer_runtime_validation.json").write_text(
                '{"result":"PASS"}',
                encoding="utf-8",
            )
            report = module.build_report(
                report_dir,
                "90 minutes ago",
                3,
                SAMPLE_SUCCESS_LOG.strip().splitlines(),
                None,
            )

        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["latest_consecutive_success_count"], 3)
        self.assertEqual(report["checks"]["minimum_successful_runs_observed"], "PASS")
        self.assertEqual(report["boundary"]["new_production_request_sent"], "NO")
        self.assertEqual(report["boundary"]["go_live"], "NO-GO")

    def test_build_report_blocks_on_latest_failure(self):
        lines = (
            SAMPLE_SUCCESS_LOG
            + "\nJul 31 04:39:21 vultr systemd[1]: Starting Project Anchor read-only post-production monitoring refresh..."
            + "\nJul 31 04:39:21 vultr bash[4]: POST_PRODUCTION_MONITORING_ONCE_RESULT=FAIL"
            + "\nJul 31 04:39:21 vultr bash[4]: RUN_STATUS=POST_PRODUCTION_MONITORING_RUN_BLOCKED"
            + "\nJul 31 04:39:21 vultr bash[4]: NEW_PRODUCTION_REQUEST_SENT=NO"
            + "\nJul 31 04:39:21 vultr bash[4]: SECOND_PRODUCTION_REQUEST_SENT=NO"
            + "\nJul 31 04:39:21 vultr bash[4]: GO_LIVE=NO-GO"
            + "\nJul 31 04:39:21 vultr bash[4]: LIVE_TRADING=NO-GO"
            + "\nJul 31 04:39:21 vultr systemd[1]: Finished Project Anchor read-only post-production monitoring refresh."
        ).strip().splitlines()
        with tempfile.TemporaryDirectory() as tmp:
            report = module.build_report(Path(tmp), "90 minutes ago", 3, lines, None)

        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["checks"]["latest_run_passed"], "FAIL")
        self.assertEqual(report["latest_consecutive_success_count"], 0)


if __name__ == "__main__":
    unittest.main()
