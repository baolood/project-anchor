import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "validate_cloud_operations_evidence_layout.py"

spec = importlib.util.spec_from_file_location("validate_cloud_operations_evidence_layout", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


class CloudOperationsEvidenceLayoutTest(unittest.TestCase):
    def test_split_layout_passes_when_runtime_and_source_evidence_are_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "runtime"
            source = root / "source"
            runtime.mkdir()
            source.mkdir()
            write_json(
                runtime / "post_production_monitoring_run.json",
                {
                    "generated_at": "2026-07-31T05:09:39Z",
                    "result": "PASS",
                    "boundary": {
                        "new_production_request_sent": "NO",
                        "second_production_request_sent": "NO",
                        "go_live": "NO-GO",
                        "live_trading": "NO-GO",
                    },
                },
            )
            write_json(runtime / "post_production_monitoring_timer_runtime_validation.json", {"result": "PASS"})
            write_json(
                runtime / "post_production_monitoring_timer_stability_validation.json",
                {"result": "PASS", "latest_consecutive_success_count": 6},
            )
            write_json(
                runtime / "post_production_monitoring_telegram_send_result.json",
                {"result": "BLOCKED", "send_attempted": "NO"},
            )
            write_json(
                source / "production_exactly_one_send_result.json",
                {
                    "result": "PASS",
                    "success": True,
                    "terminal": {
                        "external_status": "FILLED",
                        "external_order_id_present": True,
                    },
                },
            )
            write_json(source / "post_production_send_reconciliation.json", {"result": "PASS"})
            write_json(
                source / "production_post_send_readonly_reconciliation.json",
                {
                    "result": "PASS",
                    "order_reconciliation": {
                        "matching_filled_order_count": 1,
                        "symbol_order_count_in_window": 1,
                    },
                    "boundary": {
                        "go_live": "NO-GO",
                        "live_trading": "NO-GO",
                    },
                },
            )
            write_json(
                source / "post_production_operations_decision.json",
                {
                    "result": "PASS",
                    "decision": "FIRST_PRODUCTION_VALIDATION_COMPLETE_CONTINUOUS_TRADING_DISABLED",
                    "summary": {
                        "production_request_sent": "YES",
                        "matching_filled_order_count": 1,
                    },
                },
            )

            report = module.build_report(runtime, source)

        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["layout"]["single_directory_layout_required"], "NO")
        self.assertEqual(report["checks"]["source_production_evidence_present"], "PASS")
        self.assertEqual(report["checks"]["runtime_monitoring_reports_present"], "PASS")
        self.assertEqual(report["boundary"]["new_production_request_sent"], "NO")
        self.assertEqual(report["boundary"]["go_live"], "NO-GO")

    def test_blocks_when_source_send_evidence_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "runtime"
            source = root / "source"
            runtime.mkdir()
            source.mkdir()
            for name in module.RUNTIME_REQUIRED:
                write_json(runtime / name, {"result": "PASS"})

            report = module.build_report(runtime, source)

        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["checks"]["source_production_evidence_present"], "FAIL")


if __name__ == "__main__":
    unittest.main()
