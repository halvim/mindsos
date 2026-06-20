"""DM-1 measurements (plan §8 gate, PB-E / P7).

Two numbers the DM-1 gate records:
  1. **RAM** under the full 4-brain stack (4 KLs + 4 CLs + 4 Intelligence
     LayerS + worker pools) — feeds the Mac-Mini sizing (PB-N: now 4
     Globals, not 1).
  2. **Sim-jitter proxy** under synthetic 4-brain load — a 50 Hz busy
     stepping thread (the sim stand-in; the real MuJoCo loop is DM-3)
     while the 4 ILs loop enqueued trivial lifecycles. We report the step
     interval distribution and the provisional gate **p99 ≤ 2× nominal**.
     Absolute numbers won't transfer to the real sim — the real bar lands
     in DM-3 (P7).

Run: ``python -m demo_backend.measure`` (needs the full stack → Python
3.12 host). Reads RSS via psutil if present, else /proc/self/status.
"""

from __future__ import annotations

import statistics
import threading
import time
from dataclasses import dataclass
from typing import List

from .bootstrap import bootstrap

NOMINAL_HZ = 50.0
NOMINAL_DT = 1.0 / NOMINAL_HZ


def rss_mb() -> float:
    """Resident set size in MB (psutil if available, else /proc)."""
    try:
        import psutil  # type: ignore

        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:
        try:
            with open("/proc/self/status") as fh:
                for line in fh:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1]) / 1024.0
        except Exception:
            pass
        return float("nan")


@dataclass
class JitterReport:
    samples: int
    nominal_ms: float
    mean_ms: float
    p50_ms: float
    p99_ms: float
    max_ms: float

    @property
    def passes(self) -> bool:
        return self.p99_ms <= 2.0 * self.nominal_ms


def _stepper(stop: threading.Event, intervals: List[float]) -> None:
    """50 Hz stepping loop (the sim stand-in). Records actual inter-step
    intervals — jitter = how far the GIL lets them drift from NOMINAL_DT."""
    last = time.perf_counter()
    next_t = last + NOMINAL_DT
    while not stop.is_set():
        now = time.perf_counter()
        if now < next_t:
            time.sleep(max(0.0, next_t - now))
        now = time.perf_counter()
        intervals.append(now - last)
        last = now
        next_t += NOMINAL_DT


def measure_jitter(duration_s: float = 8.0) -> JitterReport:
    """Run the stepper under synthetic 4-brain load and report jitter."""
    result = bootstrap()
    brains = list(result.brains.values())

    stop = threading.Event()
    intervals: List[float] = []
    stepper = threading.Thread(
        target=_stepper, args=(stop, intervals), name="sim-proxy", daemon=True
    )
    stepper.start()

    # Synthetic load: each IL continuously runs trivial lifecycles.
    load_stop = threading.Event()

    def _load(brain) -> None:
        i = 0
        while not load_stop.is_set():
            fut = brain.il.enqueue(
                lambda b=brain, i=i: b.orch.run_lifecycle(
                    {"text": "load"}, task_id=f"load-{b.device_id}-{i}"
                )
            )
            try:
                fut.result(timeout=30)
            except Exception:
                break
            i += 1

    loaders = [
        threading.Thread(target=_load, args=(b,), name=f"load-{b.device_id}", daemon=True)
        for b in brains
    ]
    for t in loaders:
        t.start()

    time.sleep(duration_s)
    load_stop.set()
    stop.set()
    stepper.join(timeout=2)
    for b in brains:
        b.il.stop()

    ms = [x * 1000.0 for x in intervals[5:]]  # drop warmup
    ms_sorted = sorted(ms)
    p99 = ms_sorted[min(len(ms_sorted) - 1, int(0.99 * len(ms_sorted)))]
    return JitterReport(
        samples=len(ms),
        nominal_ms=NOMINAL_DT * 1000.0,
        mean_ms=statistics.fmean(ms),
        p50_ms=statistics.median(ms),
        p99_ms=p99,
        max_ms=max(ms),
    )


def main() -> int:
    print(f"[RAM] pre-bootstrap RSS: {rss_mb():.1f} MB")
    report = measure_jitter()
    print(f"[RAM] full 4-brain stack RSS: {rss_mb():.1f} MB")
    print(
        f"[JITTER] n={report.samples} nominal={report.nominal_ms:.2f}ms "
        f"mean={report.mean_ms:.2f} p50={report.p50_ms:.2f} "
        f"p99={report.p99_ms:.2f} max={report.max_ms:.2f}"
    )
    bar = 2.0 * report.nominal_ms
    ok = report.p99_ms <= bar
    print(f"[JITTER] provisional gate p99 <= {bar:.2f}ms: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
