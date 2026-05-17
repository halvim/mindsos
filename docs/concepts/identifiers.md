---
last_confirmed_phase: 12
---

# Identifiers (L2)

L2 introduces structured, version-qualified IRIs on top of L1's opaque
`node_id` (ADR-0035). L1 treats every id as a blob; L2 adds parse
semantics so the system can route by role, source, and version
without re-scanning each node's properties.

## Why version-qualified

A Knowledge Layer that ingests external sources (DOLCE, OEWN,
FrameNet) needs to keep multiple **versions** of the same source
coexisting in the same Global Metagraph. DOLCE 4.0 and DOLCE 5.0
nodes are different nodes — the version is part of the identity, not
metadata. Encoding the version into the prefix:

```
dolce-dul-4.0:PhysicalObject     # DOLCE 4.0 PhysicalObject
dolce-dul-5.0:PhysicalObject     # different node, different version
```

means a single substring match on the IRI tells you which version a
node belongs to.

## Source prefixes ↔ roles

A **role** is a Knowledge Layer category (ontology, lexicon, concepts,
…). A **source** is a specific dataset that fills that role (DOLCE
fills ontology, OEWN fills lexicon, FrameNet fills concepts). Per
ADR-0045, every L2 source has a dedicated prefix on `_PREFIXES`:

| Source prefix | Role |
|---|---|
| `dolce-dul-` | ontology |
| `oewn-` | lexicon |
| `framenet-` | concepts |
| `promoted-pipelines-` | promoted-pipelines (upper-layer) |
| `task-patterns-` | task-patterns (upper-layer) |
| `memories-` | memories (upper-layer; Local-per-user per ADR-0044) |
| `problem-trace-` | problem-trace (upper-layer) |
| `capacity-state-` | capacity-state (upper-layer; Local-per-user) |

## Kind sub-prefixes

Some roles partition their nodes by a sub-kind (synset / sense / lemma
inside OEWN, frame / lu / fe inside FrameNet, pipeline / step inside
promoted-pipelines, etc.). The kind is a fixed table per role
(`_KINDS_PER_ROLE` in `identifiers.py`), so adding a new sub-kind is
a 2-line edit.

DOLCE has no kind sub-prefix — its bodies are bare fragments.
`capacity-state` extracts `snapshot:` but leaves the rest opaque
because the body embeds a colon-bearing `capacity_iri` (ADR-0066).

## user_id in the IRI

Per ADR-0044, `memories` and `capacity-state` are Local-per-user roles.
Their IRIs bake in the `user_id`, so two users' memories never collide
even when memory_ids are minted independently. The `user_id` charset
is restricted to `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$` (ADR-0044
§amendment-1) to keep the IRI parseable.

## L1 doesn't import L2

ADR-0014 keeps L1 Core-only-imports. The IRI parser lives in
`mindsos_knowledge`, not `mindsos_core`. L1's `IRIPassthroughStrategy`
(Phase 02) validates non-empty-string only; structural parsing is an
L2 concern.

## See also

* [API reference: `identifiers`](../api/knowledge/identifiers.md)
* [API reference: `REF_TYPES`](../api/knowledge/ref-types.md)
* [L1 concept: `identity`](identity.md) — L1's opaque-id stance.
* ADR-0035 (UUID generation non-deterministic), ADR-0044 (memories
  Local + user_id), ADR-0045 (per-role IRI builders), ADR-0047
  (REF_TYPES open vocabulary), ADR-0066 (capacity IRI form),
  ADR-0067 (REF_TYPES shared with KL).
