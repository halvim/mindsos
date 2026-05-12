"""Override-dict validation (Phase 06 P29 C + P36 A + round-7 P47 C +
P48 A + P57 A + P64 A bifurcation).

A subclass declares which keys are structural (bypass user-property
validation) and which are set-typed (JSON list → Python set/frozenset
coercion); everything else routes through
:func:`mindsos_core.schema.validate_user_properties` with the
subclass's KIND scope.

A key in
:data:`mindsos_core.schema.RESERVED_PROPERTY_KEYS` lands in the user-
property bucket UNLESS it appears in the subclass's structural allow-
list; in the bucket-2 path the validator raises
:class:`PropertyShapeError` which we re-raise as
:class:`OverrideScopeError` for a cleaner instance-side error API.
"""

from __future__ import annotations

from typing import Any, Dict, FrozenSet, Mapping

from mindsos_core.exceptions import PropertyShapeError
from mindsos_core.schema import validate_user_properties

from ..exceptions import OverrideScopeError

#: Universally-forbidden override keys per round-7 P47 C (`source_id`
#: redundancy removed — instance ID is covered by `id`).
UNIVERSALLY_FORBIDDEN: FrozenSet[str] = frozenset(
    {"id", "template_id", "kind", "metagraph_id"}
)


def validate_overrides(
    overrides: Mapping[str, Any],
    *,
    kind: str,
    structural_keys: FrozenSet[str],
    set_typed_keys: FrozenSet[str],
    forbids_type_name: bool,
) -> Dict[str, Any]:
    """Validate an override dict per the bifurcated routing.

    Returns a defensive-copy dict with set-typed structural fields
    coerced to :class:`frozenset` (round-7 P57 A). The shape of the
    returned mapping is suitable for storage on
    :attr:`ElementInstance.overrides`.

    Args:
        overrides: Caller-supplied override mapping.
        kind: The subclass's ``KIND`` (used as the ``scope`` argument
            to :func:`validate_user_properties`).
        structural_keys: Per-subclass allow-list of structural fields.
        set_typed_keys: Subset of ``structural_keys`` whose values are
            sets/frozensets. JSON list input is coerced (P57 A).
        forbids_type_name: When ``True``, ``type_name`` is rejected
            (Edge/HyperEdge/MetaEdge/MetaHyperEdge instances per
            P33 B).
    """
    structural_bucket: Dict[str, Any] = {}
    user_prop_bucket: Dict[str, Any] = {}

    for key, value in overrides.items():
        if not isinstance(key, str):
            raise OverrideScopeError(
                f"Override key must be a string, got {type(key).__name__}"
            )
        if key in UNIVERSALLY_FORBIDDEN:
            raise OverrideScopeError(
                f"Override key {key!r} is universally forbidden "
                f"(round-7 P47 C)."
            )
        if forbids_type_name and key == "type_name":
            raise OverrideScopeError(
                f"Override key 'type_name' is forbidden for {kind} "
                f"instances (Phase 06 P33 B)."
            )

        if key in structural_keys:
            # Round-7 P57 A — JSON-fragment list → Python set/frozenset
            # coercion for set-typed structural fields. Duplicates dedup
            # silently (matches Python set semantics).
            if key in set_typed_keys:
                if isinstance(value, (set, frozenset)):
                    coerced = frozenset(value)
                elif isinstance(value, list):
                    coerced = frozenset(value)
                else:
                    raise OverrideScopeError(
                        f"Structural override {key!r} on {kind} must be "
                        f"a list, set, or frozenset; got "
                        f"{type(value).__name__}."
                    )
                structural_bucket[key] = coerced
            else:
                # Non-set-typed structural fields (e.g., source_id,
                # label). Type validation per subclass; we accept any
                # value here and trust subclass __init__ / materialise
                # to handle type-mismatch at use time. Spec the contract
                # in row §B.
                structural_bucket[key] = value
        else:
            user_prop_bucket[key] = value

    # Bucket 2 — user-property validation via Phase 04. Re-raise
    # PropertyShapeError as OverrideScopeError for a cleaner public API.
    try:
        validated = validate_user_properties(user_prop_bucket, scope=kind)
    except PropertyShapeError as exc:
        raise OverrideScopeError(str(exc)) from exc

    out: Dict[str, Any] = {}
    out.update(structural_bucket)
    out.update(validated)
    return out


def split_single_override(
    key: str,
    value: Any,
    *,
    kind: str,
    structural_keys: FrozenSet[str],
    set_typed_keys: FrozenSet[str],
    forbids_type_name: bool,
) -> Any:
    """Validate + coerce a single override key/value pair.

    Returns the (possibly-coerced) value suitable for storage. Used by
    :meth:`ElementInstance.set_override` for incremental mutation.
    """
    out = validate_overrides(
        {key: value},
        kind=kind,
        structural_keys=structural_keys,
        set_typed_keys=set_typed_keys,
        forbids_type_name=forbids_type_name,
    )
    return out[key]
