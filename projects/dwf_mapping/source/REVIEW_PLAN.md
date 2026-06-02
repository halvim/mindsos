# Review Plan — Validating and refining the OEWN ↔ DOLCE alignment

**Date:** 2026-04-22
**Status:** Draft, awaiting your decisions on scope and cadence
**Context:** Complements the v1 release in `release/`. The alignment currently covers 107,518 / 107,518 OEWN synsets with an estimated 90–96% per-synset precision. This plan turns that first-pass alignment into a reviewed, calibrated v2.

---

## 1. The review surface

Across Phases 1–5 we produced three kinds of artefact that need human attention:

| Queue | Size | What's in it | Confidence that items are errors |
|---|---:|---|---|
| **Q1 — Phase 2 noun topmappings** | 82 flagged | Gangemi R1–R6 rule flags on the 840 seed synsets | Mixed: 10 very-high-confidence, 61 cosmetic (full-IRI classes), 11 judgment calls |
| **Q2 — Phase 3.5 verb revalidations** | 1,228 flagged | R1–R7 rule flags on the propagated verb tier | Graduated: 3 very-high, 516 high, 709 low |
| **Q3 — Phase 5 audit sample** | 200 stratified | Random cross-POS precision audit | Not flags — just sampling for an evaluation metric |
| **Q4 — Phase 5 hypernym violations** | 516 disjoint + 653 unrelated | Structural consistency failures | ~50% real errors, ~50% translation-layer artefacts |
| **Q5 — Phase 5 multi-class synsets** | 791 synsets | Framester legitimately assigned two disjoint classes | Design question, not error |
| **Q6 — Phase 4 novel adj/adv rules** | entire 21,833-row tier | Unpublished methodology | Pilot showed ~95% quality; needs formal peer signoff for publication |

Plus two hidden surfaces:

- **4,542 gap-filled nouns from Phase 5-alt** — propagated from hypernyms, never spot-checked.
- **SUB-POS distributions** — satellites inherited from heads; satellite-head disagreements would be invisible without targeted sampling.

## 2. Suggested review order (with rationale)

Each review track has a different cost/value profile. I'd sequence them:

### Track A — Auto-applicable corrections (≈30 minutes of your time total)

Two sub-steps:

**A1. Apply the 13 "very-high-confidence" corrections automatically.** These are items where ≥2 independent rules agree. They are:

- 10 from Phase 2 (4 metalevel + 6 perdurant-gloss): *attribute, property, relation, dependence, gather, goal, representation, tankage, use*
- 3 from Phase 3.5 score≥4: *change*, *join*, *change surface*

Cost: ~15 minutes of your review time to read the 13-row diff and say yes/no; then I run a 30-second script.

**A2. Batch-accept the 61 Phase 2 "full-IRI" cosmetic flags.** These are `Supplements.owl` classes that just need a prefix declaration, not semantic review. Cost: 0 decisions — it's format-only.

### Track B — Top-50 high-leverage verbs (≈1 hour)

The Phase 3.5 flagged verbs include several whose class changes would propagate to dozens of troponyms:

| Verb | Current | Proposed | Troponyms affected |
|---|---|---|---:|
| `be` ("occupy a certain position") | Event | State | 36 |
| `change` ("become different…") | State | Achievement | 73 |
| `change state` ("undergo transformation") | State | Process | 73 |
| `join` ("become part of…") | State | Achievement | 4 |
| `fail` ("fail to do something") | State | Action | 8 |
| `preserve` ("prevent from rotting") | Action | Process | 9 |

And ~40 more with 3+ troponyms each.

**Method:** open `release/review-queues/phase3_5-verb-review.tsv` in a spreadsheet, filter to `confidence_score ≥ 2` AND `rules_triggered contains R1 OR R3`, sort descending by troponym count, review top 50. Mark `decision` column with `accept_proposed` / `accept_current` / `other:dul:X`.

**Why this first:** fixing 50 parents revises ~1,000 descendants automatically via re-propagation. ROI is highest here.

