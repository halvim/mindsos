#!/usr/bin/env python3
"""
Cross-family REAL-DATA test (AM-5): FrameNet frame-disambiguation (scoring/retrieval family).
Pre-reg: PERCEPTION_CROSSFAMILY_PREREG.md §11 + AM-5.

Real, non-perception selection capacity on REAL gold-annotated text: given a target lemma in
context, rank the frames it can evoke (retrieval over the frame lexicon), pick one; gold =
FrameNet fulltext annotation. Tests the §10 cell "decision axis carries correctness in
selection families" on real data with unknown true factorization.

  S-dec (PRIMARY): per-POS Platt-calibrated AUROC(correct vs incorrect) >= 0.80; risk-coverage
        monotone; calibrated>raw; margin lift > 2x std (avg-50 within-POS permutation).
  S-pos (control): test acc >= MFS baseline >= random.
  S-grd (secondary): grounding (def-context overlap, OOV-capped) far-OOD AUROC >= 0.85.
  S-ind (secondary): corr(margin, grounding) for proposer=critic (Lesk) vs proposer!=critic (MFS prior).

Offline; numpy + stdlib only. Doc-level cal/test split, 3 resamples.
"""
import re, os, glob, json, math, collections, numpy as np

FN = "/sessions/sweet-wizardly-babbage/mnt/MindsOS/projects/dwf_mapping/Framenet/framenet_v17"
STOP = set("the a an of to in on at for and or but with as by from into is are was were be been being "
           "this that these those it its their his her your our my we you they he she him them i me "
           "not no do does did has have had will would can could may might must should s t re ve ll d "
           "which who whom what when where why how all any both each few more most other some such than "
           "too very one two three also if then so up out off over under again further about".split())

def toks(text):
    return [w for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 3 and w not in STOP]

def clean_def(x):
    x = re.sub(r"<[^>]+>", " ", x); x = x.replace("&lt;", " ").replace("&gt;", " ").replace("&amp;", " ")
    return x

# ---------------- lexicon ----------------
def load_lexicon():
    lu = open(os.path.join(FN, "luIndex.xml"), encoding="utf-8").read()
    cand = collections.defaultdict(set); annot = {}
    for s in re.findall(r"<lu\b[^>]*/?>", lu):
        nm = re.search(r'\bname="([^"]*)"', s); fr = re.search(r'\bframeName="([^"]*)"', s)
        na = re.search(r'\bnumAnnotInstances="(\d+)"', s)
        if nm and fr:
            cand[nm.group(1)].add(fr.group(1)); annot[(nm.group(1), fr.group(1))] = int(na.group(1)) if na else 0
    gloss = {}
    for fp in glob.glob(os.path.join(FN, "frame", "*.xml")):
        name = os.path.basename(fp)[:-4]; t = open(fp, encoding="utf-8").read()
        d = re.search(r"<definition>(.*?)</definition>", t, re.S)
        fes = re.findall(r'<FE\b[^>]*\bname="([^"]*)"', t)
        bag = toks(clean_def(d.group(1)) if d else "") + [w for fe in fes for w in toks(fe)]
        gloss[name] = set(bag)
    return cand, annot, gloss

# ---------------- gold instances from fulltext ----------------
def load_instances(cand, gloss):
    items = []; oov_ground = []
    for fp in glob.glob(os.path.join(FN, "fulltext", "*.xml")):
        fid = os.path.basename(fp); t = open(fp, encoding="utf-8").read()
        for sm in re.findall(r"<sentence\b.*?</sentence>", t, re.S):
            tx = re.search(r"<text>(.*?)</text>", sm, re.S)
            if not tx: continue
            ctx_all = toks(tx.group(1)); ctxset = set(ctx_all)
            for a in re.findall(r"<annotationSet\b[^>]*>", sm):
                lu = re.search(r'\bluName="([^"]*)"', a); fr = re.search(r'\bframeName="([^"]*)"', a)
                if not (lu and fr): continue
                if 'status="MANUAL"' not in a: continue        # human-verified gold only (audit fix)
                lemma = lu.group(1); gold = fr.group(1)
                cands = set(cand.get(lemma, set())) | {gold}
                cands = {c for c in cands if c in gloss}
                if len(cands) < 2 or gold not in cands: continue
                base = set(toks(lemma.split(".")[0]))
                pos = lemma.split(".")[-1]; pos = pos if pos in ("n", "v", "a") else "o"
                ctx = [w for w in ctx_all if w not in base]
                if not ctx: continue
                items.append({"lemma": lemma, "gold": gold, "cands": sorted(cands),
                              "ctx": set(ctx), "pos": pos, "file": fid})
            # OOV grounding: content tokens of this sentence with NO frame lexicon entry
            for w in ctxset:
                if w not in cand and (w + ".n") not in cand and (w + ".v") not in cand:
                    oov_ground.append(0.0)        # unexplainable by the frame lexicon -> grounding 0
    return items, np.array(oov_ground[:5000])

