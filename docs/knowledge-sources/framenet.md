---
last_confirmed_phase: 15a
---

# FrameNet concepts source

Phase 15a's `FrameNetImporter` reads the **Berkeley FrameNet 1.7**
XML distribution and writes it into the `concepts` Global role-graph
per [ADR-0150](../decisions/adr/0150-l2-knowledge-lifecycle.md).

## Pin

* **Version:** FrameNet 1.7 (Phase 15a PB-6 lock).
* **Source URL:** https://framenet.icsi.berkeley.edu/fndrupal/framenet_request_data
* **License:** Berkeley click-through agreement — **NOT
  repo-shippable** and **NOT auto-downloadable**.
* **Format:** XML — one file per frame in `frame/*.xml`, plus
  `frRelation.xml` for cross-frame relations. Parser: `lxml` (with
  stdlib `xml.etree.ElementTree` fallback).

## Manual download (required)

1. Visit the Berkeley FrameNet release page (URL above).
2. Accept the click-through license.
3. Download `fndata-1.7.zip`.
4. Extract the contents to `data/datasets/framenet-1.7/` such that
   the directory contains `frame/` (per-frame XMLs) and
   `frRelation.xml`.

The `scripts/fetch_datasets.{sh,py}` helpers refuse to fetch
FrameNet — they only print this instruction. The license cannot be
auto-accepted on your behalf.

Synthetic test fixture (license-safe; content fabricated) at
`tests/phase_15a/fixtures/framenet_synth.xml`. The single-file
fixture and the Berkeley directory layout are both supported by
`FrameNetImporter` (`path.is_dir()` auto-detect).

## Import command

```sh
mindsos admin import framenet \
    --source data/datasets/framenet-1.7/ \
    --version 1.7 \
    --json
```

## Expected stats

| Key | What it counts |
|---|---|
| `frames` | `<frame>` declarations |
| `frame_elements` | `<FE>` declarations (per-frame) |
| `lexical_units` | `<lexUnit>` declarations |
| `has_fe_edges` | `Frame → FrameElement` (`HAS_FE`) |
| `evokes_edges` | `LexicalUnit → Frame` (`EVOKES`) |
| `frame_relations` | `<frameRelation>` rolled into typed edges (inherits, uses, etc.) |
| `fe_mappings_edges` | `<FERelation>` cross-frame FE alignments (`FE_MAPPED_TO`) |

IRIs minted via `framenet_frame_iri(version, frame_id)` /
`framenet_fe_iri(version, frame_id, fe_id)` /
`framenet_lu_iri(version, lu_id)` per
[ADR-0045](../decisions/adr/0045-per-role-iri-builders.md).

## Relation-type mapping

FrameNet frame-relation types → MindsOS `EdgeType` names (defined in
`mindsos_knowledge.schemas.concepts`):

| FrameNet type | MindsOS EdgeType |
|---|---|
| `Inheritance` | `INHERITS_FROM` |
| `Using` | `USES` |
| `Perspective_on` | `PERSPECTIVE_ON` |
| `Subframe` | `SUBFRAME_OF` |
| `Precedes` | `PRECEDES` |
| `Causative_of` | `IS_CAUSATIVE_OF` |
| `Inchoative_of` | `IS_INCHOATIVE_OF` |

Unmapped relation types are silently skipped; expand
`_FRAME_REL_MAP` in `mindsos_admin/importers/framenet.py` as needed.

Frame-relation direction: child frame → parent frame (sub inherits
from super). FE mappings nested inside a `<frameRelation>` are
emitted as `subFE → superFE` `FE_MAPPED_TO` edges.

## Alignment with OEWN

The OEWN-FrameNet alignment pair-graph (`alignment:lexicon:concepts`)
is a Phase 15b deliverable per
[admin-global-shipping.md](../concepts/admin-global-shipping.md).
Berkeley FrameNet publishes its own WN-mapping; Phase 15b's
`AlignmentsImporter` consumes it.
