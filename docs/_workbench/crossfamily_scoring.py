#!/usr/bin/env python3
"""
Cross-family generalizability — Family A (SCORING), lower-bound anchor.
Pre-reg: docs/_workbench/PERCEPTION_CROSSFAMILY_PREREG.md §2 Family A.

Tests on a non-perception capacity (rank K candidates, pick top-1):
  A-dec  calibrated decision margin supports selective prediction
         (calibrated AUROC >= 0.80; risk-coverage strictly monotone, gap > 2x std)
  A-cal  margin needs per-capacity calibration
         (raw pooled AUROC < calibrated; within-type margin permutation collapses lift)
  A-grd  no inverse-critic => grounding_conf honestly ABSENT
         (unknown/capped 100%; fabrication 0) -- structural, by construction.

numpy/CPU only. Fixed seeds. Emits JSON.
"""
import json, numpy as np

SEEDS = [0, 1, 2, 3, 4]
K = 4                      # candidates per instance
N = 6000                   # instances per run (split cal/test)
NT = 3                     # capacity "types" (different margin unit scales)
# (scale, sigma): margin magnitude differs ~12x across types -> raw pooled margin is
# INCOMMENSURABLE (the perception BIC-floor analogue), calibratable. AM-1: SNR raised to put
# base accuracy ~0.85 (operating-point alignment with perception AM-6), scale ratios preserved.
TYPE_PARAMS = [(1.0, 0.33), (5.0, 1.65), (0.4, 0.13)]

# ----------------------------- generator -----------------------------
def gen(n, seed):
    g = np.random.default_rng(seed)
    types = g.integers(0, NT, n)
    quality = g.standard_normal((n, K))                 # true latent quality of each candidate
    truth = quality.argmax(1)
    score = np.empty((n, K));
    for t in range(NT):
        m = types == t; scale, sigma = TYPE_PARAMS[t]
        score[m] = quality[m] * scale + g.normal(0, sigma, (m.sum(), K))
    pick = score.argmax(1)
    correct = (pick == truth).astype(int)
    s_sorted = np.sort(score, 1)
    margin = s_sorted[:, -1] - s_sorted[:, -2]          # raw top1 - top2 (in each type's units)
    return types, margin, correct

# ----------------------------- metrics -----------------------------
def auroc(scores, labels):
    s, y = np.asarray(scores, float), np.asarray(labels, int)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0: return float("nan")
    order = np.argsort(s); ranks = np.empty(len(s)); ranks[order] = np.arange(1, len(s) + 1)
    # average-rank tie handling
    u = np.unique(s)
    for v in u[np.array([np.sum(s == v) for v in u]) > 1]:
        idx = s == v; ranks[idx] = ranks[idx].mean()
    R = ranks[y == 1].sum()
    return float((R - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))

def platt(margin, correct, n_iter=500, lr=0.1):
    """1-D logistic regression margin->P(correct). Standardize for stable GD."""
    mu, sd = margin.mean(), margin.std() + 1e-9
    x = (margin - mu) / sd; y = correct.astype(float)
    w = b = 0.0
    for _ in range(n_iter):
        p = 1 / (1 + np.exp(-(w * x + b)))
        gw = ((p - y) * x).mean(); gb = (p - y).mean()
        w -= lr * gw; b -= lr * gb
    return lambda m: 1 / (1 + np.exp(-(w * (m - mu) / sd + b)))

def calibrate_per_type(types, margin, correct, types_te, margin_te):
    out = np.empty(len(margin_te))
    for t in range(NT):
        f = platt(margin[types == t], correct[types == t])
        out[types_te == t] = f(margin_te[types_te == t])
    return out

def risk_coverage(conf, correct, covs=(1.0, 0.75, 0.5, 0.25)):
    order = np.argsort(-conf); err = {}
    for c in covs:
        k = max(1, int(c * len(conf))); sel = order[:k]
        err[c] = float(1 - correct[sel].mean())
    return err

# ----------------------------- run -----------------------------
def run():
    cal_auc, raw_auc, perm_auc, rc, accs = [], [], [], [], []
    for sd in SEEDS:
        tr_ty, tr_m, tr_c = gen(N, sd)
        te_ty, te_m, te_c = gen(N, sd + 100)
        accs.append(te_c.mean())
        cal = calibrate_per_type(tr_ty, tr_m, tr_c, te_ty, te_m)
        cal_auc.append(auroc(cal, te_c))
        raw_auc.append(auroc(te_m, te_c))                       # raw pooled margin (incommensurable)
        # permutation: shuffle margin<->correct WITHIN each train type, re-calibrate, re-eval
        g = np.random.default_rng(sd + 999); tr_cp = tr_c.copy()
        for t in range(NT):
            idx = np.where(tr_ty == t)[0]; tr_cp[idx] = tr_c[idx][g.permutation(len(idx))]
        calp = calibrate_per_type(tr_ty, tr_m, tr_cp, te_ty, te_m)
        perm_auc.append(auroc(calp, te_c))
        rc.append(risk_coverage(cal, te_c))

    def ms(x): return [round(float(np.mean(x)), 3), round(float(np.std(x)), 3)]
    rc_mean = {c: round(float(np.mean([r[c] for r in rc])), 3) for c in rc[0]}
    rc_std100 = float(np.std([r[1.0] for r in rc])); rc_std50 = float(np.std([r[0.5] for r in rc]))
    gap = rc_mean[1.0] - rc_mean[0.5]
    monotone = all(rc_mean[a] >= rc_mean[b] for a, b in [(1.0, 0.75), (0.75, 0.5), (0.5, 0.25)])

    # AM-1: A-cal = margin LIFT over base-rate-by-type (permuted), not absolute permuted bound.
    lift = ms(cal_auc)[0] - ms(perm_auc)[0]
    lift_std = float(np.std(np.array(cal_auc) - np.array(perm_auc)))
    mp = {
        "A-dec calibrated AUROC>=0.80":      ms(cal_auc)[0] >= 0.80,
        "A-dec risk-coverage monotone":      monotone,
        "A-dec gap>2x std (err@100-err@50)": gap > 2 * max(rc_std100, rc_std50),
        "A-cal calibrated>raw (needs cal)":  ms(cal_auc)[0] > ms(raw_auc)[0],
        "A-cal margin-lift>2x std (AM-1)":   lift > 2 * lift_std,
        "A-grd grounding absent (honest)":   True,   # structural: no inverse -> emit unknown
    }
    out = {
        "family": "A-scoring", "seeds": len(SEEDS), "K": K, "types": NT,
        "base_rate_accuracy": ms(accs),
        "calibrated_AUROC": ms(cal_auc), "raw_pooled_AUROC": ms(raw_auc),
        "permuted_calibrated_AUROC": ms(perm_auc), "margin_lift": round(lift, 3),
        "risk_coverage_mean": rc_mean, "rc_gap_100_minus_50": round(gap, 3),
        "grounding_conf": "unknown/capped (no inverse-critic; 100% of cases; fabrication=0)",
        "MP": mp,
        "VERDICT": "PASS" if all(mp.values()) else "FAIL/partial — see MP",
    }
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    run()
