"""Startup must not open on a direction that is already present.

The research backtest enters only when adjacent bars change direction
(``simulate``: ``bool(signal) and signal != previous_signal``). D5 planning
used to treat a missing ``last_observed_signal`` as a change, so the first
startup observation ``None -> -1`` opened a short.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bundle/scripts"))
import availability_fill_v1 as sim

ETH = "ema_50_100_strength_1pct|PI_ETHUSD"
BTC = "ema_50_100_strength_1pct|PI_XBTUSD"


class StartupEntryTests(unittest.TestCase):
    def test_startup_existing_short_does_not_open(self):
        state = sim.new_state()
        self.assertIsNone(state["last_observed_signal"].get(ETH))
        self.assertIsNone(state["last_observed_signal"].get(BTC))
        signals = {ETH: -1, BTC: -1}
        closes = {ETH: sim._iso(1), BTC: sim._iso(1)}
        plan = sim.plan_round(
            state, round_id="a" * 32, current_signals=signals, signal_bar_close_at=closes
        )
        self.assertEqual(plan, {})
        sim.register_round(state, plan, signals, t3=sim._iso(2), round_id="a" * 32)
        self.assertEqual(state["last_observed_signal"][ETH], -1)
        self.assertEqual(state["last_observed_signal"][BTC], -1)
        self.assertEqual(state["position"].get(ETH), None)

        still_short = sim.plan_round(
            state, round_id="b" * 32, current_signals=signals, signal_bar_close_at=closes
        )
        self.assertEqual(still_short, {})

        flipped = sim.plan_round(
            state,
            round_id="c" * 32,
            current_signals={ETH: 1, BTC: -1},
            signal_bar_close_at=closes,
        )
        self.assertEqual(set(flipped), {ETH})
        self.assertEqual(flipped[ETH]["kind"], sim.KIND_ENTER)
        self.assertEqual(flipped[ETH]["side"], 1)

    def test_startup_flat_signal_still_does_not_exit(self):
        state = sim.new_state()
        plan = sim.plan_round(
            state,
            round_id="a" * 32,
            current_signals={ETH: 0},
            signal_bar_close_at={ETH: sim._iso(1)},
        )
        self.assertEqual(plan, {})

    def test_observed_flat_to_short_still_enters(self):
        state = sim.new_state()
        state["last_observed_signal"][ETH] = 0
        plan = sim.plan_round(
            state,
            round_id="a" * 32,
            current_signals={ETH: -1},
            signal_bar_close_at={ETH: sim._iso(1)},
        )
        self.assertEqual(plan[ETH]["kind"], sim.KIND_ENTER)
        self.assertEqual(plan[ETH]["side"], -1)


if __name__ == "__main__":
    unittest.main()
