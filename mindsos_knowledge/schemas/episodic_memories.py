"""Episodic-memories role-graph schema (Phase 39 rename ship — NodeType skeleton only).

Per ADR-0044 §amendment-3 + ADR-0150 §amendment-4 + L2_CHAT_DECISIONS
D-L2-17. Renamed from ``memories`` to ``episodic_memories`` (Local-
per-user; ADR-0044 invariant unchanged). The role now hosts two
NodeTypes per Chat B D-B47 + D-B48 + L5 design notes §4.3 + §4.6:

* ``Episode`` — per-task entry; frozen full MM + outcome
  classification; immutable externally; lazy inline-on-retire is the
  only permitted internal mutation (D-B17 + L2_CHAT_DECISIONS D-L2-3
  ``append_only_with_lazy_inline`` discipline).
* ``Memory`` — clustering composite over Episodes, keyed by
  ``task_pattern_iri``. Materializes on first episode of a task-
  pattern; subsequent episodes attach via ``memory_contains_episode``
  IntergraphEdge (Phase 43 schema-v2 ship — Chat B PB-VV; NOT an
  embedded list).

``user_id`` is baked into both IRI builders per ADR-0044 §amendment-1
(charset enforced by `_USER_ID_RE` at builder-call time).

**Phase 39 scope = NodeType skeletons only.** Per Phase 39 design log
§2 PB-R1-A + PB-R1-B picks:

- EdgeTypes: NONE. Phase 13 legacy ``USED_CAPACITY`` + ``PART_OF_PIPELINE``
  dropped (single-Memory semantics superseded by Chat B Episode +
  Memory-composite split; vestigial edges on a composite would be
  honest schema rot). Phase 43 may re-add edges on the Episode
  NodeType as part of the full D-L2-17 ship.
- Advisory property frozensets (``MEMORY_PROPS`` Phase 13): NONE.
  Properties land at Phase 43 alongside ``CONTENT_FIELDS`` /
  ``METADATA_FIELDS`` / ``mutation_discipline`` apparatus per
  ADR-0153 / ADR-0152 (Rail A schema-v2 slot).
- IntergraphEdge ``memory_contains_episode``: deferred to Phase 43.

``strict=False`` per PB-3 / ADR-0149.
"""

from __future__ import annotations

from mindsos_core import NodeType

from ._base import Discipline, L2Schema


# ── Node types ─────────────────────────────────────────────────────────

NODE_EPISODE = "Episode"
NODE_MEMORY = "Memory"

EPISODIC_MEMORIES_NODE_TYPES: tuple[str, ...] = (NODE_EPISODE, NODE_MEMORY)


def build_episodic_memories_schema(strict: bool = False) -> L2Schema:
    """Construct the episodic_memories role Schema (per-user Local; ADR-0044 §am-3).

    Phase 39 shipped NodeType skeletons only (Episode + Memory). Phase 43
    PR1 commit 4 transcribes discipline (``append_only_with_lazy_inline``
    per ADR-0153 §1); Phase 43 PR2 commit 1 fills the body (per-NodeType
    properties + content/metadata partition + ``memory_contains_episode``
    IntergraphEdge per ADR-0152 §7 + D-L2-17).
    """
    s = L2Schema(
        mutation_discipline=Discipline.APPEND_ONLY_WITH_LAZY_INLINE,
        strict=strict,
    )

    for nt in EPISODIC_MEMORIES_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    return s
