import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "validate_manual_low_frequency_operations_runbook.py"

spec = importlib.util.spec_from_file_location("validate_manual_low_frequency_operations_runbook", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def _runbook(**overrides):
    data = {
        "RUNBOOK_NAME": "manual_low_frequency_operations_runbook_v1",
        "RUNBOOK_MODE": "manual_confirmed_low_frequency_execution_only",
        "POLICY_FILE": "config/manual_low_frequency_operations_policy.json",
        "BEFORE_REQUEST": [
            "confirm_ops_dashboard_health_pass",
            "confirm_post_production_monitoring_pass",
            "confirm_telegram_alert_channel_ready",
            "confirm_previous_post_send_reconciliation_pass",
            "confirm_no_unresolved_alert",
            "confirm_policy_validation_pass",
            "confirm_fresh_pre_send_readiness_pass",
            "confirm_explicit_operator_authorization_present",
        ],
        "DURING_REQUEST": [
            "send_exactly_one_request_only",
            "use_unique_idempotency_key",
            "do_not_retry",
            "do_not_send_second_request",
            "stop_on_unclear_exchange_result",
            "do_not_enable_continuous_runtime",
        ],
        "AFTER_REQUEST": [
            "run_read_only_post_send_reconciliation",
            "confirm_external_order_id_present",
            "confirm_no_duplicate_request",
            "confirm_telegram_alerting_ready",
            "observe_for_at_least_24h_before_next_request",
            "keep_go_live_no_go",
            "keep_live_trading_no_go",
        ],
        "STOP_CONDITIONS": [
            "ops_dashboard_unhealthy",
            "worker_heartbeat_missing",
            "monitoring_not_pass",
            "telegram_not_ready",
            "policy_validation_not_pass",
            "fresh_pre_send_readiness_not_pass",
            "explicit_operator_authorization_missing",
            "secret_disclosure_risk",
            "duplicate_or_second_request_risk",
            "unexpected_exchange_response",
            "reconciliation_not_pass",
            "unresolved_post_send_alert",
        ],
        "PROHIBITED_ACTIONS": [
            "automatic_trading",
            "automatic_retry",
            "second_request_same_window",
            "continuous_runtime_enablement",
            "go_live",
            "live_trading",
        ],
        "FINAL_OPERATOR_VERDICT": "APPROVED_FOR_MANUAL_LOW_FREQUENCY_OPERATIONS_RUNBOOK_ONLY",
    }
    data.update(overrides)
    return data


def _write_json(path: Path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


class ManualLowFrequencyOperationsRunbookTest(unittest.TestCase):
    def test_valid_runbook_passes_without_secret_or_production_request(self):
        report = module.validate(_runbook())

        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["checks"]["before_request_complete"], "PASS")
        self.assertEqual(report["checks"]["during_request_complete"], "PASS")
        self.assertEqual(report["checks"]["after_request_complete"], "PASS")
        self.assertEqual(report["boundary"]["secret_read"], "NO")
        self.assertEqual(report["boundary"]["production_request_sent"], "NO")
        self.assertEqual(report["boundary"]["telegram_sent_by_validator"], "NO")

    def test_missing_no_retry_step_blocks(self):
        runbook = _runbook(DURING_REQUEST=["send_exactly_one_request_only"])
        report = module.validate(runbook)

        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["checks"]["during_request_complete"], "FAIL")

    def test_missing_observation_step_blocks(self):
        runbook = _runbook(AFTER_REQUEST=["run_read_only_post_send_reconciliation"])
        report = module.validate(runbook)

        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["checks"]["after_request_complete"], "FAIL")

    def test_go_live_not_prohibited_blocks(self):
        runbook = _runbook(PROHIBITED_ACTIONS=["automatic_trading"])
        report = module.validate(runbook)

        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["checks"]["prohibited_actions_complete"], "FAIL")

    def test_cli_writes_non_sensitive_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            runbook_path = tmp_path / "runbook.json"
            json_out = tmp_path / "validation.json"
            md_out = tmp_path / "validation.md"
            _write_json(runbook_path, _runbook())

            result = subprocess.run(
                [
                    "python3",
                    str(MODULE_PATH),
                    "--runbook",
                    str(runbook_path),
                    "--json-out",
                    str(json_out),
                    "--md-out",
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
        self.assertIn("telegram_sent_by_validator: NO", result.stdout)
        self.assertNotIn("API_KEY", markdown)
        self.assertNotIn("SECRET", markdown)


if __name__ == "__main__":
    unittest.main()
