---
title: "Lexicon empirical layer: selectional-association edge vocabulary"
status: Accepted
date: 2026-06-10
accepted_date: 2026-06-10
layer: knowledge
related: [0021, 0149, 0150, 0153, 0181, 0182]
---

# ADR-0184: Lexicon empirical layer — selectional-association edge vocabulary

**Status:** Accepted (Phase 51 / WSD-1 — drafted at ship R0 per the
WSD_INSTALLATION design-log §6 reservation; design settled at
WSD_INSTALLATION_CHAT closure 2026-06-10, PB-W2/PB-W14/PB-W15/PB-W21)

**Date:** 2026-06-10

**Related:** ADR-0021 (Cypher rel-type identifier regex — all names
below conform), ADR-0149 (`strict=False` seed schemas — property
declarations are informative until strict), ADR-0150 (closed role-set
— this ADR adds NO role-graph; D-L2-2's `sense-correlations` data
lands as lexicon-internal vocabulary), ADR-0153 (mutation discipline —
`ADMIN_AUTHORED` unchanged), ADR-0181 (Falkor index strategy — the
empirical-layer lookup index is created at Phase 52, the first
retrieval consumer), ADR-0182 (node-value serialization — explicitly
NOT extended to edge property bags; see §6).

Design authority: `confirmation_docs/WSD_INSTALLATION_DESIGN_LOG.md`
(PB-W2, PB-W14, PB-W15, PB-W21) + `confirmation_docs/PHASE_51_DESIGN_LOG.md`
(PB-51-1/2/3/4/8/9 — consumer-column finalization at slot R0).

## Context

WSD scoring (Phase 53, `scoring.wsd_rank_senses`) is Resnik-style
selectional association over the WordNet hypernym stratum plus an
MFS-prior fallback (PB-W15). The correlation data — "verb sense *v*
takes argument-class *c* in role *r* with strength *s*" — had no home:
the `sense-correlations` role-graph was withdrawn (L2 chat D-L2-2) and
the named successor, the lexicon "empirical layer", was never shipped
(WSD design log §0.1). PB-W2 settled the home: **new EdgeTypes on the
`lexicon` schema**, release-side. This ADR fixes the vocabulary against
its actual consumers: the Phase-52 importers (writers) and the
Phase-53 scorer (reader).

A Resnik association is a *(verb sense, argument role, hypernym class)*
triple. Two grounded constraints shaped the encoding (Phase 51 R0):

1. `role` is in `RESERVED_PROPERTY_KEYS` (`schema/validation.py`) — a
   role-discriminating edge *property* would be rejected by
   `validate_user_properties`. The role therefore lives in the
   **EdgeType name**.
2. Edge persistence is id-keyed (`MERGE (s)-[e:TYPE {id: row.id}]->(t)`,
   `cypher/builders.py`) — parallel co-typed edges between the same
   node pair round-trip safely, so per-corpus provenance can be
   carried by **separate edges** rather than in-place mutation.

## Decision

### 1. EdgeTypes (per argument role)

Three new EdgeTypes on the `lexicon` schema, **Sense → Synset**
(`allowed_sources={Sense}`, `allowed_targets={Synset}` — restricted,
deviating deliberately from the lexicon's any→any structural pattern;
type membership is enforced even at `strict=False`, per Phase-50 I5):

| EdgeType | Meaning |
|---|---|
| `SEL_ASSOC_NSUBJ` | source Sense selects target hypernym class in UD `nsubj` position |
| `SEL_ASSOC_DOBJ` | … in UD `dobj` position |
| `SEL_ASSOC_IOBJ` | … in UD `iobj` position |

Oblique arguments (v2, WSD §5.2) are **additive EdgeTypes** under the
same `SEL_ASSOC_*` naming scheme — no schema change to existing types.

### 2. Constant placement

The three names live in a **separate tuple**
`LEXICON_EMPIRICAL_EDGE_TYPES` in `mindsos_knowledge/schemas/lexicon.py`;
`build_lexicon_schema` registers both tuples. `LEXICON_EDGE_TYPES`
(the Phase-13 structural vocabulary) is untouched — the
structural/empirical stratum boundary is expressed in the constants
(PB-51-9). Phase-13 pins (`test_seed_schemas` set-equality,
`test_dimensional_snapshot` edge count) update to the union/new count.

