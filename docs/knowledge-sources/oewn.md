---
last_confirmed_phase: 15a
---

# Open English WordNet (OEWN) lexicon source

Phase 15a's `OewnImporter` reads the **Open English WordNet 2024**
LMF distribution and writes it into the `lexicon` Global role-graph
per [ADR-0150](../decisions/adr/0150-l2-knowledge-lifecycle.md).

## Pin

* **Version:** OEWN 2024 (Phase 15a PB-6 lock).
* **Source URL:** https://en-word.net/static/english-wordnet-2024.xml.gz
* **License:** CC-BY-SA 4.0 — repo-shippable; downloader fetches
  ungz'd version (~30 MB).
* **Format:** OEWN-LMF XML (Lexical Markup Framework dialect).
  Parser: `lxml` (with stdlib `xml.etree.ElementTree` fallback for
  environments without lxml).

## Download

```sh
scripts/fetch_datasets.sh oewn
# or:
python scripts/fetch_datasets.py oewn
```

Real dataset lands at `data/datasets/oewn-2024.xml` (gitignored).
Synthetic test fixture at `tests/phase_15a/fixtures/oewn_synth.xml`.

## Import command

```sh
mindsos admin import oewn \
    --source data/datasets/oewn-2024.xml \
    --version 2024 \
    --json
```

## Expected stats

| Key | What it counts |
|---|---|
| `synsets` | `<Synset>` declarations |
| `lemmas` | Distinct `(writtenForm, partOfSpeech)` from `<Lemma>` |
| `senses` | `<Sense>` declarations |
| `has_sense_edges` | `Lemma → Sense` (`HAS_SENSE`) |
| `in_synset_edges` | `Sense → Synset` (`IN_SYNSET`) |
| `synset_relations` | `<SynsetRelation>` rolled into typed edges (hypernym, hyponym, meronym families, etc.) |
| `sense_relations` | `<SenseRelation>` rolled into typed edges (antonym, derivation) |

IRIs minted via `oewn_synset_iri(version, synset_id, pos)` /
`oewn_sense_iri(version, sense_id)` /
`oewn_lemma_iri(version, lemma, pos)` per
[ADR-0045](../decisions/adr/0045-per-role-iri-builders.md).

## Relation-type mapping

OEWN-LMF rel-types → MindsOS `EdgeType` names (defined in
`mindsos_knowledge.schemas.lexicon`):

| OEWN rel-type | MindsOS EdgeType |
|---|---|
| `hypernym` | `HYPERNYM_OF` |
| `hyponym` | `HYPONYM_OF` |
| `instance_hypernym` | `INSTANCE_HYPERNYM_OF` |
| `instance_hyponym` | `INSTANCE_HYPONYM_OF` |
| `mero_part` / `mero_member` / `mero_substance` | `MERONYM_*` |
| `holo_part` / `holo_member` / `holo_substance` | `HOLONYM_*` |
| `similar` | `SIMILAR_TO` |
| `antonym` (sense-level) | `ANTONYM_OF` |
| `derivation` (sense-level) | `DERIVATIONALLY_RELATED_TO` |

Unmapped OEWN rel-types are silently skipped; expand the map in
`mindsos_admin/importers/oewn.py` (`_SYNSET_REL_MAP` /
`_SENSE_REL_MAP`) as schema coverage grows.
