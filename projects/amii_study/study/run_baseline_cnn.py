"""Real harness sanity-run: train the naive 1-D CNN through the concept stream
and print the per-class forgetting matrix + the credible signals.

Expected sanity signal (an observation, not a claim): each primitive learns on
its own increment, then decays after later ones → bwt_primitives < 0. That
confirms generator -> stream -> train -> joint-test -> metrics works before any
judged run. No number here is a scored result (single seed, unconverged net).

Run from the repo root:  python3 -m study.run_baseline_cnn
"""
import numpy as np

from study.baselines.cnn import CNNArm
from study.runner import run_stream
from study.stream import CONCEPT_STREAM


def main():
    res = run_stream(CNNArm(epochs=40), n_train=128, n_test=96, seed=0)
    np.set_printoptions(precision=2, suppress=True, linewidth=120)
    print("increments:", [n for n, _ in CONCEPT_STREAM])
    print("classes:   ", res["classes"])
    print("R (row = after increment, col = class F1 on joint test):")
    print(res["R"])
    print("final per-class F1:", {k: round(v, 2) for k, v in res["final_f1"].items()})
    print(f"BWT (primitives) = {res['bwt_primitives']:.3f}   (negative = forgetting)")
    print(f"notch F1 (held-out primitive, A5) = {res['notch_f1']:.3f}")
    print("zero-shot composition (held-out combos, A4):",
          {k: round(v, 3) for k, v in res["heldout_composition"].items()})


if __name__ == "__main__":
    main()
