"""Signature validation for the PQ generator — trust the waveforms before
anything downstream consumes them.

Each disturbance must show its physical signature; combinations must show
both; noise must hit the target SNR; generation must be deterministic; and
the held-out design must be internally consistent.
"""
import numpy as np
import pytest

from study.generator import (
    ALL_CLASSES,
    HELD_OUT_COMBINATIONS,
    HELD_OUT_PRIMITIVE,
    TAUGHT_COMBINATIONS,
    TAUGHT_PRIMITIVES,
    SignalConfig,
    add_awgn,
    generate_event,
    multihot,
    sample_event,
)

CFG = SignalConfig()


def _gen(present, seed=0, snr=80.0):
    """A near-clean realization (high SNR) so signatures aren't masked."""
    rng = np.random.default_rng(seed)
    sig, _ = generate_event(present, CFG, rng, snr)
    return sig


def _rms(x):
    return float(np.sqrt(np.mean(x ** 2)))


def _band_energy(x, lo, hi):
    spec = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(CFG.n, 1.0 / CFG.fs)
    return float(np.sum(spec[(freqs >= lo) & (freqs < hi)]))


def _per_cycle_rms_std(x):
    spc, nc = CFG.samples_per_cycle, CFG.n_cycles
    cycles = x[: spc * nc].reshape(nc, spc)
    return float(np.std(np.sqrt(np.mean(cycles ** 2, axis=1))))


def test_config_dimensions():
    assert CFG.fs == 15360.0
    assert CFG.n == 2560


def test_clean_fundamental_rms():
    assert _rms(_gen(())) == pytest.approx(1 / np.sqrt(2), abs=0.02)


def test_sag_reduces_rms():
    assert _rms(_gen({"sag"})) < _rms(_gen(())) - 0.02


def test_swell_increases_rms():
    assert _rms(_gen({"swell"})) > _rms(_gen(())) + 0.02


def test_harmonic_adds_spectral_lines():
    clean = _gen(())
    harm = _gen({"harmonic"})
    for f in (180.0, 300.0, 420.0):
        assert _band_energy(harm, f - 6, f + 6) > 10 * _band_energy(clean, f - 6, f + 6) + 1e-3


def test_flicker_modulates_envelope():
    assert _per_cycle_rms_std(_gen({"flicker"})) > _per_cycle_rms_std(_gen(())) + 0.005


def test_transient_adds_high_frequency_energy():
    assert _band_energy(_gen({"transient"}), 250, 1000) > 100 * _band_energy(_gen(()), 250, 1000) + 1e-3


def test_notch_is_broadband_distinct():
    assert _band_energy(_gen({"notch"}), 600, 3000) > 100 * _band_energy(_gen(()), 600, 3000) + 1e-3


def test_combination_shows_both_signatures():
    combo = _gen({"sag", "harmonic"})
    # harmonic signature: 180 Hz line present
    assert _band_energy(combo, 174, 186) > 1e-2
    # sag signature: a localized amplitude dip (min per-cycle RMS well below median),
    # robust to harmonic raising the global RMS
    spc, nc = CFG.samples_per_cycle, CFG.n_cycles
    pcr = np.sqrt(np.mean(combo[: spc * nc].reshape(nc, spc) ** 2, axis=1))
    assert pcr.min() < 0.95 * np.median(pcr)


def test_generation_is_deterministic():
    a, la, _ = sample_event({"sag", "harmonic"}, split="train", seed=7)
    b, lb, _ = sample_event({"sag", "harmonic"}, split="train", seed=7)
    assert np.array_equal(a, b) and la == lb


def test_snr_is_hit():
    rng = np.random.default_rng(3)
    from study.generator import _fundamental
    clean = _fundamental(CFG)
    noisy = add_awgn(clean, 30.0, rng)
    measured = 10 * np.log10(np.mean(clean ** 2) / np.mean((noisy - clean) ** 2))
    assert measured == pytest.approx(30.0, abs=1.0)


def test_multihot_encoding():
    v = multihot({"sag", "harmonic"})
    idx = {c: i for i, c in enumerate(ALL_CLASSES)}
    assert v[idx["sag"]] == 1 and v[idx["harmonic"]] == 1
    assert v[idx["swell"]] == 0 and v.sum() == 2


def test_held_out_design_is_consistent():
    # notch is never a taught primitive
    assert HELD_OUT_PRIMITIVE not in TAUGHT_PRIMITIVES
    # held-out combinations reuse only taught primitives, and none is a taught combo
    taught = set(TAUGHT_COMBINATIONS)
    for a, b in HELD_OUT_COMBINATIONS:
        assert a in TAUGHT_PRIMITIVES and b in TAUGHT_PRIMITIVES
        assert (a, b) not in taught and (b, a) not in taught


def test_unknown_disturbance_rejected():
    with pytest.raises(ValueError):
        generate_event({"blackout"}, CFG, np.random.default_rng(0), 40.0)
