import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "validate_manual_low_frequency_operations_policy.py"

spec = importlib.util.spec_from_file_location("validate_manual_low_frequency_operations_policy", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def _policy(**overrides):
    data = {
        "POLICY_NAME": "manual_low_frequency_operations_v1",
        "POLICY_MODE": "manual_confirmed_low_frequency_only",
        "AUTHORIZED_MARKET": "binance_spot",
        "AUTHORIZED_SYMBOLS": ["BTCUSDT"],
        "AUTHORIZED_SIDES": ["BUY_ONLY"],
        "MAX_NOTIONAL_PER_REQUEST": 10,
        "MAX_ORDER_COUNT_PER_REQUEST": 1,
        "MAX_REQUESTS_PER_WINDOW": 1,
        "MIN_HOURS_BETWEEN_PRODUCTION_REQUESTS": 24,
        "RECOMMENDED_MAX_REQUESTS_PER_WEEK": 3,
        "REQUIRES_EXPLICIT_OPERATOR_AUTHORIZATION_PER_REQUEST": True,
        "REQUIRES_FRESH_PRE_SEND_READINESS": True,
        "REQUIRES_POST_SEND_RECONCILIATION": True,
        "REQUIRES_POST_SEND_OBSERVATION_HOURS": 24,
        "ALLOW_AUTOMATIC_RETRY": False,
        "ALLOW_SECOND_REQUEST_IN_SAME_WINDOW": False,
        "ALLOW_AUTOMATIC_TRADING": False,
        "ALLOW_AUTOMATIC_POSITION_MANAGEMENT": False,
        "ALLOW_GO_LIVE": False,
        "ALLOW_LIVE_TRADING": False,
        "STOP_CONDITIONS": [
            "monitoring_not_pass",
            "telegram_not_ready",
            "reconciliation_not_pass",
            "unresolved_alert_present",
            "duplicate_or_second_request_risk",
            "secret_disclosure_risk",
            "unexpected_exchange_response",
            "operator_authorization_missing",
        ],
        "FINAL_OPERATOR_VERDICT": "APPROVED_FOR_MANUAL_LOW_FREQUENCY_OPERATIONS_POLICY_ONLY",
    }
    data.update(overrides)
    return data


def _write_json(path: Path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


class ManualLowFrequencyOperationsPolicyTest(unittest.TestCase):
    def test_valid_policy_passes_without_secret_or_production_request(self):
        report = module.validate(_policy())

        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["checks"]["max_notional_lte_10"], "PASS")
        self.assertEqual(report["checks"]["explicit_operator_authorization_required"], "PASS")
        self.assertEqual(report["boundary"]["secret_read"], "NO")
        self.assertEqual(report["boundary"]["production_request_sent"], "NO")
        self.assertEqual(report["boundary"]["go_live"], "NO-GO")
        self.assertEqual(report["next_single_task"], "manual_low_frequency_operations_runbook")

    def test_auto_retry_blocks(self):
        report = module.validate(_policy(ALLOW_AUTOMATIC_RETRY=True))

        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["checks"]["automatic_retry_disabled"], "FAIL")

    def test_missing_operator_authorization_blocks(self):
        report = module.validate(
            _policy(REQUIRES_EXPLICIT_OPERATOR_AUTHORIZATION_PER_REQUEST=False)
        )

        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["checks"]["explicit_operator_authorization_required"], "FAIL")

    def test_larger_notional_blocks(self):
        report = module.validate(_policy(MAX_NOTIONAL_PER_REQUEST=11))

        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["checks"]["max_notional_lte_10"], "FAIL")

    def test_cli_writes_non_sensitive_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            policy_path = tmp_path / "policy.json"
            json_out = tmp_path / "validation.json"
            md_out = tmp_path / "validation.md"
            _write_json(policy_path, _policy())

            result = subprocess.run(
                [
                    "python3",
                    str(MODULE_PATH),
                    "--policy",
                    str(policy_path),
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
        self.assertIn("secret_read: NO", result.stdout)
        self.assertNotIn("API_KEY", markdown)
        self.assertNotIn("SECRET", markdown)


if __name__ == "__main__":
    unittest.main()
