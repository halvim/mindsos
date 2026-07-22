"""Signature bake-off (DIAGNOSTIC / operator-L4 — NOT brain truth, do NOT persist).

Compares candidate appliance signatures on the CURRENT channel to see which one
separates the confusions the residual-harmonic profile could not
({CFL, Hairdryer, Microwave} mutually; kettle -> Fridge). Pure numpy: no
mindsos import, no PYTHONPATH needed. Results are session observations only
(contamination rule) — nothing here should be written into STATE/docs as a
finding; it exists to pick a representation, then throw away.

    python projects/amii_study/nilm_brain/scripts/signature_bakeoff.py \
        --data /home/sanmyaku/_sample

Candidates (each: per-window feature vector -> teach = mean over windows ->
6x6 mean-similarity, read by COLUMN dominance = does a taught profile get
matched best by its OWN appliance's windows):

  A resid_harmonic  baseline — harmonic mags of (current - fitted fundamental),
                    orders 2..K, L2-normalized, cosine. Mirrors the brain.
  B raw_harmonic    harmonic mags of RAW current at orders 2..K RELATIVE to the
                    fundamental (THD-shape). Euclidean — resistive loads cluster
                    near the origin instead of becoming cosine-noise.
  C vi_trajectory   one voltage-cycle of current vs voltage, peak-normalized,
                    resampled — shape only (resistive line vs nonlinear loop).
  D transient_harm  raw_harmonic computed on the MAX-residual window (turn-on),
                    not steady state.
  E power           magnitude/physics axis: [log Irms, power factor, crest,
                    rel. real power]. Standardized, Euclidean. Splits by size.
  F shape+power     B (THD-shape) concatenated with E (power), standardized.
                    Tests whether shape+magnitude together split the resistives.
"""

from __future__ import annotations

import argparse
import glob
import os

import numpy as np

EPS = 1e-12


# ── io ──────────────────────────────────────────────────────────────────
def load_records(base, cur_col, volt_col):
    recs = {}
    for f in sorted(glob.glob(os.path.join(base, "*.csv"))):
        arr = np.loadtxt(f, delimiter=",")
        if arr.ndim != 2 or arr.shape[1] <= max(cur_col, volt_col):
            print(f"  (skip {os.path.basename(f)}: shape {arr.shape})")
            continue
        recs[os.path.basename(f)[:-4]] = {"i": arr[:, cur_col].astype(float),
                                          "v": arr[:, volt_col].astype(float)}
    return recs


# ── signal primitives ─────────────────────────────────────────────────────
def _basis(n, f0, fs, order):
    t = np.arange(n) / fs
    w = 2 * np.pi * f0 * order
    return np.sin(w * t), np.cos(w * t)


def fundamental_residual(x, f0, fs):
    """Least-squares a*sin + b*cos + dc at f0; return the residual x - recon."""
    n = len(x)
    s, c = _basis(n, f0, fs, 1)
    D = np.stack([s, c, np.ones(n)], axis=1)
    coef, *_ = np.linalg.lstsq(D, x, rcond=None)
    return x - D @ coef


def harmonic_mags(x, f0, fs, orders):
    """Fourier projection amplitude at each k*f0 (robust to FFT-bin leakage)."""
    n = len(x)
    out = []
    for k in orders:
        s, c = _basis(n, f0, fs, k)
        a = 2.0 / n * np.sum(x * s)
        b = 2.0 / n * np.sum(x * c)
        out.append(np.hypot(a, b))
    return np.asarray(out, dtype=float)


def one_cycle_vi(iw, vw, f0, fs, npts):
    """Extract one full voltage cycle of (i) aligned to a rising v zero-cross,
    peak-normalized, resampled to `npts`. Returns None if no clean cycle."""
    spc = int(round(fs / f0))
    zc = np.where((vw[:-1] < 0) & (vw[1:] >= 0))[0]
    if len(zc) == 0 or zc[0] + spc >= len(iw):
        return None
    s = zc[0]
    seg_i = iw[s:s + spc]
    pk = np.max(np.abs(seg_i)) + EPS
    seg_i = seg_i / pk
    xp = np.linspace(0, 1, len(seg_i))
    xq = np.linspace(0, 1, npts)
    return np.interp(xq, xp, seg_i)


