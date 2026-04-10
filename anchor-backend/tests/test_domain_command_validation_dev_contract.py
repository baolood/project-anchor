import unittest

from app.api.domain_command_validation_dev import run_domain_command_validation_dev
from app.core.domain_command_validation_contract import (
    DOMAIN_COMMAND_VALIDATION_DEV_SUMMARY_KEYS,
    DOMAIN_COMMAND_VALIDATION_DEV_TOP_LEVEL_KEYS,
    DOMAIN_COMMAND_VALIDATION_DEV_VALIDATION_KEYS,
)


class DomainCommandValidationDevContractTest(unittest.TestCase):
    def assert_contract_shape(self, response: dict) -> None:
        self.assertEqual(tuple(response.keys()), DOMAIN_COMMAND_VALIDATION_DEV_TOP_LEVEL_KEYS)
        self.assertEqual(
            tuple(response["summary"].keys()),
            DOMAIN_COMMAND_VALIDATION_DEV_SUMMARY_KEYS,
        )
        self.assertEqual(
            tuple(response["summary"]["validation"].keys()),
            DOMAIN_COMMAND_VALIDATION_DEV_VALIDATION_KEYS,
        )

    def test_quote_payload_success_contract(self) -> None:
        response = run_domain_command_validation_dev(
            "quote",
            {"command_type": "quote", "symbol": "BTCUSDT"},
        )

        self.assert_contract_shape(response)
        self.assertEqual(response["command_type"], "quote")
        self.assertEqual(
            response["payload"],
            {"command_type": "quote", "symbol": "BTCUSDT"},
        )
        self.assertEqual(
            response["summary"],
            {
                "command_type": "quote",
                "is_valid": True,
                "error_codes": (),
                "validation": {
                    "command_type": "quote",
                    "is_valid_command_type": True,
                    "missing_required_fields": (),
                    "unexpected_fields": (),
                },
            },
        )

    def test_quote_payload_missing_symbol_contract(self) -> None:
        response = run_domain_command_validation_dev("quote", {"command_type": "quote"})

        self.assert_contract_shape(response)
        self.assertEqual(response["command_type"], "quote")
        self.assertEqual(response["payload"], {"command_type": "quote"})
        self.assertEqual(
            response["summary"],
            {
                "command_type": "quote",
                "is_valid": False,
                "error_codes": ("MISSING_REQUIRED_FIELDS",),
                "validation": {
                    "command_type": "quote",
                    "is_valid_command_type": True,
                    "missing_required_fields": ("symbol",),
                    "unexpected_fields": (),
                },
            },
        )

    def test_invalid_command_type_contract(self) -> None:
        response = run_domain_command_validation_dev(
            "bad_type",
            {"command_type": "bad_type"},
        )

        self.assert_contract_shape(response)
        self.assertEqual(response["command_type"], "bad_type")
        self.assertEqual(response["payload"], {"command_type": "bad_type"})
        self.assertEqual(response["summary"]["is_valid"], False)
        self.assertEqual(
            response["summary"]["error_codes"],
            ("INVALID_COMMAND_TYPE", "UNEXPECTED_FIELDS"),
        )
        self.assertEqual(
            response["summary"]["validation"]["is_valid_command_type"],
            False,
        )
        self.assertEqual(
            response["summary"]["validation"]["missing_required_fields"],
            (),
        )
        self.assertEqual(
            response["summary"]["validation"]["unexpected_fields"],
            ("command_type",),
        )


if __name__ == "__main__":
    unittest.main()
