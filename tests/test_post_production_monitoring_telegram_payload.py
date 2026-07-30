import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "render_post_production_monitoring_telegram_payload.py"

spec = importlib.util.spec_from_file_location("render_post_production_monitoring_telegram_payload", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def _notification(result="EMITTED"):
    return {
        "result": result,
        "status": "POST_PRODUCTION_MONITORING_NOTIFICATION_READY",
        "reason": "alert transitioned to ACTIVE",
        "alert_result": "ACTIVE",
        "alert_status": "POST_PRODUCTION_MONITORING_ALERT_ACTIVE",
        "failed_checks": [
            {
                "name": "snapshot_result_pass",
                "result": "FAIL",
                "evidence": "post-production monitoring snapshot returned PASS",
            }
        ],
        "boundary": {
            "new_production_request_sent": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }


class PostProductionMonitoringTelegramPayloadTest(unittest.TestCase):
    def test_payload_ready_for_emitted_local_notification_without_sending(self):
        payload = module.build_payload(_notification("EMITTED"))

        self.assertEqual(payload["result"], "READY_TO_SEND")
        self.assertEqual(payload["send_authorized"], "NO")
        self.assertEqual(payload["send_attempted"], "NO")
        self.assertIn("failed_checks=1", payload["message"])
        self.assertEqual(payload["boundary"]["alerting_env_read"], "NO")
        self.assertEqual(payload["boundary"]["telegram_http_attempted"], "NO")
        self.assertEqual(payload["boundary"]["production_request_sent"], "NO")

    def test_payload_suppressed_when_notification_is_suppressed(self):
        payload = module.build_payload(_notification("SUPPRESSED"))

        self.assertEqual(payload["result"], "SUPPRESSED")
        self.assertEqual(payload["status"], "POST_PRODUCTION_MONITORING_TELEGRAM_PAYLOAD_SUPPRESSED")
        self.assertEqual(payload["send_attempted"], "NO")

    def test_cli_writes_non_sensitive_payload_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            notification_path = tmp_path / "notification.json"
            json_out = tmp_path / "payload.json"
            md_out = tmp_path / "payload.md"
            notification_path.write_text(json.dumps(_notification("EMITTED")), encoding="utf-8")
            result = subprocess.run(
                [
                    "python3",
                    str(MODULE_PATH),
                    "--notification-json",
                    str(notification_path),
                    "--json-out",
                    str(json_out),
                    "--markdown-out",
                    str(md_out),
                ],
                cwd=PROJECT_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(json_out.read_text(encoding="utf-8"))
            markdown = md_out.read_text(encoding="utf-8")

        self.assertEqual(payload["result"], "READY_TO_SEND")
        self.assertIn("telegram_http_attempted: NO", result.stdout)
        self.assertNotIn("TELEGRAM_BOT_TOKEN", markdown)
        self.assertNotIn("TELEGRAM_CHAT_ID", markdown)


if __name__ == "__main__":
    unittest.main()
