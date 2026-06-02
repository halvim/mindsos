# Phase 4 Pilot Report — Adjective + Adverb mapping (100 synsets)

**Date:** 2026-04-22
**Status:** Pilot complete — **awaiting your sign-off on the rule set before scaling to all 21,833 adj/adv synsets.**

## Context

Neither Gangemi 2003 nor Silva 2018 covered adjectives and adverbs; they are explicitly listed as future work. This pilot is the first pass at mapping them for our DOLCE-Lite / DULplus alignment. I want your sign-off on the rules before we commit to 21,833 assignments.

## The conceptual basis

Gangemi 2003 §"Quality vs Quale" distinguishes:

- **Quality** — the particular inhering in an entity (the redness of *this* rose).
- **Quale** — the value/position in a quality space (the shade of red = a region in colour space).

Adjectives predicate qualities of entities — *red*, *heavy*, *tall*. Adverbs predicate qualities of events or of other qualities — *quickly* (manner of a perdurant), *yesterday* (temporal region), *here* (spatial region), *very* (degree). So:

- **Adjectives → `dul:Quality`** (default), with `dul:PhysicalAttribute` for measurable physical properties (colour, weight, size, temperature, etc.).
- **Adverbs → `dul:Region`** (default = quality region / quale), with sub-classes for temporal (`dul:TimeInterval`), spatial (`dul:SpaceRegion`), and modal/epistemic (`dul:Abstract`) contexts.

## Proposed rule set

### Adjective rules

| ID | Rule | Target class |
|---|---|---|
| **A1** | Satellite (`pos='s'`) inherits its head via `wn:similar` | head's class |
| **A2** | Pertainym adjective (from `adj.pert.yaml`, gloss opens "of or relating to…") | `dul:Quality` |
| **A3** | Participial adjective (from `adj.ppl.yaml`, deverbal) | `dul:Quality` |
| **A4** | Gloss contains physical-attribute keyword (colour, size, weight, temperature, texture, taste, smell, sound, brightness, speed) | `dul:PhysicalAttribute` |
| **A5** | Descriptive head (adj.all, default) | `dul:Quality` |

### Adverb rules (applied in order; first match wins)

| ID | Rule | Target class |
|---|---|---|
| **R1_adv** | Gloss opens "in a [adj] manner/way/style/fashion" | `dul:Region` |
| **R4_adv** | Gloss contains frequency marker (*always, often, rarely, never*) but no temporal marker | `dul:Region` |
| **R2_adv** | Gloss contains temporal marker (*era, period, past, future, year, historically*) | `dul:TimeInterval` |
| **R3_adv** | Gloss contains spatial marker (*place, position, direction, upward, north, here, there*) | `dul:SpaceRegion` |
| **R5_adv** | Gloss contains degree marker (*degree, extent, extremely, slightly*) | `dul:Region` |
| **R6_adv** | Gloss contains modal marker (*possibly, probably, certainly, likely*) | `dul:Abstract` |
| **R7_adv** | Default | `dul:Region` |

## Pilot results (100 synsets)

Stratified sample: 25 adj.all heads, 15 adj.all satellites, 8 adj.pert, 2 adj.ppl, 50 adverbs.

### Rule distribution in the pilot

- Adjective heads: 23 `dul:Quality` + 2 `dul:PhysicalAttribute` (saturated, monochromatic — both colour-related)
- Adjective satellites: 13 inherited `dul:Quality`, 2 inherited `dul:PhysicalAttribute` (deep, biggish)
- Pertainyms: 8 `dul:Quality`
- Participials: 2 `dul:Quality`
- Adverbs: 20 R1 manner, 4 R5 degree, 2 R2 temporal, 2 R3 spatial, 22 R7 default

### Quality assessment (manual review of all 100)

