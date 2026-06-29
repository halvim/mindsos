#!/usr/bin/env python3
"""
Leaf-Learning NOVELTY — STRONG opaque-ML baseline (torch). Spec: PERCEPTION_LEAF_NOVELTY_PREREG.md
(v2 + AM-2/3/4). Runs on the USER'S LINUX MACHINE (torch absent / no data egress in the authoring
sandbox -- same pattern as discovery_test.py). Consumes the IDENTICAL frozen dataset
`leaf_novelty_data.npz` the MindsOS chain used, so P0 parity is comparable (PB-G).

This is the fair, NON-strawman baseline the pre-reg requires:
  - small CNN (data -> class), deep ENSEMBLE (M models) for a real OOD/abstain head;
  - OOD score = ensemble max-softmax + predictive entropy + disagreement (the pre-reg's
    "deep-ensemble disagreement / max-softmax"); the OOD head IS ALLOWED to flag circles (high
    OOD AUROC is fine -- NOT the differentiator, §3).
  - few-shot REPAIR path in TWO modes so the ML-advocate's strongest variant is already measured:
      (R-full)  full fine-tune on k circles  -> expect catastrophic forgetting (retention << 1)
      (R-head)  FROZEN backbone + new 3-way head on k circles  -> the auditor's best case;
                report its retention honestly (usually < 1 and/or backbone-limited).

Frozen contrasts emitted (compared to leaf_novelty_mindsos_results.json if present):
  P0          : CNN 3-class in-vocab accuracy across the noise sweep  (parity gate vs MindsOS)
  S-pos       : positive control -- CNN P0 must be >= MindsOS - 5 pts or the contest is VOID
  OODauroc    : ensemble OOD AUROC(in-vocab vs circle)  (reported; expected high)
  fabricate   : high-confidence wrong-class rate on circles at the 95%-coverage operating point
  repair_cost : {labeled_circles k, params_changed, polygon_retention} for R-full and R-head
  structured  : the gap signal is a SCALAR OOD score / residual heatmap -- cannot NAME 'curvature'
  nearmiss    : OOD score vs curvature f (the continuous analog of MindsOS's request-atom curve)

Run on Linux/Colab (CPU fine, ~3-8 min):  python leaf_novelty_baseline.py
Reproducible (fixed seeds; >=3 seeds). Written WITHOUT execution -- if anything errors the fix is
almost certainly local; report the traceback.
"""
import json, os, numpy as np, torch, torch.nn as nn, torch.nn.functional as F

DEV = "cuda" if torch.cuda.is_available() else "cpu"
SEEDS = [0, 1, 2]
M_ENS = 3                       # deep-ensemble size (the OOD head)
EPOCHS, BATCH, LR = 35, 128, 2e-3
DROP = 0.2
KSHOT = [5, 20, 100]           # few-shot repair budgets (labeled circles)
TRAIN_N_PER_CELL = 220         # AM-6/AM-7: large CNN train set (test unchanged -> P0 comparable)
MINDSOS_RESULTS = "leaf_novelty_mindsos_results.json"


# ----------------------------- model -----------------------------
class CNN(nn.Module):
    def __init__(self, nc):
        super().__init__()
        self.c = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.Conv2d(32, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2),  # 32
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.Conv2d(64, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),  # 16
        )
        self.drop = nn.Dropout(DROP)
        self.feat = nn.Linear(64 * 16 * 16, 128)
        self.fbn = nn.BatchNorm1d(128)
        self.head = nn.Linear(128, nc)

    def features(self, x):
        h = self.c(x).flatten(1)
        return F.relu(self.fbn(self.feat(self.drop(h))))

    def forward(self, x):
        return self.head(self.drop(self.features(x)))


def _t(x):
    return torch.tensor(x, dtype=torch.float32, device=DEV).unsqueeze(1)


def train_model(X, y, nc, seed, epochs=EPOCHS, init=None, freeze_backbone=False):
    torch.manual_seed(seed); np.random.seed(seed)
    m = CNN(nc).to(DEV)
    if init is not None:
        sd = m.state_dict()
        for k, v in init.items():
            if k in sd and sd[k].shape == v.shape:
                sd[k] = v.clone()
        m.load_state_dict(sd)
    m.train()
    if freeze_backbone:
        for p in m.c.parameters():
            p.requires_grad = False
        for p in m.feat.parameters():
            p.requires_grad = False
        m.c.eval(); m.feat.eval(); m.fbn.eval()
    Xt, yt = _t(X), torch.tensor(y, device=DEV)
    opt = torch.optim.Adam([p for p in m.parameters() if p.requires_grad], lr=LR)
    sched = torch.optim.lr_scheduler.StepLR(opt, step_size=max(1, int(epochs * 0.4)), gamma=0.3)
    n = len(X)
    for ep in range(epochs):
        idx = np.random.permutation(n)
        for s in range(0, n, BATCH):
            b = idx[s:s + BATCH]
            opt.zero_grad()
            loss = F.cross_entropy(m(Xt[b]), yt[b])
            loss.backward(); opt.step()
        sched.step()
    return m


