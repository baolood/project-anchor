import os
import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "run_post_production_monitoring_once.sh"


class PostProductionMonitoringOnceScriptTest(unittest.TestCase):
    def test_manual_command_is_strict_shell(self):
        text = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("set -euo pipefail", text)
        self.assertIn("scripts/run_post_production_monitoring.py", text)
        self.assertIn("credential_file_read", text)
        self.assertIn("new_production_request_sent", text)
        self.assertIn("second_production_request_sent", text)
        self.assertNotIn("production.env", text)
        self.assertNotIn("execute_exactly_one_production_request.py", text)
        self.assertNotIn("reconcile_production_post_send_readonly.py", text)
        self.assertNotIn("curl ", text)

    def test_manual_command_passes_without_touching_network_or_credentials(self):
        env = os.environ.copy()
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            cwd=PROJECT_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("POST_PRODUCTION_MONITORING_ONCE_RESULT=PASS", result.stdout)
        self.assertIn("CREDENTIAL_FILE_READ=NO", result.stdout)
        self.assertIn("NEW_PRODUCTION_REQUEST_SENT=NO", result.stdout)
        self.assertIn("SECOND_PRODUCTION_REQUEST_SENT=NO", result.stdout)
        self.assertIn("GO_LIVE=NO-GO", result.stdout)
        self.assertIn("LIVE_TRADING=NO-GO", result.stdout)


if __name__ == "__main__":
    unittest.main()