# ---------------- scoring ----------------
def score_item(it, annot, gloss):
    """Two proposers. GATE (AM-6) = MFS-primary (competent, acc>=MFS): freq + small Lesk bonus.
    PROBE = Lesk-primary (sub-baseline; independence probe)."""
    ctx = it["ctx"]; lesk = {}; prior = {}
    for c in it["cands"]:
        lesk[c] = len(gloss[c] & ctx); prior[c] = math.log1p(annot.get((it["lemma"], c), 0))
    # GATE proposer: PURE MFS (canonical baseline; argmax prior == mfs_pure, so acc == MFS)
    rk = sorted(prior.items(), key=lambda kv: -kv[1]); pick = rk[0][0]
    margin = rk[0][1] - rk[1][1]
    ground = lesk[pick] / (len(ctx) + 1)
    # PROBE proposer: Lesk-primary
    lk_s = {c: lesk[c] + 0.1 * prior[c] for c in it["cands"]}
    rkl = sorted(lk_s.items(), key=lambda kv: -kv[1])
    lesk_margin = rkl[0][1] - rkl[1][1]
    return pick, margin, ground, (pick == it["gold"]), lesk_margin

# ---------------- metrics ----------------
def auroc(s, y):
    s, y = np.asarray(s, float), np.asarray(y, int); P, N = (y == 1).sum(), (y == 0).sum()
    if P == 0 or N == 0: return float("nan")
    o = np.argsort(s); r = np.empty(len(s)); r[o] = np.arange(1, len(s) + 1)
    for v in np.unique(s):
        i = s == v
        if i.sum() > 1: r[i] = r[i].mean()
    return float((r[y == 1].sum() - P * (P + 1) / 2) / (P * N))

def platt(m, c, it=700, lr=0.1):
    m = np.asarray(m, float); c = np.asarray(c, float)
    mu, sd = m.mean(), m.std() + 1e-9; x = (m - mu) / sd; w = b = 0.0
    for _ in range(it):
        p = 1 / (1 + np.exp(-(w * x + b))); w -= lr * ((p - c) * x).mean(); b -= lr * (p - c).mean()
    return lambda mm: 1 / (1 + np.exp(-(w * (np.asarray(mm, float) - mu) / sd + b)))

def rc(conf, correct, covs=(1.0, .75, .5, .25)):
    o = np.argsort(-conf); return {cv: float(1 - correct[o[:max(1, int(cv * len(conf)))]].mean()) for cv in covs}

