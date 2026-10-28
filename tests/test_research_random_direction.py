"""Research-gate random-direction control. PARAMS.lock hashes stay intact."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

from research.random_direction import Rnd, beats_random_direction, match_p


ROOT = Path(__file__).resolve().parents[1]


class _Always:
    def __init__(self) -> None:
        self.entered: list[dict] = []

    def decision(self, i: int) -> bool:
        return True

    def make(self, i: int, side: str) -> dict:
        return {"i": i, "side": side}

    def on_entry(self, sig: dict) -> None:
        self.entered.append(sig)


class _EvenOnly:
    def decision(self, i: int) -> bool:
        return i % 2 == 0

    def make(self, i: int, side: str) -> dict:
        return {"i": i, "side": side}


class RandomDirectionTests(unittest.TestCase):
    def test_match_p_is_the_trade_rate_capped_at_one(self) -> None:
        self.assertEqual(match_p(3, 12), 0.25)
        self.assertEqual(match_p(0, 0), 0.0)
        self.assertEqual(match_p(50, 10), 1.0)
        with self.assertRaises(ValueError):
            match_p(-1, 4)

    def test_rnd_keeps_the_decision_bars_and_a_fixed_seed(self) -> None:
        base = _Always()
        rnd = Rnd(base, 1.0, 7)
        first = [rnd.signal(i) for i in range(40)]
        other = Rnd(_Always(), 1.0, 7)
        second = [other.signal(i) for i in range(40)]
        self.assertEqual(first, second)
        sides = [row["side"] for row in first]
        self.assertGreater(sides.count("long"), 10)
        self.assertGreater(sides.count("short"), 10)
        self.assertEqual([Rnd(_Always(), 0.0, 7).signal(i) for i in range(10)], [None] * 10)
        even = Rnd(_EvenOnly(), 1.0, 3)
        self.assertIsNone(even.signal(1))
        self.assertIsNotNone(even.signal(2))

    def test_on_entry_is_forwarded_and_p3_uses_the_percentile(self) -> None:
        base = _Always()
        rnd = Rnd(base, 1.0, 1)
        sig = rnd.signal(0)
        rnd.on_entry(sig)
        self.assertEqual(base.entered, [sig])
        controls = [-0.05, 0.0, 0.05, 0.139]
        inside = beats_random_direction(0.046, controls)
        above = beats_random_direction(0.2, controls)
        self.assertFalse(inside["pass"])
        self.assertEqual(inside["reason"], "inside_random_range")
        self.assertTrue(above["pass"])
        self.assertEqual(above["reason"], "above_random")
        self.assertGreater(inside["threshold"], 0.046)
        empty = beats_random_direction(1.0, [])
        self.assertFalse(empty["pass"])
        self.assertEqual(empty["reason"], "no_control")

    def test_params_locks_still_match_the_pre_registration(self) -> None:
        expected = {
            "research/eval-pass-prob": "d665798820dbf3ec726192491529ac28afa158ae0c54b8d71d23c68d4f5acf64",
            "research/eval-dir-families": "4657ac56e6f5c8eacec015fed9ff07d9f85ba84d06527695ed8d897c9a9c7b39",
        }
        for folder, digest in expected.items():
            params = (ROOT / folder / "PARAMS.md").read_bytes()
            lock = (ROOT / folder / "PARAMS.lock").read_text(encoding="utf-8").split()[0]
            self.assertEqual(hashlib.sha256(params).hexdigest(), digest)
            self.assertEqual(lock, digest)
        gate = (ROOT / "research" / "RESEARCH_GATE.md").read_text(encoding="utf-8")
        self.assertIn("EVAL_PASS_PROB_V1", gate)
        self.assertIn("EVAL_DIR_FAMILIES_V1", gate)
        self.assertIn("## 8.", gate)


class ParamsLockTests(unittest.TestCase):
    def test_every_params_lock_matches_params_md(self) -> None:
        families = sorted(
            path.parent.relative_to(ROOT).as_posix()
            for path in (ROOT / "research").rglob("PARAMS.lock")
            if path.is_file()
        )
        self.assertEqual(
            families,
            [
                "research/basis-mr",
                "research/eval-dir-families",
                "research/eval-pass-prob",
                "research/funding-carry",
                "research/liq-cascade",
                "research/multicoin-trend",
                "research/quarterly-basis-cc",
                "research/regime-bull",
                "research/regime-bull-v2",
                "research/regime-bull-v3",
                "research/regime-bull-voltarget",
            ],
        )
        for folder in families:
            params = (ROOT / folder / "PARAMS.md").read_bytes()
            lock = (ROOT / folder / "PARAMS.lock").read_text(encoding="utf-8").split()[0]
            self.assertEqual(hashlib.sha256(params).hexdigest(), lock, folder)

        script = ROOT / "scripts" / "check_research_params_lock.sh"
        proc = subprocess.run(
            [str(script)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("[pass]", proc.stdout)
        for folder in families:
            self.assertIn(folder, proc.stdout)

        help_proc = subprocess.run(
            [str(script), "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(help_proc.returncode, 0, help_proc.stderr)
        self.assertIn("PARAMS.lock", help_proc.stdout)
        bad = subprocess.run(
            [str(script), "--nope"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(bad.returncode, 2)

    def test_scoreboard_report_links_resolve_beside_the_board(self) -> None:
        board = ROOT / "research" / "SCOREBOARD.md"
        text = board.read_text(encoding="utf-8")
        self.assertIn("MULTICOIN_TREND_V1", text)
        self.assertIn("REGIME_BULL_SURVIVE_V1", text)
        self.assertIn("REGIME_BULL_VOLTARGET_V1", text)
        self.assertTrue((ROOT / "research" / "IDEAS.md").is_file())
        links = []
        for line in text.splitlines():
            if "REPORT.md" not in line or not line.startswith("|"):
                continue
            cell = line.strip().strip("|").split("|")[-1].strip()
            links.append(cell)
            self.assertTrue((board.parent / cell).is_file(), cell)
        self.assertEqual(
            links,
            [
                "funding-carry/REPORT.md",
                "basis-mr/REPORT.md",
                "quarterly-basis-cc/REPORT.md",
                "eval-dir-families/REPORT.md",
                "eval-dir-families/REPORT.md",
                "eval-dir-families/REPORT.md",
                "eval-pass-prob/REPORT.md",
                "multicoin-trend/REPORT.md",
                "regime-bull/REPORT.md",
                "regime-bull-voltarget/REPORT.md",
            ],
        )


class ReportTextTests(unittest.TestCase):
    def test_pass_prob_report_records_the_locked_verdict(self) -> None:
        report = (ROOT / "research" / "PASS_PROB_20261024.md").read_text(encoding="utf-8")
        self.assertIn("EVAL_PASS_PROB_V1", report)
        self.assertIn("d6657988", report)


if __name__ == "__main__":
    unittest.main()
