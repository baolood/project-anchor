import unittest
from unittest.mock import patch

from app.executors.testnet_real_handoff_adapter import (
    build_real_handoff_adapter_skeleton,
    build_real_handoff_runtime_snapshot,
)


class TestnetRealHandoffAdapterV1Test(unittest.TestCase):
    def test_snapshot_reports_credential_free_mock_posture(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "TESTNET_EXCHANGE_BASE_URL": "https://testnet.binancefuture.com",
                "TESTNET_EXECUTOR_MODE": "mock",
                "TESTNET_EXECUTOR_REAL_ENABLE": "0",
                "TESTNET_EXCHANGE_API_KEY": "",
                "TESTNET_EXCHANGE_API_SECRET": "",
                "TESTNET_EXCHANGE_KEY_ID": "",
            },
            clear=False,
        ):
            snapshot = build_real_handoff_runtime_snapshot()

        self.assertEqual(snapshot["configured_origin"], "https://testnet.binancefuture.com")
        self.assertEqual(snapshot["executor_mode"], "mock")
        self.assertEqual(snapshot["real_enable"], "0")
        self.assertFalse(snapshot["api_key_present"])
        self.assertFalse(snapshot["api_secret_present"])
        self.assertFalse(snapshot["key_id_present"])
        self.assertTrue(snapshot["credential_free_mock_posture"])
        self.assertEqual(snapshot["blocked_reasons"], [])

    def test_snapshot_never_exposes_secret_values(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "TESTNET_EXCHANGE_BASE_URL": "https://testnet.binancefuture.com",
                "TESTNET_EXECUTOR_MODE": "mock",
                "TESTNET_EXECUTOR_REAL_ENABLE": "0",
                "TESTNET_EXCHANGE_API_KEY": "real-key",
                "TESTNET_EXCHANGE_API_SECRET": "real-secret",
                "TESTNET_EXCHANGE_KEY_ID": "kid-1",
            },
            clear=False,
        ):
            snapshot = build_real_handoff_runtime_snapshot()

        self.assertTrue(snapshot["api_key_present"])
        self.assertTrue(snapshot["api_secret_present"])
        self.assertTrue(snapshot["key_id_present"])
        self.assertNotIn("real-key", str(snapshot))
        self.assertNotIn("real-secret", str(snapshot))
        self.assertNotIn("kid-1", str(snapshot))
        self.assertFalse(snapshot["credential_free_mock_posture"])

    def test_adapter_marks_real_mode_drift_as_not_openable(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "TESTNET_EXCHANGE_BASE_URL": "https://testnet.binancefuture.com",
                "TESTNET_EXECUTOR_MODE": "real",
                "TESTNET_EXECUTOR_REAL_ENABLE": "1",
            },
            clear=False,
        ):
            adapter = build_real_handoff_adapter_skeleton()

        self.assertFalse(adapter["task_opening_allowed"])
        self.assertEqual(adapter["type"], "real_credential_handoff_adapter_skeleton")
        self.assertIn("executor_mode_not_mock", adapter["current_runtime"]["blocked_reasons"])
        self.assertIn("real_enable_not_zero", adapter["current_runtime"]["blocked_reasons"])
        self.assertFalse(adapter["allows_runtime_mutation"])
        self.assertFalse(adapter["allows_external_request"])
        self.assertFalse(adapter["allows_live_trading"])


if __name__ == "__main__":
    unittest.main()
