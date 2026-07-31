import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "validate_post_production_alert_policy.py"

spec = importlib.util.spec_from_file_location("validate_post_production_alert_policy", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class PostProductionAlertPolicyTest(unittest.TestCase):
    def test_policy_cases_pass_without_secret_or_telegram_http(self):
        report = module.build_report()

        self.assertEqual(report["result"], "PASS")
        cases = {case["name"]: case for case in report["cases"]}
        self.assertEqual(
            cases["clear_state_stays_silent"]["observed"]["notification_result"],
            "SUPPRESSED",
        )
        self.assertEqual(
            cases["active_transition_prepares_single_notification"]["observed"][
                "notification_result"
            ],
            "EMITTED",
        )
        self.assertEqual(
            cases["active_transition_prepares_single_notification"]["observed"][
                "payload_result"
            ],
            "READY_TO_SEND",
        )
        self.assertEqual(
            cases["repeated_active_is_suppressed"]["observed"]["notification_result"],
            "SUPPRESSED",
        )
        self.assertEqual(
            cases["recovered_then_active_notifies_again"]["observed"]["notification_result"],
            "EMITTED",
        )
        self.assertEqual(report["boundary"]["alerting_env_read"], "NO")
        self.assertEqual(report["boundary"]["telegram_http_attempted"], "NO")
        self.assertEqual(report["boundary"]["production_request_sent"], "NO")

    def test_cli_writes_non_sensitive_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_out = Path(tmp) / "policy.json"
            md_out = Path(tmp) / "policy.md"
            result = subprocess.run(
                [
                    "python3",
                    str(MODULE_PATH),
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
            report = json.loads(json_out.read_text(encoding="utf-8"))
            markdown = md_out.read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["result"], "PASS")
        self.assertIn("telegram_http_attempted: NO", result.stdout)
        self.assertNotIn("TELEGRAM_BOT_TOKEN", markdown)
        self.assertNotIn("TELEGRAM_CHAT_ID", markdown)
        self.assertNotIn("secret-token", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
