"""Property-bag validation and reserved-key enforcement.

Phase 04 slim port. Defers ``validate_namespaced_properties`` (the
graph-level / metagraph-level property bag helper, ADR-0130) to
Phase 05/10.

All property bags that flow into Core primitives go through
:func:`validate_user_properties`, which:

1. Rejects reserved keys (``id``, ``type``, ``label``, ``kind``, etc.)
   that the Core Layer uses to round-trip its own metadata.
2. Rejects non-primitive values (tuples, sets, dicts, custom objects).
3. Optionally enforces a per-type property-type map when a ``Schema``
   is in strict mode — see :meth:`Schema.validate_node_properties`.

Cross-graph references are permitted via a dedicated prefix so they
don't collide with ordinary keys — see :data:`REF_PROPERTY_PREFIX`.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Tuple

from ..exceptions import PropertyShapeError

#: Property keys the Core Layer uses for its own metadata. User property
#: bags may not contain these.
#:
#: ``deprecated_at`` / ``disputed_at`` (ADR-0133) and ``_version`` (ADR-0127)
#: are reserved for soft-delete and optimistic concurrency, respectively —
#: even though the Phase 04 slim ``Node`` / ``Edge`` / ``HyperEdge`` don't
#: yet ship those fields (Phase 07 / 10), the user-property contract still
#: forbids the keys.
RESERVED_PROPERTY_KEYS = frozenset({
    "id",
    "uuid",
    "node_id",
    "edge_id",
    "graph_id",
    "metagraph_id",
    "instance_id",
    "type",
    "type_name",
    "kind",
    "label",
    "role",
    "value",
    "source_id",
    "target_id",
    # ADR-0133 — soft-delete representation on edges/hyperedges/metaedges/metahyperedges.
    "deprecated_at",
    "disputed_at",
    # ADR-0127 — optimistic concurrency on Global writes.
    "_version",
    # Phase 05a — P13 lock. Metagraph-structural top-level field names
    # become reserved at user-property scope so a metagraph property bag
    # (ADR-0130) cannot collide with serialization fields when Phase 07
    # persistence stamps properties onto Cypher anchor rows alongside
    # structural fields. ``_state_version`` is reserved across all
    # state-file kinds. ``contained_graphs`` / ``metaedges`` /
    # ``metahyperedges`` are top-level metagraph-state fields.
    #
    # Deliberately EXCLUDED (would break Phase 03/04 user-prop tests):
    #   ``name``        — common user property key (e.g. Person.name).
    #   ``properties``  — recursive bag use case is plausible.
    "_state_version",
    "contained_graphs",
    "metaedges",
    "metahyperedges",
    "metagraph_name",  # graph-state v=4 back-pointer field (P05a B2).
    # Phase 05b — Pushback 18-A. Top-level metagraph state v=2 fields
    # become reserved at user-property scope (parity with P13 reasoning).
    # ``intergraph_edges`` is the new top-level array introduced by 05b's
    # state-file v=2 bump. ``schema_name`` is also top-level on metagraph
    # state v=2 (and graph state v=2 since Phase 04 — reserving in 05b
    # closes the user-property collision case for both kinds).
    "intergraph_edges",
    "schema_name",
    # Phase 05b — P6 carry-forward (deferred from 05a). The ``_compositional``
    # reserved key is the future Phase 07 Cypher emit's stamped property
    # on the anchor-node Pattern B; reserving at user-property scope
    # prevents the user-bag from colliding with the system-stamped key.
    # Note: ``compositional`` (without underscore) is the dataclass field
    # name + top-level state-file field (Pushback 2-A); only the
    # underscore-prefixed Cypher-property form is reserved.
    "_compositional",
    # Phase 05c — locked decision (smaller items folded; mirror P05b
    # Pushback 18-A pattern). Top-level state-file fields introduced by
    # the v=2→v=3 metagraph bump and v=1→v=2 metagraph-schema bump
    # become reserved at user-property scope so a property bag (ADR-0130
    # or per-element) cannot collide with serialization fields.
    # ``intergraph_hyperedges`` is the new top-level array on metagraph
    # state v=3. ``intergraph_hyperedge_types`` is the new top-level
    # array on metagraph-schema state v=2. ``anchors`` / ``members`` are
    # per-entry fields on intergraph_hyperedges; reserving them aligns
    # with the established "structural keys can't be user properties"
    # convention (mirror Phase 05a P13: ``contained_graphs`` /
    # ``metaedges`` / ``metahyperedges`` reserved even though they're
    # one level deeper than the user-property scope a typical caller
    # uses; defense in depth).
    "intergraph_hyperedges",
    "intergraph_hyperedge_types",
    "anchors",
    "members",
    # Phase 48 — ADR-0161 / ADR-0177. D'1 lazy-inline-on-retire marker.
    # System-written single-underscore key (same family as ``_version`` /
    # ``_compositional``): KL writes it directly on the retired node via
    # ``retire_version``; reserving it here forbids a user property bag from
    # forging or colliding with the marker.
    "_retired_inline_pending",
    # Phase 50 — ADR-0182. Node-level JSON-encoded structured-value column
    # (same family as ``_props_json``): the persist path writes it for
    # dict/list node values; reserving it forbids user property bags from
    # colliding with the serialization column.
    "_value_json",
})

#: Prefix for cross-graph reference properties. Properties whose key
#: starts with this prefix are allowed to hold a UUID string pointing
#: at another element in the same metagraph's identity scope. The
#: portion after the prefix is treated as the *role* the reference
#: plays — e.g. ``"ref:anchor"`` references the anchor node.
REF_PROPERTY_PREFIX = "ref:"

#: Reserved key prefixes (excluding ``ref:`` which has dedicated handling).
#: Any user property whose key starts with one of these raises
#: :class:`PropertyShapeError`.
#:
#: - ``ov__`` — instance override marker (ADR-0025); user properties
#:   colliding with this prefix would be mis-routed as overrides on load.
RESERVED_PROPERTY_PREFIXES: Tuple[str, ...] = ("ov__",)

#: Primitive types accepted in property values.
_PRIMITIVES: Tuple[type, ...] = (str, int, float, bool)


def _is_primitive_list(v: Any) -> bool:
    if not isinstance(v, list):
        return False
    if not v:
        return True  # empty list is fine
    kind = type(v[0])
    if kind not in _PRIMITIVES:
        return False
    return all(type(x) is kind for x in v)


def _is_primitive(v: Any) -> bool:
    # Note: bool is a subclass of int, which is fine — we allow it.
    return isinstance(v, _PRIMITIVES) or _is_primitive_list(v) or v is None


def validate_user_properties(
    properties: Mapping[str, Any],
    *,
    scope: str = "property",
) -> Dict[str, Any]:
    """Return a defensive copy of ``properties`` after validation.

    Args:
        properties: User-supplied property bag.
        scope: Human-readable tag for error messages
            ("node", "edge", "hyperedge", …).

    Raises:
        PropertyShapeError: if a key is reserved or a value is
            non-primitive.
    """
    out: Dict[str, Any] = {}
    for key, value in properties.items():
        if not isinstance(key, str):
            raise PropertyShapeError(
                f"{scope} property key must be a string, got {type(key).__name__}"
            )
        if not key:
            raise PropertyShapeError(f"{scope} property key must be non-empty")
        # Reference properties: key starts with "ref:" and value is a UUID-shaped str.
        if key.startswith(REF_PROPERTY_PREFIX):
            if not isinstance(value, str) or not value:
                raise PropertyShapeError(
                    f"{scope} ref property {key!r} must be a non-empty string id"
                )
            out[key] = value
            continue
        if key in RESERVED_PROPERTY_KEYS:
            raise PropertyShapeError(
                f"{scope} property key {key!r} is reserved by the Core Layer"
            )
        for reserved_prefix in RESERVED_PROPERTY_PREFIXES:
            if key.startswith(reserved_prefix):
                raise PropertyShapeError(
                    f"{scope} property key {key!r} starts with reserved prefix "
                    f"{reserved_prefix!r}"
                )
        if not _is_primitive(value):
            raise PropertyShapeError(
                f"{scope} property {key!r} has non-primitive value of type "
                f"{type(value).__name__}"
            )
        out[key] = value
    return out


def iter_ref_properties(properties: Mapping[str, Any]) -> Iterable[Tuple[str, Any]]:
    """Yield ``(role, target_id)`` tuples for every cross-graph reference."""
    for key, value in properties.items():
        if key.startswith(REF_PROPERTY_PREFIX):
            yield key[len(REF_PROPERTY_PREFIX):], value
