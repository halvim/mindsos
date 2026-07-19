"""Parametric power-quality (PQ) waveform generator — Phase 1.

Synthesizes 1-D grid-voltage waveforms with disturbances stamped in
parametrically, plus exact multi-label ground truth. The **raw waveform is
the model input** (no hand-computed features), so no arm — MindsOS, a
neural baseline, or an LLM — can shortcut via textbook feature names; every
arm must learn structure from the signal.

Design (prereg §3-4):

* Base: 60 Hz fundamental, 256 samples/cycle, 10-cycle window.
* Taught primitives: sag, swell, harmonic, flicker, transient.
* Held-out primitive (honesty axis A5, never taught): notch.
* A combination reuses the *identical* single-primitive operation — the sag
  inside ``sag+harmonic`` is the same sag applied standalone. That shared
  structure is what makes forgetting/transfer non-trivial and measurable.
* AWGN swept over SNR 20-50 dB; train and test draw from **disjoint SNR
  bands** with independent RNG streams so exact instances never leak.

numpy only. Deterministic given a seed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, Iterable, Tuple

import numpy as np

# ── Vocabulary ─────────────────────────────────────────────────────────
F0 = 60.0
SAMPLES_PER_CYCLE = 256
N_CYCLES = 10

TAUGHT_PRIMITIVES: Tuple[str, ...] = ("sag", "swell", "harmonic", "flicker", "transient")
HELD_OUT_PRIMITIVE: str = "notch"
ALL_CLASSES: Tuple[str, ...] = TAUGHT_PRIMITIVES + (HELD_OUT_PRIMITIVE,)

TAUGHT_COMBINATIONS: Tuple[Tuple[str, str], ...] = (
    ("sag", "harmonic"),
    ("swell", "harmonic"),
    ("flicker", "harmonic"),
)
# Both parts are taught; the pairing is never trained -> tests composition (A4).
HELD_OUT_COMBINATIONS: Tuple[Tuple[str, str], ...] = (
    ("sag", "transient"),
    ("swell", "transient"),
)

TRAIN_SNRS_DB: Tuple[float, ...] = (20.0, 30.0, 40.0)
TEST_SNRS_DB: Tuple[float, ...] = (25.0, 35.0, 45.0, 50.0)


@dataclass(frozen=True)
class SignalConfig:
    f0: float = F0
    samples_per_cycle: int = SAMPLES_PER_CYCLE
    n_cycles: int = N_CYCLES

    @property
    def fs(self) -> float:
        return self.f0 * self.samples_per_cycle

    @property
    def n(self) -> int:
        return self.samples_per_cycle * self.n_cycles

    @property
    def t(self) -> np.ndarray:
        return np.arange(self.n) / self.fs


# ── Base + single-primitive operations ─────────────────────────────────
def _fundamental(cfg: SignalConfig) -> np.ndarray:
    return np.sin(2 * np.pi * cfg.f0 * cfg.t)


def _region(cfg: SignalConfig, rng: np.random.Generator) -> Tuple[int, int]:
    start = rng.uniform(0.2, 0.4)
    dur = rng.uniform(0.2, 0.4)
    i0 = int(start * cfg.n)
    i1 = min(cfg.n, int((start + dur) * cfg.n))
    return i0, i1


def _sag_env(cfg: SignalConfig, rng: np.random.Generator) -> np.ndarray:
    env = np.ones(cfg.n)
    i0, i1 = _region(cfg, rng)
    env[i0:i1] = 1.0 - rng.uniform(0.1, 0.9)
    return env


def _swell_env(cfg: SignalConfig, rng: np.random.Generator) -> np.ndarray:
    env = np.ones(cfg.n)
    i0, i1 = _region(cfg, rng)
    env[i0:i1] = 1.0 + rng.uniform(0.1, 0.8)
    return env


def _flicker_env(cfg: SignalConfig, rng: np.random.Generator) -> np.ndarray:
    alpha = rng.uniform(0.1, 0.2)
    beta = rng.uniform(5.0, 20.0)
    return 1.0 + alpha * np.sin(2 * np.pi * beta * cfg.t)


def _notch_env(cfg: SignalConfig, rng: np.random.Generator) -> np.ndarray:
    """Periodic notch: a brief dip at a firing angle each half-cycle."""
    env = np.ones(cfg.n)
    depth = rng.uniform(0.5, 0.9)
    half = cfg.samples_per_cycle // 2
    width = max(2, cfg.samples_per_cycle // 32)
    offset = int(rng.uniform(0.2, 0.4) * half)
    for k in range(2 * cfg.n_cycles):
        pos = k * half + offset
        env[pos:pos + width] = 1.0 - depth
    return env


def _harmonic(cfg: SignalConfig, rng: np.random.Generator) -> np.ndarray:
    out = np.zeros(cfg.n)
    for k in (3, 5, 7):
        out += rng.uniform(0.05, 0.15) * np.sin(2 * np.pi * k * cfg.f0 * cfg.t)
    return out


def _transient(cfg: SignalConfig, rng: np.random.Generator) -> np.ndarray:
    beta = rng.uniform(0.1, 0.8)
    tau = rng.uniform(0.0005, 0.002)
    f_n = rng.uniform(300.0, 900.0)
    t1 = rng.uniform(0.3, 0.6) * (cfg.n / cfg.fs)
    dt = cfg.t - t1
    ring = beta * np.exp(-dt / tau) * np.sin(2 * np.pi * f_n * dt)
    return np.where(cfg.t >= t1, ring, 0.0)


_MULTIPLICATIVE = {"sag": _sag_env, "swell": _swell_env, "flicker": _flicker_env, "notch": _notch_env}
_ADDITIVE = {"harmonic": _harmonic, "transient": _transient}


# ── Noise + assembly ───────────────────────────────────────────────────
def add_awgn(sig: np.ndarray, snr_db: float, rng: np.random.Generator) -> np.ndarray:
    p_sig = float(np.mean(sig ** 2))
    p_noise = p_sig / (10.0 ** (snr_db / 10.0))
    return sig + rng.normal(0.0, np.sqrt(p_noise), size=sig.shape)


def generate_event(
    present: Iterable[str],
    cfg: SignalConfig,
    rng: np.random.Generator,
    snr_db: float,
) -> Tuple[np.ndarray, FrozenSet[str]]:
    """Return (waveform, multi-label set) for the disturbances in ``present``.

    A combination reuses the identical single-primitive operations — the
    same functions, just parameterized per instance from ``rng``.
    """
    present = frozenset(present)
    unknown = present - set(ALL_CLASSES)
    if unknown:
        raise ValueError(f"unknown disturbance(s): {sorted(unknown)}")

    sig = _fundamental(cfg)
    env = np.ones(cfg.n)
    for name, fn in _MULTIPLICATIVE.items():
        if name in present:
            env = env * fn(cfg, rng)
    sig = sig * env
    for name, fn in _ADDITIVE.items():
        if name in present:
            sig = sig + fn(cfg, rng)
    sig = add_awgn(sig, snr_db, rng)
    return sig, present


def multihot(label: Iterable[str]) -> np.ndarray:
    label = set(label)
    return np.array([1 if c in label else 0 for c in ALL_CLASSES], dtype=int)


def sample_event(
    present: Iterable[str],
    *,
    split: str = "train",
    seed: int = 0,
    cfg: SignalConfig | None = None,
) -> Tuple[np.ndarray, FrozenSet[str], Dict[str, object]]:
    """Deterministic single event, with the SNR drawn from the split's band.

    Same (present, split, seed) -> identical waveform. Train and test bands
    are disjoint so a test instance never coincides with a train one.
    """
    if split not in ("train", "test"):
        raise ValueError(f"split must be 'train' or 'test', got {split!r}")
    cfg = cfg or SignalConfig()
    rng = np.random.default_rng(seed)
    snr = float(rng.choice(TRAIN_SNRS_DB if split == "train" else TEST_SNRS_DB))
    sig, label = generate_event(present, cfg, rng, snr)
    return sig, label, {"snr_db": snr, "split": split, "seed": seed}
