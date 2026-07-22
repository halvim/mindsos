"""Leave-one-INSTANCE-out appliance classification over PLAID submetered.
The first cross-instance (non n=1) test — and, unlike the nearest-centroid
bake-off, k-NN represents a class by many exemplars so it is not biased toward
tight classes. Diagnostic/operator — NOT brain truth, do not persist.

    python projects/amii_study/nilm_brain/scripts/classify_eval.py \
        --data /home/sanmyaku/_plaid_full/_sample_expanded --k 5

Feature sets compared (does the transient crack Hairdryer<->kettle?):
  P        physics per window  [PF, crest, THD, logIrms]
  U        union     per window [physics (+) raw-harmonic ratios]
  U+onset  U with record-level turn-on features [inrush ratio, onset time]
"""
from __future__ import annotations

import argparse
import glob
import os
import re
from collections import Counter

import numpy as np

EPS = 1e-12


def label_of(path):
    return re.sub(r"_\d+$", "", os.path.basename(path)[:-4])


# ── primitives (same math as the bake-off) ─────────────────────────────────
def _basis(n, f0, fs, k):
    t = np.arange(n) / fs
    w = 2 * np.pi * f0 * k
    return np.sin(w * t), np.cos(w * t)


def fundamental_residual(x, f0, fs):
    n = len(x)
    s, c = _basis(n, f0, fs, 1)
    D = np.stack([s, c, np.ones(n)], 1)
    coef, *_ = np.linalg.lstsq(D, x, rcond=None)
    return x - D @ coef


def harmonic_mags(x, f0, fs, orders):
    n = len(x)
    out = []
    for k in orders:
        s, c = _basis(n, f0, fs, k)
        out.append(np.hypot(2.0 / n * np.sum(x * s), 2.0 / n * np.sum(x * c)))
    return np.asarray(out)


def window_feats(iw, vw, cfg):
    irms = np.sqrt(np.mean(iw ** 2)) + EPS
    vrms = np.sqrt(np.mean(vw ** 2)) + EPS
    pf = np.mean(vw * iw) / (vrms * irms)
    crest = np.max(np.abs(iw)) / irms
    fund = harmonic_mags(iw, cfg["f0"], cfg["fs"], [1])[0] + EPS
    harm = harmonic_mags(iw, cfg["f0"], cfg["fs"], cfg["orders"])
    thd = np.linalg.norm(harm) / fund
    phys = np.array([pf, crest, thd, np.log10(irms)])
    return {"P": phys, "U": np.concatenate([phys, harm / fund])}


def onset_feats(i, cfg):
    """PLAID off-on: locate turn-on, measure inrush ratio + onset time frac."""
    env = np.abs(i)
    steady = np.sqrt(np.mean(env[int(0.8 * len(env)):] ** 2)) + EPS
    thr = 0.2 * (np.max(env) + EPS)
    on = int(np.argmax(env > thr)) if np.any(env > thr) else 0
    span = int(5 * cfg["fs"] / cfg["f0"])
    inrush = np.max(env[on:on + span]) if on < len(env) else np.max(env)
    return np.array([inrush / steady, on / len(env)])


def extract(path, cfg):
    arr = np.loadtxt(path, delimiter=",")
    i, v = arr[:, 0], arr[:, 1]
    spc = cfg["fs"] / cfg["f0"]
    wlen = int(round(4 * spc))
    step = int(round(2 * spc))
    start0 = int(round(15 * spc))       # skip the transient for STEADY features
    starts = list(range(start0, len(i) - wlen, step))[:cfg["max_windows"]]
    if not starts:                       # short record: fall back to whatever fits
        starts = list(range(0, max(1, len(i) - wlen), step))[:cfg["max_windows"]]
    P, U = [], []
    for s in starts:
        f = window_feats(i[s:s + wlen], v[s:s + wlen], cfg)
        P.append(f["P"]); U.append(f["U"])
    onset = onset_feats(i, cfg)
    P, U = np.asarray(P), np.asarray(U)
    UO = np.hstack([U, np.tile(onset, (len(U), 1))])
    return {"P": P, "U": U, "U+onset": UO}


def knn_loio(data, key, k):
    """data: list of (label, Xwindows[key]). Leave one instance out; each test
    window voted by k nearest TRAIN windows; instance = majority of its windows."""
    labels = sorted({lab for lab, _ in data})
    conf = {a: Counter() for a in labels}
    correct = 0
    for idx, (lab, _) in enumerate(data):
        Xtr, ytr = [], []
        for j, (l2, X2) in enumerate(data):
            if j == idx:
                continue
            Xtr.append(X2[key]); ytr += [l2] * len(X2[key])
        Xtr = np.vstack(Xtr); ytr = np.array(ytr)
        mu, sd = Xtr.mean(0), Xtr.std(0) + EPS
        Xtr = (Xtr - mu) / sd
        Xte = (data[idx][1][key] - mu) / sd
        preds = []
        for x in Xte:
            d = np.linalg.norm(Xtr - x, axis=1)
            preds.append(Counter(ytr[np.argsort(d)[:k]]).most_common(1)[0][0])
        pred = Counter(preds).most_common(1)[0][0]
        conf[lab][pred] += 1
        correct += (pred == lab)
    return correct / len(data), conf, labels


def print_conf(title, acc, conf, labels):
    def sh(x):
        return x.split("_")[0][:9]
    print(f"\n### {title}   accuracy = {acc:.3f} ({sum(sum(c.values()) for c in conf.values())} instances)")
    print("true\\pred".ljust(12) + "".join(sh(l).ljust(10) for l in labels))
    for lab in labels:
        row = "".join(f"{conf[lab][p]:<10d}" for p in labels)
        tot = sum(conf[lab].values()) or 1
        rec = conf[lab][lab] / tot
        print(sh(lab).ljust(12) + row + f"  recall={rec:.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--fs", type=float, default=30000.0)
    ap.add_argument("--f0", type=float, default=60.0)
    ap.add_argument("--orders", type=int, nargs="+", default=[2, 3, 4, 5, 6, 7])
    ap.add_argument("--max-windows", type=int, default=16)
    ap.add_argument("--k", type=int, default=5)
    a = ap.parse_args()
    cfg = {"fs": a.fs, "f0": a.f0, "orders": a.orders, "max_windows": a.max_windows}

    files = sorted(glob.glob(os.path.join(a.data, "*.csv")))
    data = [(label_of(f), extract(f, cfg)) for f in files]
    counts = Counter(lab for lab, _ in data)
    print(f"instances/class: {dict(counts)}")
    usable = {c for c, n in counts.items() if n >= 2}
    if len(usable) < 2:
        raise SystemExit("need >=2 instances for >=2 classes for leave-one-out")
    data = [d for d in data if d[0] in usable]
    dropped = set(counts) - usable
    if dropped:
        print(f"(dropped single-instance classes: {sorted(dropped)})")

    for key in ("P", "U", "U+onset"):
        acc, conf, labels = knn_loio(data, key, a.k)
        print_conf(key, acc, conf, labels)

    print("\nread: per-class recall; watch Hairdryer & Water rows. U+onset beating "
          "U on those two = the transient is the discriminant for the resistive pair.")


if __name__ == "__main__":
    main()
