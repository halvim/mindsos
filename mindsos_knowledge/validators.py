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
  ``alignment:<a><->b>`` naming.
* :func:`validate_ref_type` — ``ref_type`` is in :data:`REF_TYPES`.
* :func:`validate_promotion_candidate` — Local draft, not already
  promoted (no ``ref_type=PROMOTED`` stamp), not deprecated.

Each returns :class:`ValidationResult` (frozen; ``ok`` + optional
``violation``). The v1 result-type carries only those two fields per
R2-PB-D; future amendments add structured detail fields when a
consumer needs them.

:data:`_VALIDATORS_BY_ROLE` is the per-role adapter registry consumed
by :meth:`KLWriteHandle.validate_node`. Phase 36 ships 2 adapters
(``memories`` + ``problem-trace``) per the 2 shipped L3 write
capacities; per-flow discipline (ADR-0147 §am-1 clause 3) governs
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
    ROLE_MEMORIES,
    ROLE_PROBLEM_TRACE,
    alignment_role,
)

if TYPE_CHECKING:
    from mindsos_core import Metagraph

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
    """``role`` matches canonical ``alignment:<a><->b>`` sorted form.

    Uses :func:`alignment_role` for canonical construction; checks
    structural shape (``alignment:`` prefix + ``<->`` separator) then
    sort-order canonicalisation.

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
    if "<->" not in body:
        return ValidationResult.violated(
            f"alignment role {role!r} missing '<->' separator"
        )
    a, b = body.split("<->", 1)
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


def _validate_node_memories(
    handle: "KLWriteHandle",
    value: Any,
    type_: str,
    **refs: Any,
) -> ValidationResult:
    """Adapter for ``ROLE_MEMORIES`` consumed by ``handle.validate_node``.

    Phase 36 chain: ``(validate_role_routing,)``. Future per-flow
    phases extend this chain as additional invariants land for
    memory writes.
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
    """Adapter for ``ROLE_PROBLEM_TRACE`` — same chain as memories at Phase 36."""
    return validate_role_routing(
        role=handle.role, scope=handle.scope, mg=handle._metagraph
    )


_VALIDATORS_BY_ROLE: dict[str, object] = {
    ROLE_MEMORIES: _validate_node_memories,
    ROLE_PROBLEM_TRACE: _validate_node_problem_trace,
}


__all__ = [
    "ValidationResult",
    "validate_role_routing",
    "validate_local_to_global_ref",
    "validate_alignment_role_naming",
    "validate_ref_type",
    "validate_promotion_candidate",
]
