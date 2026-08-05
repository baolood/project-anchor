import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "check_next_manual_operation_eligibility.py"

spec = importlib.util.spec_from_file_location("check_next_manual_operation_eligibility", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def _write_json(path: Path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def _policy(**overrides):
    data = {
        "POLICY_MODE": "manual_confirmed_low_frequency_only",
        "AUTHORIZED_MARKET": "binance_spot",
        "AUTHORIZED_SYMBOLS": ["BTCUSDT"],
        "AUTHORIZED_SIDES": ["BUY_ONLY"],
        "MAX_NOTIONAL_PER_REQUEST": 10,
        "MAX_ORDER_COUNT_PER_REQUEST": 1,
        "MAX_REQUESTS_PER_WINDOW": 1,
        "MIN_HOURS_BETWEEN_PRODUCTION_REQUESTS": 24,
        "RECOMMENDED_MAX_REQUESTS_PER_WEEK": 3,
        "REQUIRES_EXPLICIT_OPERATOR_AUTHORIZATION_PER_REQUEST": True,
        "ALLOW_AUTOMATIC_RETRY": False,
        "ALLOW_AUTOMATIC_TRADING": False,
        "ALLOW_GO_LIVE": False,
        "ALLOW_LIVE_TRADING": False,
    }
    data.update(overrides)
    return data


def _reports(tmp_path: Path, *, send_at="2026-08-01T00:00:00Z", reconciliation="PASS", stability="PASS"):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_json(
        reports_dir / "production_exactly_one_send_result.json",
        {
            "generated_at": send_at,
            "result": "PASS",
            "terminal": {
                "external_status": "FILLED",
                "external_order_id_present": True,
                "external_order_id": "must_not_render",
            },
        },
    )
    _write_json(reports_dir / "production_post_send_readonly_reconciliation.json", {"result": reconciliation})
    _write_json(reports_dir / "post_production_72h_stability_review.json", {"result": stability})
    _write_json(reports_dir / "post_production_monitoring_run.json", {"result": "PASS"})
    _write_json(reports_dir / "post_production_telegram_channel_evidence.json", {"result": "PASS"})
    return reports_dir


class NextManualOperationEligibilityTest(unittest.TestCase):
    def test_passes_when_interval_and_required_evidence_are_satisfied(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            policy_path = tmp_path / "policy.json"
            _write_json(policy_path, _policy())
            reports_dir = _reports(tmp_path)

            report = module.build_report(
                policy_path,
                reports_dir,
                module.parse_utc("2026-08-03T00:00:00Z"),
            )

        self.assertEqual(report["result"], "PASS")
        self.assertEqual(
            report["decision"],
            "READY_FOR_NEXT_MANUAL_LOW_FREQUENCY_OPERATOR_AUTHORIZATION_DECISION",
        )
        self.assertEqual(report["eligibility"]["production_send_authorization_granted"], "NO")
        self.assertEqual(report["boundary"]["production_request_sent"], "NO")
        self.assertEqual(report["boundary"]["secret_read"], "NO")

    def test_blocks_before_minimum_interval(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            policy_path = tmp_path / "policy.json"
            _write_json(policy_path, _policy())
            reports_dir = _reports(tmp_path, send_at="2026-08-01T00:00:00Z")

            report = module.build_report(
                policy_path,
                reports_dir,
                module.parse_utc("2026-08-01T12:00:00Z"),
            )

        self.assertEqual(report["result"], "BLOCKED")
        self.assertIn("minimum_interval_satisfied", report["blockers"])
        self.assertEqual(report["eligibility"]["next_eligible_at"], "2026-08-02T00:00:00Z")

    def test_blocks_when_reconciliation_is_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            policy_path = tmp_path / "policy.json"
            _write_json(policy_path, _policy())
            reports_dir = _reports(tmp_path, reconciliation="BLOCKED")

            report = module.build_report(
                policy_path,
                reports_dir,
                module.parse_utc("2026-08-03T00:00:00Z"),
            )

        self.assertEqual(report["result"], "BLOCKED")
        self.assertIn("post_send_reconciliation_pass", report["blockers"])

    def test_blocks_when_72h_stability_is_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            policy_path = tmp_path / "policy.json"
            _write_json(policy_path, _policy())
            reports_dir = _reports(tmp_path, stability="BLOCKED")

            report = module.build_report(
                policy_path,
                reports_dir,
                module.parse_utc("2026-08-03T00:00:00Z"),
            )

        self.assertEqual(report["result"], "BLOCKED")
        self.assertIn("post_production_72h_stability_pass", report["blockers"])

    def test_markdown_does_not_render_sensitive_identifiers(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            policy_path = tmp_path / "policy.json"
            _write_json(policy_path, _policy())
            reports_dir = _reports(tmp_path)
            report = module.build_report(
                policy_path,
                reports_dir,
                module.parse_utc("2026-08-03T00:00:00Z"),
            )
            text = module.markdown(report)

        self.assertIn("external_order_reference_present: True", text)
        self.assertNotIn("must_not_render", text)
        self.assertNotIn("external_order_id", text)
        self.assertNotIn("production.env", text)

    def test_cli_writes_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            policy_path = tmp_path / "policy.json"
            json_out = tmp_path / "eligibility.json"
            md_out = tmp_path / "eligibility.md"
            _write_json(policy_path, _policy())
            reports_dir = _reports(tmp_path)

            result = subprocess.run(
                [
                    "python3",
                    str(MODULE_PATH),
                    "--policy",
                    str(policy_path),
                    "--reports-dir",
                    str(reports_dir),
                    "--json-out",
                    str(json_out),
                    "--md-out",
                    str(md_out),
                    "--now",
                    "2026-08-03T00:00:00Z",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            report = json.loads(json_out.read_text(encoding="utf-8"))
            markdown = md_out.read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["result"], "PASS")
        self.assertIn("production_send_authorization_granted: NO", result.stdout)
        self.assertNotIn("API_SECRET", markdown)


if __name__ == "__main__":
    unittest.main()
