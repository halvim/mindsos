#!/usr/bin/env python3
"""
Cross-family generalizability — Family B (RETRIEVAL), the decisive grounding test.
Pre-reg: docs/_workbench/PERCEPTION_CROSSFAMILY_PREREG.md §2 Family B.

Capacity: given a query, retrieve the best-matching item from a store, over SYMBOLIC keys
(discrete attribute vectors over a finite vocab — NOT perceptual embeddings, the B-fair rule).

  B-dec   similarity margin (sim1 - sim2) supports selective prediction
          (per-capacity calibrated AUROC >= 0.80; risk-coverage monotone, gap > 2x std)
  B-grd   the "regenerate the query from the retrieved item" inverse-critic flags
          ungroundable retrievals:
            far-OOD grounding AUROC >= 0.85  AND  AUROC increases monotonically with
            novelty distance (the curve is present, not a single number; P15)
  B-fair  grounding is not perception in disguise:
            symbolic keys (discrete); grounding(correct item) >> grounding(random item);
            shuffled-store -> decision calibration collapses to chance.

Inverse-critic (grounding analogue, anchored at the symbol vocab = known atoms):
  grounding_conf(query, retrieved) = 1 - (in-vocab mismatches / D), capped to 0 if the query
  contains any OUT-OF-VOCAB symbol (the generative model "item + <=c in-vocab subs" cannot
  produce it -> unexplainable). This is analysis-by-synthesis for symbols.

numpy/CPU only. Fixed seeds. Emits JSON. (Audit carry-forward from Family A: permutation
control averaged over 50 shuffles.)
"""
import json, numpy as np

SEEDS = [0, 1, 2, 3, 4]
V = 5                       # in-vocab symbol count (0..V-1); OOV symbols are V..V+2
M = 200                    # store size per type
D_TYPES = [6, 12, 20]      # 3 capacity "types": key length -> different margin scales (calib)
NQ = 2000                  # queries per (type, kind)
TARGET_ACC = 0.85          # operating-point alignment (AM-1 precedent)

# ----------------------------- core ops -----------------------------
def make_store(D, M, g):
    return g.integers(0, V, (M, D))

def sims(q, store):
    return (store == q).sum(1)            # symbolic Hamming similarity (OOV never matches)

def retrieve(q, store):
    s = sims(q, store); i = int(s.argmax())
    srt = np.sort(s)
    return i, float(srt[-1] - srt[-2])    # (index, raw margin)

def grounding(q, item, D):
    if np.any(q >= V):                    # any OOV symbol -> unexplainable
        return 0.0
    return 1.0 - (item != q).sum() / D    # 1 - in-vocab mismatch fraction

def corrupt(item, c, g):                  # c in-vocab substitutions
    q = item.copy()
    pos = g.choice(len(q), c, replace=False)
    for p in pos: q[p] = g.integers(0, V)
    return q

# ----------------------------- query generators -----------------------------
def in_store_queries(store, c, n, g):
    src = g.integers(0, len(store), n)
    Q = np.array([corrupt(store[s], c, g) for s in src])
    return Q, src

def ood_invocab_queries(D, n, g):         # independent random in-vocab vectors (not from store)
    return g.integers(0, V, (n, D))