### Track C — Batch review by flip pattern (≈2 hours)

Once the top-50 are done, the remaining 1,178 Phase 3.5 flags cluster into ~10 flip patterns. Review can be batched:

| Flip pattern | Count | Suggested sample size | Decision approach |
|---|---:|---:|---|
| `Action → State` | 289 | 30 | If the sample's 30 are >80% correct flips, batch-accept all 289; otherwise fall through to individual review |
| `State → Action` | 181 | 25 | Same |
| `Action → Event` | 152 | 20 | Same |
| `State → Achievement` | 120 | 20 | Same |
| `Event → Action` | 85 | 15 | Same |
| `Action → Achievement` | 82 | 15 | Same |
| `Action → Process` | 75 | 15 | Same |
| `State → Process` | 61 | 10 | Same |
| `State → Event` | 58 | 10 | Same |
| `Event → State` | 46 | 10 | Same |

**Method:** for each pattern, I can write a short filter script that outputs a random 20-row sample in a dedicated TSV. You mark `accept_flip / reject_flip / defer` on each sample row. If your accept rate on the sample is ≥80%, we batch-accept the whole pattern; else we fall back to row-by-row on the full pattern.

**Why this works:** batch decisions cost ~2 minutes per sample row × 170 samples ≈ 5.5 hours if done exhaustively — but we don't need exhaustive, we need statistical confidence. A 20-row sample gives us a 95% CI of ±20% on the true accept rate, which is enough to make the batch call.

### Track D — Complete the Phase 5 audit sample (≈1.5 hours)

The 200 stratified random synsets in `phase5-audit-sample.tsv` produce the **formal precision metric** for the alignment. Without this, we can only say "estimated 90–96%"; with it, we get a real number with a confidence interval.

**Method:** open the TSV in a spreadsheet. For each row read the gloss + class, mark `manual_agreement` as one of:
- `yes` — class is correct
- `no` — class is wrong, note what should be correct in a comments column
- `debatable` — reasonable alternative exists
- `cannot_judge` — domain expertise required

Target time: ~25 seconds per synset × 200 = 85 minutes.

**Output:** a precision estimate for each (POS, method) bucket. If any bucket scores <85%, Track E kicks in.

### Track E — Targeted re-mapping for low-precision buckets (conditional, ≈variable)

Only if Track D flags a specific bucket as weak. For example:

- If `phase3_propagated_from_hypernym` verbs score <85%, we'd tighten Phase 3 propagation rules and re-run.
- If `phase4_A1_satellite_inherits_head` satellites score <85%, we'd add head-specific sub-rules.

This is where script time and rule-design time go in; I'd write the targeted fix after Track D results come in.

### Track F — Phase 5 hypernym violations (≈1–2 hours for spot-check)

516 disjoint pairs + 653 unrelated. Two sub-steps:

**F1. Filter the translation-layer artefacts.** The `PhysicalPlace → Place` and similar cases are not errors — they're my DUL→DOLCE translation being too coarse. I can auto-identify these by cross-checking the DUL docs; probably 200–300 of the 516 are in this class.

**F2. Review the remaining 200–300 genuine violations.** These cluster into patterns:
- `DesignedArtifact → FunctionalSubstance` (24) — often legitimate (fuel under engine); sometimes errors
- `DesignedArtifact → InformationRealization` (12) — e.g. maps vs. signs; judgment call
- `Substance → Quality` (10) — almost certainly errors, should be Amount

Suggested method: one 30-synset stratified sample across the top patterns, confirming whether each pattern is "real error" or "WordNet hypernymy quirk". Batch-fix the clear errors; leave the rest documented.

### Track G — Design decision on multi-class synsets (≈20 minutes, one-shot call)

The 791 synsets Framester assigned to two classes (e.g., `ontopic:Topic + dul:Action` on "lecture"-like synsets). Currently collapsed to single-class in the primary deliverable; multi-class preserved in `oewn-dulplus-master-full.tsv`.

Three design options — pick one:

