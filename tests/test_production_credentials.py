import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "anchor-backend"))

from app.executors.production_credentials import (  # noqa: E402
    load_production_credentials,
    parse_env_lines,
    redacted_credential_shape,
    validate_production_credential_values,
)


def _fixture_env() -> str:
    return "\n".join(
        [
            "PRODUCTION_EXCHANGE_BASE_URL=https://api.binance.com",
            "PRODUCTION_EXCHANGE_API_KEY=fixture-production-key",
            "PRODUCTION_EXCHANGE_API_SECRET=fixture-production-secret",
            "PRODUCTION_EXCHANGE_KEY_ID=fixture-production-key-id",
        ]
    )


class ProductionCredentialsTest(unittest.TestCase):
    def test_parse_env_lines_only_extracts_known_fields(self):
        values = parse_env_lines(_fixture_env() + "\nIGNORED=value\n")

        self.assertEqual(values["PRODUCTION_EXCHANGE_BASE_URL"], "https://api.binance.com")
        self.assertEqual(values["PRODUCTION_EXCHANGE_KEY_ID"], "fixture-production-key-id")
        self.assertNotIn("IGNORED", values)

    def test_loader_defaults_to_read_not_authorized(self):
        credentials, report = load_production_credentials("/tmp/not-read.env")

        self.assertIsNone(credentials)
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], "PRODUCTION_CREDENTIAL_READ_NOT_AUTHORIZED")

    def test_loader_reads_authorized_fixture_and_redacts_shape(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as tmp:
            tmp.write(_fixture_env())
            tmp.flush()

            credentials, report = load_production_credentials(tmp.name, allow_read=True)
            shape = redacted_credential_shape(credentials, report)

        self.assertTrue(report["ok"])
        self.assertEqual(report["code"], "PRODUCTION_CREDENTIALS_LOADED")
        self.assertTrue(shape["loaded"])
        self.assertTrue(shape["base_url_present"])
        self.assertTrue(shape["api_key_present"])
        self.assertTrue(shape["api_secret_present"])
        self.assertTrue(shape["key_id_present"])
        self.assertNotIn("fixture-production-key", str(shape))
        self.assertNotIn("fixture-production-secret", str(shape))
        self.assertNotIn("fixture-production-key-id", str(shape))

    def test_validate_rejects_non_allowlisted_base_url(self):
        ok, field_status, reason = validate_production_credential_values(
            {
                "PRODUCTION_EXCHANGE_BASE_URL": "https://example.com",
                "PRODUCTION_EXCHANGE_API_KEY": "fixture-production-key",
                "PRODUCTION_EXCHANGE_API_SECRET": "fixture-production-secret",
                "PRODUCTION_EXCHANGE_KEY_ID": "fixture-production-key-id",
            }
        )

        self.assertFalse(ok)
        self.assertEqual(reason, "PRODUCTION_CREDENTIAL_SHAPE_INVALID")
        self.assertEqual(field_status["PRODUCTION_EXCHANGE_BASE_URL"], "MISSING_INVALID")

    def test_loader_rejects_missing_secret(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as tmp:
            tmp.write(
                "\n".join(
                    [
                        "PRODUCTION_EXCHANGE_BASE_URL=https://api.binance.com",
                        "PRODUCTION_EXCHANGE_API_KEY=fixture-production-key",
                        "PRODUCTION_EXCHANGE_KEY_ID=fixture-production-key-id",
                    ]
                )
            )
            tmp.flush()

            credentials, report = load_production_credentials(tmp.name, allow_read=True)

        self.assertIsNone(credentials)
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], "PRODUCTION_CREDENTIAL_SHAPE_INVALID")
        self.assertEqual(
            report["field_status"]["PRODUCTION_EXCHANGE_API_SECRET"],
            "MISSING_INVALID",
        )


if __name__ == "__main__":
    unittest.main()
