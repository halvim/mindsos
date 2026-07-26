"""Episodic-memories role-graph schema (Phase 43 PR2 ship — full body).

Per ADR-0044 §amendment-3 + ADR-0150 §amendment-4 + ADR-0152 §7 +
ADR-0153 §1 + L2_CHAT_DECISIONS D-L2-17. Renamed from ``memories`` to
``episodic_memories`` at Phase 39 (Local-per-user; ADR-0044 invariant
unchanged). Phase 43 PR2 commit 1 fills the body — Episode + Memory
NodeType properties + per-NodeType content/metadata partition + the
within-role-graph ``MEMORY_CONTAINS_EPISODE`` EdgeType.

NodeTypes per Chat B D-B47 + D-B48 + L5 design notes §4.3 + §4.6:

* ``Episode`` — per-task entry; frozen full MM + outcome
  classification; reference-stable per ADR-0153 §4; lazy
  inline-on-retire is the only permitted internal mutation
  (D-B17 + L2_CHAT_DECISIONS D-L2-3 + D-L2-5).
* ``Memory`` — clustering composite over Episodes, keyed by
  ``request_pattern_iri``. Materializes on first episode of a
  request-pattern; subsequent episodes attach via the
  ``MEMORY_CONTAINS_EPISODE`` edge (Phase 43 schema-v2 ship — Chat B
  PB-VV; NOT an embedded list).

**Memory_contains_episode edge form (Phase 43 PR2 impl-time discovery
R6 — recorded in design log §9.1):** ADR-0152 §7 names this edge an
"IntergraphEdge", but `IntergraphEdgeType` lives on
:class:`MetagraphSchema` (per ADR-0148 + Phase 05b), not on the
per-graph :class:`Schema`. Both NodeTypes live in the same
``episodic_memories`` Schema. Phase 43 ships as a regular
:class:`EdgeType` (``MEMORY_CONTAINS_EPISODE``: Memory → Episode);
within-role-graph routing matches the actual data shape per Chat B
D-B47 "inside the same role-graph". MetagraphSchema-level
``IntergraphEdgeType`` registration may be reconsidered if a
cross-role-graph use case surfaces.

``user_id`` is baked into both IRI builders per ADR-0044 §amendment-1
(charset enforced by ``_USER_ID_RE`` at builder-call time).

``strict=False`` per PB-3 / ADR-0149.
"""

from __future__ import annotations

from mindsos_core import EdgeType, NodeType

from ._base import Discipline, L2Schema


# ── Node types ─────────────────────────────────────────────────────────

NODE_EPISODE = "Episode"
NODE_MEMORY = "Memory"

EPISODIC_MEMORIES_NODE_TYPES: tuple[str, ...] = (NODE_EPISODE, NODE_MEMORY)


# ── Edge types ─────────────────────────────────────────────────────────

EDGE_MEMORY_CONTAINS_EPISODE = "MEMORY_CONTAINS_EPISODE"

EPISODIC_MEMORIES_EDGE_TYPES: tuple[str, ...] = (
    EDGE_MEMORY_CONTAINS_EPISODE,
)


# ── Episode content / metadata partition (Phase 43 — ADR-0152 §7 + ADR-0153 §3) ──
#
# 6 content fields (Chat B D-B47). Episode has NO metadata partition in
# v1 — externally append-only; all fields are reference-stable per
# ADR-0153 §4. ``crash_marker`` is set during consolidation per Chat B
# D-B50 when the previous session crashed; once written, immutable like
# other Episode content. Storage tier for ``request_input_ref`` cascades
# through the XRef target's ``storage_mode`` per ADR-0151 (no
# Episode-level ``storage_mode`` declaration per design log §6.1).

EPISODE_CONTENT_FIELDS: frozenset[str] = frozenset({
    "request_input_ref",
    "mm_root_ref",
    "request_pattern_iri",
    "outcome_classification",
    "crash_marker",
    "consolidated_at",
})

EPISODE_METADATA_FIELDS: frozenset[str] = frozenset()

EPISODE_PROPS: frozenset[str] = (
    EPISODE_CONTENT_FIELDS | EPISODE_METADATA_FIELDS
)


# ── Memory content / metadata partition (Phase 43 — ADR-0152 §7) ──
#
# 1 content field (``request_pattern_iri`` — the primary cluster key per
# Chat B D-B47). 3 metadata fields per ADR-0152 §7 — ``rejected_promotions``
# is denormalised list; audit log remains authoritative per D-B47.

MEMORY_CONTENT_FIELDS: frozenset[str] = frozenset({
    "request_pattern_iri",
})

MEMORY_METADATA_FIELDS: frozenset[str] = frozenset({
    "created_at",
    "admin_notes",
    "rejected_promotions",
})

MEMORY_PROPS: frozenset[str] = (
    MEMORY_CONTENT_FIELDS | MEMORY_METADATA_FIELDS
)


def build_episodic_memories_schema(strict: bool = False) -> L2Schema:
    """Construct the episodic_memories role Schema (per-user Local; ADR-0044 §am-3).

    Phase 43 PR2 ship — full body: Episode + Memory NodeTypes,
    ``MEMORY_CONTAINS_EPISODE`` EdgeType (Memory → Episode within the
    same role-graph), per-NodeType content/metadata partition per
    ADR-0152 §7 + ADR-0153 §3, ``append_only_with_lazy_inline``
    discipline per ADR-0153 §1.
    """
    s = L2Schema(
        mutation_discipline=Discipline.APPEND_ONLY_WITH_LAZY_INLINE,
        strict=strict,
    )

    for nt in EPISODIC_MEMORIES_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    # ``MEMORY_CONTAINS_EPISODE`` — Memory → Episode within the
    # episodic_memories role-graph (Chat B D-B46 + D-B47 PB-VV).
    s.add_edge_type(
        EdgeType(
            EDGE_MEMORY_CONTAINS_EPISODE,
            allowed_sources=frozenset({NODE_MEMORY}),
            allowed_targets=frozenset({NODE_EPISODE}),
        )
    )

    return s