# ── candidate features (per window -> vector, or None to skip) ─────────────
def feat_resid_harmonic(iw, vw, cfg):
    r = fundamental_residual(iw, cfg["f0"], cfg["fs"])
    m = harmonic_mags(r, cfg["f0"], cfg["fs"], cfg["orders"])
    n = np.linalg.norm(m)
    return m / n if n > EPS else np.zeros_like(m)


def feat_raw_harmonic(iw, vw, cfg):
    allm = harmonic_mags(iw, cfg["f0"], cfg["fs"], [1] + list(cfg["orders"]))
    return allm[1:] / (allm[0] + EPS)          # THD-shape rel. to fundamental


def feat_vi(iw, vw, cfg):
    return one_cycle_vi(iw, vw, cfg["f0"], cfg["fs"], cfg["n_vi"])


def feat_power(iw, vw, cfg):
    irms = np.sqrt(np.mean(iw ** 2)) + EPS
    vrms = np.sqrt(np.mean(vw ** 2)) + EPS
    p = np.mean(vw * iw)
    pf = p / (vrms * irms)
    crest = np.max(np.abs(iw)) / irms
    return np.array([np.log10(irms), pf, crest, p])   # standardized later


def feat_physics(iw, vw, cfg):
    """Low-dim interpretable vector [PF, crest, THD, log Irms] — the scalars the
    physics table separates on, kept low-dim so cosine/dimensionality can't wash
    them out."""
    irms = np.sqrt(np.mean(iw ** 2)) + EPS
    vrms = np.sqrt(np.mean(vw ** 2)) + EPS
    pf = np.mean(vw * iw) / (vrms * irms)
    crest = np.max(np.abs(iw)) / irms
    fund = harmonic_mags(iw, cfg["f0"], cfg["fs"], [1])[0] + EPS
    thd = np.linalg.norm(harmonic_mags(iw, cfg["f0"], cfg["fs"], cfg["orders"])) / fund
    return np.array([pf, crest, thd, np.log10(irms)])


CANDIDATES = {
    "A resid_harmonic": ("cosine", feat_resid_harmonic),
    "B raw_harmonic":   ("euclid", feat_raw_harmonic),
    "C vi_trajectory":  ("cosine", feat_vi),
    "E power":          ("euclid", feat_power),
    "H physics_scalars": ("euclid", feat_physics),
}


# ── matrix build + read ────────────────────────────────────────────────────
def _sim(a, b, metric, scale):
    if metric == "cosine":
        return float(a @ b / ((np.linalg.norm(a) * np.linalg.norm(b)) + EPS))
    return float(np.exp(-np.linalg.norm(a - b) / (scale + EPS)))


def _standardize(feats, names):
    stack = np.vstack([feats[n] for n in names])
    mu, sd = stack.mean(0), stack.std(0) + EPS
    return {n: (feats[n] - mu) / sd for n in names}


