import importlib.util
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "validate_production_execution_host_contract.py"

spec = importlib.util.spec_from_file_location("validate_production_execution_host_contract", MODULE_PATH)
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
spec.loader.exec_module(validator)


def _contract():
    return {
        "expected_hostname": "vultr",
        "expected_os_family": "Linux",
        "expected_repo_path": "/root/project-anchor",
        "expected_binance_api_ip_whitelist": "45.76.190.109",
        "expected_branch": "main",
        "expected_runtime_identity": "project_anchor_runtime",
    }


def _observed(**overrides):
    data = {
        "hostname": "vultr",
        "os_family": "Linux",
        "repo_path": "/root/project-anchor",
        "branch": "main",
        "head": "d220dc4",
        "git_status_short": "",
        "user": "root",
    }
    data.update(overrides)
    return data


class ProductionExecutionHostContractTest(unittest.TestCase):
    def test_matching_cloud_host_passes_without_secrets_or_network(self):
        report = validator.validate(_contract(), observed=_observed())

        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["boundary"]["credential_file_read"], "NO")
        self.assertEqual(report["boundary"]["dns_lookup"], "NO")
        self.assertEqual(report["boundary"]["socket_opened"], "NO")
        self.assertEqual(report["boundary"]["production_request_sent"], "NO")

    def test_macos_local_host_blocks(self):
        report = validator.validate(
            _contract(),
            observed=_observed(
                hostname="MacBook-Air",
                os_family="Darwin",
                repo_path="/Users/baolood/Projects/project-anchor",
            ),
        )

        self.assertEqual(report["result"], "BLOCKED")
        self.assertIn("hostname_matches", report["errors"])
        self.assertIn("os_family_matches", report["errors"])
        self.assertIn("repo_path_matches", report["errors"])
        self.assertEqual(report["boundary"]["credential_file_read"], "NO")
        self.assertEqual(report["boundary"]["production_request_sent"], "NO")

    def test_dirty_workspace_blocks(self):
        report = validator.validate(_contract(), observed=_observed(git_status_short=" M file.py"))

        self.assertEqual(report["result"], "BLOCKED")
        self.assertIn("workspace_clean", report["errors"])

    def test_missing_ip_whitelist_blocks(self):
        contract = _contract()
        contract["expected_binance_api_ip_whitelist"] = ""

        report = validator.validate(contract, observed=_observed())

        self.assertEqual(report["result"], "BLOCKED")
        self.assertIn("api_ip_whitelist_present", report["errors"])


if __name__ == "__main__":
    unittest.main()
