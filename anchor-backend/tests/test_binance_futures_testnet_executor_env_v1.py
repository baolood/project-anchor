import os
import unittest
from unittest.mock import patch

from app.executors.binance_futures_testnet import (
    BinanceFuturesTestnetExecutor,
    DEFAULT_BASE,
)


class BinanceFuturesTestnetExecutorEnvV1Test(unittest.TestCase):
    def test_uses_canonical_testnet_env_names(self) -> None:
        env = {
            "TESTNET_EXCHANGE_BASE_URL": "https://demo-fapi.binance.com",
            "TESTNET_EXCHANGE_API_KEY": "k" * 64,
            "TESTNET_EXCHANGE_API_SECRET": "s" * 64,
            "TESTNET_EXCHANGE_RECV_WINDOW": "7000",
        }
        with patch.dict(os.environ, env, clear=True):
            ex = BinanceFuturesTestnetExecutor()

        self.assertEqual(ex.base, "https://demo-fapi.binance.com")
        self.assertEqual(ex.api_key, "k" * 64)
        self.assertEqual(ex.api_secret, "s" * 64)
        self.assertEqual(ex.recv_window, 7000)

    def test_missing_canonical_credentials_raise(self) -> None:
        with patch.dict(
            os.environ,
            {"TESTNET_EXCHANGE_BASE_URL": DEFAULT_BASE},
            clear=True,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "TESTNET_EXCHANGE_API_KEY/TESTNET_EXCHANGE_API_SECRET missing",
            ):
                BinanceFuturesTestnetExecutor()
