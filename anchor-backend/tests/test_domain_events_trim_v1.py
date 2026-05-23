import unittest

from app.domain_events import _trim_payload


class DomainEventsTrimV1Test(unittest.TestCase):
    def test_trim_payload_keeps_preflight_review_fields(self) -> None:
        payload = {
            "type": "ORDER",
            "attempt": 1,
            "enabled": False,
            "source": "redis",
            "execution_mode": "testnet",
            "gate": "credential_presence",
            "failure_family": "TESTNET_CREDENTIALS_MISSING",
            "external_request_started": False,
            "external_order_id_present": False,
            "host_label": "binance_futures_testnet",
            "configured_origin": "https://testnet.binancefuture.com",
            "market": "binance_testnet",
            "canonical_path": "ORDER:testnet",
            "key_id_present": True,
            "preflight_passed": False,
            "ignore_me": "drop",
        }

        trimmed = _trim_payload(payload)

        self.assertEqual(trimmed["type"], "ORDER")
        self.assertEqual(trimmed["attempt"], 1)
        self.assertFalse(trimmed["enabled"])
        self.assertEqual(trimmed["source"], "redis")
        self.assertEqual(trimmed["execution_mode"], "testnet")
        self.assertEqual(trimmed["gate"], "credential_presence")
        self.assertEqual(trimmed["failure_family"], "TESTNET_CREDENTIALS_MISSING")
        self.assertFalse(trimmed["external_request_started"])
        self.assertFalse(trimmed["external_order_id_present"])
        self.assertEqual(trimmed["host_label"], "binance_futures_testnet")
        self.assertEqual(trimmed["configured_origin"], "https://testnet.binancefuture.com")
        self.assertEqual(trimmed["market"], "binance_testnet")
        self.assertEqual(trimmed["canonical_path"], "ORDER:testnet")
        self.assertTrue(trimmed["key_id_present"])
        self.assertFalse(trimmed["preflight_passed"])
        self.assertNotIn("ignore_me", trimmed)


if __name__ == "__main__":
    unittest.main()
