---
last_confirmed_phase: 13
---

# Lexicon role schema

OEWN three-level lexicon vocabulary. **4 NodeTypes, 22 EdgeTypes,
0 HyperEdgeTypes** at `strict=False`.

## NodeTypes

`Lemma`, `Sense`, `Synset`, `SenseExample`.

## EdgeTypes

**Structural:** `HAS_SENSE` (Lemma → Sense), `IN_SYNSET` (Sense → Synset).

**Taxonomic (Synset → Synset):** `HYPERNYM_OF`, `HYPONYM_OF`,
`INSTANCE_HYPERNYM_OF`, `INSTANCE_HYPONYM_OF`.

**Part/whole:** `MERONYM_PART_OF`, `MERONYM_MEMBER_OF`,
`MERONYM_SUBSTANCE_OF`, `HOLONYM_PART_OF`, `HOLONYM_MEMBER_OF`,
`HOLONYM_SUBSTANCE_OF`.

**Verb-synset:** `ENTAILS`, `CAUSES`.

**Misc synset:** `SIMILAR_TO`, `ATTRIBUTE_OF`, `ALSO_SEE`.

**Sense-level:** `ANTONYM_OF`, `DERIVATIONALLY_RELATED_TO`,
`PERTAINS_TO`, `PARTICIPLE_OF`.

**Example attachment:** `HAS_EXAMPLE`.

## Strict-tighten status

`strict=False` (ADR-0149). Glosses, examples, and lex-file metadata
vary per OEWN release.

## Where it's used

Phase 15 (OEWN importer) is the first content consumer.
Phase 14 (KL bootstrap) calls `ensure_role_graph(global_mg, "lexicon")`.
