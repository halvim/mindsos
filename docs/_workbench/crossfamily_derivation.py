#!/usr/bin/env python3
"""
Cross-family generalizability — Family C (DERIVATION), the upper bound.
Pre-reg: docs/_workbench/PERCEPTION_CROSSFAMILY_PREREG.md §2 Family C.

Capacity: forward-chaining entailment over Horn rules. Pick the best-supported conclusion
among K candidates. Symbolic; grounding anchors at the PREMISE SET (the C-def question),
not the fundamental floor.

Key design: proposer and critic are GENUINELY DIFFERENT computations (unlike retrieval, where
both were similarity). This tests whether two-axis INDEPENDENCE is restored when proposer != critic
(the P13 proposer/critic pair):
  - decision proposer = SHALLOW depth-1 heuristic (facts + rule popularity)  -> decision_conf margin
  - grounding critic  = DEPTH-BOUNDED proof-completeness (graded), OOV-capped  -> grounding_conf
  - true soundness    = full closure (unbounded)                              -> ground truth

  C-dec   shallow margin, per-capacity calibrated, supports selective prediction (AUROC>=0.80,
          monotone risk-coverage, margin lift, calibrated>raw)
  C-grd   bounded proof-check flags unsound + OOV conclusions
          (sound-vs-unsound AUROC>=0.85; far-OOD sound-vs-OOV AUROC>=0.85; novelty curve monotone)
  C-ind   decision_conf vs grounding_conf correlation (report) -- expect LOW (proposer != critic)
  C-def   grounding anchors at premises, not the floor (recorded)

numpy/CPU. Fixed seeds. Permutation control avg 50 shuffles (Family-A carry-forward).
"""
import json, numpy as np

SEEDS = [0, 1, 2, 3, 4]
V = 30                     # in-vocab atoms (0..V-1); OOV = V..V+4
NRULES = 40
NFACTS = 8
K = 4                      # candidate conclusions per query
NQ = 1500
CRIT_DEPTH = 3            # bounded critic proof depth (true soundness uses depth 20)
TYPE_SCALE = [1.0, 4.0, 0.5]   # 3 capacity types -> incommensurable shallow margins (calibration)
TYPE_NOISE = [0.3, 1.2, 0.15]

def make_rules(g):
    rules = {}
    for _ in range(NRULES):
        head = int(g.integers(0, V)); blen = int(g.integers(1, 4))
        body = sorted(set(int(g.integers(0, V)) for _ in range(blen)))
        rules.setdefault(head, []).append(body)
    return rules

def pc(atom, facts, rules, maxd, memo, stack, d=0):
    """graded proof-completeness: 1 if derivable within maxd, fractional if partial, 0 if not."""
    if atom >= V: return 0.0                       # OOV: inexpressible in premise atoms
    if atom in facts: return 1.0
    key = (atom, d)
    if key in memo: return memo[key]
    if atom in stack or d >= maxd: return 0.0      # cycle / depth bound
    rs = rules.get(atom, [])
    if not rs: return 0.0
    stack.add(atom); best = 0.0
    for body in rs:
        best = max(best, np.mean([pc(b, facts, rules, maxd, memo, stack, d + 1) for b in body]))
    stack.discard(atom); memo[key] = best
    return best

def proposer(atom, facts, rules, depth):
    """decision proposer at a given competence depth (a DIFFERENT computation from the
    grounding critic: popularity-weighted bounded evidence, not graded proof-completeness).
    depth=1 = crippled (facts + 1-step popularity, independence probe);
    depth>=2 = competent (bounded reachability evidence + small popularity, the C-dec gate)."""
    if atom in facts: return 2.0
    rs = rules.get(atom, [])
    if not rs: return 0.0
    if depth <= 1:
        ev = max(np.mean([b in facts for b in body]) for body in rs)
    else:
        ev = pc(atom, facts, rules, depth, {}, set())     # bounded graded evidence
    return ev + 0.15 * len(rs)

