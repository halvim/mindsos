"""Learned-pipelines role-graph schema (ADR-0203 — NET-NEW).

First-class **Local** persistence surface for taught ``ConjunctionFinder``
pipelines. A brain composes a converging capacity DAG at runtime
(``mindsos_capacity.pipeline.Pipeline``) and teaches it under a name; this
role is where that taught pipeline lives so it survives a boot (F9) and
appears in ``mindsos brain pl``.

Single NodeType (``LearnedPipeline``); **no EdgeTypes** — this role mirrors
the ``learned_parameters`` / ``request_patterns`` zero-edge shape. Cross-version
lineage (a ``DERIVED_FROM``-style edge, à la promoted pipelines) is
deliberately NOT modelled (ADR-0203 §Decision #2 → "no edges"): latest is
resolved by an append-ordinal scan, not by a lineage link.

**Value contract (ADR-0203 §Decision + ADR-0182).** ``LearnedPipeline.value``
is the *full* ``Pipeline.to_dict()`` blob — an OPAQUE ADR-0182 ``_value_json``
payload carrying all four keys ``{start_datastates, target_datastate, steps,
edges}``. It is emphatically **not** an L2 per-field step schema: enumerating
step internals would duplicate the shipped ADR-0182 codec and re-expose the
deferred D38 hyperedge shape (ADR-0203 §Problems P4). The typed accessor is
``Pipeline.from_dict(node.value)``; validation = ``from_dict`` succeeds AND
every ``capacity_iri`` resolves AND the DAG reaches ``target_datastate`` (the
writer/consumer's obligation, ADR-0203 §P2).

**Discipline = ``immutable_successor``** (ADR-0203 §Decision #Q4). A taught
pipeline is a *structure*, not a continuously re-estimated weight, so
``mutable_with_retention`` (learned_parameters' Local discipline) is wrong for
it. ``immutable_successor`` is only a content-field immutability guard
(``validators.py`` — it forbids in-place edits to content fields; it does NOT
mint or link a successor and there is no active-version routing, which is
vacated + locked per ADR-0150 §am-3). Re-teaching a name therefore **appends**
a new immutable node stamped with the next monotonic ``taught_seq`` ordinal
(metadata); the reader groups by ``pipeline_name`` and returns ``max(taught_seq)``.
This copies the ``request_patterns`` / ``installed-skills`` append-ordinal
precedent verbatim (``mindsos_server/skills/records.py``).

**Content / metadata partition (ADR-0153 §3).** ``pipeline_name`` is content
(frozen, set-once — matches ``immutable_successor``'s fixture). ``taught_seq``
+ ``recorded_at`` are metadata (writable) — the append ordinal is metadata
since content is frozen. The ``to_dict`` blob rides on ``node.value`` (opaque,
never lifted; ADR-0182 rule 5), so it is not a partitioned *property*; the
partition below covers the flat queryable properties only.

``strict=False`` per ADR-0149.
"""

from __future__ import annotations

from mindsos_core import NodeType

from ._base import Discipline, L2Schema


# ── Node type ──────────────────────────────────────────────────────────

NODE_LEARNED_PIPELINE = "LearnedPipeline"

LEARNED_PIPELINES_NODE_TYPES: tuple[str, ...] = (NODE_LEARNED_PIPELINE,)


# ── Edge types ─────────────────────────────────────────────────────────

LEARNED_PIPELINES_EDGE_TYPES: tuple[str, ...] = ()  # zero-edge role (ADR-0203 #2).


# ── Content / metadata partition (ADR-0203 §Decision #Q4 + ADR-0153 §3) ──
#
# ``pipeline_name`` is the only content property (frozen, set-once). The
# ``Pipeline.to_dict()`` blob rides on ``node.value`` (opaque codec payload),
# not as a flat property, so it is not enumerated here. ``taught_seq`` (the
# append ordinal) + ``recorded_at`` are metadata.

LEARNED_PIPELINE_CONTENT_FIELDS: frozenset[str] = frozenset({
    "pipeline_name",
})

LEARNED_PIPELINE_METADATA_FIELDS: frozenset[str] = frozenset({
    "taught_seq",
    "recorded_at",
})

LEARNED_PIPELINE_PROPS: frozenset[str] = (
    LEARNED_PIPELINE_CONTENT_FIELDS | LEARNED_PIPELINE_METADATA_FIELDS
)


def build_learned_pipelines_schema(strict: bool = False) -> L2Schema:
    """Construct the learned-pipelines role Schema.

    Local-only, single NodeType (``LearnedPipeline``), no EdgeTypes,
    discipline ``immutable_successor`` (ADR-0203). ``strict`` defaults to
    ``False`` per ADR-0149.
    """
    s = L2Schema(
        mutation_discipline=Discipline.IMMUTABLE_SUCCESSOR, strict=strict
    )

    for nt in LEARNED_PIPELINES_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    # No EdgeTypes per ADR-0203 §Decision #2 (zero-edge mirror).
    return s


__all__ = [
    "NODE_LEARNED_PIPELINE",
    "LEARNED_PIPELINES_NODE_TYPES",
    "LEARNED_PIPELINES_EDGE_TYPES",
    "LEARNED_PIPELINE_CONTENT_FIELDS",
    "LEARNED_PIPELINE_METADATA_FIELDS",
    "LEARNED_PIPELINE_PROPS",
    "build_learned_pipelines_schema",
]