def build_and_print(title, per_window, names, metric):
    """per_window: {name: [vec, ...]}  ->  6x6 mean-sim, column-read, score."""
    feats = {n: np.asarray([v for v in per_window[n] if v is not None])
             for n in names}
    feats = {n: f for n, f in feats.items() if len(f)}
    live = [n for n in names if n in feats]
    if len(live) < 2:
        print(f"\n### {title}: too few usable records ({live})")
        return

    dist = metric != "cosine"          # "euclid" | "euclid_raw" are distance-based
    if metric == "euclid":             # standardize; "euclid_raw" = already in final space
        feats = _standardize({n: feats[n] for n in live}, live)
    teach = {n: feats[n].mean(0) for n in live}
    if dist:
        profs = np.vstack([teach[n] for n in live])
        gaps = [np.linalg.norm(profs[i] - profs[j])
                for i in range(len(live)) for j in range(i + 1, len(live))]
        scale = float(np.median(gaps)) or 1.0
    else:
        scale = 1.0

    sim_metric = "euclid" if dist else "cosine"
    M = np.zeros((len(live), len(live)))
    for r, rn in enumerate(live):
        for c, cn in enumerate(live):
            M[r, c] = np.mean([_sim(v, teach[cn], sim_metric, scale) for v in feats[rn]])

    def short(x):
        return x.split("_")[0][:9]

    print(f"\n### {title}   (metric={metric})")
    print("row \\ col".ljust(12) + "".join(short(t).ljust(10) for t in live))
    col_pass = 0
    margins = []
    for r, rn in enumerate(live):
        row = M[r]
        cells = "".join(f"{row[c]:<10.3f}" for c in range(len(live)))
        mark = ""
        if rn in live:
            own = live.index(rn)
            if row[own] < row.max() - 1e-9:
                mark = f"  <-- row-confused w/ {short(live[np.argmax(row)])}"
        print(short(rn).ljust(12) + cells + mark)
    # column read: does each taught profile's own appliance top its column?
    print("col-winner: ", end="")
    wins = []
    for c, cn in enumerate(live):
        col = M[:, c]
        winner = live[int(np.argmax(col))]
        ok = winner == cn
        col_pass += ok
        # margin = own - best other, down the column
        own_v = col[c]
        other = np.delete(col, c)
        margins.append(own_v - other.max())
        wins.append(f"{short(cn)}={'ok' if ok else short(winner)}")
    print("  ".join(wins))
    worst = min(margins) if margins else float("nan")
    print(f"SCORE: {col_pass}/{len(live)} columns own-dominant | "
          f"worst column margin = {worst:+.3f}")


# ── physics readout (measure before fixing) ───────────────────────────────
def physics_table(recs, names, cfg, starts_fn):
    print("\n=== physics readout (per record, mean over windows) ===")
    print(f"{'record':30s} Irms(rel)  crest   PF     THD    residfrac")
    irms_all = {}
    rows = []
    for n in names:
        iw, vw = recs[n]["i"], recs[n]["v"]
        cr = th = pf = rf = ir = 0.0
        ws = starts_fn(len(iw))
        for s in ws:
            i, v = iw[s:s + cfg["wlen"]], vw[s:s + cfg["wlen"]]
            irms = np.sqrt(np.mean(i ** 2)) + EPS
            vrms = np.sqrt(np.mean(v ** 2)) + EPS
            fund = harmonic_mags(i, cfg["f0"], cfg["fs"], [1])[0] + EPS
            harm = harmonic_mags(i, cfg["f0"], cfg["fs"], cfg["orders"])
            resid = fundamental_residual(i, cfg["f0"], cfg["fs"])
            ir += irms
            cr += np.max(np.abs(i)) / irms
            pf += np.mean(v * i) / (vrms * irms)
            th += np.linalg.norm(harm) / fund
            rf += np.sqrt(np.mean(resid ** 2)) / irms
        k = len(ws)
        irms_all[n] = ir / k
        rows.append((n, ir / k, cr / k, pf / k, th / k, rf / k))
    imax = max(irms_all.values()) + EPS
    for n, ir, cr, pf, th, rf in rows:
        print(f"{n:30s} {ir/imax:8.3f}  {cr:6.2f}  {pf:6.3f} {th:6.3f} {rf:8.3f}")


