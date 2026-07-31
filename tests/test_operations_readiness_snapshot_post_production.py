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
            stability_path = tmp_path / "post_production_monitoring_timer_stability_validation.json"
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
            stability_path.write_text(
                json.dumps(
                    {
                        "result": "PASS",
                        "status": "POST_PRODUCTION_MONITORING_TIMER_STABILITY_VALID",
                        "observed_run_count": 6,
                        "latest_consecutive_success_count": 6,
                        "min_successful_runs": 3,
                        "latest_run": {
                            "started_at": "Jul 31 04:39:21",
                            "finished_at": "Jul 31 04:39:21",
                            "run_status": "POST_PRODUCTION_MONITORING_RUN_READY",
                        },
                        "checks": {"minimum_successful_runs_observed": "PASS"},
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
            old_stability = module.POST_PRODUCTION_MONITORING_TIMER_STABILITY_REPORT
            module.POST_PRODUCTION_MONITORING_RUN_REPORT = monitoring_path
            module.POST_PRODUCTION_ALERTING_READINESS_REPORT = readiness_path
            module.POST_PRODUCTION_TELEGRAM_SEND_RESULT_REPORT = telegram_path
            module.POST_PRODUCTION_MONITORING_TIMER_RUNTIME_REPORT = timer_path
            module.POST_PRODUCTION_MONITORING_TIMER_STABILITY_REPORT = stability_path
            try:
                monitoring = module.load_post_production_monitoring_run()
                readiness = module.load_post_production_alerting_readiness()
                telegram = module.load_post_production_telegram_send_result()
                timer = module.load_post_production_monitoring_timer_runtime()
                stability = module.load_post_production_monitoring_timer_stability()
            finally:
                module.POST_PRODUCTION_MONITORING_RUN_REPORT = old_monitoring
                module.POST_PRODUCTION_ALERTING_READINESS_REPORT = old_readiness
                module.POST_PRODUCTION_TELEGRAM_SEND_RESULT_REPORT = old_telegram
                module.POST_PRODUCTION_MONITORING_TIMER_RUNTIME_REPORT = old_timer
                module.POST_PRODUCTION_MONITORING_TIMER_STABILITY_REPORT = old_stability

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
        self.assertEqual(stability["result"], "PASS")
        self.assertEqual(stability["observed_run_count"], 6)
        self.assertEqual(stability["latest_consecutive_success_count"], 6)
        self.assertEqual(stability["boundary"]["new_production_request_sent"], "NO")
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

    def test_cloud_operations_evidence_layout_loader_preserves_split_evidence_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = Path(tmp) / "cloud_operations_evidence_layout_audit.json"
            audit_path.write_text(
                json.dumps(
                    {
                        "result": "PASS",
                        "status": "CLOUD_OPERATIONS_EVIDENCE_LAYOUT_VALID",
                        "runtime_reports_dir": "/var/lib/project-anchor/reports",
                        "source_reports_dir": "/root/project-anchor/reports",
                        "layout": {
                            "runtime_reports_role": "timer output and current monitoring status",
                            "source_reports_role": "repository historical production send and reconciliation evidence",
                            "single_directory_layout_required": "NO",
                        },
                        "runtime_files": {"post_production_monitoring_run.json": True},
                        "source_files": {"production_exactly_one_send_result.json": True},
                        "summary": {
                            "production_send_result": "PASS",
                            "production_order_status": "FILLED",
                            "matching_filled_order_count": 1,
                        },
                        "checks": {
                            "runtime_monitoring_reports_present": "PASS",
                            "source_production_evidence_present": "PASS",
                        },
                        "boundary": {
                            "secret_value_disclosed": "NO",
                            "new_production_request_sent": "NO",
                            "second_production_request_sent": "NO",
                            "go_live": "NO-GO",
                            "live_trading": "NO-GO",
                        },
                    }
                ),
                encoding="utf-8",
            )

            old_audit = module.CLOUD_OPERATIONS_EVIDENCE_LAYOUT_AUDIT_REPORT
            module.CLOUD_OPERATIONS_EVIDENCE_LAYOUT_AUDIT_REPORT = audit_path
            try:
                audit = module.load_cloud_operations_evidence_layout_audit()
            finally:
                module.CLOUD_OPERATIONS_EVIDENCE_LAYOUT_AUDIT_REPORT = old_audit

        self.assertEqual(audit["result"], "PASS")
        self.assertEqual(audit["layout"]["single_directory_layout_required"], "NO")
        self.assertEqual(audit["checks"]["runtime_monitoring_reports_present"], "PASS")
        self.assertEqual(audit["checks"]["source_production_evidence_present"], "PASS")
        self.assertEqual(audit["summary"]["production_order_status"], "FILLED")
        self.assertEqual(audit["boundary"]["new_production_request_sent"], "NO")
        self.assertEqual(audit["boundary"]["secret_value_disclosed"], "NO")

    def test_post_production_alert_policy_loader_preserves_noise_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            policy_path = Path(tmp) / "post_production_alert_policy_validation.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "result": "PASS",
                        "status": "POST_PRODUCTION_ALERT_POLICY_VALID",
                        "policy": {
                            "clear_state_telegram_send": "SUPPRESSED",
                            "first_active_transition_telegram_payload": "READY_TO_SEND",
                            "repeated_active_telegram_send": "SUPPRESSED",
                            "recovered_then_active_telegram_payload": "READY_TO_SEND",
                            "telegram_delivery_requires_execute_flag": "YES",
                        },
                        "cases": [{"name": "clear_state_stays_silent", "result": "PASS"}],
                        "boundary": {
                            "alerting_env_read": "NO",
                            "telegram_http_attempted": "NO",
                            "secret_value_disclosed": "NO",
                            "production_request_sent": "NO",
                            "go_live": "NO-GO",
                            "live_trading": "NO-GO",
                        },
                    }
                ),
                encoding="utf-8",
            )

            old_policy = module.POST_PRODUCTION_ALERT_POLICY_VALIDATION_REPORT
            module.POST_PRODUCTION_ALERT_POLICY_VALIDATION_REPORT = policy_path
            try:
                policy = module.load_post_production_alert_policy_validation()
            finally:
                module.POST_PRODUCTION_ALERT_POLICY_VALIDATION_REPORT = old_policy

        self.assertEqual(policy["result"], "PASS")
        self.assertEqual(policy["policy"]["clear_state_telegram_send"], "SUPPRESSED")
        self.assertEqual(policy["policy"]["repeated_active_telegram_send"], "SUPPRESSED")
        self.assertEqual(
            policy["policy"]["first_active_transition_telegram_payload"],
            "READY_TO_SEND",
        )
        self.assertEqual(policy["boundary"]["telegram_http_attempted"], "NO")
        self.assertEqual(policy["boundary"]["secret_value_disclosed"], "NO")



if __name__ == "__main__":
    unittest.main()
