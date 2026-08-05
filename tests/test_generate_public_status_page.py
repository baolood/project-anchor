import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "generate_public_status_page.py"

spec = importlib.util.spec_from_file_location("generate_public_status_page", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


class PublicStatusPageTest(unittest.TestCase):
    def test_public_status_excludes_internal_evidence_and_execution_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            reports = Path(tmp)
            write_json(
                reports / "operations_readiness_snapshot.json",
                {
                    "overall_status": "WARN",
                    "post_production_monitoring": {"result": "PASS"},
                    "worker": {"kill_switch": False},
                    "boundary": {"secret_read": "NO"},
                },
            )
            write_json(
                reports / "post_production_72h_stability_review.json",
                {"result": "PASS", "internal_order_id": "do-not-render"},
            )
            write_json(
                reports / "manual_low_frequency_operations_policy_validation.json",
                {
                    "result": "PASS",
                    "policy": {
                        "min_hours_between_production_requests": 24,
                    },
                    "risk_limits": {"max_notional": 10},
                },
            )
            write_json(
                reports / "production_exactly_one_send_result.json",
                {
                    "result": "PASS",
                    "terminal": {
                        "external_status": "FILLED",
                        "external_order_id": "do-not-render",
                    },
                    "Authorization": "do-not-render",
                    "client_order_id": "do-not-render",
                },
            )
            write_json(
                reports / "production_post_send_readonly_reconciliation.json",
                {"result": "PASS"},
            )
            write_json(
                reports / "post_production_telegram_channel_evidence.json",
                {
                    "result": "PASS",
                    "TELEGRAM_BOT_TOKEN": "do-not-render",
                },
            )

            summary = module.public_summary(reports)
            html = module.render_html(summary)
            validation = module.validate_html(html, summary)

        self.assertEqual(summary["public_status"], "OBSERVATION_ACTIVE")
        self.assertEqual(summary["production_validation"], "COMPLETE")
        self.assertEqual(summary["observation_window"], "PASS")
        self.assertEqual(validation["result"], "PASS")
        self.assertIn("Project Anchor is operating under monitored review.", html)
        self.assertIn("NOT OPEN", html)
        self.assertNotIn("do-not-render", html)
        self.assertNotIn("external_order_id", html)
        self.assertNotIn("client_order_id", html)
        self.assertNotIn("TELEGRAM_BOT_TOKEN", html)
        self.assertNotIn("Authorization", html)
        self.assertNotIn("risk_limits", html)
        self.assertNotIn("worker", html)
        self.assertNotIn("production.env", html)
        self.assertNotRegex(html.lower(), r"method=['\"]post")
        embedded = re.search(
            r'<script id="projectAnchorPublicStatus" type="application/json">(.*?)</script>',
            html,
            re.S,
        )
        self.assertIsNotNone(embedded)
        self.assertEqual(json.loads(embedded.group(1))["trading"]["live_trading"], "NOT_OPEN")
        self.assertEqual(validation["boundary"]["production_request_sent"], "NO")


if __name__ == "__main__":
    unittest.main()