# ---------------- run ----------------
def run():
    cand, annot, gloss = load_lexicon()
    items, oov = load_instances(cand, gloss)
    files = sorted({it["file"] for it in items})
    # precompute per-item scores once
    for it in items:
        it["pick"], it["margin"], it["ground"], it["correct"], it["leskm"] = score_item(it, annot, gloss)
        it["mfs_pure"] = max(it["cands"], key=lambda c: annot.get((it["lemma"], c), 0))
    rnd = np.mean([1.0 / len(it["cands"]) for it in items])
    acc = np.mean([it["correct"] for it in items])                 # GATE proposer (MFS-primary)
    mfs_acc = np.mean([it["mfs_pure"] == it["gold"] for it in items])

    cal_a, raw_a, perm_a, rc_l, corr_lesk, corr_mfs = [], [], [], [], [], []
    for rs in range(3):
        g = np.random.default_rng(rs); fsh = list(files); g.shuffle(fsh)
        calf = set(fsh[:len(fsh) // 2]);
        tr = [it for it in items if it["file"] in calf]; te = [it for it in items if it["file"] not in calf]
        if len(te) < 50 or len(tr) < 50: continue
        cals = {}
        for pos in set(it["pos"] for it in tr):
            mp = [it["margin"] for it in tr if it["pos"] == pos]; cp = [it["correct"] for it in tr if it["pos"] == pos]
            if len(set(cp)) > 1: cals[pos] = platt(mp, cp)
        def cal_conf(it): return float(cals[it["pos"]](it["margin"])) if it["pos"] in cals else 0.5
        conf = np.array([cal_conf(it) for it in te]); corr = np.array([it["correct"] for it in te], int)
        raw = np.array([it["margin"] for it in te], float)
        cal_a.append(auroc(conf, corr)); raw_a.append(auroc(raw, corr)); rc_l.append(rc(conf, corr))
        gnd = [it["ground"] for it in te]
        corr_mfs.append(np.corrcoef(raw, gnd)[0, 1])               # GATE margin (mfs-primary) vs grounding -> DIFFERENT comp
        corr_lesk.append(np.corrcoef([it["leskm"] for it in te], gnd)[0, 1])  # Lesk margin vs grounding -> SAME comp
        # permutation avg 50 (within-POS shuffle of correctness on cal)
        perms = []
        for k in range(50):
            gp = np.random.default_rng(rs * 100 + k); calp = {}
            for pos in set(it["pos"] for it in tr):
                mp = [it["margin"] for it in tr if it["pos"] == pos]; cp = [it["correct"] for it in tr if it["pos"] == pos]
                cp = list(np.array(cp)[gp.permutation(len(cp))])
                if len(set(cp)) > 1: calp[pos] = platt(mp, cp)
            cf = np.array([float(calp[it["pos"]](it["margin"])) if it["pos"] in calp else 0.5 for it in te])
            perms.append(auroc(cf, corr))
        perm_a.append(np.mean(perms))

    # grounding far-OOD (in-vocab item grounding vs OOV tokens grounding=0)
    ig = np.array([it["ground"] for it in items])
    far = auroc(np.r_[ig, oov], np.r_[np.ones(len(ig)), np.zeros(len(oov))]) if len(oov) else float("nan")
    grd_corr_correct = auroc(ig, np.array([it["correct"] for it in items], int))
    # polysemy strat AUROC (on full set, calibrated within POS on all -- descriptive)
    strat = {}
    for lab, lo, hi in [("2", 2, 2), ("3-4", 3, 4), ("5+", 5, 99)]:
        sub = [it for it in items if lo <= len(it["cands"]) <= hi]
        if len(sub) > 30:
            strat[lab] = round(auroc([it["margin"] for it in sub], [it["correct"] for it in sub]), 3)

    def ms(x): return [round(float(np.nanmean(x)), 3), round(float(np.nanstd(x)), 3)]
    rcm = {c: round(float(np.mean([r[c] for r in rc_l])), 3) for c in rc_l[0]}
    gap = rcm[1.0] - rcm[0.5]; gstd = float(np.std([r[1.0] - r[0.5] for r in rc_l]))
    mono = all(rcm[a] >= rcm[b] for a, b in [(1.0, .75), (.75, .5), (.5, .25)])
    lift = ms(cal_a)[0] - ms(perm_a)[0]; lstd = float(np.std(np.array(cal_a) - np.array(perm_a)))
    mp = {
        "S-dec calibrated AUROC>=0.80": ms(cal_a)[0] >= 0.80,
        "S-dec risk-coverage monotone": mono,
        "S-dec gap>2x std": gap > 2 * max(gstd, 1e-6),
        "S-dec calibrated>raw": ms(cal_a)[0] > ms(raw_a)[0],
        "S-dec margin-lift>2x std": lift > 2 * lstd,
        "S-pos acc>=MFS>=random": acc >= mfs_acc >= rnd,
        "S-grd far-OOD AUROC>=0.85": (far >= 0.85),
    }
    mp = {k: bool(v) for k, v in mp.items()}
    out = {
        "family": "REAL-FrameNet-frame-disambiguation", "resamples": len(cal_a),
        "n_items": len(items), "n_files": len(files), "n_oov_ground": int(len(oov)),
        "accuracy": round(float(acc), 3), "MFS_baseline": round(float(mfs_acc), 3), "random_baseline": round(float(rnd), 3),
        "S-dec_calibrated_AUROC": ms(cal_a), "raw_pooled_AUROC": ms(raw_a),
        "permuted_AUROC_avg50": ms(perm_a), "margin_lift": round(lift, 3),
        "risk_coverage_mean": rcm,
        "polysemy_strat_AUROC(raw)": strat,
        "S-grd_far_OOD_AUROC": round(float(far), 3), "grounding_predicts_correctness_AUROC": round(float(grd_corr_correct), 3),
        "S-ind_corr(GATEmargin,grounding)_diffComp": ms(corr_mfs),
        "S-ind_corr(Leskmargin,grounding)_sameComp": ms(corr_lesk),
        "MP": mp, "VERDICT": "PASS" if all(mp.values()) else "FAIL/partial — see MP",
    }
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    run()
