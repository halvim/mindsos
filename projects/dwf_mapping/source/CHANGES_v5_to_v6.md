# CHANGES — v5 → v6

## Scope

Phase 11a — expand the OEWN↔FrameNet leg via three cumulative strategies.
OEWN↔DOLCE leg unchanged. Triangle-driven DOLCE revision (Stage 11c/d)
**not** executed — requires non-Claude LLM API access; tracked as the v7
surface.

## What shipped

Three staged passes, each building on the previous:

| Pass | New strategy | Mappings | Δ vs prev | Coverage | Consistency |
|:---|:---|---:|---:|---:|---:|
| v5 baseline | (primary-lemma only) | 17,483 | — | 16.3% | 58.0% |
| v5.1 | + sense-level lemma match | 30,772 | +13,289 | 19.9% | 58.3% |
| v5.2 | + derivational propagation | 38,671 | +7,899 | 21.9% | 57.3% |
| v5.3 (= v6) | + frame-inheritance propagation | 38,998 | +327 | 21.9% | 57.4% |

Final v6 ships `oewn-framenet-alignment.tsv` = v5.3, plus the
intermediate v5.1 and v5.2 versions as an audit trail.

## By method in the final v6

| Method | Count | Origin |
|:---|---:|:---|
| phase10_lemma_overlap | 13,603 | v5 |
| phase10_lemma_overlap_triangle_bonus | 9,940 | v5 |
| phase11_sense_lemma | 4,290 | **v6 strategy i** |
| phase11_sense_lemma_triangle_bonus | 2,939 | **v6 strategy i** |
| phase11_derivational_propagation | 7,893 | **v6 strategy ii** |
| phase11_frame_inheritance_propagation | 333 | **v6 strategy iii** |

Edge-type split: 21,373 EVOKES (primary), 17,625 CLOSE_MATCH (secondary
/ propagated).

## New artefacts

- `release-v6/data/synset-lemmas.tsv` (185,129 rows) — every synset's
  full lemma set extracted from OEWN 2025 TTL.
- `release-v6/data/synset-derivations.tsv` (44,121 rows) — synset-level
  derivation edges (resolved from OEWN's sense-level `wn:derivation`
  predicates).
- `release-v6/data/oewn-framenet-alignment.tsv` — final v6 alignment.
- `release-v6/mindsos-imports/oewn-framenet-alignment.json` — MindsOS-ready
  expanded alignment (9.5 MB, 38,998 mappings).
- Three per-iteration audit TSV / JSON pairs (`*.v5.{1,2,3}.*`).
- Three per-iteration triangle reports (`TRIANGLE_v5.{1,2,3}.md`).

## New scripts

- `scripts/phase11_precompute.py` — TTL → lemmas + derivations.
- `scripts/phase11a_expand_fn_alignment.py` — cumulative expansion with
  `--strategies {i,ii,iii}` flags.

All v5 scripts unchanged and still work.

## What didn't change

- OEWN↔DOLCE master TSV unchanged (tier, confidence, class assignments
  all as v5 shipped).
- OEWN↔DOLCE MindsOS JSON unchanged (copy from v5).
- DOLCE tier precision, adverb revisions, pertainym pilot, known
  violations — all unchanged from v5.
- `release-v4/`, `release-v5/` — unchanged audit baselines.

## Verification

```
$ python3 scripts/validate_mindsos_roundtrip.py \
      --json release-v6/mindsos-imports/oewn-dolce-alignment.json
OK — strict-mode round-trip passed.  (107,518 mappings, 107,583 anchors)

$ python3 scripts/validate_mindsos_roundtrip.py \
      --json release-v6/mindsos-imports/oewn-framenet-alignment.json
OK — strict-mode round-trip passed.  (38,998 mappings, 24,550 anchors)

$ python3 -m pytest tests_v5/ --basetemp=/tmp/pytest_v5
18 passed in 0.20s
```

## v7 surface (what to do next)

The big remaining item is the **reverse co-refinement arrow** — using the
now-doubled set of triangle inconsistencies (12,138 pairs, up from
5,170 in v5) to revise DOLCE classes where the frame strongly
disagrees. Script ready, gated on LLM API access:

```bash
python3 scripts/phase9j_crossmodel_judge.py \
    --mode phase11c \
    --sample release-v6/data/triangle-inconsistencies.tsv \
    --out    release-v7/data/phase11c-judgements.tsv \
    --judge-backend openai --model gpt-4.1
```

After judging, verdict-A cases get their DOLCE class revised and the
expansion re-runs — the co-refinement loop that v6 set up but didn't
execute.
