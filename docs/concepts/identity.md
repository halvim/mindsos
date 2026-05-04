---
title: Identity and IRIs
tag: shipped
last_confirmed_phase: 02
teaser: IdentityRegistry scope, stable version-qualified IRIs, and why this matters.
source: mindsos_core/models/identity.py
next: concepts/instancing.md
---

# Identity and IRIs

Every node needs a unique identifier — something that distinguishes it
from all other nodes in the system and survives persistence and
reconstruction. MindsOS uses two different identifier schemes depending
on where the node comes from and what stability guarantee you need.

!!! info "Quick facts"
    - **Identity scope:** scoped to one Metagraph, not global
    - **Default IDs:** UUIDs (non-deterministic, per ADR-0035)
    - **Imported nodes:** version-qualified IRIs (deterministic, stable
      across re-import — Knowledge Layer convention, Phase 12+)
    - **Re-import:** same IRI = same node, even years later
    - **Core treats `node_id` as opaque.** It does not parse IRIs. IRI
      parsing (role / source / version / kind) lives in
      `mindsos_knowledge` (L2) and ships in Phase 12.

## The IdentityRegistry

Every `Metagraph` owns an `IdentityRegistry` — a set that tracks which
node, edge, and hyperedge ids have been assigned. When you create a new
element in the metagraph (by calling `graph.add_node(...)` or any add
method), the registry assigns it a fresh UUID and records the
assignment.

The registry is **metagraph-scoped**, not global. If you create two
separate metagraphs (e.g., a Global Knowledge metagraph and an Alice's
Local Knowledge metagraph), each has its own registry. This means:

- UUIDs generated in Global will never collide with UUIDs generated in
  Alice's Local, by construction.