1. **Accept the single-class collapse.** Matches typical ontology-alignment conventions.
2. **Expose both classes** as `skos:relatedMatch` (soft) in addition to the primary `skos:broadMatch` (hard). Preserves information, valid SKOS.
3. **Model explicitly as separate facets** via `dct:hasPart` sub-concepts (the lecture-as-act vs. lecture-as-topic distinction).

Recommendation: **option 2** (SKOS related-match for the secondary class). It's a one-line script change and preserves the multi-class information without forcing disjointness.

### Track H — Novel adj/adv peer review (optional, several weeks wall-clock)

The Phase 4 work is unpublished. If you plan to publish this alignment or use it in formal work, the adjective/adverb rule set needs peer validation. Options:

**H1. Internal validation** — have 1–2 colleagues with ontology background review the Phase 4 pilot TSV + a fresh 100-synset sample. ~2 hours per reviewer.

**H2. Community consultation** — post the Phase 4 rule set to the Global WordNet Association's discussion forum or to the DOLCE/LOA mailing list. Asks for feedback over 2–4 weeks. Low cost, high credibility.

**H3. Formal paper submission** — turn Phase 4 into a short paper for LREC or GWC (Global WordNet Conference). Highest validation bar but longest timeline (6+ months).

My recommendation: **H2 first, then H3 if response is positive.** H1 is fine as a sanity check but doesn't carry citation weight.

### Track I — Spot-check the gap-filled Phase 5-alt nouns (≈30 minutes)

4,542 nouns received their class via Phase 5-alt hypernym propagation, never spot-checked. These are OEWN-native (post-PWN-3.0) synsets — often technical/new terms where propagation is reliable, but worth a quick audit.

**Method:** I write a 30-synset stratified random sampling script. You read 30 glosses and classes, mark agreement. Takes ~15 minutes. If ≥90% correct, accept the whole tier; if <90%, tighten the propagation rules.

---

## 3. Timeline & cadence options

Three realistic cadences, pick the one that fits your bandwidth:

### Option 1 — Focused week (≈10 hours total)

- Day 1 (2h): Track A auto-corrections + Track B top-50 verbs.
- Day 2 (2h): Track C batch review (10 pattern samples, ~12 minutes each).
- Day 3 (1.5h): Track D audit sample.
- Day 4 (1.5h): Track F hypernym violations + Track I gap-fill spot-check.
- Day 5 (2h): Track G multi-class decision + Track E conditional re-mapping if triggered.
- Day 6+: I run integration script, produce v2 release.

Fastest path to a reviewed artefact. Good for a publication push or a sprint.

### Option 2 — One track per week (≈2 hours/week for 8 weeks)

Spread out. You get more breathing room and fresher judgment on each track; v2 release lands in month 2.

### Option 3 — Minimal viable review (≈3 hours total)

- Track A auto-corrections (30m)
- Track B top-50 only (1h)
- Track D half-sample (100 synsets, 45m)
- Track G design decision (15m)

Accept the rest as-is for now, revisit only if the alignment gets used in anger and specific issues surface.

## 4. Tooling — what you'll actually look at

Every review queue is a TSV. Suggested workflow:

1. **Open in a spreadsheet** (Excel / Numbers / Google Sheets) — the `decision` / `manual_agreement` columns are already there.
2. **Use column filters** to slice by flag type, confidence score, POS, or rule.
3. **Save as TSV when done** — I'll write a Phase R-integration script that reads your decisions back and applies them.

**For Track C batch review specifically**, I can write a lightweight web-based UI — a single HTML page with keyboard shortcuts (y/n/d) and auto-save to a decisions JSON — if the TSV review is too tedious. Low effort (~2 hours to build); only worth it if you're going to review ≥500 rows.

For anything more elaborate (e.g., a custom label-studio instance), the setup cost exceeds the labeling cost for this volume.

## 5. Acceptance criteria for v2 release

A reviewed alignment should satisfy:

