import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "validate_post_production_alerting_readiness.py"

spec = importlib.util.spec_from_file_location("validate_post_production_alerting_readiness", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class PostProductionAlertingReadinessTest(unittest.TestCase):
    def _expected_identity(self, path: Path):
        st = path.stat()
        return module._owner_name(st), module._group_name(st), oct(os.stat(path).st_mode & 0o777)[2:]

    def test_missing_file_blocks_without_secret_or_http(self):
        result, exit_code = module.build_result(
            env_path=Path("/path/that/does/not/exist"),
            inspect_env=False,
            expected_owner="root",
            expected_group="project_anchor_runtime",
            expected_mode="640",
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(result["failure_code"], "ALERTING_ENV_FILE_MISSING_OR_UNREADABLE_METADATA")
        self.assertEqual(result["boundary"]["alerting_env_content_read"], "NO")
        self.assertEqual(result["boundary"]["telegram_http_attempted"], "NO")

    def test_metadata_pass_still_blocks_without_field_inspection(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "alerting.env"
            env_path.write_text("TELEGRAM_BOT_TOKEN=secret\n", encoding="utf-8")
            env_path.chmod(0o600)
            owner, group, mode = self._expected_identity(env_path)

            result, exit_code = module.build_result(
                env_path=env_path,
                inspect_env=False,
                expected_owner=owner,
                expected_group=group,
                expected_mode=mode,
            )

        self.assertEqual(exit_code, 1)
        self.assertEqual(result["failure_code"], "ALERTING_ENV_FIELD_INSPECTION_NOT_AUTHORIZED")
        self.assertEqual(result["checks"]["owner_match"], "YES")
        self.assertEqual(result["boundary"]["alerting_env_content_read"], "NO")
        self.assertNotIn("secret", str(result))

    def test_metadata_mismatch_blocks_before_field_inspection(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "alerting.env"
            env_path.write_text("TELEGRAM_BOT_TOKEN=secret\n", encoding="utf-8")
            env_path.chmod(0o600)
            owner, group, mode = self._expected_identity(env_path)

            result, exit_code = module.build_result(
                env_path=env_path,
                inspect_env=True,
                expected_owner=owner,
                expected_group=group,
                expected_mode="644" if mode != "644" else "600",
            )

        self.assertEqual(exit_code, 1)
        self.assertEqual(result["failure_code"], "ALERTING_ENV_METADATA_CONTRACT_MISMATCH")
        self.assertEqual(result["boundary"]["alerting_env_content_read"], "NO")

    def test_inspect_env_checks_presence_without_disclosure(self):
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
            env_path.chmod(0o600)
            owner, group, mode = self._expected_identity(env_path)

            result, exit_code = module.build_result(
                env_path=env_path,
                inspect_env=True,
                expected_owner=owner,
                expected_group=group,
                expected_mode=mode,
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["checks"]["telegram_bot_token_present"], "YES")
        self.assertEqual(result["boundary"]["alerting_env_content_read"], "YES")
        self.assertEqual(result["boundary"]["telegram_http_attempted"], "NO")
        self.assertNotIn("secret-token", str(result))
        self.assertNotIn("secret-chat", str(result))


if __name__ == "__main__":
    unittest.main()
