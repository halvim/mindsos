"""SubMinds role-graph schema (feat/subminds — Slice 1 NET-NEW).

Per ADR-0190 + ADR-0150 §amendment-7 (closed role-set 13 → 14). Holds
**SubMind definition records** — the persisted endowment record for an
autonomous, no-reasoning self-state reflex (ADR-0188). A SubMind is
inherently cross-layer (check-capacity → L3, threshold → L2,
resolver → skill/capacity, loop + scheduler + arbitration → L4); this
role-graph is the durable, auditable home for its **definition** only.
Runtime lives in ``mindsos_intelligence`` (ADR-0189/0190 §2).

**Scope.** Designed Global + Local (ADR-0190 §1). Slice 1 bootstraps the
**Global** form only (authored, admin-gated endowment via the ADR-0180
write gate); the Local form + the taught endowment path land in a later
slice. The schema itself is scope-agnostic — one builder serves both.

**Discipline:** ``admin_authored`` (ADR-0153 §1). An authored endowment
is an admin-gated Global write, mirroring the learned-parameters Global
form. De-endowment semantics (marker-only deprecation per the Phase-50
installed-skills precedent) are deferred to the lifecycle slice; the
discipline may be revisited there.

Single NodeType (``SubMindDefinition``); no EdgeTypes in v1.

**Record shape (ADR-0182 consumer).** The record's ``value`` is a
structured dict carrying the full ADR-0190 §1 endowment record:
check-capacity ref, threshold/criterion ref(s), severity-normalization
range, severity→tier mapping, importance weight, resolver ref + its
declared exclusive-resource needs (``resolver_resources`` — present at
Slice 1 but **unconsumed**; the resource model / contention engine lands
Slice 2 per the consumer-discipline pattern), cadence-law parameters,
activation class, declared Reflex conditions + pre-wired actions
(Slice 3 consumer), and refractory/reset parameters. Per ADR-0182 rule 5
(queryability is the writer's obligation) the endowment driver lifts
filterable fields flat into node properties: ``submind_name``,
``activation_class``, ``status``.

**Per-NodeType storage_mode** (ADR-0151 + installed-skills precedent):
``SubMindDefinition.value`` is the large-payload field; tier ``inline``
at v1 (endowment records are small; an oversized record fails loud at the
ADR-0182 rule-4 persist boundary, the correct v1 behavior).

``strict=False`` per ADR-0149.
"""

from __future__ import annotations

from mindsos_core import NodeType

from ._base import Discipline, L2Schema


# ── Node type ──────────────────────────────────────────────────────────

NODE_SUBMIND_DEFINITION = "SubMindDefinition"

SUBMINDS_NODE_TYPES: tuple[str, ...] = (NODE_SUBMIND_DEFINITION,)


# ── Edge types ─────────────────────────────────────────────────────────

SUBMINDS_EDGE_TYPES: tuple[str, ...] = ()  # v1 has no edge types.


# ── Advisory property constants (ADR-0190; flat per ADR-0182 rule 5) ──

SUBMIND_DEFINITION_PROPS: frozenset[str] = frozenset({
    "submind_name",
    "activation_class",
    "status",
})

#: ``activation_class`` vocabulary per ADR-0188 §6 / design log §6.
SUBMIND_ACTIVATION_CLASSES: frozenset[str] = frozenset({
    "always_on",
    "context_gated",
})

#: ``status`` vocabulary. ``endowed`` = active definition; ``deprecated``
#: = marker-only de-endowment (lifecycle slice; read-filtered by the
#: registry, no removal — Phase-50 installed-skills precedent).
SUBMIND_STATUSES: frozenset[str] = frozenset({
    "endowed",
    "deprecated",
})


# ── Per-NodeType large-payload field declaration (ADR-0151 precedent) ─

STORAGE_MODE_FIELDS: dict[str, frozenset[str]] = {
    NODE_SUBMIND_DEFINITION: frozenset({"value"}),
}


def build_subminds_schema(strict: bool = False) -> L2Schema:
    """Construct the subminds role Schema (Global + Local; ADR-0190).

    Discipline ``admin_authored`` per ADR-0153 §1. Scope-agnostic — the
    same schema serves the Global (authored) and Local (taught) forms;
    scope is metagraph-level routing, not in the schema.

    Args:
        strict: Opt-in property-type enforcement. Default ``False`` per
            ADR-0149.
    """
    s = L2Schema(mutation_discipline=Discipline.ADMIN_AUTHORED, strict=strict)

    for nt in SUBMINDS_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    # No EdgeTypes in v1 (ADR-0190).
    return s
