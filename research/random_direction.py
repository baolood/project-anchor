"""Random-direction control for the research gate.

``Rnd`` and ``match_p`` are the control used by EVAL_DIR_FAMILIES_V1 (P3):
same decision bars and exit template, side chosen by a fair coin, with
probability ``p`` of taking the bar. ``p`` is the strategy's own trade
count divided by its flat decision bars. A family passes P3 only when its
out-of-sample mean R is strictly above the control percentile.

No market data and no orders.
"""

from __future__ import annotations

import math
import random
from typing import Any, Sequence


class Rnd:
    """Random direction at ``base`` decision bars with probability ``p``."""

    def __init__(self, base: Any, p: float, seed: int) -> None:
        if isinstance(p, bool) or not isinstance(p, (int, float)):
            raise ValueError("p_out_of_range")
        chance = float(p)
        if chance < 0.0 or chance > 1.0:
            raise ValueError("p_out_of_range")
        self.base = base
        self.p = chance
        self.rng = random.Random(seed)

    def signal(self, i: int) -> Any:
        if not self.base.decision(i) or self.rng.random() >= self.p:
            return None
        side = "long" if self.rng.random() < 0.5 else "short"
        return self.base.make(i, side)

    def on_entry(self, sig: Any) -> None:
        hook = getattr(self.base, "on_entry", None)
        if callable(hook):
            hook(sig)


def match_p(n_trades: int, n_flat_decisions: int) -> float:
    """Trade rate on flat decision bars, capped at 1.

    This is ``trades / flat decisions`` from the research ``match_p`` helper.
    """
    if isinstance(n_trades, bool) or isinstance(n_flat_decisions, bool):
        raise ValueError("counts_must_be_non_negative")
    if not isinstance(n_trades, int) or not isinstance(n_flat_decisions, int):
        raise ValueError("counts_must_be_non_negative")
    if n_trades < 0 or n_flat_decisions < 0:
        raise ValueError("counts_must_be_non_negative")
    return min(1.0, n_trades / max(n_flat_decisions, 1))


def beats_random_direction(
    observed_mean_r: float,
    control_mean_rs: Sequence[float],
    percentile: float = 95.0,
) -> dict[str, Any]:
    """P3: observed mean R must sit strictly above the control percentile."""
    if isinstance(percentile, bool) or not isinstance(percentile, (int, float)):
        raise ValueError("percentile_out_of_range")
    pct = float(percentile)
    if not 0.0 <= pct <= 100.0:
        raise ValueError("percentile_out_of_range")
    controls = [float(value) for value in control_mean_rs]
    if not controls:
        return {
            "pass": False,
            "reason": "no_control",
            "threshold": None,
            "percentile": pct,
            "n_controls": 0,
        }
    threshold = _percentile(controls, pct)
    passed = float(observed_mean_r) > threshold
    return {
        "pass": passed,
        "reason": "above_random" if passed else "inside_random_range",
        "threshold": threshold,
        "percentile": pct,
        "n_controls": len(controls),
    }


def _percentile(values: Sequence[float], pct: float) -> float:
    """Linear percentile, matching NumPy's default (Hyndman type 7)."""
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * (pct / 100.0)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return float(ordered[int(rank)])
    weight = rank - low
    return float(ordered[low] * (1.0 - weight) + ordered[high] * weight)