- Cross-metagraph references (e.g., "Alice's node X points to Global
  node Y") are safe because the ids are unique within each metagraph.
- If you later merge two metagraphs, id collisions are impossible.

When you add a `Graph` to a metagraph for the first time (via
`metagraph.add_graph(graph)`), if the graph already has its own registry,
it is abandoned — the graph adopts the metagraph's shared registry from
that point forward. This is important: once a graph is in a metagraph,
every element in that graph shares identity scope with every other
element in the metagraph.

Phase 02 ships the registry primitive with a CLI surface — `mindsos
identity registry --register ID --list` — for tester-driven exploration.
That surface persists state to a JSON file scoped by `--scope NAME` so
you can reproduce the duplicate-rejection path interactively. **Treat
this as debug only.** It is not a substitute for the metagraph-scoped
registry that Phase 05 will exercise.

## Pluggable id strategies (ADR-0131)

`IdStrategy` is a Protocol; three implementations ship in Phase 02:

```text
$ mindsos identity strategies
uuid4  mindsos_core.UUID4Strategy
    deterministic: False, ignores_content: True
    Default strategy — non-deterministic UUID4 per call. Content is
    ignored. Matches the historical mindsos_core behaviour.
uuid5  mindsos_core.UUID5FromContentStrategy
    deterministic: True, ignores_content: False
    Deterministic UUID5 derived from canonical (kind, content) under
    NAMESPACE_MINDSOS. Same content + kind always yields the same id.
    Not safe under release auto-upgrade — content-addressable ids
    change with content.
iri    mindsos_core.IRIPassthroughStrategy
    deterministic: True, ignores_content: False
    Returns content['iri'] verbatim when supplied (KL importer
    convention). Falls back to UUID4 when no 'iri' key is present.
    Phase 02 does not parse the IRI — it is treated as opaque.
```

The CLI does not silently default-pin a strategy; `--strategy` is
required on every `mindsos identity mint` invocation (per ADR-0131 and
Phase 02's pass criterion).

## Version-qualified IRIs

For imported data (DOLCE ontologies, OEWN lexicons, FrameNet concepts),
UUIDs are a problem. When you re-import OEWN in a year, you want the same
node to have the same id, so that old memories and references still
work. The solution is a **version-qualified IRI** — an Internationalized
Resource Identifier that encodes source, version, and a stable fragment:

```
oewn-2024:synset:02086723-n
^         ^     ^   ^
source    |     |   fragment
          |     |
       version  kind
```

- **`oewn`:** the source (lexicon identifier)
- **`2024`:** the version (OEWN release year)
- **`synset:02086723-n`:** a stable fragment from the original data

When you import OEWN 2024, this node gets `node_id =
"oewn-2024:synset:02086723-n"`. A year later, when you import OEWN 2025,
the nodes in the new import get `node_id = "oewn-2025:synset:..."` — a
different id, because the version changed. Both versions coexist in the
Knowledge Layer metagraph. Old references that point at
`oewn-2024:synset:02086723-n` still resolve to the old node.

!!! note "Stable IRIs are an importer convention"
    The Core Layer does **not** enforce any IRI format. It accepts any
    string as a `node_id`. The Knowledge Layer's importers (for DOLCE,
    OEWN, FrameNet) mint version-qualified IRIs when they create nodes.
    This is a layer-above-Core decision; Core just persists whatever id
    you give it.

    Phase 02 honours this boundary: there is no IRI parser in
    `mindsos_core`. The `iri` strategy returns `content['iri']`
    verbatim and exits non-zero if the supplied value is empty or
    non-string, but performs no structural decomposition.

## Importer-specific IRI builders (Phase 12, L2)

Each Knowledge Layer importer uses a source-specific builder to mint
IRIs. These builders ship in Phase 12 with the L2 identifiers package:

- **`dolce_iri(version, fragment)`** → `"dolce-dul-4.0:PhysicalObject"`
- **`oewn_synset_iri(version, synset_id, pos)`** → `"oewn-2024:synset:02086723-n"`
- **`oewn_sense_iri(version, sense_id)`** → `"oewn-2024:sense:02086723-01"`
- **`framenet_frame_iri(version, frame_id)`** → `"framenet-1.7:frame:Commerce_buy"`

When you call an importer (Phase 15+), it scans its input
(RDF/JSON/XML) and uses the builder to mint stable IRIs for every
element it finds. These IRIs become the `node_id` of every created
node.

## What "stable" means

An IRI is **stable** when you can re-run the importer on the same source
data and get the same IRI for the same conceptual element. This holds
for OEWN because the fragment comes directly from the OEWN source data
(the synset id, sense key, etc.). If you update the source to version
2025, the fragment usually stays the same, so the old 2024 version and
the new 2025 version have a clear mapping.

Stability is **per-version**. When OEWN updates, a synset may be merged
with another, deleted, or split. The 2024 version and the 2025 version
have different id spaces. Mapping between them is a Knowledge Layer
concern (see [Global / Local](global-local.md) for how versions
coexist).

## Determinism vs. discovery

Because imported IRIs are deterministic (same source → same IRI every
time), two independent systems importing the same OEWN release will mint
identical ids for corresponding nodes. This is different from
user-authored data, where:

```python
# Every time this runs, different UUID
node = g.add_node(value="my-concept", type_="CustomConcept")
print(node.node_id)  # "a7f3e9c1-...", "b2d4c8a5-...", etc.
```

User-authored graphs and locally-discovered capacities get UUIDs.
Shipped, versioned, imported datasets get IRIs. This split lets the
system distinguish **discovered knowledge** (reproducible, referenceable,
shareable) from **user knowledge** (unique, session-specific, not
necessarily meant to be shared).

## Inference and ref walking

The fact that an IRI encodes source and version does not mean Core
understands those fields. If you have a node with `node_id =
"oewn-2024:synset:02086723-n"`, Core can tell you it's a string and
persist it. But Core does not parse the string, extract the version, or
do anything special with it. That's knowledge-layer work. Core just
keeps the id stable across read/write cycles.

---

**Next:** [Instancing model](instancing.md) — how the Mental Model reuses
knowledge with task-specific overrides.
