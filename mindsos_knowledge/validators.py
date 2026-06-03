"""Semantic validators for L2 Knowledge writes (Phase 36; ADR-0139 Accepted).

ADR-0139 §Decision splits L2 write invariants into:

* **Structural** — L1's responsibility (schema shape, XRef integrity, ID
  uniqueness, reserved property keys). Fires unconditionally inside
  ``Graph.add_node`` / ``add_xref``; violations raise typed errors.
* **Semantic** — KL's responsibility, this module. Pure functions, no
  mutation, no I/O. L3 write capacities call them as preconditions
  before invoking ``handle.write_and_validate(...)`` (ADR-0139
  §Capacity-contract). Bypass is a code-review failure, not a runtime
  error (ADR-0139 §Decision + ``docs/dev/review-checklist.md`` §4).

Phase 36 ships ADR-0139's 5 listed validators as pure functions per
§Acceptance criterion (a) literal closure:

* :func:`validate_role_routing` — role-graph exists in scope's metagraph.
* :func:`validate_local_to_global_ref` — Local→Global ref target exists
  in the active version-graph of the target role.
* :func:`validate_alignment_role_naming` — canonical sorted
  ``alignment:<a>:<b>`` naming (Phase 39 L2-35 reconciliation per
  ADR-0154 + D-L2-1; separator canonical form is ``:`` between sorted
  role atoms).
* :func:`validate_ref_type` — ``ref_type`` is in :data:`REF_TYPES`.
* :func:`validate_promotion_candidate` — Local draft, not already
  promoted (no ``ref_type=PROMOTED`` stamp), not deprecated.

Phase 43 adds two L2-substrate validators per ADR-0153:

* :func:`validate_mutation_discipline` — per-write enforcement of the
  declared discipline (ADR-0153 §2 + §3). Used by the L4 startup
  invariant dispatch table (built once at
  :meth:`KnowledgeLayer.bootstrap`) and by L3 write capacities as a
  pre-mint check. Pure function; raises nothing — discipline violations
  surface as :class:`ValidationResult.violated`; ``KLWriteHandle``
  composes this into :class:`MutationDisciplineError` at the write
  site.
* :func:`validate_partition_invariant` — schema-build-time check that
  ``*_CONTENT_FIELDS`` and ``*_METADATA_FIELDS`` form a clean partition
  over the schema's declared field list (ADR-0153 §3).

Each returns :class:`ValidationResult` (frozen; ``ok`` + optional
``violation``). The v1 result-type carries only those two fields per
R2-PB-D; future amendments add structured detail fields when a
consumer needs them.

:data:`_VALIDATORS_BY_ROLE` is the per-role adapter registry consumed
by :meth:`KLWriteHandle.validate_node`. Phase 39 ships 2 adapters
(``episodic_memories`` + ``problem-trace``) per the 2 shipped L3
write capacities (memories renamed per ADR-0044 §am-3);
per-flow discipline (ADR-0147 §am-1 clause 3) governs
*adapter* extension as new write capacities land. The underlying
validators are L2 substrate, not L3 capacity declarations — per-flow
does not gate them at the function level.

Composition contract:

* **Canonical**: ``handle.validate_node(value, type_)`` runs the
  role's registered adapter chain (first-failure-wins per R3-PB-I).
* **Fallback**: capacity bodies may call individual validators
  directly from this module for one-off checks (ADR-0139
  §Capacity-contract).

See ``docs/dev/internals/knowledge.md`` §Validator surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Optional

from .identifiers import (
    REF_TYPES,
    REF_TYPE_KEY,
    ROLE_EPISODIC_MEMORIES,
    ROLE_PROBLEM_TRACE,
    alignment_role,
)

if TYPE_CHECKING:
    from mindsos_core import Metagraph

    from .schemas._base import Discipline
    from .write_handle import KLWriteHandle


@dataclass(frozen=True)
class ValidationResult:
    """Result of a semantic validator call.

    Frozen per ADR-0139 §Semantic-invariants ("validators are
    idempotent and side-effect-free"). v1 fields (R2-PB-D):

    * ``ok`` — True iff the validator passed.
    * ``violation`` — human-readable failure reason; ``None`` when ok.

    Construct via :meth:`success` / :meth:`violated`; do not construct
    by hand (the factory methods document the two valid states).

    Future amendments may add structured detail fields (kind enum,
    structured detail mapping) when a consumer needs them; v1 keeps
    the surface minimal per per-flow rationale.
    """

    ok: bool
    violation: Optional[str]

    @classmethod
    def success(cls) -> "ValidationResult":
        """Return the canonical success ValidationResult."""
        return cls(ok=True, violation=None)

    @classmethod
    def violated(cls, reason: str) -> "ValidationResult":
        """Return a failure ValidationResult bearing ``reason``."""
        return cls(ok=False, violation=reason)


def validate_role_routing(
    *,
    role: str,
    scope: Literal["local", "global"],
    mg: "Metagraph",
) -> ValidationResult:
    """``role`` is a registered role-graph in ``scope``'s metagraph ``mg``.

    Covers ADR-0139 §Semantic-invariants bullet 2 ("role is a
    registered role-graph in the scope's metagraph"). Pre-mint
    timing per R3-PB-H: runs in capacity precondition before
    :meth:`KLWriteHandle.mint_iri`. The structural overlap with
    :meth:`KLWriteHandle.graph` ``KeyError`` is intentional — the
    validator surfaces violation as :class:`ValidationResult`
    before any IRI mint, while the ``KeyError`` fires later inside
    ``write_and_validate``.

    Args:
        role: The role-graph the capacity is writing to.
        scope: ``'local'`` or ``'global'`` (reserved for future
            scope-specific routing rules; v1 informational only).
        mg: The :class:`Metagraph` to inspect.

    Returns:
        :class:`ValidationResult` — success iff some graph in
        ``mg.graphs.values()`` has ``role`` matching the argument.
    """
    for g in mg.graphs.values():
        if g.role == role:
            return ValidationResult.success()
    return ValidationResult.violated(
        f"role {role!r} not registered in metagraph "
        f"{mg.metagraph_id!r} (scope={scope!r})"
    )


def validate_local_to_global_ref(
    *,
    target_role: str,
    target_iri: str,
    mg: "Metagraph",
) -> ValidationResult:
    """``target_iri`` exists in the active version-graph of ``target_role``.

    Covers ADR-0139 §Semantic-invariants bullet 1. At Phase 36
    (ADR-0150 §am-3 locks one-graph-per-role), "active version-graph"
    reduces to "the single graph with ``role == target_role``" in
    ``mg``. Future multi-version phases rewrite the body; the
    signature stays.

    Args:
        target_role: The role of the Global target graph.
        target_iri: The IRI of the target node.
        mg: The Global :class:`Metagraph`.

    Returns:
        :class:`ValidationResult` — success iff a graph with
        ``role == target_role`` exists and contains ``target_iri``.
    """
    for g in mg.graphs.values():
        if g.role == target_role:
            if target_iri in g.nodes:
                return ValidationResult.success()
            return ValidationResult.violated(
                f"target IRI {target_iri!r} not present in graph "
                f"with role {target_role!r} (metagraph "
                f"{mg.metagraph_id!r})"
            )
    return ValidationResult.violated(
        f"no graph with role {target_role!r} in metagraph "
        f"{mg.metagraph_id!r}"
    )


def validate_alignment_role_naming(*, role: str) -> ValidationResult:
    """``role`` matches canonical ``alignment:<a>:<b>`` sorted form.

    Uses :func:`alignment_role` for canonical construction; checks
    structural shape (``alignment:`` prefix + ``:`` separator between
    sorted role atoms) then sort-order canonicalisation. Phase 39
    L2-35 reconciliation per ADR-0154 + L2_CHAT_DECISIONS D-L2-1
    locks the canonical separator as ``:``.

    Args:
        role: The alignment role name to validate.

    Returns:
        :class:`ValidationResult` — success iff ``role`` is the
        canonical alignment naming form.
    """
    if not role.startswith("alignment:"):
        return ValidationResult.violated(
            f"role {role!r} is not alignment-prefixed"
        )
    body = role[len("alignment:") :]
    if ":" not in body:
        return ValidationResult.violated(
            f"alignment role {role!r} missing ':' separator between "
            f"sorted role atoms"
        )
    a, b = body.split(":", 1)
    canonical = alignment_role(a, b)
    if role != canonical:
        return ValidationResult.violated(
            f"alignment role {role!r} not canonical "
            f"(expected {canonical!r}; roles must be sorted)"
        )
    return ValidationResult.success()


def validate_ref_type(
    *,
    ref_type: str,
    target_role: str,
) -> ValidationResult:
    """``ref_type`` is a member of :data:`REF_TYPES` (open vocabulary).

    Covers ADR-0139 §Semantic-invariants bullet 4. At Phase 36
    :data:`REF_TYPES` is an open vocabulary per ADR-0047; no per-role
    whitelist exists yet. ``target_role`` is reserved for future
    role-specific enforcement when per-flow capacities require it
    (per ADR-0047's open-vocabulary extension recipe).

    Args:
        ref_type: The ref_type value to validate.
        target_role: The target role (reserved; not yet enforced).

    Returns:
        :class:`ValidationResult` — success iff ``ref_type`` is in
        :data:`REF_TYPES`.
    """
    if ref_type not in REF_TYPES:
        return ValidationResult.violated(
            f"ref_type {ref_type!r} not in REF_TYPES "
            f"(known: {sorted(REF_TYPES)!r})"
        )
    return ValidationResult.success()


def validate_promotion_candidate(
    *,
    local_iri: str,
    mg: "Metagraph",
) -> ValidationResult:
    """``local_iri`` is a Local draft, not already promoted, not deprecated.

    Covers ADR-0139 §Semantic-invariants bullet 5. Inspects ``mg``
    (Local) for the candidate node; rejects if absent, if the node
    carries a ``ref_type=PROMOTED`` stamp (already-promoted
    breadcrumb per ADR-0044), or if the node bears a ``deprecated_at``
    property (ADR-0133 soft-delete).

    Args:
        local_iri: The Local IRI of the candidate.
        mg: The user's Local :class:`Metagraph`.

    Returns:
        :class:`ValidationResult` — success iff the candidate is
        present, not promoted, and not deprecated.
    """
    for g in mg.graphs.values():
        if local_iri in g.nodes:
            node = g.nodes[local_iri]
            props = getattr(node, "properties", None) or {}
            if props.get(REF_TYPE_KEY) == "PROMOTED":
                return ValidationResult.violated(
                    f"candidate {local_iri!r} is already PROMOTED"
                )
            if "deprecated_at" in props:
                return ValidationResult.violated(
                    f"candidate {local_iri!r} is deprecated"
                )
            return ValidationResult.success()
    return ValidationResult.violated(
        f"candidate {local_iri!r} not found in metagraph "
        f"{mg.metagraph_id!r}"
    )


def validate_mutation_discipline(
    *,
    discipline: "Discipline",
    field: str,
    role: str,
    iri: str,
    content_fields: frozenset[str] = frozenset(),
    is_settled: bool = False,
    is_admin: bool = False,
    via_lazy_inline: bool = False,
) -> ValidationResult:
    """Reject writes that violate the declared mutation discipline.

    ADR-0153 §3 (per-field content/metadata partition) + §2 (L4 startup
    invariant dispatch). Phase 43 (Rail A slot 2). Used both by the L4
    startup invariant (eager check at
    :meth:`KnowledgeLayer.bootstrap`) and by L3 write capacities as a
    pre-mint check composed via ADR-0139 §Capacity-contract.

    Discipline-by-discipline behaviour:

    * ``immutable_successor`` — writes to fields in ``content_fields``
      are rejected; caller must mint a successor IRI. Metadata fields
      are always mutable.
    * ``append_only_with_lazy_inline`` — writes to ``content_fields``
      are rejected unless ``via_lazy_inline=True`` (the only permitted
      content mutation per ADR-0153 §1).
    * ``append_only`` — writes to ``content_fields`` are rejected
      unconditionally.
    * ``mutable_with_retention`` — no field-level check; admin-tunable
      retention TTL handles freshness (out of scope for this validator).
    * ``audit_only_after_settled`` — writes to a settled row are
      rejected (``is_settled=True``); pre-settled rows mutate freely.
    * ``admin_authored`` — writes without ``is_admin=True`` are
      rejected; admin tooling bypasses.

    The validator is pure: discipline violations surface as
    :class:`ValidationResult.violated`. ``KLWriteHandle`` composes the
    violation into :class:`MutationDisciplineError` at the write site.

    Args:
        discipline: The declared discipline of the target role-graph
            (per ``L2Schema.mutation_discipline``).
        field: The property name being written.
        role: The role-graph name (for diagnostics).
        iri: The target node IRI (for diagnostics).
        content_fields: The schema's ``*_CONTENT_FIELDS`` partition.
            Empty frozenset for disciplines without partition.
        is_settled: True iff the target row is in a terminal status
            (``audit_only_after_settled`` only).
        is_admin: True iff the write is via an admin importer or admin
            tooling (``admin_authored`` only).
        via_lazy_inline: True iff the write is the lazy-inline-on-retire
            mechanism (``append_only_with_lazy_inline`` only).

    Returns:
        :class:`ValidationResult` — success iff the write is permitted
        under the discipline.
    """
    if discipline == "admin_authored" and not is_admin:
        return ValidationResult.violated(
            f"role={role!r} iri={iri!r}: discipline=admin_authored "
            f"requires admin flag for any write (field={field!r})"
        )
    if discipline == "audit_only_after_settled" and is_settled:
        return ValidationResult.violated(
            f"role={role!r} iri={iri!r}: discipline="
            f"audit_only_after_settled forbids writes to settled row "
            f"(field={field!r})"
        )
    if discipline == "immutable_successor" and field in content_fields:
        return ValidationResult.violated(
            f"role={role!r} iri={iri!r}: discipline=immutable_successor "
            f"forbids in-place write to content field {field!r}; "
            f"mint a successor IRI"
        )
    if (
        discipline == "append_only_with_lazy_inline"
        and field in content_fields
        and not via_lazy_inline
    ):
        return ValidationResult.violated(
            f"role={role!r} iri={iri!r}: discipline="
            f"append_only_with_lazy_inline forbids in-place write to "
            f"content field {field!r} outside the lazy-inline-on-retire "
            f"mechanism"
        )
    if discipline == "append_only" and field in content_fields:
        return ValidationResult.violated(
            f"role={role!r} iri={iri!r}: discipline=append_only forbids "
            f"in-place write to content field {field!r}"
        )
    return ValidationResult.success()


def validate_partition_invariant(
    *,
    content_fields: frozenset[str],
    metadata_fields: frozenset[str],
    all_fields: frozenset[str],
) -> ValidationResult:
    """``content_fields`` + ``metadata_fields`` partition ``all_fields``.

    ADR-0153 §3 partition discipline. Phase 43 (Rail A slot 2). Used at
    schema-build time (or PR1 commit 5 sentinel test) to verify a
    Phase 43 schema's ``*_CONTENT_FIELDS`` + ``*_METADATA_FIELDS`` are
    coherent with the schema's declared field list.

    Checks (in this order):

    * **No overlap** — ``content_fields ∩ metadata_fields == ∅``.
    * **Complete coverage** — every field in ``all_fields`` belongs to
      exactly one partition.
    * **No phantom fields** — neither partition references a field not
      in ``all_fields``.

    Args:
        content_fields: The ``*_CONTENT_FIELDS`` frozenset.
        metadata_fields: The ``*_METADATA_FIELDS`` frozenset.
        all_fields: The full declared field set for the NodeType.

    Returns:
        :class:`ValidationResult` — success iff the two frozensets form
        a clean partition over ``all_fields``.
    """
    intersection = content_fields & metadata_fields
    if intersection:
        return ValidationResult.violated(
            f"content/metadata partition overlap: "
            f"{sorted(intersection)!r} appear in both partitions"
        )
    union = content_fields | metadata_fields
    missing = all_fields - union
    if missing:
        return ValidationResult.violated(
            f"content/metadata partition incomplete: "
            f"{sorted(missing)!r} unclassified"
        )
    extra = union - all_fields
    if extra:
        return ValidationResult.violated(
            f"content/metadata partition references unknown fields: "
            f"{sorted(extra)!r}"
        )
    return ValidationResult.success()


def _validate_node_episodic_memories(
    handle: "KLWriteHandle",
    value: Any,
    type_: str,
    **refs: Any,
) -> ValidationResult:
    """Adapter for ``ROLE_EPISODIC_MEMORIES`` consumed by ``handle.validate_node``.

    Phase 39 chain: ``(validate_role_routing,)`` — unchanged from
    Phase 36 chain shape; role-name only renamed per ADR-0044 §am-3.
    Future per-flow phases extend this chain as additional invariants
    land for episodic-memory writes.
    """
    return validate_role_routing(
        role=handle.role, scope=handle.scope, mg=handle._metagraph
    )


def _validate_node_problem_trace(
    handle: "KLWriteHandle",
    value: Any,
    type_: str,
    **refs: Any,
) -> ValidationResult:
    """Adapter for ``ROLE_PROBLEM_TRACE`` — same chain as episodic_memories at Phase 39."""
    return validate_role_routing(
        role=handle.role, scope=handle.scope, mg=handle._metagraph
    )


_VALIDATORS_BY_ROLE: dict[str, object] = {
    ROLE_EPISODIC_MEMORIES: _validate_node_episodic_memories,
    ROLE_PROBLEM_TRACE: _validate_node_problem_trace,
}


__all__ = [
    "ValidationResult",
    "validate_role_routing",
    "validate_local_to_global_ref",
    "validate_alignment_role_naming",
    "validate_ref_type",
    "validate_promotion_candidate",
    "validate_mutation_discipline",
    "validate_partition_invariant",
]
