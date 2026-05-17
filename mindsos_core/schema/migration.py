"""Schema migration scanner (Phase 11 — ADR-0134).

Detection-only scanner that compares persisted Graph data against an
older :class:`Schema` to surface what would violate the current schema
if the data were re-validated.

Phase 11 design picks (recorded in
``confirmation_docs/PHASE_11_DESIGN_LOG.md``):

* **PB-1 A** — detection only. No apply path; ADR-0134 §"What it does
  NOT do" honored verbatim.
* **PB-7 C** — coverage = Schema-level (Node + Edge + HyperEdge).
  MetagraphSchema scanner (MetaEdge / IntergraphEdge / etc.)
  carried forward to Phase 12+.
* **PB-8 A** — two detail modes. ``summary`` aggregates per (kind,
  type_name) with counts. ``each`` emits one
  :class:`SchemaViolation` per offending element. Default ``summary``
  caps pathological output.
* **PB-17 C** — both per-:class:`Graph` and per-:class:`Metagraph`
  dispatch through one entry point :func:`migrate_from` (target is
  ``Graph | Metagraph``). Per-Metagraph scope walks every contained
  graph that carries a schema; ``old_schema_name`` opt-in surfaces a
  per-graph policy warning (NOT a SchemaViolation) when
  ``graph.schema_name`` differs.

The scanner does NOT mutate anything. Callers handle violations
(write a migration script, drop-and-reimport, accept-as-stale).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import (
    Iterable,
    Iterator,
    List,
    Literal,
    Mapping,
    Optional,
    Union,
)

from ..exceptions import CoreError
from .schema import Schema
from .types import PropertyType

_log = logging.getLogger(__name__)


# Kind discriminator for :class:`SchemaViolation`. Five kinds across
# three element families (Node/Edge/HyperEdge) plus the two
# property-level kinds.
ViolationKind = Literal[
    "removed_node_type",
    "removed_edge_type",
    "removed_hyperedge_type",
    "tightened_property",
    "missing_required_property",
]

DetailMode = Literal["summary", "each"]


class SchemaMigrationError(CoreError):
    """``migrate_from`` was called with an unsupported target.

    Raised when ``target`` is neither a :class:`Graph` nor a
    :class:`Metagraph`, or when ``detail`` is not one of
    ``"summary"`` / ``"each"``.
    """


@dataclass(frozen=True)
class SchemaViolation:
    """One violation surfaced by :func:`migrate_from`.

    Phase 11 design picks:

    * ``frozen=True`` — value object; never mutated by callers (PB-7
      deferred items §SchemaViolation: frozen dataclass).
    * In ``summary`` mode (PB-8 A), ``element_id`` is empty and ``count``
      carries the aggregate; one entry per (``kind``, ``type_name``,
      ``graph_id``) triple.
    * In ``each`` mode, ``element_id`` carries the offending node /
      edge / hyperedge id and ``count`` is always 1.

    Attributes:
        kind: One of the five recognised :data:`ViolationKind` values.
        type_name: The affected node / edge / hyperedge type.
        element_id: Identifier of the offending element in ``each``
            mode; empty string in ``summary`` mode.
        graph_id: The graph the violation was found in. Always set
            for both per-Graph and per-Metagraph scans.
        property_name: For ``tightened_property`` /
            ``missing_required_property`` violations, the affected
            property key. Empty for ``removed_*_type`` violations.
        count: Aggregate count in ``summary`` mode; ``1`` in ``each``
            mode.
        detail: Human-readable one-liner describing the violation.
    """

    kind: ViolationKind
    type_name: str
    element_id: str
    graph_id: str
    property_name: str
    count: int
    detail: str


# ── public API ──────────────────────────────────────────────────────────────


def migrate_from(
    old: Schema,
    target: object,
    *,
    new: Optional[Schema] = None,
    detail: DetailMode = "summary",
    old_schema_name: Optional[str] = None,
) -> List[SchemaViolation]:
    """Scan persisted data for violations vs the new schema.

    Args:
        old: The previous :class:`Schema` the data was validated under.
            Used to identify *removed* node/edge/hyperedge types.
        target: A :class:`mindsos_core.models.graph.Graph` or
            :class:`mindsos_core.models.metagraph.Metagraph`. Per
            PB-17 C, a single entry point dispatches on type.
        new: Optional explicit *new* :class:`Schema`. When ``None``:
            * Graph target — uses ``target.schema``. Skips if
              ``target.schema is None``.
            * Metagraph target — uses each ``graph.schema`` per
              contained graph.
        detail: ``"summary"`` (default) — aggregate one entry per
            (kind, type_name, graph_id). ``"each"`` — emit one entry
            per offending element.
        old_schema_name: Optional. When set AND target is a
            Metagraph, the scanner emits a logger WARNING for each
            contained graph whose ``schema_name`` differs from
            ``old_schema_name``. NOT a :class:`SchemaViolation` —
            caller decides whether the mismatch is meaningful (PB-17 C
            warn-not-mutate discipline).

    Returns:
        List of :class:`SchemaViolation`. Empty when the new schema
        is compatible with all persisted data of every contained
        graph that has a schema attached.

    Raises:
        SchemaMigrationError: invalid ``target`` type or invalid
            ``detail`` value.
    """
    if detail not in ("summary", "each"):
        raise SchemaMigrationError(
            f"detail must be 'summary' or 'each'; got {detail!r}"
        )

    # Lazy imports to avoid circular dependency at module load.
    from ..models.graph import Graph
    from ..models.metagraph import Metagraph

    if isinstance(target, Graph):
        active_new = new if new is not None else target.schema
        if active_new is None:
            # No new schema — nothing to compare; clean by definition.
            return []
        return list(
            _scan_graph(old, active_new, target, detail=detail)
        )

    if isinstance(target, Metagraph):
        violations: List[SchemaViolation] = []
        for g in target.graphs.values():
            if old_schema_name is not None:
                gname = getattr(g, "schema_name", None)
                if gname is not None and gname != old_schema_name:
                    _log.warning(
                        "migrate_from: graph %r has schema_name=%r; "
                        "old schema name=%r — skipping scan of this "
                        "graph (policy=name_mismatch_warn)",
                        g.graph_id, gname, old_schema_name,
                    )
                    continue
            active_new = new if new is not None else g.schema
            if active_new is None:
                continue
            violations.extend(_scan_graph(old, active_new, g, detail=detail))
        return violations

    raise SchemaMigrationError(
        f"migrate_from: target must be a Graph or Metagraph; got "
        f"{type(target).__name__}"
    )


# ── private scanners ────────────────────────────────────────────────────────


def _scan_graph(
    old: Schema,
    new: Schema,
    graph: object,
    *,
    detail: DetailMode,
) -> Iterator[SchemaViolation]:
    """Yield violations for a single :class:`Graph`.

    Walks three element families against the (old, new) schema pair:

    * Nodes — :data:`removed_node_type` for node types in ``old`` but
      not ``new``; :data:`tightened_property` /
      :data:`missing_required_property` for surviving node types.
    * Edges — :data:`removed_edge_type` + property violations.
    * HyperEdges — :data:`removed_hyperedge_type` + property
      violations.
    """
    # ── Nodes ───────────────────────────────────────────────────────────
    yield from _scan_elements(
        elements=graph.nodes.values(),
        type_getter=lambda n: n.type_name,
        id_getter=lambda n: n.node_id,
        properties_getter=lambda n: n.properties,
        old_types=old.node_types,
        new_types=new.node_types,
        removed_kind="removed_node_type",
        graph_id=graph.graph_id,
        detail=detail,
    )
    # ── Edges ───────────────────────────────────────────────────────────
    yield from _scan_elements(
        elements=graph.edges.values(),
        type_getter=lambda e: e.type_name,
        id_getter=lambda e: e.edge_id,
        properties_getter=lambda e: e.properties,
        old_types=old.edge_types,
        new_types=new.edge_types,
        removed_kind="removed_edge_type",
        graph_id=graph.graph_id,
        detail=detail,
    )
    # ── HyperEdges ──────────────────────────────────────────────────────
    yield from _scan_elements(
        elements=graph.hyperedges.values(),
        type_getter=lambda h: h.type_name,
        id_getter=lambda h: h.edge_id,
        properties_getter=lambda h: h.properties,
        old_types=old.hyperedge_types,
        new_types=new.hyperedge_types,
        removed_kind="removed_hyperedge_type",
        graph_id=graph.graph_id,
        detail=detail,
    )


def _scan_elements(
    *,
    elements: Iterable,
    type_getter,
    id_getter,
    properties_getter,
    old_types: Mapping[str, object],
    new_types: Mapping[str, object],
    removed_kind: ViolationKind,
    graph_id: str,
    detail: DetailMode,
) -> Iterator[SchemaViolation]:
    """Generic per-element-family scan loop.

    For each element, route to one of three buckets:

    * Type removed in ``new`` (existed in ``old``) → ``removed_*_type``.
    * Type present in both — diff ``property_types`` of new vs old:
      added → :data:`missing_required_property` checks; changed →
      :data:`tightened_property` checks.
    * Type absent from ``old`` — unknown lineage; out of scope (the
      loader policy ADR-0134 amendment-1 handles this surface).
    """
    # Pre-compute per-type the (added properties, changed properties)
    # diffs so each element only walks its own type's diff bucket.
    type_diffs = {}
    for type_name, new_type in new_types.items():
        if type_name not in old_types:
            # Type added — not a violation; scanner is interested only
            # in shrinkages / tightenings, not expansions.
            continue
        old_type = old_types[type_name]
        old_props = getattr(old_type, "property_types", {}) or {}
        new_props = getattr(new_type, "property_types", {}) or {}
        added = {k: v for k, v in new_props.items() if k not in old_props}
        changed = {
            k: (old_props[k], v)
            for k, v in new_props.items()
            if k in old_props and old_props[k] != v
        }
        if added or changed:
            type_diffs[type_name] = (added, changed)

    # Counters keyed by (kind, type_name, property_name) for summary mode.
    summary_counts: dict = {}
    summary_details: dict = {}

    for elem in elements:
        type_name = type_getter(elem)
        # Type removed entirely.
        if type_name in old_types and type_name not in new_types:
            key = (removed_kind, type_name, "")
            summary_counts[key] = summary_counts.get(key, 0) + 1
            summary_details[key] = (
                f"element type {type_name!r} removed from new schema"
            )
            if detail == "each":
                yield SchemaViolation(
                    kind=removed_kind,
                    type_name=type_name,
                    element_id=id_getter(elem),
                    graph_id=graph_id,
                    property_name="",
                    count=1,
                    detail=summary_details[key],
                )
            continue
        # Type present in both — property-level checks.
        diffs = type_diffs.get(type_name)
        if diffs is None:
            continue
        added, changed = diffs
        props = properties_getter(elem) or {}
        # Missing required (added in new schema, missing from element).
        for prop_name, expected_type in added.items():
            if prop_name not in props:
                key = ("missing_required_property", type_name, prop_name)
                summary_counts[key] = summary_counts.get(key, 0) + 1
                summary_details[key] = (
                    f"property {prop_name!r} (type {expected_type.value!r}) "
                    f"required by new schema; missing from persisted "
                    f"{type_name!r} elements"
                )
                if detail == "each":
                    yield SchemaViolation(
                        kind="missing_required_property",
                        type_name=type_name,
                        element_id=id_getter(elem),
                        graph_id=graph_id,
                        property_name=prop_name,
                        count=1,
                        detail=summary_details[key],
                    )
        # Tightened (type changed in new schema; persisted value
        # does not match the new type).
        for prop_name, (old_pt, new_pt) in changed.items():
            if prop_name not in props:
                continue  # missing-required path handles absences only
                # for newly-added props; for type-change on existing
                # absent prop, the old schema also allowed absence so
                # not a tightening.
            value = props[prop_name]
            if not _value_matches_type(value, new_pt):
                key = ("tightened_property", type_name, prop_name)
                summary_counts[key] = summary_counts.get(key, 0) + 1
                summary_details[key] = (
                    f"property {prop_name!r} tightened "
                    f"{old_pt.value!r} → {new_pt.value!r}; persisted "
                    f"{type_name!r} elements carry incompatible values"
                )
                if detail == "each":
                    yield SchemaViolation(
                        kind="tightened_property",
                        type_name=type_name,
                        element_id=id_getter(elem),
                        graph_id=graph_id,
                        property_name=prop_name,
                        count=1,
                        detail=summary_details[key],
                    )

    # Summary mode — emit one entry per (kind, type_name, property_name).
    if detail == "summary":
        for (kind, type_name, prop_name), count in summary_counts.items():
            yield SchemaViolation(
                kind=kind,
                type_name=type_name,
                element_id="",
                graph_id=graph_id,
                property_name=prop_name,
                count=count,
                detail=summary_details[(kind, type_name, prop_name)],
            )


def _value_matches_type(value: object, pt: PropertyType) -> bool:
    """Check if ``value`` matches the :class:`PropertyType` enum variant.

    Mirrors :mod:`mindsos_core.schema.schema` ``_TYPE_TO_PY`` mapping —
    primitives plus list-of-primitive. ``None`` never matches (the
    current PropertyType vocabulary has no nullable variant per
    ADR-0017 §strict semantics).
    """
    if value is None:
        return False
    if pt is PropertyType.STRING:
        return isinstance(value, str)
    if pt is PropertyType.INT:
        return isinstance(value, int) and not isinstance(value, bool)
    if pt is PropertyType.FLOAT:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if pt is PropertyType.BOOL:
        return isinstance(value, bool)
    if pt is PropertyType.LIST_STRING:
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    if pt is PropertyType.LIST_INT:
        return isinstance(value, list) and all(
            isinstance(v, int) and not isinstance(v, bool) for v in value
        )
    if pt is PropertyType.LIST_FLOAT:
        return isinstance(value, list) and all(
            isinstance(v, (int, float)) and not isinstance(v, bool)
            for v in value
        )
    if pt is PropertyType.LIST_BOOL:
        return isinstance(value, list) and all(isinstance(v, bool) for v in value)
    return False


__all__ = [
    "SchemaViolation",
    "SchemaMigrationError",
    "ViolationKind",
    "DetailMode",
    "migrate_from",
]
