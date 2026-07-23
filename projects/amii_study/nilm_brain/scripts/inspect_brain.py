"""Boot the mindsos brain and print what is inside it — DataStates, the
finder-composed pipelines, the capacity registry (by family), and the learned
appliance state after a teach. Read-only introspection; nothing persisted.

    PYTHONPATH=.:projects/amii_study python \
      projects/amii_study/nilm_brain/scripts/inspect_brain.py
"""
from __future__ import annotations

import numpy as np

from nilm_brain import ontology as O
from nilm_brain.control import Solver


def _short(iri):
    return iri.rsplit(":", 1)[-1].rsplit(".", 1)[-1]


def _record(amp, harm, crest, inrush, seed, n_cycles=60, fs=30000.0, f0=60.0):
    n = int(round(n_cycles * fs / f0)); t = np.arange(n) / fs
    rng = np.random.default_rng(seed)
    v = 170.0 * np.sin(2 * np.pi * f0 * t)
    i = amp * np.sin(2 * np.pi * f0 * t)
    for k, c in harm.items():
        i = i + amp * c * np.sin(2 * np.pi * f0 * k * t)
    i = np.sign(i) * np.abs(i) ** crest
    on = int(0.2 * n); i[:on] = 0.0; i[on:on + 500] *= inrush
    i = i + 0.01 * amp * rng.standard_normal(n)
    return np.stack([i, v], axis=1)


def main():
    s = Solver("nilm-inspect")

    print("=" * 70)
    print("DATASTATES (ontology realm `nilm`)")
    print("=" * 70)
    print(f"count = {len(O.ONTOLOGY)}")
    for ds in O.ONTOLOGY:
        print(f"  {_short(ds.iri):24s} {ds.description}")

    def show(name, seg):
        print("\n" + "=" * 70)
        print(f"COMPOSED PIPELINE: {name}   (finder-returned, executes to real values)")
        print("=" * 70)
        print(f"target -> {_short(seg.target_datastate)}")
        for i, st in enumerate(seg.steps, 1):
            print(f"  step {i}: {_short(st.capacity_iri)}")

    show("cycle recognition segment", s.segment)
    show("appliance signature segment", s.appliance_segment)

    print("\n" + "=" * 70)
    print("CAPACITY REGISTRY (by family; upsert re-list — the same caps boot has)")
    print("=" * 70)
    from nilm_brain.perception import register_perception
    from nilm_brain.derivation import register_derivation
    from nilm_brain.scoring import register_scoring
    from nilm_brain.decision import register_decision
    from nilm_brain.comprehension import register_comprehension, register_predicate
    for fam, fn in [("perception", register_perception), ("derivation", register_derivation),
                    ("scoring", register_scoring), ("decision", register_decision),
                    ("comprehension", register_comprehension), ("predicate", register_predicate)]:
        try:
            iris = fn(s.cl, s.session)
            print(f"  {fam:14s} ({len(iris)}): {', '.join(_short(i) for i in iris)}")
        except Exception as e:
            print(f"  {fam:14s} (could not re-list: {e})")

    print("\n" + "=" * 70)
    print("LEARNED APPLIANCE STATE (after teaching 2 classes x 2 instances)")
    print("=" * 70)
    specs = {"heaterA": (8.0, {3: 0.02}, 1.0, 1.2),
             "electronics": (0.8, {3: 0.5, 5: 0.3}, 1.6, 1.0)}
    for name, (amp, h, ce, inr) in specs.items():
        for seed in (1, 2):
            s.teach_appliance(name, _record(amp, h, ce, inr, seed), max_windows=6)
    s.fit_appliance()
    print(f"library exemplars   = {len(s.appliance_library)} "
          f"(classes: {sorted({r['name'] for r in s.appliance_library})})")
    ex = s.appliance_library[0]
    print(f"one exemplar        = name={ex['name']!r} inst={ex['inst']} "
          f"dim={len(ex['vector'])} vector[:4]={[round(x,3) for x in ex['vector'][:4]]}")
    print(f"signature_norm      = provenance={s.signature_norm.get('provenance')} "
          f"dim={len(s.signature_norm.get('std', []))}")
    print(f"match_cutoff        = {s.match_cutoff}")

    # one live recognition, to show the verdict object the brain emits
    outs = s.recognize_appliance(_record(8.0, {3: 0.02}, 1.0, 1.2, seed=99), max_windows=4, k=3)
    print("\nlive recognize (held-out heaterA), first window verdict:")
    print(f"  {outs[0]['verdict']}")


if __name__ == "__main__":
    main()
