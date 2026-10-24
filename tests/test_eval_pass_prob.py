"""Cap-150 sizing, trade log, and pass-probability Monte Carlo. No network."""

from __future__ import annotations

import hashlib
import json
import stat
import time
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from ops.mf4.eval_guard import (
    BUFFER,
    RISK_MIN,
    account_status,
    btc_size,
    evaluate,
    latest_daily_reset,
    planned_risk_usd,
)
from ops.mf4.eval_outcomes import (
    append_trade,
    main as trade_main,
    summarize_costs,
    trade_risk_usd,
)
from ops.mf4.pass_prob import (
    COST_R,
    PATHS,
    SEED,
    baseline_mean_r,
    book_from_outcomes,
    hours_since_daily_reset,
    pass_probability,
    simulate,
)
from ops.mf4.sealed import sealed_reason


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc)
TRADE = {
    "signal_id": "mf4-20261022-1",
    "side": "long",
    "entry": 84499.5,
    "stop": 83633.1,
    "tp": 87812.6,
    "size": 0.16,
    "realized_r": -1.03,
    "commission": 10.8,
    "funding": 3.2,
    "mae": -1.05,
    "mfe": 0.4,
    "duration_h": 18.0,
    "exit_reason": "stop",
    "gap_h": 72.0,
}


def _account(balance: str, daily_ref: str | None = None, position: dict | None = None) -> dict:
    return {
        "balance": balance,
        "daily_ref_balance": daily_ref or balance,
        "daily_ref_at": "2026-10-22T00:30:00Z",
        "floor": 9400,
        "target": 11000,
        "position": position,
        "snapshot_at": "2026-10-22T09:00:00Z",
    }


class SizingTests(unittest.TestCase):
    def test_october_22_quote_is_150_and_floored_size(self) -> None:
        result = evaluate(
            _account(
                "10120.42",
                position={
                    "side": "long",
                    "size": "0.176",
                    "entry": "84499.5",
                    "sl": "83633.1",
                    "tp": "87812.6",
                },
            ),
            "84499.5",
            now=NOW,
        )
        self.assertEqual(result["daily_line"], 9816.81)
        self.assertEqual(result["planned_risk"], 150.0)
        self.assertEqual(result["size"], 0.16)
        self.assertEqual(result["verdict"], "ok")
        self.assertEqual(result["account_status"], "running")
        self.assertFalse(result["may_cross_reset"])
        sized = btc_size(Decimal("150"), Decimal("84499.5"), Decimal("83633.1"))
        self.assertEqual(sized, Decimal("0.160"))

    def test_too_close_to_the_floor_is_locked_and_logged(self) -> None:
        with self.assertLogs("ops.mf4.eval_guard", level="INFO") as captured:
            result = evaluate(_account("9470"), None, now=NOW)
        self.assertEqual(result["verdict"], "block")
        self.assertEqual(result["reason"], "too_close")
        self.assertEqual(result["planned_risk"], 40.0)
        self.assertEqual(result["account_status"], "locked")
        self.assertNotEqual(result["account_status"], "breached")
        self.assertTrue(any("reason=too_close" in line for line in captured.output))
        self.assertTrue(any("planned_risk=40.00" in line for line in captured.output))

    def test_daily_headroom_skip_is_not_locked(self) -> None:
        result = evaluate(_account("9760", "10000"), None, now=NOW)
        self.assertEqual(result["reason"], "too_close")
        self.assertEqual(result["planned_risk"], 30.0)
        self.assertEqual(result["account_status"], "running")
        self.assertGreater(result["est_equity"], result["floor"])
        self.assertGreater(result["est_equity"], result["daily_line"])

    def test_breach_stays_distinct_from_too_close(self) -> None:
        with self.assertLogs("ops.mf4.eval_guard", level="INFO") as captured:
            result = evaluate(_account("9300", "10000"), None, now=NOW)
        self.assertEqual(result["verdict"], "block")
        self.assertEqual(result["reason"], "worst_case_breaches_line")
        self.assertEqual(result["account_status"], "breached")
        self.assertTrue(any("reason=worst_case_breaches_line" in line for line in captured.output))

    def test_stale_snapshot_is_logged_unknown(self) -> None:
        account = _account("10120.42")
        account["snapshot_at"] = "2026-10-20T09:00:00Z"
        with self.assertLogs("ops.mf4.eval_guard", level="INFO") as captured:
            result = evaluate(account, "84499.5", now=NOW)
        self.assertEqual(result["verdict"], "unknown")
        self.assertEqual(result["account_status"], "unknown")
        self.assertIsNone(result["planned_risk"])
        self.assertTrue(any("reason=snapshot_stale" in line for line in captured.output))

    def test_overnight_cap_uses_three_percent_of_balance(self) -> None:
        capped = planned_risk_usd(
            Decimal("12000"),
            Decimal("9000"),
            Decimal("9400"),
            Decimal("4000"),
            True,
        )
        open_cap = planned_risk_usd(
            Decimal("12000"),
            Decimal("9000"),
            Decimal("9400"),
            Decimal("4000"),
            False,
        )
        self.assertEqual(capped, Decimal("90"))
        self.assertEqual(open_cap, Decimal("150"))
        self.assertEqual(
            account_status(Decimal("9470"), Decimal("9185.9"), Decimal("9400"), Decimal("11000")),
            "locked",
        )
        self.assertEqual(
            account_status(Decimal("9300"), Decimal("9700"), Decimal("9400"), Decimal("11000")),
            "breached",
        )
        self.assertEqual(
            account_status(Decimal("11000"), Decimal("9700"), Decimal("9400"), Decimal("11000")),
            "passed",
        )
        self.assertGreater(Decimal("9480") - Decimal("9400") - BUFFER, RISK_MIN - 1)

    def test_daily_reset_clock_matches_the_guard(self) -> None:
        self.assertEqual(latest_daily_reset(NOW), datetime(2026, 10, 22, 0, 30, tzinfo=timezone.utc))
        self.assertAlmostEqual(hours_since_daily_reset(NOW), 9.5)