# ── main ──────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--fs", type=float, default=30000.0)
    ap.add_argument("--f0", type=float, default=60.0)
    ap.add_argument("--orders", type=int, nargs="+", default=[2, 3, 4, 5, 6, 7])
    ap.add_argument("--window-cycles", type=int, default=4)
    ap.add_argument("--window-step", type=int, default=2)
    ap.add_argument("--max-windows", type=int, default=16)
    ap.add_argument("--n-vi", type=int, default=64)
    ap.add_argument("--cur-col", type=int, default=0)
    ap.add_argument("--volt-col", type=int, default=1)
    args = ap.parse_args()

    cfg = {"fs": args.fs, "f0": args.f0, "orders": args.orders, "n_vi": args.n_vi}
    spc = args.fs / args.f0
    cfg["wlen"] = int(round(args.window_cycles * spc))
    step = int(round(args.window_step * spc))

    def starts(n):
        return list(range(0, max(1, n - cfg["wlen"]), step))[:args.max_windows]

    recs = load_records(args.data, args.cur_col, args.volt_col)
    names = list(recs.keys())
    if len(names) < 2:
        raise SystemExit(f"need >=2 records in {args.data}, found {names}")
    print(f"records: {names}")
    print(f"fs={args.fs} f0={args.f0} orders={args.orders} "
          f"wlen={cfg['wlen']} step={step} max_windows={args.max_windows}")

    physics_table(recs, names, cfg, starts)

    # per-window features for steady candidates
    for title, (metric, fn) in CANDIDATES.items():
        per_window = {}
        for n in names:
            iw, vw = recs[n]["i"], recs[n]["v"]
            per_window[n] = [fn(iw[s:s + cfg["wlen"]], vw[s:s + cfg["wlen"]], cfg)
                             for s in starts(len(iw))]
        build_and_print(title, per_window, names, metric)

    # D: transient (max-residual window) raw-harmonic — one vector per record
    trans = {}
    for n in names:
        iw, vw = recs[n]["i"], recs[n]["v"]
        best = None
        for s in starts(len(iw)):
            i = iw[s:s + cfg["wlen"]]
            e = np.sqrt(np.mean(fundamental_residual(i, cfg["f0"], cfg["fs"]) ** 2))
            if best is None or e > best[0]:
                best = (e, feat_raw_harmonic(i, vw[s:s + cfg["wlen"]], cfg))
        trans[n] = [best[1]]
    build_and_print("D transient_harm (1 vec/record — diagonal is trivial, read off-diag only)",
                    trans, names, "euclid")

    # F: shape (B) + power (E) concatenated PER WINDOW — honest diagonal, spread counts
    combo = {}
    for n in names:
        iw, vw = recs[n]["i"], recs[n]["v"]
        combo[n] = [np.concatenate([
            feat_raw_harmonic(iw[s:s + cfg["wlen"]], vw[s:s + cfg["wlen"]], cfg),
            feat_power(iw[s:s + cfg["wlen"]], vw[s:s + cfg["wlen"]], cfg)])
            for s in starts(len(iw))]
    build_and_print("F shape+power (per-window)", combo, names, "euclid")

    # G: V-I shape (C) + power (E) concatenated PER WINDOW — does magnitude fix VI's
    #    Hairdryer/kettle->Fridge leak? (caveat: 64 shape dims vs 4 power dims after
    #    standardizing, so shape still dominates the distance — directional only)
    gcombo = {}
    for n in names:
        iw, vw = recs[n]["i"], recs[n]["v"]
        rows = []
        for s in starts(len(iw)):
            i, v = iw[s:s + cfg["wlen"]], vw[s:s + cfg["wlen"]]
            vi = feat_vi(i, v, cfg)
            rows.append(np.concatenate([vi, feat_power(i, v, cfg)]) if vi is not None else None)
        gcombo[n] = rows
    build_and_print("G vi+power (per-window)", gcombo, names, "euclid")

    # I: union [physics H (+) raw_harmonic] with a WHITENED (Mahalanobis) metric.
    #    Pooled ZCA-whitening decorrelates axes so an internally-variable class
    #    (kettle) isn't penalized for its own spread — tests metric-vs-feature.
    def feat_union(i, v, cfg):
        return np.concatenate([feat_physics(i, v, cfg), feat_raw_harmonic(i, v, cfg)])

    uni = {}
    for n in names:
        iw, vw = recs[n]["i"], recs[n]["v"]
        uni[n] = np.asarray([feat_union(iw[s:s + cfg["wlen"]], vw[s:s + cfg["wlen"]], cfg)
                             for s in starts(len(iw))])
    allX = np.vstack([uni[n] for n in names])
    mu, sd = allX.mean(0), allX.std(0) + EPS
    Xs = (allX - mu) / sd
    C = np.cov(Xs.T) + 1e-3 * np.eye(Xs.shape[1])
    w, V = np.linalg.eigh(C)
    Wht = V @ np.diag(1.0 / np.sqrt(np.clip(w, 1e-9, None))) @ V.T
    whit = {n: list(((uni[n] - mu) / sd) @ Wht) for n in names}
    build_and_print("I union+whitened (Mahalanobis, decorrelated axes)",
                    whit, names, "euclid_raw")

    print("\nread: SCORE line per candidate. Higher own-dominant count + larger "
          "worst margin = better separation. Compare against baseline A.")


if __name__ == "__main__":
    main()