def repair_row_frozen(base, Xpoly, ypoly, Xcirc_k, Xte_poly, yte_poly, Xte_circ, n_poly_cls, seed):
    """ML-ADVOCATE'S BEST repair (AM-5): FROZEN backbone + FROZEN warm-started polygon head rows;
    train ONLY a new circle logit (one linear on frozen features). Polygon-vs-polygon logits are
    byte-identical to the pre-repair model -> the ONLY way retention drops is the new circle logit
    out-firing a polygon logit on a polygon input. This is the strongest case against MindsOS's
    exact-1.0 retention; if even this cannot reach 1.0, the repair-cost discriminator survives."""
    torch.manual_seed(seed)
    base.eval()
    with torch.no_grad():
        Fp = base.features(_t(Xpoly)).detach()           # frozen polygon features (for negatives)
        Fc = base.features(_t(Xcirc_k)).detach()          # frozen circle features (k positives)
        Lp_te = base.head(base.features(_t(Xte_poly))).detach()      # frozen 2-way polygon logits (test)
        Fte_p = base.features(_t(Xte_poly)).detach()
        Lc_te_poly = base.head(base.features(_t(Xte_circ))).detach()
        Fte_c = base.features(_t(Xte_circ)).detach()
    w = nn.Linear(Fp.shape[1], 1).to(DEV)                  # the ONLY trainable repair params
    opt = torch.optim.Adam(w.parameters(), lr=5e-2)
    Xf = torch.cat([Fp, Fc]); yf = torch.cat([torch.zeros(len(Fp)), torch.ones(len(Fc))]).to(DEV)
    for _ in range(300):
        opt.zero_grad()
        loss = F.binary_cross_entropy_with_logits(w(Xf).squeeze(1), yf)
        loss.backward(); opt.step()
    with torch.no_grad():
        # 3-way logits = [frozen polygon logits | new circle logit]
        L_polytest = torch.cat([Lp_te, w(Fte_p)], 1)
        L_circtest = torch.cat([Lc_te_poly, w(Fte_c)], 1)
    ret = float((L_polytest.argmax(1).cpu().numpy() == yte_poly).mean())     # polygon retention
    cur = float((L_circtest.argmax(1).cpu().numpy() == n_poly_cls).mean())   # circle = class index n_poly_cls
    return {"retention": ret, "curved_acc": cur, "params_changed": "one_circle_logit_only"}


@torch.no_grad()
def ens_probs(models, X):
    """ensemble mean softmax + disagreement (std of class-1/2 probs)."""
    Xt = _t(X)
    ps = []
    for m in models:
        m.eval()
        ps.append(F.softmax(m(Xt), dim=1).cpu().numpy())
    P = np.stack(ps)                       # M x N x C
    mean = P.mean(0)
    disag = P.std(0).mean(1)               # mean across classes of cross-model std
    return mean, disag


@torch.no_grad()
def feats(model, X):
    model.eval()
    return model.features(_t(X)).cpu().numpy()


def maha_auroc(model, Xtr_poly, ytr_poly, Xte_poly, Xte_circ):
    """Mahalanobis OOD (the fair strong signal): class-conditional means + shared covariance on
    penultimate features; score = min distance to any in-vocab class (high = OOD)."""
    Ftr = feats(model, Xtr_poly)
    cs = np.unique(ytr_poly)
    means = {c: Ftr[ytr_poly == c].mean(0) for c in cs}
    cen = np.vstack([Ftr[ytr_poly == c] - means[c] for c in cs])
    cov = np.cov(cen.T) + 1e-3 * np.eye(Ftr.shape[1])
    inv = np.linalg.pinv(cov)

    def score(F):
        return np.min(np.stack([(((F - means[c]) @ inv) * (F - means[c])).sum(1) for c in cs], 1), 1)
    s_in = score(feats(model, Xte_poly)); s_out = score(feats(model, Xte_circ))
    return auroc(np.concatenate([s_in, s_out]),
                 np.concatenate([np.zeros(len(s_in)), np.ones(len(s_out))]))