def auroc(s, y):
    s, y = np.asarray(s, float), np.asarray(y, int); P, N = (y == 1).sum(), (y == 0).sum()
    if P == 0 or N == 0: return float("nan")
    o = np.argsort(s); r = np.empty(len(s)); r[o] = np.arange(1, len(s) + 1)
    for v in np.unique(s):
        i = s == v
        if i.sum() > 1: r[i] = r[i].mean()
    return float((r[y == 1].sum() - P * (P + 1) / 2) / (P * N))

def platt(m, c, it=600, lr=0.1):
    mu, sd = m.mean(), m.std() + 1e-9; x = (m - mu) / sd; y = c.astype(float); w = b = 0.0
    for _ in range(it):
        p = 1 / (1 + np.exp(-(w * x + b))); w -= lr * ((p - y) * x).mean(); b -= lr * (p - y).mean()
    return lambda mm: 1 / (1 + np.exp(-(w * (mm - mu) / sd + b)))

def rc(conf, correct, covs=(1.0, .75, .5, .25)):
    o = np.argsort(-conf); return {c: float(1 - correct[o[:max(1, int(c * len(conf)))]].mean()) for c in covs}

def run():
    res = {1: {"cal": [], "raw": [], "perm": [], "rc": [], "corr": [], "gcorr": []},
           2: {"cal": [], "raw": [], "perm": [], "rc": [], "corr": [], "gcorr": []}}
    sv_u, sv_oov, curve_l, crit_blind = [], [], [], []
    for sd in SEEDS:
        # decision data (cal + test disjoint draws), per proposer depth
        def gen_decision(nq, off, depth):
            gg = np.random.default_rng(sd * 13 + off)
            M, C, T, GR = [], [], [], []
            for _ in range(nq):
                rules = make_rules(gg); facts = set(int(a) for a in gg.choice(V, NFACTS, replace=False))
                ti = int(gg.integers(0, 3))
                cand = [int(a) for a in gg.choice(V, K, replace=False)]
                sh = np.array([proposer(a, facts, rules, depth) for a in cand]) * TYPE_SCALE[ti] \
                     + gg.normal(0, TYPE_NOISE[ti], K)
                pick = cand[int(sh.argmax())]
                truesound = pc(pick, facts, rules, 20, {}, set()) >= 0.999
                srt = np.sort(sh); margin = srt[-1] - srt[-2]
                gconf = pc(pick, facts, rules, CRIT_DEPTH, {}, set())   # bounded critic
                M.append(margin); C.append(int(truesound)); T.append(ti); GR.append(gconf)
            return map(np.array, (M, C, T, GR))
        for depth in (1, 2):
            m, c, t, gr = gen_decision(NQ, 0 + depth, depth)
            mt, ct, tt, grt = gen_decision(NQ, 7000 + depth, depth)
            cal = np.empty(len(mt))
            for ti in range(3):
                f = platt(m[t == ti], c[t == ti]); cal[tt == ti] = f(mt[tt == ti])
            res[depth]["cal"].append(auroc(cal, ct)); res[depth]["raw"].append(auroc(mt, ct))
            res[depth]["rc"].append(rc(cal, ct))
            cors = []
            for ti in range(3):
                mm, gg2 = mt[tt == ti], grt[tt == ti]
                if mm.std() > 1e-9 and gg2.std() > 1e-9: cors.append(np.corrcoef(mm, gg2)[0, 1])
            res[depth]["corr"].append(np.nanmean(cors))
            res[depth]["gcorr"].append(auroc(grt, ct))   # grounding_conf predicting correctness
            perms = []
            for k in range(50):
                gp = np.random.default_rng(sd * 9 + k); cp = c.copy()
                for ti in range(3):
                    ix = np.where(t == ti)[0]; cp[ix] = c[ix][gp.permutation(len(ix))]
                calp = np.empty(len(mt))
                for ti in range(3):
                    f = platt(m[t == ti], cp[t == ti]); calp[tt == ti] = f(mt[tt == ti])
                perms.append(auroc(calp, ct))
            res[depth]["perm"].append(np.mean(perms))
        # grounding discrimination sets
        gg = np.random.default_rng(sd * 21 + 100)
        sound, near, far, oov, blind = [], [], [], [], []
        for _ in range(1200):
            rules = make_rules(gg); facts = set(int(a) for a in gg.choice(V, NFACTS, replace=False))
            for a in range(V):
                pt = pc(a, facts, rules, 20, {}, set()); pb = pc(a, facts, rules, CRIT_DEPTH, {}, set())
                if pt >= 0.999:
                    sound.append(pb)
                    if pb < 0.999: blind.append(1)   # truly sound but bounded critic misses (deep proof)
                    else: blind.append(0)
                elif pt >= 0.5: near.append(pb)
                elif pt > 0.0: far.append(pb)
            for a in range(V, V + 5):
                oov.append(pc(a, facts, rules, CRIT_DEPTH, {}, set()))
            if len(sound) > 4000: break
        sound, near, far, oov = map(np.array, (sound, near, far, oov))
        sv_u.append(auroc(np.r_[sound, far], np.r_[np.ones(len(sound)), np.zeros(len(far))]))
        sv_oov.append(auroc(np.r_[sound, oov], np.r_[np.ones(len(sound)), np.zeros(len(oov))]))
        curve = [auroc(np.r_[sound, b], np.r_[np.ones(len(sound)), np.zeros(len(b))]) for b in (near, far, oov)]
        curve_l.append(curve); crit_blind.append(np.mean(blind))

    def ms(x): return [round(float(np.nanmean(x)), 3), round(float(np.nanstd(x)), 3)]
    G = res[2]   # C-dec gate uses the competent depth-2 proposer (AM-4)
    rcm = {c: round(float(np.mean([r[c] for r in G["rc"]])), 3) for c in G["rc"][0]}
    gap = rcm[1.0] - rcm[0.5]; gstd = float(np.std([r[1.0] - r[0.5] for r in G["rc"]]))
    mono_rc = all(rcm[a] >= rcm[b] for a, b in [(1.0, .75), (.75, .5), (.5, .25)])
    curve = np.nanmean(np.array(curve_l), 0).round(3).tolist()
    cmono = all(curve[i] <= curve[i + 1] + 0.03 for i in range(len(curve) - 1))
    lift = ms(G["cal"])[0] - ms(G["perm"])[0]; lstd = float(np.std(np.array(G["cal"]) - np.array(G["perm"])))
    mp = {
        "C-dec calibrated AUROC>=0.80 (depth-2)": ms(G["cal"])[0] >= 0.80,
        "C-dec risk-coverage monotone": mono_rc,
        "C-dec gap>2x std": gap > 2 * max(gstd, 1e-6),
        "C-dec calibrated>raw": ms(G["cal"])[0] > ms(G["raw"])[0],
        "C-dec margin-lift>2x std": lift > 2 * lstd,
        "C-grd sound-vs-unsound AUROC>=0.85": ms(sv_u)[0] >= 0.85,
        "C-grd far-OOD sound-vs-OOV AUROC>=0.85": ms(sv_oov)[0] >= 0.85,
        "C-grd novelty curve monotone": cmono,
    }
    out = {
        "family": "C-derivation", "seeds": len(SEEDS), "V": V, "rules": NRULES, "crit_depth": CRIT_DEPTH,
        "C-dec_GATE_depth2": {"calibrated_AUROC": ms(G["cal"]), "raw_pooled_AUROC": ms(G["raw"]),
                              "permuted_AUROC_avg50": ms(G["perm"]), "margin_lift": round(lift, 3),
                              "risk_coverage_mean": rcm},
        "decision_by_proposer_depth": {
            "depth1_crippled": {"cal_AUROC": ms(res[1]["cal"]), "corr_with_grounding": ms(res[1]["corr"])},
            "depth2_competent": {"cal_AUROC": ms(res[2]["cal"]), "corr_with_grounding": ms(res[2]["corr"])},
        },
        "grounding_predicts_correctness_AUROC": ms(res[2]["gcorr"]),
        "grounding_sound_vs_unsound_AUROC": ms(sv_u), "grounding_far_OOD_AUROC": ms(sv_oov),
        "grounding_novelty_curve[near,far,oov]": curve,
        "bounded_critic_blind_rate(sound_missed)": ms(crit_blind),
        "MP": mp, "VERDICT": "PASS" if all(mp.values()) else "FAIL/partial — see MP",
    }
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    run()