- **At least Tracks A + D completed** (auto-corrections applied, precision metric measured).
- **Precision ≥85% on the audit sample**, overall and per-POS. If below 85%, trigger Track E for the weak bucket.
- **Zero high-confidence Phase 3.5 flags unresolved.** Either accept the proposal or explicitly mark `accept_current` with a comment.
- **Hypernym disjoint-violation rate ≤1%.** Currently 0.63% — already passes, but Track F should confirm this number after filtering translation-layer artefacts.
- **A documented decision on multi-class synsets** (Track G).

Optional for v2 but required for publication / peer work:

- **Track H** peer review of the adj/adv methodology.
- **Track I** gap-fill spot-check.
- **Complete Track C** batch-or-individual decisions on all 1,228 verb flags.

## 6. What I'll produce to support the review

Regardless of which option you pick, I can write these supporting scripts ahead of time:

1. **`apply_decisions.py`** — reads the reviewed TSVs (with your `decision` / `manual_agreement` columns filled in), applies accepted revisions to the master alignment, re-runs propagation from revised anchors, regenerates the Turtle files. Output: `release-v2/`.

2. **`pattern_sampler.py`** — for Track C. Takes a flip pattern (e.g., `Action→State`) and pulls a stratified random N-sample into its own TSV ready for review.

3. **`precision_report.py`** — reads the completed audit sample (Track D), computes precision per (POS, method) bucket, produces a report.

4. **`filter_disjoint_violations.py`** — for Track F. Auto-identifies the translation-layer artefacts vs. likely-real violations, outputs a stratified review TSV.

5. **`adj_adv_sampler.py`** — for Track H. Produces a fresh 100-synset stratified adj/adv sample distinct from the pilot, for independent peer review.

6. **`gapfill_sampler.py`** — for Track I.

These aren't heavy scripts; I can have all six ready within an hour. Tell me which tracks you're committing to and I'll prioritize.

## 7. What I need from you right now

Three quick decisions to unblock the review sprint:

**(a) Cadence — pick Option 1, 2, or 3 from §3.** Your bandwidth determines the plan.

**(b) Supporting scripts — do you want me to write any of the 6 helpers in §6 ahead of time**, or wait until you hit each track? Writing them up front adds ~1 hour of script time but saves context-switching later.

**(c) Track H (peer review) — yes, no, or defer?** If yes, I'll draft the email / forum post we'd send to the GWN / DOLCE community asking for feedback on the adj/adv methodology. If no, we treat v2 as an internal release only.

A reply like `1, yes-all-six, defer-H` is enough to kick off.

---

## Appendix — full review timeline if you pick Option 1 + all scripts

```
D0 (now):     I write apply_decisions.py, pattern_sampler.py, precision_report.py,
              filter_disjoint_violations.py, adj_adv_sampler.py, gapfill_sampler.py
              (1 hour of script time)

D1:           Track A1 — read 13-row diff, 13 yes/no (15m)
              Track A2 — batch-accept 61 full-IRI flags (0m)
              Track B  — top-50 verbs (1h)
              I run apply_decisions.py; re-propagation completes (10m)

D2:           Track C — run pattern_sampler.py for 10 patterns
              review 170 samples (2h)
              I run batch-apply or fall-through to individual

D3:           Track D — complete audit sample (1.5h)
              I run precision_report.py (5m)

D4:           Track F — run filter_disjoint_violations.py
              review 30-synset consolidated sample (1h)
              I apply fixes (15m)

              Track I — run gapfill_sampler.py
              review 30-synset sample (15m)

D5:           Track G — design decision on multi-class synsets (15m)
              Track E — triggered only if Track D precision flagged any bucket
              (variable)

D6:           I run final apply_decisions.py + Phase 5 re-verification
              produce release-v2/ bundle (20m)

              TOTAL HUMAN TIME: ~6–7 hours focused review
              TOTAL CALENDAR DAYS: ~1 week
```

---

This plan complements but does not replace the v1 release — the current alignment is already usable for most downstream work. Review transforms v1 from "methodologically defensible first pass" into "peer-validatable second pass" and raises the formal precision metric from "estimated" to "measured".
