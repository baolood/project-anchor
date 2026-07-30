import importlib.util
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "validate_production_runtime_identity_provisioning_plan.py"

spec = importlib.util.spec_from_file_location(
    "validate_production_runtime_identity_provisioning_plan",
    MODULE_PATH,
)
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)


def _contract():
    return {
        "runtime_identity": "project_anchor_runtime",
        "runtime_group": "project_anchor_runtime",
        "canonical_env_dir": "/etc/project-anchor",
        "canonical_env_path": "/etc/project-anchor/production.env",
        "expected_env_dir_owner": "root",
        "expected_env_dir_group": "project_anchor_runtime",
        "expected_env_dir_mode": "710",
        "expected_env_owner": "project_anchor_runtime",
        "expected_env_group": "project_anchor_runtime",
        "expected_env_mode": "600",
    }


def _plan():
    return {
        "target_runtime_identity": "project_anchor_runtime",
        "target_runtime_group": "project_anchor_runtime",
        "target_env_dir": "/etc/project-anchor",
        "target_env_dir_owner": "root",
        "target_env_dir_group": "project_anchor_runtime",
        "target_env_dir_mode": "710",
        "target_env_path": "/etc/project-anchor/production.env",
        "target_env_owner": "project_anchor_runtime",
        "target_env_group": "project_anchor_runtime",
        "target_env_mode": "600",
        "execution_authorized": "NO",
        "dry_validation_only": "YES",
        "interactive_sudo_send": "NO",
        "secret_value_read": "NO",
        "production_request_authorized": "NO",
        "go_live": "NO-GO",
        "live_trading": "NO-GO",
        "provisioning_steps": [
            {
                "name": "create_runtime_group",
                "operation": "create_group_if_absent",
                "command_template": "sudo dscl . -create /Groups/project_anchor_runtime",
            },
            {
                "name": "create_runtime_identity",
                "operation": "create_user_if_absent",
                "command_template": "sudo dscl . -create /Users/project_anchor_runtime",
            },
            {
                "name": "align_production_env_owner",
                "operation": "chown",
                "command_template": (
                    "sudo chown project_anchor_runtime:project_anchor_runtime "
                    "/etc/project-anchor/production.env"
                ),
            },
            {
                "name": "align_production_env_dir_group",
                "operation": "chgrp",
                "command_template": "sudo chgrp project_anchor_runtime /etc/project-anchor",
            },
            {
                "name": "enforce_production_env_dir_mode",
                "operation": "chmod",
                "command_template": "sudo chmod 710 /etc/project-anchor",
            },
            {
                "name": "enforce_production_env_mode",
                "operation": "chmod",
                "command_template": "sudo chmod 600 /etc/project-anchor/production.env",
            },
            {
                "name": "validate_runtime_owner_contract",
                "operation": "read_only_validate",
                "command_template": "python3 scripts/validate_production_runtime_owner_contract.py",
            },
        ],
        "rollback_steps": [
            {
                "name": "restore_root_wheel_owner_if_required",
                "operation": "chown",
                "command_template": "sudo chown root:wheel /etc/project-anchor/production.env",
            },
            {
                "name": "restore_root_wheel_dir_group_if_required",
                "operation": "chgrp",
                "command_template": "sudo chgrp wheel /etc/project-anchor",
            },
            {
                "name": "restore_dir_mode_700",
                "operation": "chmod",
                "command_template": "sudo chmod 700 /etc/project-anchor",
            },
            {
                "name": "restore_mode_600",
                "operation": "chmod",
                "command_template": "sudo chmod 600 /etc/project-anchor/production.env",
            },
        ],
    }


class ProductionRuntimeIdentityProvisioningPlanValidatorTest(unittest.TestCase):
    def test_valid_dry_plan_passes_without_execution(self):
        report = validator.validate(_plan(), _contract(), {"result": "BLOCKED"})

        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["boundary"]["provisioning_executed"], "NO")
        self.assertEqual(report["boundary"]["production_env_changed"], "NO")
        self.assertEqual(report["boundary"]["production_request_sent"], "NO")

    def test_execution_authorized_blocks(self):
        plan = _plan()
        plan["execution_authorized"] = "YES"

        report = validator.validate(plan, _contract(), {"result": "BLOCKED"})

        self.assertEqual(report["result"], "BLOCKED")
        self.assertIn("execution_authorized_no", report["errors"])

    def test_wrong_owner_target_blocks(self):
        plan = _plan()
        plan["target_env_owner"] = "root"

        report = validator.validate(plan, _contract(), {"result": "BLOCKED"})

        self.assertEqual(report["result"], "BLOCKED")
        self.assertIn("target_env_owner_matches_contract", report["errors"])

    def test_wrong_mode_target_blocks(self):
        plan = _plan()
        plan["target_env_mode"] = "640"

        report = validator.validate(plan, _contract(), {"result": "BLOCKED"})

        self.assertEqual(report["result"], "BLOCKED")
        self.assertIn("target_env_mode_600", report["errors"])

    def test_wrong_directory_mode_target_blocks(self):
        plan = _plan()
        plan["target_env_dir_mode"] = "700"

        report = validator.validate(plan, _contract(), {"result": "BLOCKED"})

        self.assertEqual(report["result"], "BLOCKED")
        self.assertIn("target_env_dir_mode_710", report["errors"])

    def test_send_or_network_command_blocks(self):
        plan = _plan()
        plan["provisioning_steps"].append(
            {
                "name": "bad_send",
                "operation": "send",
                "command_template": "python3 scripts/execute_exactly_one_production_request.py --execute",
            }
        )

        report = validator.validate(plan, _contract(), {"result": "BLOCKED"})

        self.assertEqual(report["result"], "BLOCKED")
        self.assertIn("command_templates_no_send_or_network", report["errors"])


if __name__ == "__main__":
    unittest.main()
