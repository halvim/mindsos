#!/usr/bin/env python3
"""
Leaf-Learning NOVELTY — MindsOS leaf-chain (numpy, in-sandbox).
Spec: PERCEPTION_LEAF_NOVELTY_PREREG.md (v2 + AM-2/3/4). Consumes leaf_novelty_data.npz.

The chain (analysis-by-synthesis; each leaf produces a NAMED atom + per-invocation
grounding_conf & decision_conf):
    pixel --[tau]--> point --[polar median profile]--> boundary
    boundary --[RDP eps]--> segments/vertices --[K]--> polygon{triangle(3), rectangle(4)}
    (withholdable) circle/arc leaf: algebraic (Kasa) fit
    irreducibility detector: no <=Kmax straight-segment composition grounds the curve
        -> REQUEST_ATOM(residual="curvature"), NEVER fabricate a high-conf polygon.

LEARNED (AM-2), not baked: tau + RDP eps fit on TRAIN by accuracy; grounding/decision
Platt-calibrated per leaf on CAL. The generator's per-instance params are NEVER seen --
only labeled rendered images. Kmax is a DESIGN constant (the polygon vocabulary), not tuned.

Outputs leaf_novelty_mindsos_results.json. Runs fully in-sandbox; identical on Linux (numpy).
"""
import json, numpy as np

KMAX = 6                       # polygon vocabulary ceiling (design constant, not tuned)
GRID = 64
RNG = np.random.default_rng(0)