def ood_oov_queries(D, n, g):             # contain out-of-vocab symbols (far novelty)
    Q = g.integers(0, V, (n, D))
    for r in range(n):
        pos = g.choice(D, max(1, D // 4), replace=False)
        Q[r, pos] = g.integers(V, V + 3, len(pos))
    return Q

def tune_c(store, D, g):                  # pick corruption to hit ~TARGET_ACC retrieval
    best = (1, 1.0)
    for c in range(1, D):
        Q, src = in_store_queries(store, c, 800, g)
        acc = np.mean([retrieve(q, store)[0] == s for q, s in zip(Q, src)])
        if abs(acc - TARGET_ACC) < abs(best[1] - TARGET_ACC): best = (c, acc)
        if acc < TARGET_ACC - 0.05: break
    return best[0]

# ----------------------------- metrics -----------------------------
def auroc(scores, labels):
    s, y = np.asarray(scores, float), np.asarray(labels, int)
    pos, neg = (y == 1).sum(), (y == 0).sum()
    if pos == 0 or neg == 0: return float("nan")
    order = np.argsort(s); ranks = np.empty(len(s)); ranks[order] = np.arange(1, len(s) + 1)
    for v in np.unique(s):
        idx = s == v
        if idx.sum() > 1: ranks[idx] = ranks[idx].mean()
    return float((ranks[y == 1].sum() - pos * (pos + 1) / 2) / (pos * neg))

def platt(margin, correct, n_iter=600, lr=0.1):
    mu, sd = margin.mean(), margin.std() + 1e-9
    x = (margin - mu) / sd; yv = correct.astype(float); w = b = 0.0
    for _ in range(n_iter):
        p = 1 / (1 + np.exp(-(w * x + b)))
        w -= lr * ((p - yv) * x).mean(); b -= lr * (p - yv).mean()
    return lambda m: 1 / (1 + np.exp(-(w * (m - mu) / sd + b)))

def risk_coverage(conf, correct, covs=(1.0, 0.75, 0.5, 0.25)):
    order = np.argsort(-conf)
    return {c: float(1 - correct[order[:max(1, int(c * len(conf)))]].mean()) for c in covs}

# ----------------------------- run -----------------------------
def run():
    cal_auc, raw_auc, perm_auc, rc_list = [], [], [], []
    far_auc, curve_all, fair_corr, fair_rand, shuf_auc = [], [], [], [], []

    for sd in SEEDS:
        g = np.random.default_rng(sd)
        all_m, all_c, all_ty = [], [], []          # decision: margins, correct, type
        all_m_te, all_c_te, all_ty_te = [], [], []
        for ti, D in enumerate(D_TYPES):
            store = make_store(D, M, g)
            c_in = tune_c(store, D, g)
            # --- decision-axis data (calibration split = cal/test disjoint draws) ---
            for bucket, (mm, cc, tt) in [("cal", (all_m, all_c, all_ty)),
                                         ("test", (all_m_te, all_c_te, all_ty_te))]:
                gg = np.random.default_rng(sd * 17 + ti + (0 if bucket == "cal" else 5000))
                Q, src = in_store_queries(store, c_in, NQ, gg)
                for q, s in zip(Q, src):
                    idx, margin = retrieve(q, store)
                    mm.append(margin); cc.append(int(idx == s)); tt.append(ti)
            # --- grounding-axis data ---
            gg = np.random.default_rng(sd * 31 + ti + 9000)
            Qin, _ = in_store_queries(store, c_in, NQ, gg)
            g_in = np.array([grounding(q, store[retrieve(q, store)[0]], D) for q in Qin])
            Qoov = ood_oov_queries(D, NQ, gg)
            g_oov = np.array([grounding(q, store[retrieve(q, store)[0]], D) for q in Qoov])
            # far-OOD AUROC (in-store vs OOV)
            far_auc.append(auroc(np.r_[g_in, g_oov], np.r_[np.ones(len(g_in)), np.zeros(len(g_oov))]))
            # AM-2: novelty-distance curve via CONTROLLED corruption fraction (discrete symbolic
            # distances make quantile bins degenerate -> NaN). Each level = store item corrupted
            # at fraction f in-vocab (near f -> blind-spot regime; far f -> clean), then OOV.
            curve = []
            for f in (0.25, 0.45, 0.65, 0.85):
                Ql = np.array([corrupt(store[s], max(1, round(f * D)), gg)
                               for s in gg.integers(0, M, NQ)])
                gl = np.array([grounding(q, store[retrieve(q, store)[0]], D) for q in Ql])
                curve.append(auroc(np.r_[g_in, gl], np.r_[np.ones(len(g_in)), np.zeros(len(gl))]))
            curve.append(far_auc[-1])                  # OOV = farthest point
            curve_all.append(curve)
            # B-fair: grounding vs correct/nearest item >> vs random item
            rand_items = store[gg.integers(0, M, len(Qin))]
            fair_corr.append(g_in.mean())
            fair_rand.append(np.array([grounding(q, ri, D) for q, ri in zip(Qin, rand_items)]).mean())

        # decision calibration (per-type Platt, cal->test, disjoint)
        m, c, ty = map(np.array, (all_m, all_c, all_ty))
        mt, ct, tyt = map(np.array, (all_m_te, all_c_te, all_ty_te))
        cal = np.empty(len(mt))
        for ti in range(len(D_TYPES)):
            f = platt(m[ty == ti], c[ty == ti]); cal[tyt == ti] = f(mt[tyt == ti])
        cal_auc.append(auroc(cal, ct)); raw_auc.append(auroc(mt, ct))
        rc_list.append(risk_coverage(cal, ct))
        # permutation: avg 50 within-type shuffles (Family-A audit carry-forward)
        perms = []
        for k in range(50):
            gp = np.random.default_rng(sd * 7 + k); cp = c.copy()
            for ti in range(len(D_TYPES)):
                ix = np.where(ty == ti)[0]; cp[ix] = c[ix][gp.permutation(len(ix))]
            calp = np.empty(len(mt))
            for ti in range(len(D_TYPES)):
                f = platt(m[ty == ti], cp[ty == ti]); calp[tyt == ti] = f(mt[tyt == ti])
            perms.append(auroc(calp, ct))
        perm_auc.append(np.mean(perms))
        # shuffled-store decision control: break query<->store link -> margin uninformative
        gsh = np.random.default_rng(sd + 12321)
        D = D_TYPES[0]; store = make_store(D, M, gsh)
        Q, src = in_store_queries(store, tune_c(store, D, gsh), NQ, gsh)
        sh_m, sh_c = [], []
        for q, s in zip(Q, src):
            idx, margin = retrieve(q, gsh.permutation(store))   # retrieve against shuffled store
            sh_m.append(margin); sh_c.append(int(idx == s))
        f = platt(np.array(sh_m), np.array(sh_c))
        shuf_auc.append(auroc(f(np.array(sh_m)), np.array(sh_c)))

    def ms(x): return [round(float(np.mean(x)), 3), round(float(np.std(x)), 3)]
    rc_mean = {c: round(float(np.mean([r[c] for r in rc_list])), 3) for c in rc_list[0]}
    gap = rc_mean[1.0] - rc_mean[0.5]
    rc_gap_std = float(np.std([r[1.0] - r[0.5] for r in rc_list]))
    monotone_rc = all(rc_mean[a] >= rc_mean[b] for a, b in [(1.0, .75), (.75, .5), (.5, .25)])
    curve = np.nanmean(np.array(curve_all), 0).round(3).tolist()
    curve_monotone = all(curve[i] <= curve[i + 1] + 0.02 for i in range(len(curve) - 1))
    lift = ms(cal_auc)[0] - ms(perm_auc)[0]; lift_std = float(np.std(np.array(cal_auc) - np.array(perm_auc)))

    mp = {
        "B-dec calibrated AUROC>=0.80":   ms(cal_auc)[0] >= 0.80,
        "B-dec risk-coverage monotone":   monotone_rc,
        "B-dec gap>2x std":               gap > 2 * max(rc_gap_std, 1e-6),
        "B-dec calibrated>raw":           ms(cal_auc)[0] > ms(raw_auc)[0],
        "B-dec margin-lift>2x std":       lift > 2 * lift_std,
        "B-grd far-OOD AUROC>=0.85":      ms(far_auc)[0] >= 0.85,
        "B-grd novelty-distance curve monotone": curve_monotone,
        "B-fair grounding(correct)>>random": ms(fair_corr)[0] > ms(fair_rand)[0] + 0.15,
        "B-fair shuffled-store collapses": ms(shuf_auc)[0] < 0.60,
    }
    out = {
        "family": "B-retrieval", "seeds": len(SEEDS), "V": V, "store": M, "D_types": D_TYPES,
        "calibrated_AUROC": ms(cal_auc), "raw_pooled_AUROC": ms(raw_auc),
        "permuted_AUROC_avg50": ms(perm_auc), "margin_lift": round(lift, 3),
        "risk_coverage_mean": rc_mean,
        "grounding_far_OOD_AUROC": ms(far_auc),
        "grounding_novelty_curve[f.25,f.45,f.65,f.85,oov]": curve,
        "fair_grounding_correct": ms(fair_corr), "fair_grounding_random": ms(fair_rand),
        "fair_shuffled_store_AUROC": ms(shuf_auc),
        "MP": mp,
        "VERDICT": "PASS" if all(mp.values()) else "FAIL/partial — see MP",
    }
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    run()
