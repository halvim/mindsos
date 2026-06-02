# Handoff Document — OEWN ↔ DOLCE+DnS Ultralite ↔ FrameNet (v5)

**Purpose:** give a fresh model every decision, rationale, artefact, and
open issue from the v5 work, so the project can be audited or continued
without loss of context.

**Supersedes:** `HANDOFF_v4.md` (preserved unmodified for audit).

**Status:** v5 shipped. All non-external-dependency deliverables done;
four items stubbed pending API keys or external data downloads.

---

## 1. Project state

The v4 pipeline (nouns via Gangemi 2003 + OntoWordNet seed; verbs via
Silva 2018 three-tier; adj/adv via novel Phase 4 rules) remains the
load-bearing core of the alignment. v5 added MindsOS-compliant imports,
per-tier confidence, adverb-rule corrections, known-violations
tracking, a pertainym redesign pilot, and an OEWN↔FrameNet alignment.

**Final deliverable:** `release-v5/` — 107,518 OEWN synsets mapped to
DULplus classes plus 17,483 mapped to FrameNet frames, MindsOS-ready.

**Headline numbers:**

| Metric | Value |
|:---|---:|
| OEWN synsets aligned to DOLCE | 107,518 (100%) |
| Distinct DULplus classes | 66 |
| Tier: verified / provisional / propagated | 891 / 16,745 / 89,882 |
| OEWN↔FrameNet mappings | 17,483 |
| …with DOLCE-FN triangle bonus | 7,127 (41%) |
| Known DOLCE disjointness violations | 612 |
| Triangle consistency rate | 58.0% |
| Self-agreement precision (v4, Claude-vs-Claude) | 75.6% strict / 89.2% acceptable |
| Cross-model precision | **pending** (Stage 4 gated on API access) |

---

## 2. How v5 differs from v4

See `CHANGES_v4_to_v5.md` for the full diff. Headline:

1. **MindsOS import rewritten.** v4's exported files were rejected by
   MindsOS's `AlignmentsImporter`. v5 uses the real IRI builders, the
   native edge vocabulary, and a single JSON file per alignment.
2. **Tiered confidence.** Master TSV now carries `tier` and `confidence`
   columns calibrated against the Phase 9f sample.
3. **Adverb rules corrected.** 3,643 rows moved off `dul:Region` /
   `dul:TimeInterval` / `dul:SpaceRegion` onto `dul:Quality` / `dul:Concept`
   per DOLCE's Quality/Region/Concept distinction.
4. **Known violations shipped as a first-class artefact** (612 rows,
   classified into 3 buckets).
5. **Pertainym redesign piloted** (200 synsets; 76% would flip; full
   rewrite gated on LLM judge).
6. **FrameNet leg built** (Stage 5). 17,483 OEWN↔FN mappings, 41% with
   a DOLCE-compatible triangle bonus.

---

## 3. File layout

```
workspace root
├── REVIEW.md                    ← this session's critique of v4
├── IMPLEMENTATION_PLAN.md       ← the v5 plan
├── CHANGES_v4_to_v5.md          ← diff summary
├── HANDOFF.md                   ← this file
├── HANDOFF_v4.md                ← v4 handoff, preserved
├── english-wordnet-2025.ttl     ← OEWN source (200 MB)
├── DLP3971/                     ← DOLCE Lightweight Plus (context only, NOT the target vocabulary)
├── Framenet/framenet_v17/       ← FrameNet 1.7 XML distribution
├── scripts/                     ← v5 scripts (11 files + 1 aux)
├── tests_v5/                    ← 18 unit tests, all passing
├── release-v4/                  ← v4 deliverable, unchanged (audit baseline)
└── release-v5/                  ← v5 deliverable
    ├── README.md
    ├── METHODOLOGY.md
    ├── MINDSOS_IMPORT_V2.md
    ├── release-stats.json
    ├── data/                    (master TSV + 8 other data files)
    ├── mindsos-imports/
    │   ├── oewn-dolce-alignment.json    (25 MB, 107,518 mappings)
    │   └── oewn-framenet-alignment.json (5 MB, 17,483 mappings)
    └── reports/                 (6 Markdown reports)
```

---

## 4. Decisions log

### v5 Stage 1 — MindsOS import

Three parameter decisions the user should re-confirm:

| Knob | v5 value | Notes |
|:---|:---|:---|
| OEWN version tag | `2025` | Matches the `english-wordnet-2025.ttl` in workspace |
| DOLCE-DUL version tag | `4.0` | Matches `mindsos_knowledge/identifiers.py` example. **Important:** alignment vocabulary is DUL (ontologydesignpatterns.org), *not* DLP3971 (loa-cnr.it). MindsOS must load `DUL.owl`, not `DLP_397.owl`. |
| INSTANCE_OF_CLASS heuristic | capitalised primary lemma AND class in {Person, Place, Organization, Organism, PhysicalAgent, PhysicalObject, DesignedArtifact, InformationObject, TimeInterval, Event, SocialAgent, PhysicalPlace} | OEWN 2025 dropped `wn:instance_hypernym`, so direct lookup isn't possible. 4,308 rows got INSTANCE_OF_CLASS, remaining got NARROWER_THAN. |

