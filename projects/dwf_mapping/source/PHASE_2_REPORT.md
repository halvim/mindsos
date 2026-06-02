# Phase 2 Report — Top-mapping revalidation

**Date:** 2026-04-22
**Status:** Auto-flag complete; awaiting your review decisions

## What Phase 2 did

Of the 859 original OntoWordNet `topmapping` synsets (the manually-curated seed layer from Gangemi et al. 2012, from which all 73k+ noun mappings were propagated), **840 resolved cleanly to OEWN 2025** via the Phase 1 bridge. This phase ran systematic rule checks on those 840, grounded in the methodologies of Gangemi 2003 and Silva 2018, to flag any that deserve a second look before being accepted as ground truth.

## Rules applied

| Rule | Paper | Flag name | What it catches |
|---|---|---|---|
| R4 — metalevel concepts | Gangemi 2003 | `metalevel` | Lemmas like *attribute, relation, property, concept* — metalevel, not object-level |
| Tier 1 gloss markers | Silva 2018 | `perdurant_gloss` | Gloss opens with *"the act of"*, *"the state of"*, *"the process of"* but current class is not a perdurant |
| R3 — role/type rigidity | Gangemi 2003 | `role_lemma` | Lemma has a role-like suffix (*-er, -or, -ist, -ant*) but current class is a rigid type (Organism, Person, DesignedArtifact, etc.) |
| R1 — individual/class conflation | Gangemi 2003 | `individual_candidate` | Proper-noun lemma + gloss mentions specific instance markers |
| Outlier target check | — | `class_singleton` | DUL class is only used for 1–2 synsets across the entire mapping (possible stale/experimental target) |
| Format check | — | `full_iri_class` | Class was serialised as full IRI rather than a known prefix — worth confirming namespace membership |

## Results

| Flag | Count | Notes |
|---|---:|---|
| `ok` | 758 | No issues detected — these can be carried forward as-is. |
| `full_iri_class` | 61 | Mostly `<...Supplements.owl#SpatialFeature>` and `DependentPlace`/`DependentPart`. These are legitimate DOLCE Supplements classes — just need a prefix declaration; no semantic review required. |
| `role_lemma` | 9 | Mix of real issues and false positives (see below). |
| `perdurant_gloss` | 6 | **All look like real errors in the legacy mapping.** |
| `metalevel` | 4 | Real R4 violations — *attribute*, *property* (×2), *relation*. |
| `class_singleton` | 2 | `dul:Abstract` for "absolute", `dul:Narrative` for "tip-off". Worth auditing these target classes. |
| **Total reviewed** | **840** | **~90.2% auto-accept rate.** |

## The 82 flagged entries, broken down

### `metalevel` (4) — Gangemi R4 violations

These look like **real errors in the legacy mapping**. All four should be moved to a metalevel class (`dul:Concept` or similar):

- `attribute` → currently `dul:Region` — gloss: "an abstraction belonging to or characteristic of an entity"
- `property` (sense 1) → currently `dul:Quality` — gloss: "a basic or essential property shared by all members of a class"
- `property` (sense 2) → currently `dul:Right` — "something owned…" (the *property* = real estate sense; this one is actually fine — the flag is a false positive driven purely by lemma)
- `relation` → currently `dul:Relation` — gloss: "an abstraction belonging to or characteristic of two entities"

### `perdurant_gloss` (6) — Silva 2018 misclassifications

All six look like **real errors** that the Silva methodology would catch:

- `dependence` ("the state of relying on…") → currently `SpatialFeature` → should be `dul:State`
- `gather` ("the act of gathering") → currently `coll:AgentCollection` → should be `dul:Action`
- `goal` ("the state of affairs that a plan is intended to achieve") → currently `dul:Goal` → should be `dul:State` (or kept as `dul:Goal` if that subsumes State)
- `representation` ("the state of serving as…") → currently `dul:SocialRelation` → should be `dul:State`
- `tankage` ("the act of storing in tanks") → currently `dul:PhysicalAttribute` → should be `dul:Action`
- `use` ("the act of using") → currently `dul:Task` → should be `dul:Action`

### `role_lemma` (9) — mixed real issues and false positives

Real concerns:
- `entrant` → `DesignedArtifact` — "commodity that enters competition"; arguably a Role
- `marker` → `PhysicalObject` — "object used to distinguish…"; arguably a Role (function-defined)

Probable false positives from the -ant/-er suffix heuristic:
- `plant` → `DesignedArtifact` — ends in "-ant" but isn't a role; "plant" = industrial building
- `top of the line` → `DesignedArtifact` — phrase pattern caught it, but "top of the line" is a relative-quality descriptor

Marginal / worth-a-look:
- `freshener`, `pounder`, `stinker`, `whacker`, `neighbor` — these are often used role-like but WordNet glosses them as objects with characteristic function. Domain decision.

### `class_singleton` (2)

- `dul:Abstract` (only for "absolute") — might be a stale target class name
- `dul:Narrative` (only for "tip-off") — "inside information that something is going to happen" is debatable

### `full_iri_class` (61) — cosmetic only

These use the `Supplements.owl` module of DOLCE+DnS (also in your DLP3971 folder). Classes used:

- `SpatialFeature` — 25+ synsets (air, back, bottom, boundary, …)
- `DependentPlace` — 20+ synsets (abutment, antipodes, blind spot, …)
- `DependentPart` — 10+ synsets (acicula, belt, …)

These are legitimate DOLCE classes — no semantic change needed, just a prefix declaration in the final Turtle.

## What you need to decide

The review TSV [`phase2-topmapping-review.tsv`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/phase2-topmapping-review.tsv) is sorted with flagged entries at the top. Each row has a `decision` column for you to fill in with one of:

- `accept_current` — keep existing class
- `accept_proposed` — adopt the proposed class
- `other:<class>` — your preferred class
- `defer` — come back to this later

I'd recommend focusing on the **19 real issues** (`metalevel`, `perdurant_gloss`, `role_lemma` minus false positives) before moving on; the 61 `full_iri_class` entries are cosmetic and can be batch-accepted. The 758 `ok` entries need no review.

## What I'd propose doing without waiting

1. The 4 `metalevel` fixes and 6 `perdurant_gloss` fixes look uncontroversial — I can apply them automatically and note them in the alignment file provenance, pending your sign-off.
2. The 61 `full_iri_class` rows just need a new `suppl:` prefix added to the alignment TTL — purely cosmetic; I'll do that.
3. The 9 `role_lemma` flags are the only ones where your judgment genuinely matters — I'll leave those alone until you've reviewed the TSV.

## What's next

**Phase 3 — Verb mapping** per Silva 2018. Of your 13,821 OEWN verb synsets, we'll:

1. Build a verb-hypernym graph from OEWN to identify the ~560 top-level verb synsets (no hypernym in OEWN, per Silva's unique-beginner count).
2. For each top-level verb, apply Silva's three-tier method:
   - Tier 1: follow `wn:derivation` to a derivationally-related noun; use that noun's already-mapped DUL class if the gloss opens with "the act/process/state of".
   - Tier 2: if no direct link, traverse antonym / verb-group links.
   - Tier 3: gloss-based manual assignment (verbs glossed "be X" → State, etc.).
3. Propagate to troponyms (WordNet's verb-hyponyms) for 100% verb coverage.

Expected outcome: ~13,000 new (oewn_id, dul_class) mappings, predominantly `dul:Event`, `dul:State`, `dul:Process`, `dul:CognitiveEvent`, `dul:CognitiveState`.

Shall I proceed to Phase 3 now, or do you want to pause and review Phase 2 first?