### 3. Edge properties

Declared via `EdgeType.property_types` (informative at `strict=False`,
binding when strict lands):

| Property | Type | Semantics |
|---|---|---|
| `count` | INT | raw co-occurrence count in the source corpus |
| `smoothed_score` | FLOAT | Resnik selectional association (smoothed) |
| `source` | STRING | provenance: `"semcor"`, `"glosstag"`, `"promotion"` (open string enum) |
| `corpus_version` | STRING | source corpus release identifier |

All four names verified clean against `RESERVED_PROPERTY_KEYS`.

### 4. Edge identity + provenance discipline

**One edge per (sense, role EdgeType, target class, source corpus).**
Corpus provenance is per-edge, not aggregated: SemCor and GlossTag
contributions to the same triple are **two parallel edges** (id-keyed
MERGE makes this round-trip safe). The Phase-53 scorer sums across
parallel edges, applying the GlossTag down-weight from
`learned-parameters` at read time — no weight column on edges.

Promotion application (Phase 55, S10 loop) **appends** edges with
`source="promotion"` rather than mutating shipped edges — consistent
with `ADMIN_AUTHORED` append-style discipline and clean audit.

**`smoothed_score` recompute ownership:** the Phase-52 bootstrap
computes scores once at import completion; the Phase-55 promotion
application is the named owner of recomputing scores affected by
newly applied correlations. A stored score is otherwise stale-prone;
readers must treat `count` as ground truth and `smoothed_score` as a
cache with a named maintainer.

### 5. MFS prior — Sense node property

The MFS fallback needs a per-sense scalar; no frequency/rank data
exists anywhere in the shipped lexicon (the OEWN importer records no
sense ordering — Phase 51 R0 grounding). This ADR names the property;
**Phase 52 populates it** from SemCor counts:

- `corpus_frequency` (INT, on `Sense` nodes; clean against
  `RESERVED_PROPERTY_KEYS`) — raw sense-tagged occurrence count.
  MFS for a lemma = argmax over its senses' `corpus_frequency`.
- **Absence semantics:** when no sense of a lemma carries the
  property, the MFS prior is unavailable; the scorer's behavior
  (family dont-know vs association-only) is Phase 53's contract —
  this ADR only guarantees the property name is settled before the
  importers ship.

### 6. Codec boundary

Edge property bags are **Falkor-primitive only**. ADR-0182's
`_value_json` codec covers node `value` exclusively and is NOT
extended to edges. All properties in §3 are primitives by
construction; future empirical-layer additions must stay primitive or
trigger an explicit ADR-0182 amendment.

### 7. Discipline and writers (PB-W21 — unchanged)

`lexicon` stays `ADMIN_AUTHORED`. The only writers of empirical-layer
edges are: (a) the Phase-52 bootstrap importers (admin path), and
(b) the Phase-55 promotion application (admin path). ALL runtime
learning routes through the S10 promotion loop (miner →
`parameter-staging` (Local) → `pending-promotions` → admin
application). Zero discipline exceptions; no runtime-writer surface
ships in this ADR.

### 8. DOLCE stratum — name reserved, home NOT here

The "DOLCE/FrameNet correlation stratum" (PB-W14 layer 2) is reserved
**by name only**. It is geometrically NOT a lexicon EdgeType: DOLCE
classes live in the ontology graph and edges are intra-graph — this
vocabulary cannot reach them. Its home (likely alignment-anchor-based)
is decided at Phase 56 R0 with the DWF alignment-density number in
hand. Nothing in this ADR pre-commits the encoding.

## Consequences

- Phase 52 importers have a fully named write target (edge types,
  properties, identity rule, MFS property) before they are designed.
- Phase 53's scorer reads rel-type-filtered traversals per role —
  index-friendly (the lookup index lands with ADR-0181's physical
  creation at Phase 52).
- The closed role-set (13) is untouched; no ADR-0150 amendment
  anywhere in the WSD plan (PB-W20 preserved).
- Phase-13 dimensional pins flip once, mechanically.

## Pass criteria binding (phase-map §2 WSD-1)

The empirical-layer schema round-trips through the ADR-0182 persister
path: a lexicon graph carrying `SEL_ASSOC_*` edges with the §3
property set persists and reloads byte-equal (live-marked test;
`InMemoryClient` unit variant for the hermetic gate).