### v5 Stage 3b — Adverb rules

Rule changes permanent in v5 master TSV; affected rows are tagged `_v2`
in the `method` column. See `release-v5/reports/ADVERB_ONTOLOGY.md`.

### v5 Stage 3c — Pertainym design

Pilot clearly favours referent inheritance over uniform `dul:Quality`
(76% of pertainyms would flip, across 10+ distinct classes), but full
rewrite is **gated** on a 200-row LLM-judge sanity check.
Go-path script documented in `release-v5/reports/PERTAINYM_DECISION.md`.

### v5 Stage 5b — FN alignment

- Lemma-overlap heuristic with DOLCE-compatibility bonus. 17,483
  mappings; 7,127 got the bonus (emit with
  `method=...triangle_bonus`, confidence 0.75).
- SemLink not used — not downloadable in this run. Would add ~4–6k
  tier-verified verb mappings when available.

---

## 5. What should be audited next (in order)

1. **Run Stage 4 cross-model precision** (needs OpenAI / Gemini / Llama
   API key). The v4 75.6%/89.2% number is Claude-vs-Claude; independent
   cross-model agreement is likely 5–15 points lower.
   Script: `scripts/phase9j_crossmodel_judge.py --mode phase9j`.
2. **Run the pertainym LLM-judge gate on the pilot** (Stage 3c). Same
   script, `--mode phase9i`. If ≥85% agreement, proceed with full
   pertainym rewrite.
3. **Run the Silva-propagation audit** (Stage 3a). Same script,
   `--mode phase9g`. If agreement <70%, demote confidence for all
   7,555 `phase3_propagated_from_hypernym` rows.
4. **Download SemLink and refine the FN alignment** (Stage 5b
   completion).
5. **LLM-judge the 5,170 triangle-inconsistent pairs.**
6. **Graph-level OEWN restructuring** for the 486 hypernymy-anomaly
   violations (research project; worth reporting to GWN upstream).

---

## 6. How to verify v5 is still working

From the workspace root:

```bash
# MindsOS import — DOLCE side
python3 scripts/validate_mindsos_roundtrip.py \
    --json release-v5/mindsos-imports/oewn-dolce-alignment.json

# MindsOS import — FrameNet side
python3 scripts/validate_mindsos_roundtrip.py \
    --json release-v5/mindsos-imports/oewn-framenet-alignment.json

# Unit tests
python3 -m pytest tests_v5/ --basetemp=/tmp/pytest_v5
```

Expected: two `OK — strict-mode round-trip passed.` lines and 18
passing tests.

---

## 7. Continuing this work in a new chat

Paste this into the first message, along with this `HANDOFF.md`:

> I have a v5 release of the OEWN↔DOLCE↔FrameNet alignment at
> `release-v5/`. The v4 audit that motivated v5 is in `REVIEW.md`, the
> plan we executed is in `IMPLEMENTATION_PLAN.md`, and the diff vs v4
> is in `CHANGES_v4_to_v5.md`. Four items are stubbed pending external
> resources: cross-model precision (Stage 4), pertainym rewrite (Stage
> 3c full rollout), Silva-propagation audit (Stage 3a LLM run), and
> SemLink-seeded FN alignment. Please [specific ask, e.g. "run Stage
> 4 against GPT-4.1 and update the confidence numbers"].

---

## 8. Scripts written in v5 (end-to-end)

All in `scripts/`; every one has a `--help` flag.

| Script | Stage | Produces |
|:---|:---|:---|
| `export_mindsos_v2.py` | 1 | `release-v5/mindsos-imports/oewn-dolce-alignment.json` |
| `validate_mindsos_roundtrip.py` | 1 | (verification only) |
| `add_tiers.py` | 2 | `release-v5/data/oewn-dulplus-master.tsv` (tier + confidence cols), `reports/TIER_PRECISION.md` |
| `classify_violations.py` | 2 | `release-v5/data/known-violations.tsv`, `reports/KNOWN_VIOLATIONS_REPORT.md` |
| `phase9g_verb_propagation_sample.py` | 3a | `release-v5/data/phase9g-verb-propagation-sample.tsv` |
| `phase9h_adverb_revision.py` | 3b | revises master TSV in place |
| `phase9i_pertainym_pilot.py` | 3c | `release-v5/data/phase9i-pertainym-pilot.tsv`, `reports/PERTAINYM_DECISION.md` |
| `phase9j_crossmodel_judge.py` | 3a/3c/4 | judgement TSVs (dry-run by default; real API via `--judge-backend openai/anthropic`) |
| `phase10a_fn_to_json.py` | 5a | `release-v5/data/framenet-1.7.json` |
| `phase10b_fn_alignment.py` | 5b | `release-v5/data/oewn-framenet-alignment.tsv`, `release-v5/mindsos-imports/oewn-framenet-alignment.json` |
| `triangle_check.py` | 5c | `release-v5/data/triangle-inconsistencies.tsv`, `reports/TRIANGLE_CONSISTENCY.md` |

*End of v5 handoff.*
