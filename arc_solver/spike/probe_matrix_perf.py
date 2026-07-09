"""Slice-2a perf probe: measures invoke overhead + counts the exhaustive
comparison_matrix invocations over the 400 tasks, to extrapolate the added
layer-execution time BEFORE building the full matrix. Measurement only; no
solver change. Run: python arc_solver/spike/probe_matrix_perf.py"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from arc_solver.spike import arc_capacities as ac
from arc_solver.spike import arc_grids, arc_profile


def count_invocations(tasks):
    n_inter = n_point = n_touch = n_grid = 0
    for t in tasks:
        for pr in t["train"]:
            gi, go = pr["input"], pr["output"]
            n_inter += 10 * len(gi["objects"]) * len(go["objects"])
            n_point += len(gi["points"]) * len(go["points"])
            n_grid += 2
            for g in (gi, go):
                m = len(g["objects"]) + len(g["points"])
                n_touch += m * (m - 1) // 2
        for tt in t.get("test", []):
            g = tt["input"]
            m = len(g["objects"]) + len(g["points"])
            n_touch += m * (m - 1) // 2
    return n_inter, n_point, n_touch, n_grid


def measure_overhead(cl, k=20000):
    cap = ac.capacity_iri(ac.CATEGORY_PROFILER, "same_object")
    a = {"cells": [[0, 0], [0, 1]], "color": 1, "size": 2}
    b = {"cells": [[2, 2], [2, 3]], "color": 1, "size": 2}
    r = cl.invoke(cap, inputs={ac.DS_OBJECT: [a, b]})
    print("warm-up invoke success =", getattr(r, "success", r))
    t0 = time.perf_counter()
    for _ in range(k):
        cl.invoke(cap, inputs={ac.DS_OBJECT: [a, b]})
    return (time.perf_counter() - t0) / k


def main():
    dataset = arc_grids.load_dataset()
    ids = sorted(dataset["train"])
    tasks = [arc_profile.build_profile(dataset, "train", tid) for tid in ids]
    ni, npt, nt, ng = count_invocations(tasks)
    total = ni + npt + nt + ng

    cl = ac.fresh_layer()
    oh = measure_overhead(cl)

    print("tasks:", len(tasks))
    print("N_total invocations (exhaustive matrix): {:,}".format(total))
    print("  inter-grid obj+shape (x10): {:,}".format(ni))
    print("  point (same_point):         {:,}".format(npt))
    print("  intra-grid touching:        {:,}".format(nt))
    print("  grid dim+palette:           {:,}".format(ng))
    print("invoke overhead: {:.1f} us/call".format(oh * 1e6))
    print("extrapolated added layer time: {:.1f} s".format(total * oh))


if __name__ == "__main__":
    main()
