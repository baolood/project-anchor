import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "generate_operations_readiness_snapshot.py"

spec = importlib.util.spec_from_file_location("generate_operations_readiness_snapshot", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class OperationsReadinessSnapshotPostProductionTest(unittest.TestCase):
    def test_post_production_alerting_loaders_preserve_non_secret_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            monitoring_path = tmp_path / "post_production_monitoring_run.json"
            readiness_path = tmp_path / "post_production_alerting_readiness.json"
            telegram_path = tmp_path / "post_production_monitoring_telegram_send_result.json"
            timer_path = tmp_path / "post_production_monitoring_timer_runtime_validation.json"
            monitoring_path.write_text(
                json.dumps(
                    {
                        "result": "PASS",
                        "status": "POST_PRODUCTION_MONITORING_RUN_READY",
                        "snapshot_result": "PASS",
                        "snapshot_status": "MONITORING_READY_CONTINUOUS_TRADING_DISABLED",
                        "boundary": {"new_production_request_sent": "NO"},
                    }
                ),
                encoding="utf-8",
            )
            readiness_path.write_text(
                json.dumps(
                    {
                        "result": "PASS",
                        "status": "POST_PRODUCTION_ALERTING_READY",
                        "failure_code": "",
                        "inspect_env_requested": True,
                        "checks": {
                            "telegram_bot_token_present": "YES",
                            "telegram_chat_id_present": "YES",
                        },
                        "boundary": {
                            "telegram_bot_token_value_disclosed": "NO",
                            "telegram_chat_id_value_disclosed": "NO",
                            "telegram_http_attempted": "NO",
                        },
                    }
                ),
                encoding="utf-8",
            )
            telegram_path.write_text(
                json.dumps(
                    {
                        "result": "BLOCKED",
                        "status": "POST_PRODUCTION_MONITORING_TELEGRAM_SEND_SUPPRESSED",
                        "send_attempted": "NO",
                        "send_result": "NOT_ATTEMPTED",
                        "boundary": {
                            "secret_value_disclosed": "NO",
                            "telegram_http_attempted": "NO",
                        },
                    }
                ),
                encoding="utf-8",
            )
            timer_path.write_text(
                json.dumps(
                    {
                        "result": "PASS",
                        "status": "POST_PRODUCTION_MONITORING_TIMER_RUNTIME_VALID",
                        "timer": {
                            "active_state": "active",
                            "unit_file_state": "enabled",
                            "last_trigger": "Fri 2026-07-31 04:09:17 UTC",
                        },
                        "service": {"result": "success"},
                        "monitoring_report": {"result": "PASS"},
                        "telegram_sender_report": {"result": "BLOCKED"},
                        "checks": {"timer_active": "PASS"},
                        "boundary": {
                            "secret_value_disclosed": "NO",
                            "new_production_request_sent": "NO",
                            "go_live": "NO-GO",
                            "live_trading": "NO-GO",
                        },
                    }
                ),
                encoding="utf-8",
            )

            old_monitoring = module.POST_PRODUCTION_MONITORING_RUN_REPORT
            old_readiness = module.POST_PRODUCTION_ALERTING_READINESS_REPORT
            old_telegram = module.POST_PRODUCTION_TELEGRAM_SEND_RESULT_REPORT
            old_timer = module.POST_PRODUCTION_MONITORING_TIMER_RUNTIME_REPORT
            module.POST_PRODUCTION_MONITORING_RUN_REPORT = monitoring_path
            module.POST_PRODUCTION_ALERTING_READINESS_REPORT = readiness_path
            module.POST_PRODUCTION_TELEGRAM_SEND_RESULT_REPORT = telegram_path
            module.POST_PRODUCTION_MONITORING_TIMER_RUNTIME_REPORT = timer_path
            try:
                monitoring = module.load_post_production_monitoring_run()
                readiness = module.load_post_production_alerting_readiness()
                telegram = module.load_post_production_telegram_send_result()
                timer = module.load_post_production_monitoring_timer_runtime()
            finally:
                module.POST_PRODUCTION_MONITORING_RUN_REPORT = old_monitoring
                module.POST_PRODUCTION_ALERTING_READINESS_REPORT = old_readiness
                module.POST_PRODUCTION_TELEGRAM_SEND_RESULT_REPORT = old_telegram
                module.POST_PRODUCTION_MONITORING_TIMER_RUNTIME_REPORT = old_timer

        self.assertEqual(monitoring["result"], "PASS")
        self.assertEqual(readiness["result"], "PASS")
        self.assertEqual(readiness["checks"]["telegram_bot_token_present"], "YES")
        self.assertEqual(readiness["boundary"]["telegram_bot_token_value_disclosed"], "NO")
        self.assertEqual(telegram["result"], "BLOCKED")
        self.assertEqual(telegram["send_attempted"], "NO")
        self.assertEqual(telegram["boundary"]["telegram_http_attempted"], "NO")
        self.assertEqual(timer["result"], "PASS")
        self.assertEqual(timer["timer"]["active_state"], "active")
        self.assertEqual(timer["timer"]["unit_file_state"], "enabled")
        self.assertEqual(timer["boundary"]["new_production_request_sent"], "NO")
        self.assertNotIn("secret", json.dumps(readiness).lower())

    def test_ops_domain_ingress_snapshot_records_https_and_protection(self):
        old_domain = module.OPS_DOMAIN
        old_expected = module.OPS_EXPECTED_A
        old_health_url = module.OPS_HEALTHZ_URL
        old_protected_url = module.OPS_PROTECTED_URL
        old_getaddrinfo = module.socket.getaddrinfo
        old_http_status = module.http_status
        old_http_probe = module.http_probe
        old_tls_not_after = module.tls_not_after
        module.OPS_DOMAIN = "ops.anchor-infra.com"
        module.OPS_EXPECTED_A = "45.76.190.109"
        module.OPS_HEALTHZ_URL = "https://ops.anchor-infra.com/healthz"
        module.OPS_PROTECTED_URL = "https://ops.anchor-infra.com/ops"
        module.socket.getaddrinfo = lambda *args, **kwargs: [
            (None, None, None, None, ("45.76.190.109", 443))
        ]
        module.http_status = lambda url, timeout=5.0: (200, None)
        module.http_probe = lambda url, timeout=5.0: (
            401,
            {"WWW-Authenticate": "Basic realm=\"Project Anchor Ops\""},
            None,
        )
        module.tls_not_after = lambda hostname, port=443, timeout=5.0: (
            "Oct 29 00:16:07 2026 GMT",
            None,
        )
        try:
            snapshot = module.ops_domain_ingress_snapshot()
        finally:
            module.OPS_DOMAIN = old_domain
            module.OPS_EXPECTED_A = old_expected
            module.OPS_HEALTHZ_URL = old_health_url
            module.OPS_PROTECTED_URL = old_protected_url
            module.socket.getaddrinfo = old_getaddrinfo
            module.http_status = old_http_status
            module.http_probe = old_http_probe
            module.tls_not_after = old_tls_not_after

        self.assertEqual(snapshot["result"], "PASS")
        self.assertEqual(snapshot["dns_result"], "PASS")
        self.assertEqual(snapshot["https_healthz_result"], "PASS")
        self.assertEqual(snapshot["protected_result"], "PASS")
        self.assertEqual(snapshot["tls_result"], "PASS")
        self.assertEqual(snapshot["protected_status"], 401)
        self.assertEqual(snapshot["ops_basic_auth_challenge_result"], "PASS")
        self.assertEqual(snapshot["ops_basic_auth_realm_present"], "PASS")
        self.assertEqual(snapshot["boundary"]["authenticated_ops_access_attempted"], "NO")
        self.assertEqual(snapshot["boundary"]["production_request_sent"], "NO")

    def test_ops_dashboard_snapshot_records_read_only_basic_auth_boundary(self):
        ingress = {
            "protected_result": "PASS",
            "ops_basic_auth_challenge_result": "PASS",
            "ops_basic_auth_realm_present": "PASS",
        }

        dashboard = module.ops_dashboard_snapshot(ingress)

        self.assertEqual(dashboard["result"], "PASS")
        self.assertEqual(dashboard["published_entrypoint"], "/ops")
        self.assertEqual(dashboard["entrypoint_requires_basic_auth"], "PASS")
        self.assertEqual(dashboard["unauthenticated_access_blocked"], "PASS")
        self.assertEqual(dashboard["authenticated_content_probe"], "NOT_ATTEMPTED_BY_SNAPSHOT")
        self.assertEqual(dashboard["production_send_control_expected"], "NO")
        self.assertEqual(dashboard["canary_rerun_control_expected"], "NO")
        self.assertEqual(dashboard["go_live_control_expected"], "NO")
        self.assertEqual(dashboard["live_trading_control_expected"], "NO")
        self.assertEqual(dashboard["boundary"]["basic_auth_secret_read"], "NO")
        self.assertEqual(dashboard["boundary"]["production_request_sent"], "NO")



if __name__ == "__main__":
    unittest.main()
