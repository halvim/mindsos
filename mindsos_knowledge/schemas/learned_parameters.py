"""Learned-parameters role-graph schema (Phase 43 — Rail A slot 2 NET-NEW).

Per ADR-0152 §6 + L2_CHAT_DECISIONS D-L2-15. Dual-scope (Local + Global)
with discipline split per ADR-0153 §1 + ADR-0150 §amendment-5 (Phase 43
ship) row: Local = ``mutable_with_retention`` (in-flight user-local
parameter assignments); Global = ``admin_authored`` (cross-user ALS
applies via admin importer).

Single NodeType (``LearnedParameter``); no EdgeTypes in v1.

**Per-NodeType storage_mode** (Phase 43 — ADR-0151 §Decision +
ADR-0152 §6 + design log NPB8-1): ``LearnedParameter.value`` carries a
large-payload field warranting an explicit ``storage_mode`` declaration
per ADR-0151. The ``STORAGE_MODE_FIELDS`` dict declares which fields are
large-payload at the NodeType level; ``value`` is the only such field
in Phase 43 scope. ``storage_mode`` itself is a sibling property
carrying the tier value (``"inline"`` / ``"falkor_blob"`` / ``"blob_ref"``
per ADR-0151) at write time. Phase 43 v1 ships Tiers 1 + 2; ``blob_ref``
reserved for FOL chat (Chat A R5 D30).

**FOL #4 split deferred** per L2_CHAT_DECISIONS D-L2-12; single v1
role-graph; ``parameter_set_iri`` opaque. ADR-0152 §amendment-1 will
ship if FOL accepts the 3-way split (Chat A R5 D28).

``strict=False`` per ADR-0149.
"""

from __future__ import annotations

from typing import Literal

from mindsos_core import NodeType

from ._base import Discipline, L2Schema


# ── Node type ──────────────────────────────────────────────────────────

NODE_LEARNED_PARAMETER = "LearnedParameter"

LEARNED_PARAMETERS_NODE_TYPES: tuple[str, ...] = (NODE_LEARNED_PARAMETER,)


# ── Edge types ─────────────────────────────────────────────────────────

LEARNED_PARAMETERS_EDGE_TYPES: tuple[str, ...] = ()  # v1 has no edge types.


# ── Advisory property constants (Phase 43 — ADR-0152 §6) ──────────────

LEARNED_PARAMETER_PROPS: frozenset[str] = frozenset({
    "parameter_set_iri",
    "target_parameter_iri",
    "value",
    "storage_mode",
    "confidence",
    "applied_at",
    "applied_from_promotion_iri",
    # Provenance for direct (non-promotion) learns — CR learned-parameters
    # capacity. Advisory (strict=False); additive, non-breaking.
    "learned_by",
    "recorded_at",
    "reason",
})


# ── Per-NodeType large-payload field declaration (ADR-0151 + NPB8-1) ──
#
# Phase 43 scope: only ``LearnedParameter.value`` carries a large-payload
# field. Test ``test_storage_mode_field.py`` asserts this map exactly +
# regression-guards that other Phase 43 NodeTypes do NOT export this
# constant.

STORAGE_MODE_FIELDS: dict[str, frozenset[str]] = {
    NODE_LEARNED_PARAMETER: frozenset({"value"}),
}


def build_learned_parameters_schema(
    strict: bool = False,
    scope: Literal["local", "global"] = "local",
) -> L2Schema:
    """Construct the learned-parameters role Schema.

    The ``scope`` kwarg selects the per-scope discipline split per
    ADR-0153 §1 + ADR-0150 §amendment-5: Local (default) →
    ``mutable_with_retention`` (in-flight per-user assignments); Global
    → ``admin_authored`` (cross-user applies via admin importer; no
    L4/L3 write path).

    Args:
        strict: Opt-in property-type enforcement. Default ``False`` per
            ADR-0149.
        scope: ``"local"`` (default) or ``"global"`` — selects the
            discipline per ADR-0153 §1 + ADR-0150 §am-5.
    """
    discipline = (
        Discipline.MUTABLE_WITH_RETENTION
        if scope == "local"
        else Discipline.ADMIN_AUTHORED
    )
    s = L2Schema(mutation_discipline=discipline, strict=strict)

    for nt in LEARNED_PARAMETERS_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    # No EdgeTypes per ADR-0152 §6.
    return s
