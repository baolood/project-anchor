import importlib.util
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "validate_production_api_configuration.py"

spec = importlib.util.spec_from_file_location("validate_production_api_configuration", MODULE_PATH)
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)


class ProductionApiConfigurationValidatorTest(unittest.TestCase):
    def test_template_passes_without_secret_or_network_access(self):
        data = {
            "BINANCE_API_IP_WHITELIST": "45.76.190.109",
            "READ_PERMISSION": "YES",
            "SPOT_TRADING_PERMISSION": "NO",
            "WITHDRAW_PERMISSION": "NO",
            "PRODUCTION_API_CONFIG_SAVED": "YES",
            "AUTHORIZED_PRODUCTION_SIGNING": "NO",
            "AUTHORIZED_PRODUCTION_HTTP_NETWORK": "NO",
            "AUTHORIZED_PRODUCTION_REQUEST": "NO",
            "AUTHORIZED_GO_LIVE": "NO",
            "AUTHORIZED_LIVE_TRADING": "NO",
            "FINAL_OPERATOR_VERDICT": (
                "APPROVED_FOR_PRODUCTION_API_CONFIGURATION_READINESS_ONLY"
            ),
        }

        report = validator.validate(data, PROJECT_ROOT / "config" / "fixture.json")

        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["boundary"]["secret_value_read"], "NO")
        self.assertEqual(report["boundary"]["binance_api_called"], "NO")
        self.assertEqual(report["boundary"]["production_request_sent"], "NO")
        self.assertEqual(report["boundary"]["spot_trading_enabled"], "NO")
        self.assertEqual(report["boundary"]["go_live"], "NO-GO")

    def test_secret_like_values_are_rejected(self):
        data = {
            "BINANCE_API_IP_WHITELIST": "45.76.190.109",
            "READ_PERMISSION": "YES",
            "SPOT_TRADING_PERMISSION": "NO",
            "WITHDRAW_PERMISSION": "NO",
            "PRODUCTION_API_CONFIG_SAVED": "YES",
            "AUTHORIZED_PRODUCTION_SIGNING": "NO",
            "AUTHORIZED_PRODUCTION_HTTP_NETWORK": "NO",
            "AUTHORIZED_PRODUCTION_REQUEST": "NO",
            "AUTHORIZED_GO_LIVE": "NO",
            "AUTHORIZED_LIVE_TRADING": "NO",
            "FINAL_OPERATOR_VERDICT": "SECRET=do-not-allow",
        }

        report = validator.validate(data, PROJECT_ROOT / "config" / "fixture.json")

        self.assertEqual(report["result"], "BLOCKED")
        self.assertIn("FINAL_OPERATOR_VERDICT:SECRET_LIKE_VALUE_FORBIDDEN", report["errors"])


if __name__ == "__main__":
    unittest.main()
