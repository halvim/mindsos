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


# ── Episode lifecycle state (Dream PRE-0 Slice 1b) ────────────────────
#
# The streaming Episode carries a mutable ``state`` metadata property that
# tracks its open->grow->close lifecycle (dream-episode-model, locked w/ HA
# 2026-07-27). ``open`` = the request is in flight OR the session crashed
# before a decision (the ONLY failure); ``closed`` = a terminal decision was
# reached (solved / dont_know / conceded — all successes) OR a crash was
# recovered + recorded; ``suspended`` = needs-input / pending-confirmation
# (resumes; NOT a crash). Crash recovery scans for ``state == open``.

EPISODE_STATE_OPEN = "open"
EPISODE_STATE_CLOSED = "closed"
EPISODE_STATE_SUSPENDED = "suspended"

EPISODE_STATES: frozenset[str] = frozenset({
    EPISODE_STATE_OPEN,
    EPISODE_STATE_CLOSED,
    EPISODE_STATE_SUSPENDED,
})


# ── Episode content / metadata partition (Phase 43 — ADR-0152 §7 + ADR-0153 §3;
#    restructured Dream PRE-0 Slice 1b D1) ──
#
# Dream PRE-0 Slice 1b (D1): the Episode's fields are stored as real L1 node
# **properties** (not an opaque ``value`` blob), so the streaming lifecycle can
# edit them field-by-field through ``KLWriteHandle.update_and_validate`` (Slice
# 1a). ``state`` is the sole METADATA field (freely mutable — it flips
# open->closed/suspended through the lifecycle). The 8 CONTENT fields stay
# frozen except via the retire-time lazy-inline (``via_lazy_inline=True``): they
# are written once when known — ``request_input_ref`` / ``request_input_root_ref``
# at open; ``mm_root_ref`` / ``capacity_root_ref`` / ``request_pattern_iri`` /
# ``outcome_classification`` / ``consolidated_at`` at close; ``crash_marker`` only
# on a recovered crash (Chat B D-B50). ``append_only_with_lazy_inline`` discipline
# unchanged (ADR-0153 §1).

EPISODE_CONTENT_FIELDS: frozenset[str] = frozenset({
    "request_input_ref",
    "request_input_root_ref",
    "mm_root_ref",
    "capacity_root_ref",
    "request_pattern_iri",
    "outcome_classification",
    "crash_marker",
    "consolidated_at",
})

EPISODE_METADATA_FIELDS: frozenset[str] = frozenset({
    "state",
})

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
