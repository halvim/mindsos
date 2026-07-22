"""The objective acceptance gate (arc F1/F2/F3 + C7) — the anti-fake-brain check.

A NILM brain "works" only if its own finder composes the solve, that
composition executes to real values, and the verdict comes from the dispatched
pipeline — not Python echoing an answer. These tests encode exactly that, on a
synthetic clean-cycle signal (no PLAID dependency; synthetic bench is a
sanctioned tool). Run on Linux/Mac with mindsos importable::

    PYTHONPATH=.:projects/amii_study python -m pytest projects/amii_study/nilm_brain/tests -q
"""

from __future__ import annotations

import numpy as np
import pytest

from nilm_brain import ontology as O
from nilm_brain.control import Solver, build_given


def _clean_record(n_cycles=40, fs=30000.0, f0=60.0, v_nom=170.0, notch=False):
    """A clean grid-voltage record: fundamental + small 3rd harmonic + tiny
    noise. col0=current, col1=voltage (matches the default channel_map)."""
    n = int(round(n_cycles * fs / f0))
    t = np.arange(n) / fs
    v = v_nom * np.sin(2 * np.pi * f0 * t) + 0.03 * v_nom * np.sin(2 * np.pi * 3 * f0 * t)
    rng = np.random.default_rng(0)
    v = v + 0.002 * v_nom * rng.standard_normal(n)
    if notch:
        period = int(round(fs / f0))
        i0 = n // 2
        v[i0:i0 + max(2, period // 30)] *= 0.2      # a brief sub-cycle dip
    cur = 0.1 * v_nom * np.sin(2 * np.pi * f0 * t)
    return np.stack([cur, v], axis=1)


@pytest.fixture(scope="module")
def solver():
    return Solver("nilm-test")


# ── F1: the brain composes its own solve (unfakeable) ──────────────────
def test_f1_finder_composes_segment(solver):
    seg = solver.segment
    assert seg.target_datastate == O.CYCLE_VERDICT.iri
    names = {s.capacity_iri.rsplit(":", 1)[-1] for s in seg.steps}
    # every deterministic feature step + the learned calibrate + the verdict
    for expected in ("synthesize", "subtract", "rms", "fft", "spectral_flatness",
                     "temporal_flatness", "band_energy", "compare_across_windows",
                     "calibrate", "verdict"):
        assert expected in names, f"finder did not compose {expected}"


# ── F2: composition executes to REAL values (not None — the D6 fiction) ─
def test_f2_executes_to_real_values(solver):
    out = solver.recognize(_clean_record(), max_windows=8)
    assert out, "no windows recognized"
    for o in out:
        assert o["verdict"]["state"] in {"cycle", "held_ambiguity", "request_reference"}
        for k in ("residual_energy", "spectral", "temporal", "harmonic", "confidence"):
            assert o[k] is not None and np.isfinite(o[k])


# ── Substantive: learned calibrate makes a clean cycle read as `cycle` ──
def test_seeded_clean_cycle_is_recognized():
    s = Solver("nilm-test-seed")
    clean = _clean_record()
    s.fit_calibrate(clean)                                  # learn the normal band
    verdicts = [o["verdict"]["state"] for o in s.recognize(clean, max_windows=12)]
    assert "cycle" in verdicts, (
        "a healthy grid cycle must be recognized as `cycle` after seeding — "
        "otherwise calibrate did not resolve the single-pass collapse")


def test_disturbance_scores_below_clean():
    s = Solver("nilm-test-dist")
    s.fit_calibrate(_clean_record())
    clean_conf = np.mean([o["confidence"] for o in s.recognize(_clean_record(), max_windows=12)])
    notch_conf = np.mean([o["confidence"] for o in s.recognize(_clean_record(notch=True), max_windows=12)])
    assert notch_conf < clean_conf, "a notch must lower cycle confidence vs a clean signal"


# ── C7: the invoke envelope never raises; failure is a checked flag ────
def test_c7_invoke_envelope_on_bad_input(solver):
    from mindsos_capacity import capacity_iri, CATEGORY_DERIVATION
    r = solver.cl.invoke(capacity_iri(CATEGORY_DERIVATION, "rms"),
                         {}, session=solver.session)         # missing required residual
    assert r.success is False and r.error is not None


# ── No hidden stubs: only the declared acquisition placeholder is one ──
def test_only_declared_placeholder(solver):
    from mindsos_capacity import capacity_iri, CATEGORY_DERIVATION
    cyc = ["bind", "window", "fit_reference", "synthesize", "subtract", "rms",
           "fft", "spectral_flatness", "temporal_flatness", "band_energy",
           "compare_across_windows"]
    for name in cyc:
        decl = solver.cl.get_declaration(capacity_iri(CATEGORY_DERIVATION, name))
        assert decl.implementation is not None and not getattr(decl, "placeholder", False)


# ── Terminal-state acceptance battery (labeled synthetic; known ground truth) ─
# Good-design criterion for the three terminals: each KNOWN class must land in
# its intended terminal. The gate is fit off the clean seed ONLY; the battery is
# held-out (never fit on) — so this is not teaching-to-the-test.

def _noise_record(alpha, seed):
    """Clean grid record swamped by broadband voltage noise at ``alpha``*V_nom
    (low SNR). Intended terminal: ``held_ambiguity`` — low confidence, and no
    measurable structure to request a reference for."""
    rec = _clean_record()
    rng = np.random.default_rng(seed)
    rec[:, 1] = rec[:, 1] + alpha * 170.0 * rng.standard_normal(rec.shape[0])
    return rec


def _terminal_battery():
    """Labeled synthetic inputs with known intended terminals."""
    return [
        ("clean",     _clean_record(),           "cycle"),
        ("notch",     _clean_record(notch=True), "request_reference"),
        ("noise_1.0", _noise_record(1.0, 11),    "held_ambiguity"),
        ("noise_2.0", _noise_record(2.0, 12),    "held_ambiguity"),
    ]


def test_terminal_battery():
    """Acceptance criterion for the three terminal states. Each known class must
    land in its intended terminal; the two confusions that matter must be zero:
    a MISS (structured -> not request_reference) and a FALSE ALARM (clean/noise
    -> request_reference). Prints the confusion matrix so the baseline is visible
    before any redesign."""
    s = Solver("nilm-battery")
    s.fit_calibrate(_clean_record())
    terms = ("cycle", "held_ambiguity", "request_reference")
    rows, fails = [], []

    def _mm(outs, key):
        xs = [float(o[key]) for o in outs]
        return f"{min(xs):.3f}/{sum(xs) / len(xs):.3f}/{max(xs):.3f}"

    for name, rec, intended in _terminal_battery():
        outs = s.recognize(rec, max_windows=12)
        states = [o["verdict"]["state"] for o in outs]
        tally = {t: states.count(t) for t in terms}
        rows.append(f"  {name:10s} intended={intended:18s} got={tally}\n"
                    f"             (min/mean/max) conf={_mm(outs, 'confidence')} "
                    f"spec={_mm(outs, 'spectral')} temp={_mm(outs, 'temporal')}")
        if intended in ("cycle", "held_ambiguity") and tally["request_reference"]:
            fails.append(f"{name}: FALSE ALARM ({tally['request_reference']} request_reference)")
        if intended == "held_ambiguity" and tally["held_ambiguity"] == 0:
            fails.append(f"{name}: noise never reached held_ambiguity")
        if intended == "request_reference" and tally["request_reference"] == 0:
            fails.append(f"{name}: MISS (structured window never request_reference)")
        if intended == "cycle" and tally["cycle"] == 0:
            fails.append(f"{name}: clean never reached cycle")
    matrix = (f"learned gates: {s.thresholds}\n"
              "terminal battery (intended -> observed):\n" + "\n".join(rows))
    print("\n" + matrix)
    assert not fails, matrix + "\n\nFAILURES:\n  " + "\n  ".join(fails)
