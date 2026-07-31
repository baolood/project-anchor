import importlib.util
import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "record_telegram_channel_evidence.py"

spec = importlib.util.spec_from_file_location("record_telegram_channel_evidence", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class TelegramChannelEvidenceTest(unittest.TestCase):
    def test_delivered_evidence_records_non_secret_status_only(self):
        result = module.build_result(delivered=True, source="operator_observed_telegram_message")
        encoded = json.dumps(result)

        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["delivery_observed"], "YES")
        self.assertEqual(result["boundary"]["alerting_env_read"], "NO")
        self.assertEqual(result["boundary"]["production_request_sent"], "NO")
        self.assertEqual(result["boundary"]["go_live"], "NO-GO")
        self.assertNotIn("TELEGRAM_BOT_TOKEN", encoded)
        self.assertNotIn("TELEGRAM_CHAT_ID", encoded)
        self.assertNotIn("Authorization", encoded)


if __name__ == "__main__":
    unittest.main()
