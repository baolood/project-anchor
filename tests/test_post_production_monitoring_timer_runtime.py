import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "validate_post_production_monitoring_timer_runtime_linux.py"

spec = importlib.util.spec_from_file_location(
    "validate_post_production_monitoring_timer_runtime_linux", MODULE_PATH
)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class PostProductionMonitoringTimerRuntimeTest(unittest.TestCase):
    def test_parse_properties(self):
        props = module.parse_properties(
            "LoadState=loaded\nActiveState=active\nLastTriggerUSec=Fri 2026-07-31 04:09:17 UTC\n"
        )

        self.assertEqual(props["LoadState"], "loaded")
        self.assertEqual(props["ActiveState"], "active")
        self.assertEqual(props["LastTriggerUSec"], "Fri 2026-07-31 04:09:17 UTC")

    def test_runtime_report_passes_for_active_timer_and_clear_monitoring(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            (report_dir / "post_production_monitoring_run.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-07-31T04:09:17Z",
                        "result": "PASS",
                        "status": "POST_PRODUCTION_MONITORING_RUN_READY",
                        "boundary": {
                            "new_production_request_sent": "NO",
                            "go_live": "NO-GO",
                            "live_trading": "NO-GO",
                        },
                    }
                ),
                encoding="utf-8",
            )
            (report_dir / "post_production_monitoring_telegram_send_result.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-07-31T04:09:17Z",
                        "result": "BLOCKED",
                        "status": "POST_PRODUCTION_MONITORING_TELEGRAM_SEND_SUPPRESSED",
                        "send_attempted": "NO",
                        "send_result": "NOT_ATTEMPTED",
                        "failure_code": "PAYLOAD_NOT_READY_TO_SEND",
                        "boundary": {
                            "secret_value_disclosed": "NO",
                            "telegram_http_attempted": "NO",
                        },
                    }
                ),
                encoding="utf-8",
            )

            report = module.build_runtime_report(
                report_dir,
                {
                    "LoadState": "loaded",
                    "ActiveState": "active",
                    "UnitFileState": "enabled",
                    "LastTriggerUSec": "Fri 2026-07-31 04:09:17 UTC",
                    "Result": "success",
                },
                {
                    "LoadState": "loaded",
                    "ActiveState": "inactive",
                    "Result": "success",
                    "ExecMainStatus": "0",
                    "NRestarts": "0",
                },
                None,
                None,
            )

        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["checks"]["timer_enabled"], "PASS")
        self.assertEqual(report["checks"]["telegram_sender_fail_closed_or_delivered"], "PASS")
        self.assertEqual(report["boundary"]["new_production_request_sent"], "NO")
        self.assertEqual(report["boundary"]["go_live"], "NO-GO")
        self.assertEqual(report["boundary"]["live_trading"], "NO-GO")

    def test_runtime_report_blocks_when_timer_is_inactive(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = module.build_runtime_report(
                Path(tmp),
                {
                    "LoadState": "loaded",
                    "ActiveState": "inactive",
                    "UnitFileState": "disabled",
                    "LastTriggerUSec": "",
                    "Result": "success",
                },
                {
                    "LoadState": "loaded",
                    "ActiveState": "inactive",
                    "Result": "success",
                    "ExecMainStatus": "0",
                },
                None,
                None,
            )

        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["checks"]["timer_active"], "FAIL")
        self.assertEqual(report["checks"]["timer_enabled"], "FAIL")
        self.assertEqual(report["checks"]["timer_last_trigger_present"], "FAIL")


if __name__ == "__main__":
    unittest.main()