def auroc(scores, labels):
    """labels: 1 = positive (OOD). rank-based AUROC."""
    order = np.argsort(scores)
    ranks = np.empty(len(scores)); ranks[order] = np.arange(1, len(scores) + 1)
    npos = labels.sum(); nneg = len(labels) - npos
    if npos == 0 or nneg == 0:
        return float("nan")
    return float((ranks[labels == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg))


def acc_by_sigma(models, X, y, sig, classes_idx):
    mean, _ = ens_probs(models, X)
    pred = mean.argmax(1)
    out = {}
    for s in sorted(set(sig.tolist())):
        m = sig == s
        out[f"sigma_{round(float(s),2)}"] = round(float((pred[m] == y[m]).mean()), 3)
    return out, float((pred == y).mean())


def main():
    import leaf_novelty_generator as G
    d = np.load("leaf_novelty_data.npz", allow_pickle=True)
    classes = list(d["classes"]); CI = {c: i for i, c in enumerate(classes)}
    # AM-6: large CNN train set (seed 7, disjoint from test seed 2); TEST stays the frozen npz
    Xtr, ytr, _stc, _ktc, _ = G.make_split(TRAIN_N_PER_CELL, seed=7, include_nearmiss=False)
    Xte, yte, ste, kte = d["Xte"], d["yte"], d["sigma_te"], d["kind_te"]
    inv = kte == "invocab"
    ci = CI["circle"]

    mind = json.load(open(MINDSOS_RESULTS)) if os.path.exists(MINDSOS_RESULTS) else None
    mind_p0 = mind["multiseed_3"]["P0_overall_mean_std"][0] if mind else None

    res = {"device": DEV, "ensemble_M": M_ENS, "seeds": SEEDS, "mindsos_P0_ref": mind_p0,
           "train_n": int(len(Xtr))}
    P0s, OODs, OODm, FABs = [], [], [], []
    rep_full = {k: [] for k in KSHOT}; rep_head = {k: [] for k in KSHOT}; rep_row = {k: [] for k in KSHOT}
    nm_ood = {f: [] for f in ["nearmiss_f0.04", "nearmiss_f0.08", "nearmiss_f0.15", "nearmiss_f0.3"]}

    for seed in SEEDS:
        # ---- P0 arm: full 3-class ensemble on the SAME npz ----
        ens3 = [train_model(Xtr, ytr, len(classes), seed * 10 + j) for j in range(M_ENS)]
        bys, overall = acc_by_sigma(ens3, Xte[inv], yte[inv], ste[inv], CI)
        P0s.append(overall)
        if seed == SEEDS[0]:
            res["P0_by_sigma_seed0"] = bys

        # ---- Claim-4 arm: WITHHELD circle (train on triangle+rectangle only) ----
        poly = ytr != ci
        Xp, yp = Xtr[poly], ytr[poly]                 # labels 0/1 are triangle/rectangle (ci excluded)
        # remap labels to 0..1 contiguous
        lut = {lab: i for i, lab in enumerate(sorted(set(yp.tolist())))}
        yp2 = np.array([lut[v] for v in yp])
        ens2 = [train_model(Xp, yp2, len(lut), seed * 10 + 100 + j) for j in range(M_ENS)]

        # OOD: in-vocab polygons (test) vs circles (test). score = 1 - maxsoftmax (+ entropy/disag reported)
        polyte = inv & (yte != ci)
        circte = inv & (yte == ci)
        mean_p, dis_p = ens_probs(ens2, Xte[polyte])
        mean_c, dis_c = ens_probs(ens2, Xte[circte])
        s_in = 1 - mean_p.max(1); s_out = 1 - mean_c.max(1)
        scores = np.concatenate([s_in, s_out]); labs = np.concatenate([np.zeros(len(s_in)), np.ones(len(s_out))])
        OODs.append(auroc(scores, labs))
        OODm.append(maha_auroc(ens2[0], Xp, yp2, Xte[polyte], Xte[circte]))

        # fabrication: operating point = 95% coverage on in-vocab (threshold on maxsoftmax).
        thr = np.quantile(mean_p.max(1), 0.05)         # keep 95% of in-vocab
        conf_circle = mean_c.max(1) >= thr             # circles the model does NOT abstain on
        FABs.append(float(conf_circle.mean()))         # high-confidence (non-abstained) circle calls

        # near-miss OOD curve (continuous analog of MindsOS request-atom curve)
        for f in nm_ood:
            mte = kte == f
            if mte.any():
                mc, _ = ens_probs(ens2, Xte[mte])
                nm_ood[f].append(float((1 - mc.max(1)).mean()))

        # ---- repair: add circle class ----
        cal_circ_idx = np.where(ytr == ci)[0]
        for k in KSHOT:
            kidx = cal_circ_idx[:k]
            # 3-class fine-tune set = k circles (new label) + all polygons (labels 0,1) for R-head
            X3 = np.concatenate([Xp, Xtr[kidx]]); y3 = np.concatenate([yp2, np.full(k, len(lut))])
            init = {kk: vv.detach().clone() for kk, vv in ens2[0].state_dict().items()}

            # R-full: full fine-tune (few epochs) on circles ONLY -> catastrophic forgetting probe
            mfull = train_model(Xtr[kidx], np.full(k, len(lut)), len(lut) + 1, seed,
                                epochs=12, init=init, freeze_backbone=False)
            mean_full, _ = ens_probs([mfull], Xte[polyte])
            ret_full = float((mean_full.argmax(1) == np.array([lut[v] for v in yte[polyte]])).mean())
            cur_full = float((ens_probs([mfull], Xte[circte])[0].argmax(1) == len(lut)).mean())
            rep_full[k].append({"retention": ret_full, "curved_acc": cur_full, "params_changed": "all"})

            # R-head: FROZEN backbone + new 3-way head on k circles + polygon features (auditor's best)
            mhead = train_model(X3, y3, len(lut) + 1, seed, epochs=20, init=init, freeze_backbone=True)
            mean_h, _ = ens_probs([mhead], Xte[polyte])
            ret_head = float((mean_h.argmax(1) == np.array([lut[v] for v in yte[polyte]])).mean())
            cur_head = float((ens_probs([mhead], Xte[circte])[0].argmax(1) == len(lut)).mean())
            rep_head[k].append({"retention": ret_head, "curved_acc": cur_head, "params_changed": "head_only"})

            # R-row (AM-5): ML-advocate's BEST -- frozen warm-started polygon rows + one new circle logit
            yte_poly = np.array([lut[v] for v in yte[polyte]])
            rep_row[k].append(repair_row_frozen(ens2[0], Xp, yp2, Xtr[kidx],
                                                Xte[polyte], yte_poly, Xte[circte], len(lut), seed))

    def ms(x): return [round(float(np.mean(x)), 3), round(float(np.std(x)), 3)]

    res["P0_overall_mean_std"] = ms(P0s)
    res["S_pos_positive_control"] = {
        "cnn_P0": ms(P0s)[0], "mindsos_P0": mind_p0,
        "cnn_competitive(>=mindsos-5pts)": (mind_p0 is None) or (ms(P0s)[0] >= mind_p0 - 0.05),
        "P0_parity(|cnn-mindsos|<=5pts)": (mind_p0 is None) or (abs(ms(P0s)[0] - mind_p0) <= 0.05)}
    res["OOD_auroc_maxsoftmax_mean_std"] = ms(OODs)
    res["OOD_auroc_mahalanobis_mean_std"] = ms(OODm)
    res["fabrication_rate_nonabstain_circle_mean_std"] = ms(FABs)
    res["nearmiss_OOD_score_curve"] = {f: round(float(np.mean(v)), 3) for f, v in nm_ood.items() if v}

    def rep_ms(rep):
        return {f"k{k}": {"retention_mean_std": ms([r["retention"] for r in rep[k]]),
                          "curved_acc_mean_std": ms([r["curved_acc"] for r in rep[k]]),
                          "params_changed": rep[k][0]["params_changed"]} for k in KSHOT}
    res["repair_R_full_finetune"] = rep_ms(rep_full)
    res["repair_R_head_frozen_backbone"] = rep_ms(rep_head)
    res["repair_R_row_frozen_warmstart_BEST"] = rep_ms(rep_row)   # AM-5: the ML-advocate's strongest

    res["structured_gap_REPORTED"] = ("baseline gap signal = scalar OOD score / per-pixel residual; "
                                      "cannot NAME the missing primitive ('curvature') as MindsOS's "
                                      "REQUEST_ATOM does. AE/residual contest deferred (PB-K/AM-4).")
    res["CONTRAST_vs_mindsos"] = {
        "P0": "parity gate: see S_pos_positive_control",
        "claim4_repair": "DECISIVE comparison = repair_R_row_frozen_warmstart_BEST.retention vs "
                         "MindsOS exact 1.0. If even the row-frozen warm-started head cannot reach "
                         "1.0, the repair-cost discriminator survives; if it reaches exactly 1.0, the "
                         "novelty narrows to gap-naming (named atom vs OOD scalar), undefended in v1 (AM-5).",
        "claim4_nofab": "OOD AUROC high is allowed (not the differentiator); fabrication_rate is the "
                        "honest-failure number; the NAMED-gap is the qualitative differentiator",
        "novelty": "conjunction-at-parity (AM-4): only stands if S_pos passes AND repair retention gap is real"}
    with open("leaf_novelty_baseline_results.json", "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
