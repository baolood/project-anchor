import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "reconcile_post_production_send_result.py"

spec = importlib.util.spec_from_file_location("reconcile_post_production_send_result", MODULE_PATH)
reconcile = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(reconcile)


def _send_report(**overrides):
    report = {
        "result": "PASS",
        "success": True,
        "request": {
            "idempotency_key": "production:ops_manual:BTCUSDT:BUY:10:first-bounded-production-request:v1",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "max_notional": "10",
        },
        "terminal": {
            "http_status": 200,
            "external_status": "FILLED",
            "external_order_id_present": True,
        },
        "boundary": {
            "production_request_attempted": "YES",
            "production_request_accepted": "YES",
            "secret_value_disclosed": "NO",
            "secret_length_disclosed": "NO",
            "secret_prefix_suffix_disclosed": "NO",
            "secret_hash_disclosed": "NO",
            "authorization_header_value_disclosed": "NO",
            "canary_rerun": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }
    report.update(overrides)
    return report


def _window_plan(**overrides):
    report = {
        "result": "PASS",
        "plan_valid": True,
        "send_authorized": False,
        "planned_request": {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "max_notional": "10",
            "max_order_count": "1",
        },
    }
    report.update(overrides)
    return report


def _fresh_decision(**overrides):
    report = {
        "result": "PASS",
        "send_authorized_by_this_decision": False,
    }
    report.update(overrides)
    return report


def _risk_limits(**overrides):
    report = {"AUTHORIZED_MAX_NOTIONAL": "10"}
    report.update(overrides)
    return report


class PostProductionSendReconciliationTest(unittest.TestCase):
    def _run(self, send=None, window=None, fresh=None, risk=None):
        values = {
            reconcile.SEND_RESULT: (send or _send_report(), None),
            reconcile.WINDOW_PLAN: (window or _window_plan(), None),
            reconcile.FRESH_DECISION: (fresh or _fresh_decision(), None),
            reconcile.RISK_LIMITS: (risk or _risk_limits(), None),
        }

        def fake_read_json(path):
            return values[path]

        with patch.object(reconcile, "read_json", side_effect=fake_read_json):
            return reconcile.build_report()

    def test_filled_exactly_one_result_reconciles_pass(self):
        report, exit_code = self._run()

        self.assertEqual(exit_code, 0)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["summary"]["external_status"], "FILLED")
        self.assertTrue(report["summary"]["external_order_id_present"])
        self.assertEqual(report["boundary"]["new_production_request_sent_by_reconciliation"], "NO")
        self.assertEqual(report["boundary"]["go_live"], "NO-GO")
        self.assertEqual(report["boundary"]["live_trading"], "NO-GO")

    def test_rejected_result_blocks_reconciliation(self):
        send = _send_report(
            result="FAIL",
            success=False,
            terminal={
                "http_status": 400,
                "external_status": None,
                "external_order_id_present": False,
            },
        )

        report, exit_code = self._run(send=send)

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["result"], "BLOCKED")
        self.assertIn("FAIL", {item["result"] for item in report["checks"]})

    def test_secret_disclosure_blocks_reconciliation(self):
        send = _send_report(
            boundary={
                "production_request_attempted": "YES",
                "production_request_accepted": "YES",
                "secret_value_disclosed": "YES",
                "secret_length_disclosed": "NO",
                "secret_prefix_suffix_disclosed": "NO",
                "secret_hash_disclosed": "NO",
                "authorization_header_value_disclosed": "NO",
                "canary_rerun": "NO",
                "go_live": "NO-GO",
                "live_trading": "NO-GO",
            }
        )

        report, exit_code = self._run(send=send)

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["result"], "BLOCKED")
        self.assertIn(
            {"name": "no_secret_disclosure", "result": "FAIL", "evidence": "secret values, lengths, prefixes/suffixes, and hashes were not disclosed"},
            report["checks"],
        )

    def test_window_or_fresh_authorization_drift_blocks_reconciliation(self):
        report, exit_code = self._run(
            window=_window_plan(send_authorized=True),
            fresh=_fresh_decision(send_authorized_by_this_decision=True),
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["result"], "BLOCKED")
        failed = {item["name"] for item in report["checks"] if item["result"] == "FAIL"}
        self.assertIn("window_plan_did_not_authorize_send", failed)
        self.assertIn("fresh_decision_did_not_authorize_send", failed)

    def test_idempotency_notional_mismatch_blocks_reconciliation(self):
        report, exit_code = self._run(risk=_risk_limits(AUTHORIZED_MAX_NOTIONAL="4"))

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["result"], "BLOCKED")
        failed = {item["name"] for item in report["checks"] if item["result"] == "FAIL"}
        self.assertIn("idempotency_key_matches_risk_limit", failed)


if __name__ == "__main__":
    unittest.main()