class OutcomeTests(unittest.TestCase):
    def test_append_is_stable_and_summary_is_in_r(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            first = dict(TRADE)
            second = dict(TRADE)
            second["signal_id"] = "mf4-20261022-2"
            second["realized_r"] = 3.6
            stamp = datetime(2026, 10, 24, 4, 0, tzinfo=timezone.utc)
            path = append_trade(out, first, now=stamp)
            before = path.read_bytes()
            append_trade(out, second, now=stamp)
            after = path.read_text(encoding="utf-8")
            self.assertTrue(after.startswith(before.decode("utf-8")))
            self.assertEqual(after.count("\n"), 2)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
            rows = [json.loads(line) for line in after.splitlines()]
            summary = summarize_costs(rows)
        risk = trade_risk_usd(0.16, 84499.5, 83633.1)
        self.assertIsNotNone(risk)
        assert risk is not None
        one = (10.8 + 3.2) / risk
        self.assertAlmostEqual(summary["cost_r_mean"], one, places=6)
        self.assertEqual(summary["trades"], 2)
        self.assertAlmostEqual(summary["cost_r_sum"], one * 2, places=6)

    def test_cli_refuses_sealed_paths_and_does_not_touch_protected_files(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout
        from tempfile import TemporaryDirectory

        protected = [
            ROOT / "governance" / "ANCHOR_C9_GOVERNANCE_REGISTER.jsonl",
            ROOT / "docs" / "PROJECT_ANCHOR_PASS_LINE_V1_1_FREEZE_RECORD.md",
        ]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            source = out / "trade.json"
            source.write_text(json.dumps(TRADE), encoding="utf-8")
            with redirect_stdout(StringIO()) as stdout:
                code = trade_main(["--trade", str(source), "--out-dir", str(out / "dest")])
            self.assertEqual(code, 0)
            self.assertIn("EVAL_TRADE=APPENDED", stdout.getvalue())
            self.assertIn("DEPLOY=NO", stdout.getvalue())
            with redirect_stdout(StringIO()) as summary_out:
                summary_code = trade_main(["--summary", "--out-dir", str(out / "dest")])
            self.assertEqual(summary_code, 0)
            self.assertIn("EVAL_TRADE=SUMMARY", summary_out.getvalue())
            sealed = out / "affl-v2-official-ledger"
            sealed.mkdir()
            with redirect_stdout(StringIO()):
                refused = trade_main(["--trade", str(source), "--out-dir", str(sealed)])
            self.assertEqual(refused, 2)
            self.assertIsNotNone(sealed_reason(Path("/var/lib/private/anchor-official-ledger-20261010")))
            legacy = out / "anchor_fake_fill_equity_v2_official.csv"
            self.assertIsNotNone(sealed_reason(legacy))
            with self.assertRaises(ValueError):
                append_trade(sealed, TRADE)
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
        self.assertEqual(before, after)


class MonteCarloTests(unittest.TestCase):
    def test_baseline_cost_is_about_nine_hundredths_of_an_r(self) -> None:
        self.assertAlmostEqual(baseline_mean_r(), -COST_R, places=10)
        book, source, cost = book_from_outcomes([])
        self.assertEqual(source, "zero_edge_4r")
        self.assertEqual(cost, COST_R)
        self.assertEqual(len(book), 5)
        stored, stored_source, _stored_cost = book_from_outcomes([TRADE])
        self.assertEqual(stored_source, "stored")
        self.assertEqual(stored[0][0], -1.03)

    def test_one_loss_then_locks_and_a_daily_skip_does_not(self) -> None:
        loss = (-1.09, 0.02, -1.09, 1.0, 1.0)
        locked = simulate(
            [loss],
            equity=9600.0,
            reset_balance=9600.0,
            hours_since_reset=1.0,
            paths=1,
            seed=1,
            max_days=30,
        )
        self.assertEqual(locked["horizons"][30][2], 1.0)
        self.assertEqual(locked["horizons"][30][0], 0.0)
        self.assertEqual(locked["horizons"][30][1], 0.0)
        skipped = simulate(
            [loss],
            equity=9760.0,
            reset_balance=10000.0,
            hours_since_reset=20.0,
            paths=1,
            seed=1,
            max_days=1,
        )
        self.assertEqual(skipped["horizons"][30][3], 1.0)
        self.assertEqual(skipped["horizons"][30][2], 0.0)
        win = (3.91, 3.91, -0.1, 1.0, 1.0)
        passed = simulate(
            [win],
            equity=10600.0,
            reset_balance=10600.0,
            hours_since_reset=1.0,
            paths=1,
            seed=1,
            max_days=30,
        )
        self.assertEqual(passed["horizons"][30][0], 1.0)

    def test_terminal_states_stay_distinct_and_the_run_is_fast(self) -> None:
        locked = pass_probability(equity=9470, reset_balance=9470, status="locked")
        breached = pass_probability(equity=9300, reset_balance=10000, status="breached")
        self.assertEqual(locked["nolimit"]["locked"], 1.0)
        self.assertEqual(locked["nolimit"]["breach"], 0.0)
        self.assertEqual(breached["nolimit"]["breach"], 1.0)
        self.assertEqual(breached["nolimit"]["locked"], 0.0)
        self.assertEqual(locked["model"], "terminal")
        started = time.perf_counter()
        first = pass_probability(
            equity=9954.28,
            reset_balance=9954.28,
            status="running",
            hours_since_reset=9.5,
        )
        elapsed = time.perf_counter() - started
        second = pass_probability(
            equity=9954.28,
            reset_balance=9954.28,
            status="running",
            hours_since_reset=9.5,
        )
        self.assertLess(elapsed, 1.0)
        self.assertEqual(first, second)
        self.assertEqual(first["seed"], SEED)
        self.assertEqual(first["paths"], PATHS)
        self.assertEqual(first["source"], "zero_edge_4r")
        self.assertEqual(first["cost_r"], 0.09)
        for key in ("d30", "d60", "d90", "nolimit"):
            row = first[key]
            self.assertAlmostEqual(sum(row.values()), 1.0, places=3)
        self.assertGreater(first["nolimit"]["pass"], 0.0)
        self.assertLess(first["nolimit"]["pass"], 0.5)


if __name__ == "__main__":
    unittest.main()
