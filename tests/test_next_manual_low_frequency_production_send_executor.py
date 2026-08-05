import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "execute_next_manual_low_frequency_production_request.py"
spec = importlib.util.spec_from_file_location(
    "execute_next_manual_low_frequency_production_request",
    MODULE_PATH,
)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class _FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return (
            b'{"symbol":"BTCUSDT","orderId":67890,"clientOrderId":"fixture-next",'
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


def _eligibility_pass():
    return {
        "result": "PASS",
        "decision": module.NEXT_MANUAL_REQUIRED_DECISION,
    }


class NextManualLowFrequencyProductionSendExecutorTest(unittest.TestCase):
    def test_default_mode_blocks_without_reading_credentials_or_sending(self):
        report, exit_code = module.build_execution_report(
            execute=False,
            credential_path=Path("/tmp/not-read.env"),
            now=datetime(2026, 8, 5, 8, 0, tzinfo=timezone.utc),
            eligibility_report=_eligibility_pass(),
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(
            report["failure_code"],
            "NEXT_MANUAL_PRODUCTION_SEND_EXECUTION_NOT_REQUESTED",
        )
        self.assertEqual(report["boundary"]["credential_file_read"], "NO")
        self.assertEqual(report["boundary"]["production_request_attempted"], "NO")

    def test_execution_blocks_when_next_manual_eligibility_is_not_pass(self):
        fake_opener = _FakeOpener()
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as tmp:
            tmp.write(_fixture_env())
            tmp.flush()

            report, exit_code = module.build_execution_report(
                execute=True,
                credential_path=Path(tmp.name),
                now=datetime(2026, 8, 5, 8, 0, tzinfo=timezone.utc),
                opener=fake_opener,
                eligibility_report={"result": "BLOCKED", "decision": "NOT_READY"},
                enforce_credential_contract=False,
                platform_name="Linux",
            )

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["failure_code"], "NEXT_MANUAL_OPERATION_ELIGIBILITY_NOT_PASS")
        self.assertEqual(len(fake_opener.calls), 0)
        self.assertEqual(report["boundary"]["credential_file_read"], "NO")

    def test_fake_transport_success_uses_next_manual_report_and_redacts_secrets(self):
        fake_opener = _FakeOpener()
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            module.JSON_OUT = tmpdir / "next_manual_low_frequency_production_send_result.json"
            module.MD_OUT = tmpdir / "next_manual_low_frequency_production_send_result.md"
            old_report = tmpdir / "production_exactly_one_send_result.json"
            old_report.write_text('{"keep":"first-send"}\n', encoding="utf-8")
            credential_file = tmpdir / "production.env"
            credential_file.write_text(_fixture_env(), encoding="utf-8")

            report, exit_code = module.build_execution_report(
                execute=True,
                credential_path=credential_file,
                now=datetime(2026, 8, 5, 8, 0, tzinfo=timezone.utc),
                opener=fake_opener,
                eligibility_report=_eligibility_pass(),
                enforce_credential_contract=False,
                platform_name="Linux",
            )
            module.write_report(report)

            written = json.loads(module.JSON_OUT.read_text(encoding="utf-8"))
            old_report_text = old_report.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(len(fake_opener.calls), 1)
        self.assertEqual(written["terminal"]["external_status"], "FILLED")
        self.assertEqual(
            written["request"]["idempotency_key"],
            module.NEXT_MANUAL_LOW_FREQUENCY_PRODUCTION_IDEMPOTENCY_KEY,
        )
        self.assertEqual(old_report_text, '{"keep":"first-send"}\n')
        self.assertNotIn("fixture-production-key", str(written))
        self.assertNotIn("fixture-production-secret", str(written))
        self.assertNotIn("signature=", str(written))
        self.assertEqual(written["boundary"]["secret_value_disclosed"], "NO")


if __name__ == "__main__":
    unittest.main()
