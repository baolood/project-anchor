import importlib.util
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "validate_production_runtime_owner_contract.py"

spec = importlib.util.spec_from_file_location("validate_production_runtime_owner_contract", MODULE_PATH)
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)


def _config():
    return {
        "runtime_identity": "project-anchor-runtime",
        "runtime_group": "project-anchor-runtime",
        "canonical_env_path": "/etc/project-anchor/production.env",
        "expected_env_owner": "project-anchor-runtime",
        "expected_env_group": "project-anchor-runtime",
        "expected_env_mode": "600",
        "group_based_secret_access": "NO",
        "interactive_sudo_required": "NO",
        "owner_mismatch_fail_closed": "YES",
        "mode_mismatch_fail_closed": "YES",
        "identity_unresolved_fail_closed": "YES",
        "stat_permission_failure_fail_closed": "YES",
        "production_env_change_authorized": "NO",
        "owner_or_mode_change_authorized": "NO",
        "production_request_authorized": "NO",
        "go_live": "NO-GO",
        "live_trading": "NO-GO",
    }


def _patch_validator(*, observed, user_exists=True, group_exists=True):
    original_owner_group_mode = validator.owner_group_mode
    original_identity_exists = validator.identity_exists
    validator.owner_group_mode = lambda path: observed

    def fake_identity_exists(name, *, group=False):
        return group_exists if group else user_exists

    validator.identity_exists = fake_identity_exists
    return original_owner_group_mode, original_identity_exists


def _restore_validator(originals):
    validator.owner_group_mode, validator.identity_exists = originals


class ProductionRuntimeOwnerContractValidatorTest(unittest.TestCase):
    def test_owner_match_passes(self):
        originals = _patch_validator(
            observed={
                "exists": True,
                "owner": "project-anchor-runtime",
                "group": "project-anchor-runtime",
                "mode": "600",
                "stat_error": None,
            }
        )
        try:
            report = validator.validate(_config())
        finally:
            _restore_validator(originals)

        self.assertEqual(report["result"], "PASS")
        self.assertTrue(report["checks"]["owner_match"])
        self.assertEqual(report["boundary"]["secret_value_read"], "NO")
        self.assertEqual(report["boundary"]["transport_called_when_blocked"], "NO")

    def test_owner_mismatch_blocks(self):
        originals = _patch_validator(
            observed={
                "exists": True,
                "owner": "root",
                "group": "wheel",
                "mode": "600",
                "stat_error": None,
            }
        )
        try:
            report = validator.validate(_config())
        finally:
            _restore_validator(originals)

        self.assertEqual(report["result"], "BLOCKED")
        self.assertFalse(report["checks"]["owner_match"])
        self.assertTrue(report["checks"]["owner_mismatch_fail_closed"])

    def test_mode_mismatch_blocks(self):
        originals = _patch_validator(
            observed={
                "exists": True,
                "owner": "project-anchor-runtime",
                "group": "project-anchor-runtime",
                "mode": "640",
                "stat_error": None,
            }
        )
        try:
            report = validator.validate(_config())
        finally:
            _restore_validator(originals)

        self.assertEqual(report["result"], "BLOCKED")
        self.assertFalse(report["checks"]["mode_match"])
        self.assertTrue(report["checks"]["mode_mismatch_fail_closed"])

    def test_runtime_identity_unresolved_blocks(self):
        originals = _patch_validator(
            observed={
                "exists": True,
                "owner": "project-anchor-runtime",
                "group": "project-anchor-runtime",
                "mode": "600",
                "stat_error": None,
            },
            user_exists=False,
        )
        try:
            report = validator.validate(_config())
        finally:
            _restore_validator(originals)

        self.assertEqual(report["result"], "BLOCKED")
        self.assertFalse(report["checks"]["runtime_identity_resolved"])
        self.assertTrue(report["checks"]["identity_unresolved_fail_closed"])

    def test_stat_permission_failure_blocks(self):
        originals = _patch_validator(
            observed={
                "exists": None,
                "owner": None,
                "group": None,
                "mode": None,
                "stat_error": "PERMISSION_DENIED",
            }
        )
        try:
            report = validator.validate(_config())
        finally:
            _restore_validator(originals)

        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["observed_env"]["stat_error"], "PERMISSION_DENIED")
        self.assertTrue(report["checks"]["stat_permission_failure_fail_closed"])


if __name__ == "__main__":
    unittest.main()
