import importlib.util
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "execute_exactly_one_production_request.py"

spec = importlib.util.spec_from_file_location("execute_exactly_one_production_request", MODULE_PATH)
executor = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.path.insert(0, str(PROJECT_ROOT / "anchor-backend"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
spec.loader.exec_module(executor)


class _FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return (
            b'{"symbol":"BTCUSDT","orderId":12345,"clientOrderId":"fixture-client",'
            b'"transactTime":1234567890,"status":"FILLED"}'
        )


class _FakeOpener:
    def __init__(self):
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append({"request": request, "timeout": timeout})
        return _FakeResponse()


def _fixture_env():
    return "\n".join(
        [
            "PRODUCTION_EXCHANGE_BASE_URL=https://api.binance.com",
            "PRODUCTION_EXCHANGE_API_KEY=fixture-production-key",
            "PRODUCTION_EXCHANGE_API_SECRET=fixture-production-secret",
            "PRODUCTION_EXCHANGE_KEY_ID=fixture-production-key-id",
        ]
    )


def _readiness():
    return {
        "result": "PASS",
        "decision": "READY_FOR_EXACTLY_ONE_PRODUCTION_REQUEST_SEND_WINDOW_OPEN",
    }


class ProductionExactlyOneSendExecutorTest(unittest.TestCase):
    def test_default_mode_does_not_read_or_send(self):
        report, exit_code = executor.build_execution_report(
            execute=False,
            credential_path=Path("/tmp/project-anchor-production-not-read.env"),
            now=datetime(2026, 7, 25, 1, 0, tzinfo=timezone.utc),
            readiness_report=_readiness(),
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["failure_code"], "PRODUCTION_SEND_EXECUTION_NOT_REQUESTED")
        self.assertEqual(report["boundary"]["credential_file_read"], "NO")
        self.assertEqual(report["boundary"]["production_request_attempted"], "NO")
        self.assertEqual(report["boundary"]["production_request_accepted"], "NO")

    def test_execute_blocks_when_readiness_is_not_pass(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as tmp:
            tmp.write(_fixture_env())
            tmp.flush()

            report, exit_code = executor.build_execution_report(
                execute=True,
                credential_path=Path(tmp.name),
                now=datetime(2026, 7, 25, 1, 0, tzinfo=timezone.utc),
                readiness_report={"result": "FAIL", "decision": "BLOCKED"},
                enforce_credential_contract=False,
                platform_name="Linux",
            )

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["failure_code"], "FRESH_PRODUCTION_SEND_READINESS_NOT_PASS")
        self.assertEqual(report["boundary"]["credential_file_read"], "NO")
        self.assertEqual(report["boundary"]["production_request_attempted"], "NO")

    def test_execute_blocks_on_macos_when_api_whitelist_requires_remote_ip(self):
        fake = _FakeOpener()
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as tmp:
            tmp.write(_fixture_env())
            tmp.flush()

            report, exit_code = executor.build_execution_report(
                execute=True,
                credential_path=Path(tmp.name),
                now=datetime(2026, 7, 25, 1, 0, tzinfo=timezone.utc),
                opener=fake,
                readiness_report=_readiness(),
                enforce_credential_contract=False,
                platform_name="Darwin",
            )

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["failure_code"], "PRODUCTION_EXECUTION_HOST_NOT_WHITELISTED")
        self.assertEqual(report["execution_host_contract"]["observed_platform"], "Darwin")
        self.assertFalse(report["execution_host_contract"]["compliant"])
        self.assertEqual(
            report["credential_contract"]["stat_error"],
            "NOT_EVALUATED_EXECUTION_HOST_NOT_COMPLIANT",
        )
        self.assertEqual(report["boundary"]["credential_file_read"], "NO")
        self.assertEqual(report["boundary"]["production_signing_executed"], "NO")
        self.assertEqual(report["boundary"]["production_request_attempted"], "NO")
        self.assertEqual(len(fake.calls), 0)

    def test_execute_blocks_when_credential_stat_is_permission_denied(self):
        fake = _FakeOpener()
        original = executor.owner_group_mode
        executor.owner_group_mode = lambda path: {
            "exists": None,
            "owner": None,
            "group": None,
            "mode": None,
            "stat_error": "PERMISSION_DENIED",
        }
        try:
            report, exit_code = executor.build_execution_report(
                execute=True,
                credential_path=Path("/etc/project-anchor/production.env"),
                now=datetime(2026, 7, 25, 1, 0, tzinfo=timezone.utc),
                opener=fake,
                readiness_report=_readiness(),
                platform_name="Linux",
            )
        finally:
            executor.owner_group_mode = original

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["failure_code"], "PRODUCTION_CREDENTIAL_CONTRACT_NOT_COMPLIANT")
        self.assertEqual(report["credential_contract"]["stat_error"], "PERMISSION_DENIED")
        self.assertEqual(report["boundary"]["credential_file_read"], "NO")
        self.assertEqual(report["boundary"]["production_signing_executed"], "NO")
        self.assertEqual(report["boundary"]["production_request_attempted"], "NO")
        self.assertEqual(len(fake.calls), 0)

    def test_execute_blocks_when_credential_owner_is_not_runtime_owner(self):
        fake = _FakeOpener()
        original = executor.owner_group_mode
        executor.owner_group_mode = lambda path: {
            "exists": True,
            "owner": "root",
            "group": "wheel",
            "mode": "600",
            "stat_error": None,
        }
        try:
            report, exit_code = executor.build_execution_report(
                execute=True,
                credential_path=Path("/etc/project-anchor/production.env"),
                now=datetime(2026, 7, 25, 1, 0, tzinfo=timezone.utc),
                opener=fake,
                readiness_report=_readiness(),
                platform_name="Linux",
            )
        finally:
            executor.owner_group_mode = original

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["failure_code"], "PRODUCTION_CREDENTIAL_CONTRACT_NOT_COMPLIANT")
        self.assertFalse(report["credential_contract"]["checks"]["owner_matches"])
        self.assertEqual(report["boundary"]["credential_file_read"], "NO")
        self.assertEqual(report["boundary"]["production_request_attempted"], "NO")
        self.assertEqual(len(fake.calls), 0)

    def test_fixture_execute_with_fake_transport_redacts_secrets(self):
        fake = _FakeOpener()
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as tmp:
            tmp.write(_fixture_env())
            tmp.flush()

            report, exit_code = executor.build_execution_report(
                execute=True,
                credential_path=Path(tmp.name),
                now=datetime(2026, 7, 25, 1, 0, tzinfo=timezone.utc),
                opener=fake,
                readiness_report=_readiness(),
                enforce_credential_contract=False,
                platform_name="Linux",
            )

        rendered = str(report)
        self.assertEqual(exit_code, 0)
        self.assertTrue(report["success"])
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(report["terminal"]["external_status"], "FILLED")
        self.assertEqual(report["request"]["max_notional"], "10")
        self.assertEqual(report["requested_payload_shape"]["quoteOrderQty"], "10")
        self.assertEqual(report["boundary"]["credential_file_read"], "YES")
        self.assertEqual(report["boundary"]["production_signing_executed"], "YES")
        self.assertEqual(report["boundary"]["production_request_attempted"], "YES")
        self.assertEqual(report["boundary"]["production_request_accepted"], "YES")
        self.assertNotIn("fixture-production-key", rendered)
        self.assertNotIn("fixture-production-secret", rendered)
        self.assertNotIn("fixture-production-key-id", rendered)
        self.assertNotIn("signature=", rendered)

    def test_fixture_execute_with_runtime_owner_contract_redacts_secrets(self):
        fake = _FakeOpener()
        original = executor.owner_group_mode
        original_load_contract = executor.load_contract
        executor.owner_group_mode = lambda path: {
            "exists": True,
            "owner": "project_anchor_runtime",
            "group": "project_anchor_runtime",
            "mode": "600",
            "stat_error": None,
        }
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8") as tmp:
                tmp.write(_fixture_env())
                tmp.flush()
                executor.load_contract = lambda: {
                    "canonical_path": tmp.name,
                    "expected_owner": "project_anchor_runtime",
                    "expected_group": "project_anchor_runtime",
                    "expected_mode": "600",
                }

                report, exit_code = executor.build_execution_report(
                    execute=True,
                    credential_path=Path(tmp.name),
                    now=datetime(2026, 7, 25, 1, 0, tzinfo=timezone.utc),
                    opener=fake,
                    readiness_report=_readiness(),
                    platform_name="Linux",
                )
        finally:
            executor.owner_group_mode = original
            executor.load_contract = original_load_contract

        rendered = str(report)
        self.assertEqual(exit_code, 0)
        self.assertTrue(report["credential_contract"]["compliant"])
        self.assertTrue(report["success"])
        self.assertEqual(len(fake.calls), 1)
        self.assertNotIn("fixture-production-key", rendered)
        self.assertNotIn("fixture-production-secret", rendered)
        self.assertNotIn("fixture-production-key-id", rendered)
        self.assertNotIn("signature=", rendered)


if __name__ == "__main__":
    unittest.main()
