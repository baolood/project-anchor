import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "generate_static_ops_dashboard.py"

spec = importlib.util.spec_from_file_location("generate_static_ops_dashboard", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


class StaticOpsDashboardTest(unittest.TestCase):
    def test_sanitized_summary_excludes_secret_and_order_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            reports = Path(tmp)
            write_json(
                reports / "production_exactly_one_send_result.json",
                {
                    "result": "PASS",
                    "success": True,
                    "terminal": {
                        "external_status": "FILLED",
                        "external_order_id_present": True,
                        "external_order_id": "do-not-render",
                    },
                    "http": {"status": 200},
                    "request": {"symbol": "BTCUSDT", "side": "BUY"},
                    "risk_limits": {"max_notional": "10"},
                },
            )
            write_json(reports / "production_post_send_readonly_reconciliation.json", {"result": "PASS"})
            write_json(
                reports / "post_production_monitoring_run.json",
                {
                    "result": "PASS",
                    "status": "POST_PRODUCTION_MONITORING_RUN_READY",
                    "snapshot_status": "MONITORING_READY_CONTINUOUS_TRADING_DISABLED",
                },
            )
            write_json(
                reports / "post_production_alerting_readiness.json",
                {
                    "result": "PASS",
                    "status": "POST_PRODUCTION_ALERTING_READY",
                    "TELEGRAM_BOT_TOKEN": "do-not-render",
                    "boundary": {"telegram_bot_token_value_disclosed": "NO"},
                },
            )
            write_json(
                reports / "post_production_monitoring_telegram_send_result.json",
                {
                    "result": "BLOCKED",
                    "status": "POST_PRODUCTION_MONITORING_TELEGRAM_SEND_SUPPRESSED",
                    "send_attempted": "YES",
                    "send_result": "NOT_ATTEMPTED",
                    "Authorization": "do-not-render",
                },
            )
            write_json(
                reports / "post_production_telegram_channel_evidence.json",
                {
                    "result": "PASS",
                    "status": "POST_PRODUCTION_TELEGRAM_CHANNEL_DELIVERY_CONFIRMED",
                    "delivery_observed": "YES",
                    "evidence_source": "operator_observed_telegram_message",
                },
            )
            write_json(
                reports / "post_production_monitoring_timer_runtime_validation.json",
                {"result": "PASS", "timer": {"active_state": "active", "unit_file_state": "enabled"}},
            )
            write_json(
                reports / "post_production_monitoring_timer_stability_validation.json",
                {"result": "PASS", "latest_consecutive_success_count": 6},
            )
            write_json(
                reports / "post_production_operations_decision.json",
                {"result": "PASS", "next_gate": "POST_PRODUCTION_MONITORING_DASHBOARD_OR_FREEZE_DECISION"},
            )
            write_json(
                reports / "manual_low_frequency_operations_policy_validation.json",
                {
                    "result": "PASS",
                    "status": "MANUAL_LOW_FREQUENCY_OPERATIONS_POLICY_PASS",
                    "policy": {
                        "mode": "manual_confirmed_low_frequency_only",
                        "symbols": ["BTCUSDT"],
                        "sides": ["BUY_ONLY"],
                        "max_notional_per_request": 10,
                        "min_hours_between_production_requests": 24,
                        "recommended_max_requests_per_week": 3,
                        "requires_explicit_operator_authorization_per_request": True,
                    },
                    "boundary": {
                        "secret_read": "NO",
                        "production_request_sent": "NO",
                    },
                },
            )
            write_json(
                reports / "manual_low_frequency_operations_runbook_validation.json",
                {
                    "result": "PASS",
                    "status": "MANUAL_LOW_FREQUENCY_OPERATIONS_RUNBOOK_PASS",
                    "runbook": {
                        "mode": "manual_confirmed_low_frequency_execution_only",
                        "before_request_steps": 8,
                        "after_request_steps": 7,
                    },
                    "boundary": {
                        "secret_read": "NO",
                        "telegram_sent_by_validator": "NO",
                        "production_request_sent": "NO",
                    },
                },
            )
            write_json(
                reports / "next_manual_operation_eligibility.json",
                {
                    "result": "PASS",
                    "decision": "READY_FOR_NEXT_MANUAL_LOW_FREQUENCY_OPERATOR_AUTHORIZATION_DECISION",
                    "eligibility": {
                        "eligible_for_operator_authorization_decision": "YES",
                        "hours_since_last_production_request": 120,
                        "observed_production_requests_last_7d": 1,
                        "production_send_authorization_granted": "NO",
                    },
                    "blockers": [],
                    "boundary": {
                        "secret_read": "NO",
                        "production_request_sent": "NO",
                    },
                },
            )

            summary = module.sanitize_summary(reports)
            html = module.render_html(summary)
            validation = module.validate_html(html, summary)

        self.assertEqual(summary["production_send"]["external_status"], "FILLED")
        self.assertEqual(summary["production_send"]["external_order_reference_present"], True)
        self.assertEqual(summary["telegram"]["send_result"], "YES")
        self.assertEqual(summary["telegram"]["status"], "POST_PRODUCTION_TELEGRAM_CHANNEL_DELIVERY_CONFIRMED")
        self.assertEqual(validation["result"], "PASS")
        self.assertEqual(summary["manual_low_frequency"]["policy_result"], "PASS")
        self.assertEqual(summary["manual_low_frequency"]["runbook_result"], "PASS")
        self.assertEqual(summary["manual_low_frequency"]["eligibility_result"], "PASS")
        self.assertEqual(
            summary["manual_low_frequency"]["production_send_authorization_granted"], "NO"
        )
        self.assertEqual(summary["manual_low_frequency"]["max_notional_per_request"], 10)
        self.assertEqual(summary["manual_low_frequency"]["min_hours_between_requests"], 24)
        self.assertIn("Manual Ops", html)
        self.assertIn("eligibility_decision", html)
        self.assertIn("operator_authorization_required", html)
        self.assertNotIn("do-not-render", html)
        self.assertNotIn("TELEGRAM_BOT_TOKEN", html)
        self.assertNotIn("Authorization", html)
        self.assertIn("external_order_reference_present", html)
        self.assertNotIn('"external_order_id"', html)
        embedded = re.search(
            r'<script id="projectAnchorReports" type="application/json">(.*?)</script>',
            html,
            re.S,
        )
        self.assertIsNotNone(embedded)
        self.assertNotIn("&quot;", embedded.group(1))
        self.assertEqual(json.loads(embedded.group(1))["telegram"]["send_result"], "YES")
        self.assertEqual(validation["boundary"]["production_request_sent"], "NO")
        self.assertEqual(validation["boundary"]["go_live"], "NO-GO")


if __name__ == "__main__":
    unittest.main()
