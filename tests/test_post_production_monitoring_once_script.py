import os
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "run_post_production_monitoring_once.sh"


class PostProductionMonitoringOnceScriptTest(unittest.TestCase):
    def test_manual_command_is_strict_shell(self):
        text = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("set -euo pipefail", text)
        self.assertIn("scripts/run_post_production_monitoring.py", text)
        self.assertIn("scripts/render_post_production_monitoring_telegram_payload.py", text)
        self.assertIn("scripts/send_post_production_monitoring_telegram_alert.py", text)
        self.assertIn("POST_PRODUCTION_MONITORING_OUTPUT_DIR", text)
        self.assertIn("POST_PRODUCTION_MONITORING_TELEGRAM_AUTO_SEND", text)
        self.assertIn("/var/lib/project-anchor/reports", text)
        self.assertIn("credential_file_read", text)
        self.assertIn("new_production_request_sent", text)
        self.assertIn("second_production_request_sent", text)
        self.assertNotIn("production.env", text)
        self.assertNotIn("execute_exactly_one_production_request.py", text)
        self.assertNotIn("reconcile_production_post_send_readonly.py", text)
        self.assertNotIn("curl ", text)

    def test_manual_command_passes_without_touching_network_or_credentials(self):
        env = os.environ.copy()
        with tempfile.TemporaryDirectory() as tmp:
            env["POST_PRODUCTION_MONITORING_OUTPUT_DIR"] = tmp
            result = subprocess.run(
                ["bash", str(SCRIPT)],
                cwd=PROJECT_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            alert_path = Path(tmp) / "post_production_monitoring_alert.json"
            notification_path = Path(tmp) / "post_production_monitoring_alert_notification.json"
            telegram_payload_path = Path(tmp) / "post_production_monitoring_telegram_payload.json"
            telegram_send_path = Path(tmp) / "post_production_monitoring_telegram_send_result.json"
            self.assertTrue(alert_path.exists())
            self.assertTrue(notification_path.exists())
            self.assertTrue(telegram_payload_path.exists())
            self.assertTrue(telegram_send_path.exists())
            alert = json.loads(alert_path.read_text(encoding="utf-8"))
            notification = json.loads(notification_path.read_text(encoding="utf-8"))
            telegram_payload = json.loads(telegram_payload_path.read_text(encoding="utf-8"))
            telegram_send = json.loads(telegram_send_path.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("POST_PRODUCTION_MONITORING_ONCE_RESULT=PASS", result.stdout)
        self.assertIn("TELEGRAM_AUTO_SEND=0", result.stdout)
        self.assertIn("TELEGRAM_SEND_ATTEMPTED=NO", result.stdout)
        self.assertIn("TELEGRAM_HTTP_ATTEMPTED=NO", result.stdout)
        self.assertIn("CREDENTIAL_FILE_READ=NO", result.stdout)
        self.assertIn("NEW_PRODUCTION_REQUEST_SENT=NO", result.stdout)
        self.assertIn("SECOND_PRODUCTION_REQUEST_SENT=NO", result.stdout)
        self.assertIn("GO_LIVE=NO-GO", result.stdout)
        self.assertIn("LIVE_TRADING=NO-GO", result.stdout)
        self.assertEqual(alert["result"], "CLEAR")
        self.assertEqual(alert["boundary"]["new_production_request_sent"], "NO")
        self.assertEqual(notification["result"], "SUPPRESSED")
        self.assertEqual(notification["boundary"]["new_production_request_sent"], "NO")
        self.assertEqual(telegram_payload["result"], "SUPPRESSED")
        self.assertEqual(telegram_payload["boundary"]["telegram_http_attempted"], "NO")
        self.assertEqual(telegram_send["send_attempted"], "NO")
        self.assertEqual(telegram_send["boundary"]["alerting_env_read"], "NO")
        self.assertEqual(telegram_send["boundary"]["telegram_http_attempted"], "NO")


if __name__ == "__main__":
    unittest.main()
