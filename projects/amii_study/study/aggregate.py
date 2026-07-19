"""Multi-seed aggregation with 95% confidence intervals — reporting rigor.

The prereg requires >=5 seeds with mean +- 95% CI. This runs an arm factory
across seeds and aggregates each scalar metric as (mean, lo, hi) using the
Student-t interval (dependency-free t-table), so no single-seed number is ever
reported alone.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Sequence, Tuple

import numpy as np

from .runner import run_stream

# Two-sided 95% Student-t critical values by degrees of freedom (df = n-1).
_T95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
    8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145,
    15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056,
    27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042,
}


def mean_ci(samples: Sequence[float]) -> Tuple[float, float, float]:
    """Return (mean, lo, hi) for a two-sided 95% t-interval."""
    x = np.asarray(list(samples), dtype=float)
    n = len(x)
    m = float(np.mean(x))
    if n < 2:
        return m, m, m
    sem = float(np.std(x, ddof=1) / np.sqrt(n))
    t = _T95.get(n - 1, 1.96)
    return m, m - t * sem, m + t * sem


def run_multiseed(
    make_arm: Callable[[int], object],
    seeds: Sequence[int],
    *,
    n_train: int = 128,
    n_test: int = 96,
    cfg=None,
) -> Dict[str, object]:
    """Run ``run_stream`` for a fresh arm per seed; aggregate scalar metrics.

    ``make_arm(seed)`` must return a fresh arm seeded for determinism.
    """
    runs: List[dict] = [
        run_stream(make_arm(s), n_train=n_train, n_test=n_test, seed=s, cfg=cfg)
        for s in seeds
    ]
    agg: Dict[str, Tuple[float, float, float]] = {
        "bwt_primitives": mean_ci([r["bwt_primitives"] for r in runs]),
        "notch_f1": mean_ci([r["notch_f1"] for r in runs]),
    }
    for name in runs[0]["heldout_composition"]:
        agg[f"composition:{name}"] = mean_ci([r["heldout_composition"][name] for r in runs])
    for c in runs[0]["final_f1"]:
        agg[f"final_f1:{c}"] = mean_ci([r["final_f1"][c] for r in runs])
    return {"seeds": list(seeds), "runs": runs, "aggregate": agg}
