import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "build_post_production_monitoring_timer_units.py"
INSTALL_SCRIPT = PROJECT_ROOT / "scripts" / "install_post_production_monitoring_timer_linux.sh"
UNINSTALL_SCRIPT = PROJECT_ROOT / "scripts" / "uninstall_post_production_monitoring_timer_linux.sh"

spec = importlib.util.spec_from_file_location("build_post_production_monitoring_timer_units", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class PostProductionMonitoringTimerUnitsTest(unittest.TestCase):
    def test_unit_content_is_read_only_monitoring_only(self):
        service = module.service_unit(
            "/opt/project-anchor",
            "/var/lib/project-anchor/reports",
            "/root/project-anchor",
        )
        timer = module.timer_unit(15)
        errors = module.validate_units(service, timer)

        self.assertEqual(errors, [])
        self.assertIn("run_post_production_monitoring_once.sh", service)
        self.assertIn("WorkingDirectory=/opt/project-anchor", service)
        self.assertIn("POST_PRODUCTION_MONITORING_OUTPUT_DIR=/var/lib/project-anchor/reports", service)
        self.assertIn("NoNewPrivileges=true", service)
        self.assertIn("ProtectSystem=full", service)
        self.assertIn("ProtectHome=true", service)
        self.assertIn("BindReadOnlyPaths=/root/project-anchor:/opt/project-anchor", service)
        self.assertIn("OnUnitActiveSec=15min", timer)
        combined = service + timer
        self.assertNotIn("production.env", combined)
        self.assertNotIn("execute_exactly_one_production_request.py", combined)
        self.assertNotIn("reconcile_production_post_send_readonly.py", combined)
        self.assertNotIn("curl ", combined)

    def test_builder_writes_units_and_non_sensitive_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            unit_dir = Path(tmp) / "units"
            report_dir = Path(tmp) / "reports"
            result = subprocess.run(
                [
                    "python3",
                    str(MODULE_PATH),
                    "--unit-dir",
                    str(unit_dir),
                    "--report-dir",
                    str(report_dir),
                    "--project-root",
                    "/root/project-anchor",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((unit_dir / module.SERVICE_NAME).exists())
            self.assertTrue((unit_dir / module.TIMER_NAME).exists())
            report = json.loads(
                (report_dir / "post_production_monitoring_timer_validation.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["boundary"]["credential_file_read"], "NO")
        self.assertEqual(report["boundary"]["new_production_request_sent"], "NO")
        self.assertEqual(report["boundary"]["go_live"], "NO-GO")
        self.assertEqual(report["boundary"]["live_trading"], "NO-GO")

    def test_install_and_uninstall_scripts_keep_execution_boundary_text(self):
        install_text = INSTALL_SCRIPT.read_text(encoding="utf-8")
        uninstall_text = UNINSTALL_SCRIPT.read_text(encoding="utf-8")
        combined = install_text + "\n" + uninstall_text

        self.assertIn("systemctl enable --now", install_text)
        self.assertIn('REPORT_DIR="${POST_PRODUCTION_MONITORING_REPORT_DIR:-$OUTPUT_DIR}"', install_text)
        self.assertIn("UNIT_PROJECT_ROOT", install_text)
        self.assertIn("systemctl disable --now", uninstall_text)
        self.assertIn("CREDENTIAL_FILE_READ=NO", combined)
        self.assertIn("NEW_PRODUCTION_REQUEST_SENT=NO", combined)
        self.assertIn("GO_LIVE=NO-GO", combined)
        self.assertNotIn("execute_exactly_one_production_request.py", combined)
        self.assertNotIn("reconcile_production_post_send_readonly.py", combined)
        self.assertNotIn("production.env", combined)

    def test_bind_paths_uses_same_path_when_no_runtime_alias_is_needed(self):
        self.assertEqual(
            module.bind_paths("/srv/project-anchor", None),
            "/srv/project-anchor",
        )
        self.assertEqual(
            module.bind_paths("/srv/project-anchor", "/root/project-anchor"),
            "/root/project-anchor:/srv/project-anchor",
        )


if __name__ == "__main__":
    unittest.main()