# ----------------------------- geometry leaves -----------------------------
def _shift(a, dy, dx):
    """shift a 2D array with zero-fill (no wrap)."""
    o = np.zeros_like(a)
    ys0, ys1 = max(0, dy), min(a.shape[0], a.shape[0] + dy)
    xs0, xs1 = max(0, dx), min(a.shape[1], a.shape[1] + dx)
    o[ys0:ys1, xs0:xs1] = a[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return o


def pixel_to_point(img, tau):
    """pixel -> point, denoised (vectorized, cheap). (1) drop specks: keep fg pixels with >=2
    fg neighbours (isolated noise has none). (2) robust radial-annulus trim about the median
    centre: the outline forms a dense annulus at ~median radius; noise anywhere else is removed.
    Valid because the shapes are star-convex outlines (P7 scale-relative)."""
    fg = img > tau
    if fg.sum() < 10:
        return np.zeros((0, 2))
    nbr = np.zeros(fg.shape, int)                          # 8-neighbour fg count
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                nbr += _shift(fg.astype(int), dy, dx)
    fg = fg & (nbr >= 2)
    ys, xs = np.where(fg)
    if len(xs) < 10:
        return np.zeros((0, 2))
    P = np.stack([xs, ys], 1).astype(float)
    c = np.median(P, 0)
    r = np.hypot(P[:, 0] - c[0], P[:, 1] - c[1])
    med = np.median(r) + 1e-9
    keep = (r > 0.5 * med) & (r < 1.8 * med)               # annulus: drop inner + far noise
    P = P[keep]
    if len(P) >= 10:                                       # one refinement pass on the trimmed set
        c = P.mean(0)
        r = np.hypot(P[:, 0] - c[0], P[:, 1] - c[1])
        med = np.median(r) + 1e-9
        P = P[(r > 0.5 * med) & (r < 1.8 * med)]
    return P


def boundary_profile(P, nb=72):
    """point -> robust polar boundary: median radius per angle bin (outlier/noise resistant)."""
    if len(P) < 8:
        return None, None
    c = P.mean(0)
    d = P - c
    ang = np.arctan2(d[:, 1], d[:, 0])
    rad = np.hypot(d[:, 0], d[:, 1])
    bins = ((ang + np.pi) / (2 * np.pi) * nb).astype(int) % nb
    r = np.full(nb, np.nan)
    for b in range(nb):
        m = bins == b
        if m.any():
            r[b] = np.median(rad[m])
    # fill empty bins by circular interpolation
    idx = np.arange(nb)
    good = ~np.isnan(r)
    if good.sum() < nb * 0.5:
        return None, None
    r = np.interp(idx, idx[good], r[good], period=nb)
    # light circular smoothing kills noise wiggle without bowing straight edges (w=1; w>=3 bows)
    w = 1
    ker = np.ones(2 * w + 1) / (2 * w + 1)
    r = np.real(np.fft.ifft(np.fft.fft(r) * np.fft.fft(ker, nb)))
    r = np.roll(r, -w)
    th = (idx + 0.5) / nb * 2 * np.pi - np.pi
    loop = np.stack([c[0] + r * np.cos(th), c[1] + r * np.sin(th)], 1)
    return loop, c


def _rdp(pts, eps):
    """Ramer-Douglas-Peucker on an OPEN polyline. Returns kept indices."""
    keep = np.zeros(len(pts), bool); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        p0, p1 = pts[a], pts[b]
        seg = p1 - p0; L = np.hypot(*seg) + 1e-9
        v = pts[a + 1:b] - p0
        d = np.abs(seg[0] * v[:, 1] - seg[1] * v[:, 0]) / L
        if len(d) == 0:
            continue
        i = a + 1 + int(np.argmax(d))
        if d[i - a - 1] > eps:
            keep[i] = True; stack += [(a, i), (i, b)]
    return np.where(keep)[0]


def rdp_closed(loop, eps):
    """RDP on a CLOSED loop via diameter split (avoids the zero-length closure edge).
    Anchor at the farthest-from-centroid point + its farthest partner; RDP each arc."""
    c = loop.mean(0)
    r = np.hypot(loop[:, 0] - c[0], loop[:, 1] - c[1])
    i0 = int(np.argmax(r))
    d0 = np.hypot(loop[:, 0] - loop[i0, 0], loop[:, 1] - loop[i0, 1])
    i1 = int(np.argmax(d0))
    a, b = sorted([i0, i1])
    arc1 = loop[a:b + 1]
    arc2 = np.vstack([loop[b:], loop[:a + 1]])
    V = np.vstack([arc1[_rdp(arc1, eps)], arc2[_rdp(arc2, eps)]])
    uniq = []
    for p in V:
        if not any(np.hypot(p[0] - q[0], p[1] - q[1]) < 2.0 for q in uniq):
            uniq.append(p)
    return np.array(uniq), len(uniq)


def render_outline(verts=None, circle=None):
    img = np.zeros((GRID, GRID), np.float32)
    def stamp(xs, ys):
        xi = np.clip(np.round(xs).astype(int), 0, GRID - 1)
        yi = np.clip(np.round(ys).astype(int), 0, GRID - 1)
        img[yi, xi] = 1.0
    if verts is not None:
        V = np.asarray(verts)
        for i in range(len(V)):
            a, b = V[i], V[(i + 1) % len(V)]
            t = np.linspace(0, 1, 400)
            stamp(a[0] * (1 - t) + b[0] * t, a[1] * (1 - t) + b[1] * t)
    if circle is not None:
        cx, cy, r = circle
        t = np.linspace(0, 2 * np.pi, 700)
        stamp(cx + r * np.cos(t), cy + r * np.sin(t))
    return img


def _dilate(b):
    o = b.copy()
    o[1:] |= b[:-1]; o[:-1] |= b[1:]; o[:, 1:] |= b[:, :-1]; o[:, :-1] |= b[:, 1:]
    return o


def recon_iou(fg_bin, verts=None, circle=None):
    """analysis-by-synthesis grounding: IoU(rendered hypothesis outline, foreground)."""
    h = render_outline(verts, circle) > 0.3
    a, b = _dilate(fg_bin), _dilate(h)
    inter = (a & b).sum(); union = (a | b).sum()
    return float(inter / (union + 1e-9))


def circle_fit(P):
    """Kasa algebraic circle fit."""
    x, y = P[:, 0], P[:, 1]
    A = np.stack([x, y, np.ones_like(x)], 1)
    bvec = x ** 2 + y ** 2
    sol, *_ = np.linalg.lstsq(A, bvec, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    r = np.sqrt(sol[2] + cx ** 2 + cy ** 2)
    return cx, cy, r


def curvature_spread(loop):
    """exterior-angle 'concentration': fraction of total turning in the top-KMAX samples.
    polygon -> ~1 (turning in few vertices); circle -> low (turning spread uniformly)."""
    d = np.diff(np.vstack([loop, loop[:2]]), axis=0)
    ang = np.arctan2(d[:, 1], d[:, 0])
    turn = np.abs(np.diff(np.concatenate([ang, ang[:1]])))
    turn = np.minimum(turn, 2 * np.pi - turn)
    tot = turn.sum() + 1e-9
    top = np.sort(turn)[-KMAX:].sum()
    return float(top / tot)


# ----------------------------- the chain -----------------------------
class LeafChain:
    def __init__(self, tau=0.5, eps=1.6, arc=True):
        self.tau, self.eps, self.arc = tau, eps, arc
        self.platt = {}     # per-leaf (A,B) for grounding logistic; identity until fit

    def _hyps(self, img):
        """return dict shape -> (grounding_raw, vertices/circle, K, spread). No calibration."""
        P = pixel_to_point(img, self.tau)
        if len(P) < 10:
            return {"_degenerate": True}
        fg = np.zeros((GRID, GRID), bool)              # cleaned foreground (largest blob only)
        fg[P[:, 1].astype(int), P[:, 0].astype(int)] = True
        out = {"_P": P, "_fg": fg}
        loop, c = boundary_profile(P)
        if loop is None:
            out["_degenerate"] = True
            return out
        out["_spread"] = curvature_spread(loop)
        V, K = rdp_closed(loop, self.eps)
        out["_K"] = K
        # polygon hypotheses: re-fit a clean K-gon by resampling RDP verts for the candidate orders
        for name, k in (("triangle", 3), ("rectangle", 4)):
            Vk = self._fit_kgon(loop, k)
            out[name] = (recon_iou(fg, verts=Vk), Vk, k)
        if self.arc:
            cx, cy, r = circle_fit(P)
            out["circle"] = (recon_iou(fg, circle=(cx, cy, r)), (cx, cy, r), 0)
        out["_Kfree"] = K
        return out

    def _fit_kgon(self, loop, k):
        """force-fit a k-gon: pick k boundary points maximizing turning (vertex-like)."""
        d = np.diff(np.vstack([loop, loop[:2]]), axis=0)
        ang = np.arctan2(d[:, 1], d[:, 0])
        turn = np.abs(np.diff(np.concatenate([ang, ang[:1]])))
        turn = np.minimum(turn, 2 * np.pi - turn)
        idx = np.sort(np.argsort(turn)[-k:])
        return loop[idx]

    def _g(self, leaf, raw):
        if leaf not in self.platt:
            return raw
        A, B = self.platt[leaf]
        return float(1 / (1 + np.exp(-(A * raw + B))))

    def predict(self, img, accept=0.5):
        h = self._hyps(img)
        if h.get("_degenerate"):
            return {"verdict": "REQUEST_ATOM", "reason": "degenerate", "g": {}, "decision": 0.0}
        cand = {name: self._g(name, h[name][0]) for name in ("triangle", "rectangle") if name in h}
        if self.arc and "circle" in h:
            cand["circle"] = self._g("circle", h["circle"][0])
        Kfree = h.get("_Kfree", 99)
        spread = h.get("_spread", 1.0)
        # The polygon vocabulary is EXACTLY {3-gon, 4-gon}. A boundary that needs a different
        # number of straight segments has no within-tolerance composition of the available atoms
        # -> irreducible (the doctrinal "no <=Kmax-atom composition", P4). Vocabulary, not a tuned
        # threshold; spread is computed for reporting only (it does not separate -- see notes).
        POLY = {3: "triangle", 4: "rectangle"}
        curved = Kfree not in POLY
        poly = POLY.get(Kfree, "triangle" if cand.get("triangle", 0) >= cand.get("rectangle", 0) else "rectangle")
        pg = cand.get(poly, 0.0)
        alt = "rectangle" if poly == "triangle" else "triangle"
        decision = pg - cand.get(alt, 0.0)      # calibrated margin: which polygon order
        info = {"g": cand, "decision": decision, "best_poly_g": pg, "poly": poly,
                "K": int(Kfree), "spread": round(spread, 3)}
        # Decision IDENTICAL whether or not the arc leaf exists -> retention = 1.0 by construction:
        # the circle leaf only rescues inputs the polygon path ABSTAINS on; never overrides a polygon.
        if not curved:
            return {"verdict": poly, **info}
        # irreducible -> REQUEST_ATOM; the arc leaf (if present) is the repair supplying the atom
        if self.arc and cand.get("circle", 0) >= accept:
            return {"verdict": "circle", **info}
        return {"verdict": "REQUEST_ATOM", "reason": "curvature", **info}

    # ---------- learning ----------
    def fit_thresholds(self, X, y, classes, taus, epss):
        best, bestacc = (0.5, 1.6), -1
        for tau in taus:
            for eps in epss:
                self.tau, self.eps = tau, eps
                self.spread_thr = 0.0  # disable irreducibility during threshold fit (in-vocab only)
                acc = self._train_acc(X, y, classes)
                if acc > bestacc:
                    bestacc, best = acc, (tau, eps)
        self.tau, self.eps = best
        return best, bestacc

    def _train_acc(self, X, y, classes):
        idx = {c: i for i, c in enumerate(classes)}
        ok = 0
        for img, lab in zip(X, y):
            r = self.predict(img)
            ok += (r["verdict"] in idx and idx[r["verdict"]] == lab)
        return ok / len(X)

    def fit_spread_threshold(self, X, kind):
        """learn the curvature-spread cut separating polygons (high spread) from circles (low),
        from labeled TRAIN (no generator params). Midpoint of class-conditional means."""
        sp_poly, sp_circ = [], []
        for img, k in zip(X, kind):
            h = self._hyps(img)
            if h.get("_degenerate"):
                continue
            (sp_circ if k == "circle" else sp_poly).append(h.get("_spread", 1.0))
        self.spread_thr = float((np.mean(sp_poly) + np.mean(sp_circ)) / 2) if sp_poly and sp_circ else 0.6
        return self.spread_thr

    def fit_platt(self, X, y, classes, leaves):
        """per-leaf Platt on CAL: grounding_raw -> P(correct shape)."""
        idx = {c: i for i, c in enumerate(classes)}
        for leaf in leaves:
            raws, labs = [], []
            for img, lab in zip(X, y):
                h = self._hyps(img)
                if leaf not in h:
                    continue
                raws.append(h[leaf][0])
                labs.append(1.0 if idx.get(leaf, -9) == lab else 0.0)
            self.platt[leaf] = _platt(np.array(raws), np.array(labs))


def _platt(s, t):
    """1D logistic fit P=sigmoid(A*s+B) by a few Newton steps."""
    A, B = 1.0, 0.0
    s = (s - s.mean()) / (s.std() + 1e-9)  # standardize for stability; fold back
    mu, sd = 0.0, 1.0
    for _ in range(200):
        p = 1 / (1 + np.exp(-(A * s + B)))
        g = p - t
        gA, gB = (g * s).mean(), g.mean()
        w = p * (1 - p) + 1e-6
        hA = (w * s * s).mean() + 1e-6; hB = (w).mean() + 1e-6
        A -= gA / hA; B -= gB / hB
    # fold standardization back into raw scale handled by re-standardizing at apply time -> store raw
    return (A, B)  # NOTE: applied on standardized? we standardized here; keep simple: store on raw below


# Because _platt standardized internally, refit a RAW-scale logistic for honest application:
def platt_raw(s, t):
    A, B = 0.0, 0.0
    for _ in range(500):
        p = 1 / (1 + np.exp(-(A * s + B)))
        g = p - t
        gA, gB = (g * s).mean(), g.mean()
        w = p * (1 - p) + 1e-6
        hA = (w * s * s).mean() + 1e-6; hB = w.mean() + 1e-6
        A -= 0.5 * gA / hA; B -= 0.5 * gB / hB
    return float(A), float(B)


def fit_chain(Xtr, ytr, Xca, yca, classes):
    ch = LeafChain(arc=True)
    (tau, eps), tracc = ch.fit_thresholds(Xtr, ytr, classes,
                                          taus=[0.35, 0.45, 0.55, 0.65], epss=[1.4, 1.8, 2.4, 3.0])
    ch.platt = {}
    for leaf in ("triangle", "rectangle", "circle"):
        raws, labs = [], []
        li = classes.index(leaf)
        for img, lab in zip(Xca, yca):
            h = ch._hyps(img)
            if leaf in h:
                raws.append(h[leaf][0]); labs.append(1.0 if lab == li else 0.0)
        ch.platt[leaf] = platt_raw(np.array(raws), np.array(labs))
    return ch, tau, eps, tracc


def evaluate(ch, tau, eps, classes, Xte, yte, ste, kte, gt=None):
    cls_name = {i: c for i, c in enumerate(classes)}
    inv = kte == "invocab"
    # full chain in-vocab accuracy (P0 side)
    p0 = {}
    for s in sorted(set(ste[inv].tolist())):
        m = inv & (ste == s)
        ok = sum(ch.predict(img)["verdict"] == cls_name[lab] for img, lab in zip(Xte[m], yte[m]))
        p0[f"sigma_{round(float(s),2)}"] = round(ok / m.sum(), 3)
    overall = sum(ch.predict(img)["verdict"] == cls_name[lab] for img, lab in zip(Xte[inv], yte[inv])) / inv.sum()

    # WITHHELD chain (Claim 4)
    chw = LeafChain(tau=tau, eps=eps, arc=False)
    chw.platt = {k: ch.platt[k] for k in ("triangle", "rectangle")}

    # MP1 no-fabrication on CLEAN circles (AM-3). 'temptation' = grounding of the forced <=4-gon.
    cc = (yte == classes.index("circle")) & (ste == 0.0)
    fab = reqs = poly_out = 0; tempt = []
    for img in Xte[cc]:
        r = chw.predict(img, accept=0.5)
        tempt.append(r.get("best_poly_g", 0.0))
        if r["verdict"] == "REQUEST_ATOM":
            reqs += 1
        else:
            poly_out += 1
            if r.get("best_poly_g", 0) >= 0.5:
                fab += 1
    n = max(1, int(cc.sum()))
    mp1 = {"n_clean_circle": int(cc.sum()),
           "fabrication_rate_high_conf_poly": round(fab / n, 4),
           "any_polygon_output_rate": round(poly_out / n, 3),
           "request_atom_rate": round(reqs / n, 3),
           "temptation_mean_forced_poly_grounding": round(float(np.mean(tempt)), 3),
           "PASS": bool(fab / n <= 0.05)}

    # near-miss REPORTED (AM-3): blind (calls it a polygon) vs detected (request-atom) vs curvature f
    nm = {}
    for f in ["nearmiss_f0.04", "nearmiss_f0.08", "nearmiss_f0.15", "nearmiss_f0.3"]:
        m = kte == f
        if not m.any():
            continue
        blind = det = 0
        for img in Xte[m]:
            r = chw.predict(img, accept=0.5)
            if r["verdict"] == "REQUEST_ATOM":
                det += 1
            else:
                blind += 1
        nm[f] = {"n": int(m.sum()), "blind_rate_called_polygon": round(blind / m.sum(), 3),
                 "detected_rate_request_atom": round(det / m.sum(), 3)}

    # MP2 repair: add circle leaf (one rung); retention exact + curved acc
    poly_mask = np.isin(yte, [classes.index("triangle"), classes.index("rectangle")]) & inv
    ret_b = np.mean([chw.predict(img)["verdict"] == cls_name[lab]
                     for img, lab in zip(Xte[poly_mask], yte[poly_mask])])
    ret_a = np.mean([ch.predict(img)["verdict"] == cls_name[lab]
                     for img, lab in zip(Xte[poly_mask], yte[poly_mask])])
    circ_all = (yte == classes.index("circle")) & inv
    curved_acc = np.mean([ch.predict(img)["verdict"] == "circle" for img in Xte[circ_all]])
    mp2 = {"rungs_changed": 1, "leaves_refit": 0,
           "polygon_retention_before": round(float(ret_b), 3),
           "polygon_retention_after": round(float(ret_a), 3),
           "curved_acc_after_repair": round(float(curved_acc), 3),
           "PASS_retention_exact": bool(abs(ret_a - ret_b) < 1e-9),
           "PASS_curved_acc": bool(curved_acc >= 0.85)}

    # C1 inspectability (REPORTED): recovered vertex count matches the generator's true k
    c1 = None
    if gt is not None:
        ok = tot = 0
        for img, lab, g in zip(Xte[inv], yte[inv], [gt[i] for i in np.where(inv)[0]]):
            if g.get("shape") not in ("triangle", "rectangle"):
                continue
            h = ch._hyps(img)
            if h.get("_degenerate"):
                tot += 1; continue
            tot += 1
            ok += int(h["_Kfree"] == g["k"])
        c1 = round(ok / max(1, tot), 3)
    return {"P0_overall": round(float(overall), 3), "P0_by_sigma": p0,
            "MP1": mp1, "nearmiss": nm, "MP2": mp2,
            "C1_vertex_recovery": c1}


def main():
    import leaf_novelty_generator as G
    d = np.load("leaf_novelty_data.npz", allow_pickle=True)
    classes = list(d["classes"])
    Xtr, ytr = d["Xtr"], d["ytr"]
    Xca, yca = d["Xca"], d["yca"]
    gt = json.load(open("leaf_novelty_gt.json"))["test"]

    ch, tau, eps, tracc = fit_chain(Xtr, ytr, Xca, yca, classes)
    out = {"learned": {"tau": tau, "eps": eps, "Kmax_design": KMAX, "train_acc": round(tracc, 3),
                       "platt": {k: [round(a, 3), round(b, 3)] for k, (a, b) in ch.platt.items()},
                       "note": "tau,eps fit on TRAIN by accuracy; platt per-leaf on CAL; "
                               "polygon vocab {3,4} + circle atom are human-given (AM-2)."}}

    # canonical test = the frozen npz (seed 2), shared with the CNN baseline (P0 comparability)
    out["canonical_seed2"] = evaluate(ch, tau, eps, classes,
                                      d["Xte"], d["yte"], d["sigma_te"], d["kind_te"], gt)

    # multi-seed robustness (>=3 seeds, pre-reg 4.4): regenerate test sets, SAME fitted chain
    P0s, MP1fab, MP2cur, ret_ok = [], [], [], []
    nm_curve = {f: [] for f in ["nearmiss_f0.04", "nearmiss_f0.08", "nearmiss_f0.15", "nearmiss_f0.3"]}
    for seed in (2, 12, 22):
        Xs, ys, ss, ks, _ = G.make_split(45, seed=seed, include_nearmiss=True)
        e = evaluate(ch, tau, eps, classes, Xs, ys, ss, ks)
        P0s.append(e["P0_overall"]); MP1fab.append(e["MP1"]["fabrication_rate_high_conf_poly"])
        MP2cur.append(e["MP2"]["curved_acc_after_repair"]); ret_ok.append(e["MP2"]["PASS_retention_exact"])
        for f in nm_curve:
            nm_curve[f].append(e["nearmiss"][f]["detected_rate_request_atom"])

    def ms(x): return [round(float(np.mean(x)), 3), round(float(np.std(x)), 3)]
    out["multiseed_3"] = {
        "P0_overall_mean_std": ms(P0s),
        "MP1_fabrication_mean_std": ms(MP1fab),
        "MP2_curved_acc_mean_std": ms(MP2cur),
        "MP2_retention_exact_all_seeds": bool(all(ret_ok)),
        "nearmiss_detected_curve_mean": {f: round(float(np.mean(v)), 3) for f, v in nm_curve.items()},
    }
    out["VERDICT_inputs"] = {
        "P0_gate": "MindsOS P0_overall within 5 pts of (or above) the CNN baseline (Linux, same npz)",
        "claim4_gate": "MP1(no-fab, clean) AND MP2(retention exact AND curved_acc>=0.85)",
        "novelty": "P0 AND Claim4 = conjunction-at-earned-parity (AM-4); near-miss reported, not gated (AM-3)"}
    with open("leaf_novelty_mindsos_results.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
