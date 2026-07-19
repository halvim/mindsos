"""Eyeball run: naive CNN vs the CL baselines (ER, EWC, LwF) on the same stream.

Prints BWT (forgetting) and final macro-F1 per arm. Expected direction (an
observation, not a scored claim — single seed, unconverged nets): the CL methods
forget LESS than the naive CNN (BWT closer to 0). Multi-seed ± CI via
study.aggregate is the scored path.

Run from repo root:  python3 -m study.run_baselines_compare
"""
import numpy as np

from study.baselines.cnn import CNNArm
from study.baselines.cl import EWCArm, LwFArm, ReplayArm
from study.runner import run_stream

ARMS = {
    "naive-CNN": lambda: CNNArm(epochs=40, seed=0),
    "ER": lambda: ReplayArm(epochs=40, seed=0),
    "EWC": lambda: EWCArm(epochs=40, seed=0),
    "LwF": lambda: LwFArm(epochs=40, seed=0),
}


def main():
    for name, make in ARMS.items():
        res = run_stream(make(), n_train=128, n_test=96, seed=0)
        macro = float(np.mean(list(res["final_f1"].values())))
        print(f"{name:10s}  BWT={res['bwt_primitives']:+.3f}  final_macroF1={macro:.3f}  "
              f"notch={res['notch_f1']:.2f}")


if __name__ == "__main__":
    main()
