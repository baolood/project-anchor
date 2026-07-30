import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "generate_operations_readiness_snapshot.py"

spec = importlib.util.spec_from_file_location("generate_operations_readiness_snapshot", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class OperationsReadinessSnapshotPostProductionTest(unittest.TestCase):
    def test_post_production_alerting_loaders_preserve_non_secret_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            monitoring_path = tmp_path / "post_production_monitoring_run.json"
            readiness_path = tmp_path / "post_production_alerting_readiness.json"
            telegram_path = tmp_path / "post_production_monitoring_telegram_send_result.json"
            monitoring_path.write_text(
                json.dumps(
                    {
                        "result": "PASS",
                        "status": "POST_PRODUCTION_MONITORING_RUN_READY",
                        "snapshot_result": "PASS",
                        "snapshot_status": "MONITORING_READY_CONTINUOUS_TRADING_DISABLED",
                        "boundary": {"new_production_request_sent": "NO"},
                    }
                ),
                encoding="utf-8",
            )
            readiness_path.write_text(
                json.dumps(
                    {
                        "result": "PASS",
                        "status": "POST_PRODUCTION_ALERTING_READY",
                        "failure_code": "",
                        "inspect_env_requested": True,
                        "checks": {
                            "telegram_bot_token_present": "YES",
                            "telegram_chat_id_present": "YES",
                        },
                        "boundary": {
                            "telegram_bot_token_value_disclosed": "NO",
                            "telegram_chat_id_value_disclosed": "NO",
                            "telegram_http_attempted": "NO",
                        },
                    }
                ),
                encoding="utf-8",
            )
            telegram_path.write_text(
                json.dumps(
                    {
                        "result": "BLOCKED",
                        "status": "POST_PRODUCTION_MONITORING_TELEGRAM_SEND_SUPPRESSED",
                        "send_attempted": "NO",
                        "send_result": "NOT_ATTEMPTED",
                        "boundary": {
                            "secret_value_disclosed": "NO",
                            "telegram_http_attempted": "NO",
                        },
                    }
                ),
                encoding="utf-8",
            )

            old_monitoring = module.POST_PRODUCTION_MONITORING_RUN_REPORT
            old_readiness = module.POST_PRODUCTION_ALERTING_READINESS_REPORT
            old_telegram = module.POST_PRODUCTION_TELEGRAM_SEND_RESULT_REPORT
            module.POST_PRODUCTION_MONITORING_RUN_REPORT = monitoring_path
            module.POST_PRODUCTION_ALERTING_READINESS_REPORT = readiness_path
            module.POST_PRODUCTION_TELEGRAM_SEND_RESULT_REPORT = telegram_path
            try:
                monitoring = module.load_post_production_monitoring_run()
                readiness = module.load_post_production_alerting_readiness()
                telegram = module.load_post_production_telegram_send_result()
            finally:
                module.POST_PRODUCTION_MONITORING_RUN_REPORT = old_monitoring
                module.POST_PRODUCTION_ALERTING_READINESS_REPORT = old_readiness
                module.POST_PRODUCTION_TELEGRAM_SEND_RESULT_REPORT = old_telegram

        self.assertEqual(monitoring["result"], "PASS")
        self.assertEqual(readiness["result"], "PASS")
        self.assertEqual(readiness["checks"]["telegram_bot_token_present"], "YES")
        self.assertEqual(readiness["boundary"]["telegram_bot_token_value_disclosed"], "NO")
        self.assertEqual(telegram["result"], "BLOCKED")
        self.assertEqual(telegram["send_attempted"], "NO")
        self.assertEqual(telegram["boundary"]["telegram_http_attempted"], "NO")
        self.assertNotIn("secret", json.dumps(readiness).lower())


if __name__ == "__main__":
    unittest.main()