- **Adjective heads (25/25 defensible).** `dul:Quality` is the correct default; the 2 PhysicalAttribute flips (colour-saturation, monochromatic light) are right.
- **Adjective satellites (15/15 consistent).** Inheritance works — `biggish` correctly inherits from the `large`-sized head.
- **Pertainyms (8/8 correct as `dul:Quality`).** Relational adjectives are qualities of an entity's relation to a referent (e.g., *Venezuelan* = quality of being related to Venezuela). All 8 fit.
- **Participials (2/2 correct).** `mounded over`, `hypophysectomized` — both participial, both quality.
- **Adverbs (45–47/50 correct).** Manner adverbs (R1) all look right. Temporal (R2) `per annum`, `prematurely` — correct. **Three questionable cases:**
  - `at a loss` (gloss: "below cost") → R3 `dul:SpaceRegion` — **false positive**: "below" is metaphorical here (about money), not spatial. Should be `dul:Region` (degree-like).
  - `aback` (gloss: "by surprise") → R7 default `dul:Region` — actually archaic/spatial sense ("taken aback"); gloss doesn't reveal this. Acceptable default.
  - Some "in a X manner" adverbs where the gloss phrasing is "in a manner X-characteristic" (zero words between article and "manner") fell through to R7 default. Minor regex adjustment needed.

Overall: **~95–97% of pilot assignments are semantically correct.** The main weakness is idiom handling (finance idioms like *at a loss* trip spatial rules). I propose one rule tweak before we scale:

**Rule tweak — add R0_adv (idiom guard):** If gloss begins with "(of X)" domain marker or contains "cost/price/money/value" while also triggering R3 spatial → do *not* apply R3; fall through to default. This catches *at a loss*, *below cost*, *at par* without losing genuine spatial adverbs.

## Projected full coverage if rules applied to all 21,833 synsets

| Group | Count | Likely class breakdown |
|---|---:|---|
| adj.all heads | 3,779 | 3,563 Quality + 216 PhysicalAttribute |
| adj.all satellites | 10,717 | Inherit from heads (mostly Quality) |
| adj.pert | 3,663 | All Quality |
| adj.ppl | 60 | All Quality |
| adv.all | 3,614 | ~1,263 manner (R1) + 109 temporal + 190 spatial + 179 degree + 39 frequency + 9 modal + 1,825 default |
| **Total** | **21,833** | — |

That would complete POS coverage: **81,143 + 21,833 = 102,976 OEWN synsets mapped — roughly 95.8% of the 107,518 universe.**

## Open questions for you

Before I scale, I want your answer on three design questions:

1. **Are `dul:Quality` and `dul:Region` the right default targets?** Alternatives:
   - Use DOLCE-Lite's granular subtypes: `physical-quality`, `abstract-quality`, `temporal-quality`, `physical-region`, `abstract-region`, `quality-space`.
   - Stick with DULplus's coarser `Quality` / `Region`.
   My preference is DULplus for consistency with Phases 1–3; we can subclassify further in a Phase 5 pass if needed.
2. **Should satellites inherit *only* the head's class, or also the head's full attribute-link?** The latter would give us richer RDF (e.g., `biggish → Quality of StatureAttribute`). More work, more reviewable.
3. **Should pertainym adjectives carry a separate target class (`dul:RelationalQuality` or similar)?** DULplus doesn't have a dedicated relational-quality class, so I defaulted them to `dul:Quality`. If you want them distinguished, we'd either (a) use an external class like SKOS's `relatedMatch`, or (b) keep them as `dul:Quality` and add a relational annotation in the TTL.

## Deliverables

- [`phase4-pilot-adj-adv.tsv`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/phase4-pilot-adj-adv.tsv) — all 100 pilot rows with proposed class, rule, rationale, and a blank `user_decision` column.
- [`phase4-pilot-stats.json`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/phase4-pilot-stats.json) — projected distribution for full scale-up.
- [`phase4_pilot_adj_adv.py`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/phase4_pilot_adj_adv.py) — reproducible pilot script.

## What I need from you

Three quick responses:

**(a) Accept the rule set as-is, or with the R0_adv idiom guard added?**
**(b) Accept `dul:Quality` / `dul:Region` as the coarse defaults, or use DOLCE-Lite's finer-grained subtypes?**
**(c) Keep pertainyms as `dul:Quality` with a relational annotation, or separate class?**

Pick (a=add guard, b=DULplus coarse, c=annotation) and I'll scale to all 21,833 synsets. Or pick differently — I'll adjust before execution either way.
