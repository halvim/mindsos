#!/usr/bin/env python3
"""
Family B addendum — HONEST novelty-distance curve (AM-3).
Fixes the audit finding: the §8 curve conflated per-D baseline corruption levels.
Here: single D, a FIXED LIGHT in-store baseline (belongs), OOD swept by TRUE distance d
(substitutions from a store item, d > baseline), + an OOV far point.
Question: is near-vocabulary novelty a genuine grounding blind spot for SYMBOLIC retrieval
(like perception P15), or does symbolic grounding flag even near novelty cleanly?
"""
import json, numpy as np

V, D, M, NQ = 5, 12, 200, 4000
C0 = 1                      # fixed light baseline corruption ("belongs")
DLEVELS = [2, 3, 4, 6, 9]   # true OOD distance (substitutions); 2 ~ just beyond baseline
SEEDS = [0, 1, 2, 3, 4]

def auroc(s, y):
    s, y = np.asarray(s, float), np.asarray(y, int); pos, neg = (y == 1).sum(), (y == 0).sum()
    if pos == 0 or neg == 0: return float("nan")
    o = np.argsort(s); r = np.empty(len(s)); r[o] = np.arange(1, len(s) + 1)
    for v in np.unique(s):
        i = s == v
        if i.sum() > 1: r[i] = r[i].mean()
    return float((r[y == 1].sum() - pos * (pos + 1) / 2) / (pos * neg))

def corrupt(it, c, g):
    q = it.copy(); p = g.choice(D, c, replace=False); q[p] = g.integers(0, V, c); return q
def oov(it, g):
    q = it.copy(); p = g.choice(D, max(1, D // 4), replace=False); q[p] = g.integers(V, V + 3, len(p)); return q
def ground(q, store):
    i = (store == q).sum(1).argmax()
    return 0.0 if np.any(q >= V) else 1.0 - (store[i] != q).sum() / D

def run():
    curves = []
    for sd in SEEDS:
        g = np.random.default_rng(sd); store = g.integers(0, V, (M, D))
        base = np.array([ground(corrupt(store[s], C0, g), store) for s in g.integers(0, M, NQ)])
        row = []
        for d in DLEVELS:
            od = np.array([ground(corrupt(store[s], d, g), store) for s in g.integers(0, M, NQ)])
            row.append(auroc(np.r_[base, od], np.r_[np.ones(len(base)), np.zeros(len(od))]))
        ov = np.array([ground(oov(store[s], g), store) for s in g.integers(0, M, NQ)])
        row.append(auroc(np.r_[base, ov], np.r_[np.ones(len(base)), np.zeros(len(ov))]))
        curves.append(row)
    cv = np.array(curves); mean = cv.mean(0).round(3).tolist(); std = cv.std(0).round(3).tolist()
    labels = [f"d={d}" for d in DLEVELS] + ["oov"]
    monotone = all(mean[i] <= mean[i + 1] + 0.02 for i in range(len(mean) - 1))
    # blind spot test: is near distance (d=2, just beyond baseline) hard while far is clean?
    near, far = mean[0], mean[-2]
    print(json.dumps({
        "D": D, "baseline_corruption": C0, "labels": labels,
        "curve_mean": mean, "curve_std": std, "monotone": monotone,
        "near(d=2)_AUROC": near, "far(d=9)_AUROC": far, "oov_AUROC": mean[-1],
        "blind_spot_present": near < 0.75 and far >= 0.85,
        "reading": "near<0.75 & far>=0.85 => genuine near-vocabulary blind spot reproduced (P15)",
    }, indent=2))

if __name__ == "__main__":
    run()
