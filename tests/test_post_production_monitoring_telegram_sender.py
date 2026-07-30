import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "send_post_production_monitoring_telegram_alert.py"

spec = importlib.util.spec_from_file_location("send_post_production_monitoring_telegram_alert", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def _payload(result="READY_TO_SEND"):
    return {
        "result": result,
        "status": "POST_PRODUCTION_MONITORING_TELEGRAM_PAYLOAD_READY",
        "message": "Project Anchor alert",
    }


class _FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class PostProductionMonitoringTelegramSenderTest(unittest.TestCase):
    def test_suppressed_payload_blocks_without_env_or_http(self):
        result, exit_code = module.build_result(
            _payload("SUPPRESSED"),
            execute=False,
            env_path=Path("/path/that/must/not/be/read"),
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(result["status"], "POST_PRODUCTION_MONITORING_TELEGRAM_SEND_SUPPRESSED")
        self.assertEqual(result["failure_code"], "PAYLOAD_NOT_READY_TO_SEND")
        self.assertEqual(result["boundary"]["alerting_env_read"], "NO")
        self.assertEqual(result["boundary"]["telegram_http_attempted"], "NO")

    def test_ready_payload_without_execute_blocks_before_secret_read(self):
        result, exit_code = module.build_result(
            _payload("READY_TO_SEND"),
            execute=False,
            env_path=Path("/path/that/must/not/be/read"),
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(result["failure_code"], "EXECUTE_FLAG_REQUIRED")
        self.assertEqual(result["boundary"]["alerting_env_read"], "NO")
        self.assertEqual(result["send_attempted"], "NO")

    def test_execute_reads_presence_and_uses_injected_opener_without_disclosure(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "alerting.env"
            env_path.write_text(
                "\n".join(
                    [
                        "TELEGRAM_NOTIFY_ENABLED=1",
                        "TELEGRAM_BOT_TOKEN=secret-token",
                        "TELEGRAM_CHAT_ID=secret-chat",
                    ]
                ),
                encoding="utf-8",
            )
            calls = []

            def fake_open(request, timeout):
                calls.append((request, timeout))
                return _FakeResponse()

            result, exit_code = module.build_result(
                _payload("READY_TO_SEND"),
                execute=True,
                env_path=env_path,
                opener=fake_open,
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["send_attempted"], "YES")
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["boundary"]["alerting_env_read"], "YES")
        self.assertEqual(result["boundary"]["telegram_bot_token_read"], "YES")
        self.assertEqual(result["boundary"]["secret_value_disclosed"], "NO")
        self.assertNotIn("secret-token", json.dumps(result))
        self.assertNotIn("secret-chat", json.dumps(result))

    def test_execute_fails_closed_when_notify_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "alerting.env"
            env_path.write_text(
                "TELEGRAM_NOTIFY_ENABLED=0\nTELEGRAM_BOT_TOKEN=x\nTELEGRAM_CHAT_ID=y\n",
                encoding="utf-8",
            )

            result, exit_code = module.build_result(
                _payload("READY_TO_SEND"),
                execute=True,
                env_path=env_path,
                opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("no http")),
            )

        self.assertEqual(exit_code, 1)
        self.assertEqual(result["failure_code"], "TELEGRAM_NOTIFY_NOT_ENABLED")
        self.assertEqual(result["boundary"]["telegram_http_attempted"], "NO")


if __name__ == "__main__":
    unittest.main()
