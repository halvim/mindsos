"""Parameterised Cypher query builders (Phase 07 slim port).

Each builder returns a ``(query, params)`` tuple so callers can pass
them straight to the Client's ``run_query`` method.

**Phase 07 invariants:**

* **Typed-argument contract (P58 B).** Builders take typed primitives
  (str, int, Sequence[str], Mapping[str, Any]); they do NOT accept
  untyped ``dict`` blobs that bypass dataclass invariants. Callers
  construct from dataclass fields, not from raw dicts.
* **SET-order discipline.** MERGE-by-id-first, then ``SET props`` in a
  later clause so the immutable id can never be clobbered by the
  property bag.
* **Graph scoping.** Every element row carries a ``graph_id`` property
  (ADR-0021); hot-path index ``(:Node {graph_id})`` per P95 B uses it.
* **`_version` bump (P7 C).** Every update path includes
  ``SET n._version = coalesce(n._version, 0) + 1``. OCC predicate is
  conditional: when ``expected_version is not None`` the MATCH carries
  ``_version: $expected_version`` and zero rows return surfaces as
  :class:`OptimisticConcurrencyConflict`.
* **Tombstones (P69 A).** Per-(graph, element) tombstone shape:
  ``(:Tombstone {graph_id, element_id, element_kind, removed_at})``.
  Replaces v3's per-graph anchor (which couldn't represent multiple
  removals of distinct elements).
* **Cypher rel-type validation (ADR-0021).** Relationship type names
  are validated via :func:`validate_edge_type_identifier` before being
  spliced into Cypher text.

XRef builders ship in Phase 09 (:func:`build_create_xref` +
:func:`build_remove_xref`). Streaming / iter_load (ADR-0124) shipped
in Phase 08.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .identifiers import validate_edge_type_identifier, validate_label_identifier


# ── anchors ─────────────────────────────────────────────────────────────────


def build_create_metagraph_anchor(
    metagraph_id: str,
    name: str,
    *,
    props_json: Optional[str] = None,
    schema_name: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    """MERGE a ``:Metagraph`` anchor node.

    Phase 07 changes from v3:
    * ``_props_json`` (ADR-0130) replaces the spread-properties dict.
    * ``schema_name`` (P100 A) added as plain Cypher property using
      the existing :attr:`Metagraph.schema_name` dataclass field.
    * ``_version`` initialised to 1 on first MERGE (coalesce-bump
      preserves any existing value on idempotent re-runs).
    """
    query = (
        "MERGE (m:Metagraph {id: $mid}) "
        "ON CREATE SET m._version = 1 "
        "SET m.name = $name, "
        "    m._props_json = $props_json, "
        "    m.schema_name = $schema_name "
        "RETURN m.id AS id, m._version AS version"
    )
    return query, {
        "mid": metagraph_id,
        "name": name,
        "props_json": props_json,
        "schema_name": schema_name,
    }


def build_create_graph_anchor(
    graph_id: str,
    name: str,
    role: Optional[str],
    metagraph_id: Optional[str],
) -> Tuple[str, Dict[str, Any]]:
    """MERGE a ``:Graph`` anchor node; optionally link to its parent metagraph.

    Phase 07 changes from v3:
    * Graph ``.properties`` writer NOT shipped (P9 C — deferred per
      §7 Q4). Anchor row carries only id/name/role/metagraph_id/_version.
    * ``_version`` initialised to 1 on first MERGE.
    """
    query = (
        "MERGE (g:Graph {id: $gid}) "
        "ON CREATE SET g._version = 1 "
        "SET g.name = $name, g.role = $role"
    )
    if metagraph_id is not None:
        query += (
            ", g.metagraph_id = $mid "
            "WITH g "
            "MATCH (m:Metagraph {id: $mid}) "
            "MERGE (g)-[:IN_METAGRAPH]->(m) "
        )
    query += " RETURN g.id AS id, g._version AS version"
    params: Dict[str, Any] = {
        "gid": graph_id,
        "name": name,
        "role": role,
    }
    if metagraph_id is not None:
        params["mid"] = metagraph_id
    return query, params


# ── tombstones (per-(graph, element) per P69 A) ────────────────────────────


def build_create_tombstone(
    graph_id: str, element_id: str, element_kind: str, removed_by: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """Create a tombstone row for a (graph, element) removal event.

    Per P69 A — replaces v3's per-graph anchor pattern. Each removed
    element gets its own ``:Tombstone`` row so the read-filter (Phase
    10) can scope by both ``graph_id`` and ``element_id``. ADR-0133
    soft-delete model.
    """
    query = (
        "MERGE (t:Tombstone {graph_id: $gid, element_id: $eid}) "
        "ON CREATE SET t.element_kind = $kind, "
        "              t.removed_at = timestamp(), "
        "              t.removed_by = $by "
        "RETURN t.graph_id AS graph_id, t.element_id AS element_id"
    )
    return query, {
        "gid": graph_id,
        "eid": element_id,
        "kind": element_kind,
        "by": removed_by,
    }


# ── UNWIND batched creates ─────────────────────────────────────────────────


def build_unwind_create_nodes(
    graph_id: str, rows: Sequence[Mapping[str, Any]]
) -> Tuple[str, Dict[str, Any]]:
    """Batched node create.

    Each row must contain: ``id``, ``type_name``, ``value`` (any
    primitive), ``props`` (dict), ``_version`` (int, default 1).
    """
    query = (
        "MATCH (g:Graph {id: $gid}) "
        "UNWIND $rows AS row "
        "MERGE (n:Node {id: row.id}) "
        "ON CREATE SET n._version = coalesce(row._version, 1) "
        "SET n.type_name = row.type_name, "
        "    n.value = row.value, "
        "    n.graph_id = $gid, "
        "    n += row.props "
        "MERGE (n)-[:IN_GRAPH]->(g) "
        "RETURN count(n) AS n"
    )
    return query, {"gid": graph_id, "rows": list(rows)}


def build_unwind_create_edges(
    graph_id: str, type_name: str, rows: Sequence[Mapping[str, Any]]
) -> Tuple[str, Dict[str, Any]]:
    """Batched directed edge create for a single relationship type.

    Rel type is validated then spliced (FalkorDB cannot parameterise
    rel types). Each row: ``id``, ``source``, ``target``, ``label``,
    ``props``, ``_version``.
    """
    validate_edge_type_identifier(type_name)
    query = (
        "UNWIND $rows AS row "
        "MATCH (s:Node {id: row.source, graph_id: $gid}) "
        "MATCH (t:Node {id: row.target, graph_id: $gid}) "
        f"MERGE (s)-[e:{type_name} {{id: row.id}}]->(t) "
        "ON CREATE SET e._version = coalesce(row._version, 1) "
        "SET e.label = row.label, "
        "    e.graph_id = $gid, "
        "    e.type_name = $type_name, "
        "    e += row.props "
        "RETURN count(e) AS n"
    )
    return query, {"gid": graph_id, "type_name": type_name, "rows": list(rows)}


def build_unwind_create_hyperedges(
    graph_id: str, rows: Sequence[Mapping[str, Any]]
) -> Tuple[str, Dict[str, Any]]:
    """Batched hyperedge create.

    Each row: ``id``, ``label``, ``props``, ``member_ids`` (Sequence[str]),
    ``_version``.
    """
    query = (
        "MATCH (g:Graph {id: $gid}) "
        "UNWIND $rows AS row "
        "MERGE (h:HyperEdge {id: row.id}) "
        "ON CREATE SET h._version = coalesce(row._version, 1) "
        "SET h.graph_id = $gid, h.label = row.label, h += row.props "
        "MERGE (h)-[:IN_GRAPH]->(g) "
        "WITH h, row "
        "UNWIND row.member_ids AS nid "
        "MATCH (n:Node {id: nid, graph_id: $gid}) "
        "MERGE (h)-[:MEMBER]->(n) "
        "RETURN count(DISTINCT h) AS n"
    )
    return query, {"gid": graph_id, "rows": list(rows)}


# ── meta-edge / meta-hyperedge (Phase 05a/05d) ──────────────────────────────


def build_unwind_create_metaedges(
    metagraph_id: str, type_name: str, rows: Sequence[Mapping[str, Any]]
) -> Tuple[str, Dict[str, Any]]:
    """Batched directed MetaEdge create for a single rel type.

    MetaEdges connect two Graphs in the same Metagraph (ADR-0021 rel
    type). Each row: ``id``, ``source_graph_id``, ``target_graph_id``,
    ``label``, ``props``, ``_version``.
    """
    validate_edge_type_identifier(type_name)
    query = (
        "MATCH (m:Metagraph {id: $mid}) "
        "UNWIND $rows AS row "
        "MATCH (sg:Graph {id: row.source_graph_id})-[:IN_METAGRAPH]->(m) "
        "MATCH (tg:Graph {id: row.target_graph_id})-[:IN_METAGRAPH]->(m) "
        f"MERGE (sg)-[e:{type_name} {{id: row.id}}]->(tg) "
        "ON CREATE SET e._version = coalesce(row._version, 1) "
        "SET e.label = row.label, "
        "    e.metagraph_id = $mid, "
        "    e.type_name = $type_name, "
        "    e += row.props "
        "RETURN count(e) AS n"
    )
    return query, {"mid": metagraph_id, "type_name": type_name, "rows": list(rows)}


def build_unwind_create_metahyperedges(
    metagraph_id: str, rows: Sequence[Mapping[str, Any]]
) -> Tuple[str, Dict[str, Any]]:
    """Batched MetaHyperEdge create.

    MetaHyperEdges connect N Graphs in the same Metagraph (n-ary).
    Each row: ``id``, ``type_name`` (Phase 08 B-08-T3 hotfix —
    previously absent; round-trip required), ``label``, ``props``,
    ``member_graph_ids`` (Sequence[str]), ``_version``.
    """
    query = (
        "MATCH (m:Metagraph {id: $mid}) "
        "UNWIND $rows AS row "
        "MERGE (mh:MetaHyperEdge {id: row.id}) "
        "ON CREATE SET mh._version = coalesce(row._version, 1) "
        # Phase 08 B-08-T3 — also persist ``type_name`` so round-trip
        # preserves the dataclass field. Phase 07 omitted this; load
        # then read ``mh.type_name`` as None → CypherError on rehydrate.
        "SET mh.metagraph_id = $mid, "
        "    mh.label = row.label, "
        "    mh.type_name = row.type_name, "
        "    mh += row.props "
        "MERGE (mh)-[:IN_METAGRAPH]->(m) "
        "WITH mh, row "
        "UNWIND row.member_graph_ids AS gid "
        "MATCH (g:Graph {id: gid})-[:IN_METAGRAPH]->(:Metagraph {id: $mid}) "
        "MERGE (mh)-[:MEMBER_GRAPH]->(g) "
        "RETURN count(DISTINCT mh) AS n"
    )
    return query, {"mid": metagraph_id, "rows": list(rows)}


# ── intergraph-edge / intergraph-hyperedge (Phase 05b/05c) ──────────────────


def build_unwind_create_intergraph_edges(
    metagraph_id: str, type_name: str, rows: Sequence[Mapping[str, Any]]
) -> Tuple[str, Dict[str, Any]]:
    """Batched directed IntergraphEdge create.

    IntergraphEdges connect two Nodes that live in different Graphs of
    the same Metagraph (ADR-0021 rel type, ADR-0148). Each row: ``id``,
    ``source_node_id``, ``source_graph_id``, ``target_node_id``,
    ``target_graph_id``, ``label``, ``compositional`` (bool), ``props``,
    ``_version``.
    """
    validate_edge_type_identifier(type_name)
    query = (
        "MATCH (m:Metagraph {id: $mid}) "
        "UNWIND $rows AS row "
        "MATCH (s:Node {id: row.source_node_id, graph_id: row.source_graph_id}) "
        "MATCH (t:Node {id: row.target_node_id, graph_id: row.target_graph_id}) "
        f"MERGE (s)-[e:{type_name} {{id: row.id}}]->(t) "
        "ON CREATE SET e._version = coalesce(row._version, 1) "
        "SET e.label = row.label, "
        "    e.metagraph_id = $mid, "
        "    e.type_name = $type_name, "
        "    e.compositional = row.compositional, "
        "    e += row.props "
        "RETURN count(e) AS n"
    )
    return query, {"mid": metagraph_id, "type_name": type_name, "rows": list(rows)}


def build_unwind_create_intergraph_hyperedges(
    metagraph_id: str, rows: Sequence[Mapping[str, Any]]
) -> Tuple[str, Dict[str, Any]]:
    """Batched IntergraphHyperEdge create (n-ary; cross-graph).

    Each row: ``id``, ``label``, ``ordered`` (bool), ``compositional``
    (bool), ``props``, ``anchors`` (Sequence[Mapping] with ``node_id``
    and ``graph_id`` per entry — written via ``:ANCHOR`` rels per
    ADR-0148 Pattern B amended; **Phase 08 P61 A** fix to Phase 07's
    members-only persist), ``members`` (same shape — written via
    ``:MEMBER``), ``_version``.

    Per Phase 08 P61 A: Phase 07's implementation persisted only
    ``:MEMBER`` rels, which left anchor information unrecoverable on
    load. The dataclass invariant ``n_anchors ≥ 1`` made round-trip
    impossible. The fix is additive — extends the persist row with
    an ``anchors`` list and emits a second UNWIND for ``:ANCHOR`` rels.
    Backwards-compatible with Phase 07 readers (they ignore the new
    rels); forwards-compatible with Phase 08 load
    (:class:`MetagraphLoader` reads both ``:ANCHOR`` + ``:MEMBER``).
    """
    query = (
        "MATCH (m:Metagraph {id: $mid}) "
        "UNWIND $rows AS row "
        "MERGE (ih:IntergraphHyperEdge {id: row.id}) "
        "ON CREATE SET ih._version = coalesce(row._version, 1) "
        # Phase 08 B-08-T3 — also persist ``type_name`` so round-trip
        # preserves the dataclass field. Symmetric with MetaHyperEdge fix.
        "SET ih.metagraph_id = $mid, "
        "    ih.label = row.label, "
        "    ih.type_name = row.type_name, "
        "    ih.ordered = row.ordered, "
        "    ih.compositional = row.compositional, "
        "    ih += row.props "
        "MERGE (ih)-[:IN_METAGRAPH]->(m) "
        "WITH ih, row "
        # Phase 08 P61 A — write :ANCHOR rels alongside :MEMBER rels so
        # the dataclass round-trip preserves both sides.
        "UNWIND row.anchors AS anc "
        "MATCH (an:Node {id: anc.node_id, graph_id: anc.graph_id}) "
        "MERGE (ih)-[:ANCHOR]->(an) "
        "WITH ih, row "
        "UNWIND row.members AS mem "
        "MATCH (n:Node {id: mem.node_id, graph_id: mem.graph_id}) "
        "MERGE (ih)-[:MEMBER]->(n) "
        "RETURN count(DISTINCT ih) AS n"
    )
    return query, {"mid": metagraph_id, "rows": list(rows)}


# ── updates (with _version bump + optional OCC predicate) ───────────────────


def build_update_node_properties(
    graph_id: str,
    node_id: str,
    properties: Mapping[str, Any],
    *,
    expected_version: Optional[int] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Update node property bag; always bumps ``_version``; OCC opt-in.

    Per P7 C — ``_version`` ALWAYS bumps on update path. When
    ``expected_version`` is supplied, the MATCH predicate carries it;
    zero rows returned ⇒ caller raises
    :class:`OptimisticConcurrencyConflict` (repository layer wraps).
    """
    if expected_version is None:
        match = "MATCH (n:Node {id: $nid, graph_id: $gid}) "
    else:
        match = (
            "MATCH (n:Node {id: $nid, graph_id: $gid, _version: $expected}) "
        )
    query = (
        match
        + "SET n += $props, "
        + "    n._version = coalesce(n._version, 0) + 1 "
        + "RETURN n.id AS id, n._version AS version"
    )
    params: Dict[str, Any] = {
        "gid": graph_id,
        "nid": node_id,
        "props": dict(properties),
    }
    if expected_version is not None:
        params["expected"] = expected_version
    return query, params


def build_update_edge_properties(
    graph_id: str,
    edge_id: str,
    properties: Mapping[str, Any],
    *,
    expected_version: Optional[int] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Update edge property bag; always bumps ``_version``; OCC opt-in."""
    if expected_version is None:
        match = "MATCH ()-[e {id: $eid, graph_id: $gid}]->() "
    else:
        match = "MATCH ()-[e {id: $eid, graph_id: $gid, _version: $expected}]->() "
    query = (
        match
        + "SET e += $props, "
        + "    e._version = coalesce(e._version, 0) + 1 "
        + "RETURN e.id AS id, e._version AS version"
    )
    params: Dict[str, Any] = {
        "gid": graph_id,
        "eid": edge_id,
        "props": dict(properties),
    }
    if expected_version is not None:
        params["expected"] = expected_version
    return query, params


def build_update_hyperedge_properties(
    graph_id: str,
    hyperedge_id: str,
    properties: Mapping[str, Any],
    *,
    expected_version: Optional[int] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Update hyperedge property bag; always bumps ``_version``; OCC opt-in."""
    if expected_version is None:
        match = "MATCH (h:HyperEdge {id: $hid, graph_id: $gid}) "
    else:
        match = (
            "MATCH (h:HyperEdge {id: $hid, graph_id: $gid, _version: $expected}) "
        )
    query = (
        match
        + "SET h += $props, "
        + "    h._version = coalesce(h._version, 0) + 1 "
        + "RETURN h.id AS id, h._version AS version"
    )
    params: Dict[str, Any] = {
        "gid": graph_id,
        "hid": hyperedge_id,
        "props": dict(properties),
    }
    if expected_version is not None:
        params["expected"] = expected_version
    return query, params


# ── removals (write tombstone + DETACH DELETE element) ──────────────────────


def build_remove_node(
    graph_id: str, node_id: str, *, removed_by: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """Tombstone-write + DETACH DELETE for a node.

    Tombstone row created per-(graph, element) per P69 A. Read-path
    filter (Phase 10) honours soft-delete via ADR-0133.
    """
    query = (
        "MERGE (t:Tombstone {graph_id: $gid, element_id: $nid}) "
        "ON CREATE SET t.element_kind = 'node', "
        "              t.removed_at = timestamp(), "
        "              t.removed_by = $by "
        "WITH t "
        "MATCH (n:Node {id: $nid, graph_id: $gid}) "
        "DETACH DELETE n "
        "RETURN $nid AS id"
    )
    return query, {"gid": graph_id, "nid": node_id, "by": removed_by}


def build_remove_edge(
    graph_id: str, edge_id: str, *, removed_by: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """Tombstone-write + DELETE for an edge (any rel type)."""
    query = (
        "MERGE (t:Tombstone {graph_id: $gid, element_id: $eid}) "
        "ON CREATE SET t.element_kind = 'edge', "
        "              t.removed_at = timestamp(), "
        "              t.removed_by = $by "
        "WITH t "
        "MATCH ()-[e {id: $eid, graph_id: $gid}]->() "
        "DELETE e "
        "RETURN $eid AS id"
    )
    return query, {"gid": graph_id, "eid": edge_id, "by": removed_by}


def build_remove_hyperedge(
    graph_id: str, hyperedge_id: str, *, removed_by: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """Tombstone-write + DETACH DELETE for a hyperedge."""
    query = (
        "MERGE (t:Tombstone {graph_id: $gid, element_id: $hid}) "
        "ON CREATE SET t.element_kind = 'hyperedge', "
        "              t.removed_at = timestamp(), "
        "              t.removed_by = $by "
        "WITH t "
        "MATCH (h:HyperEdge {id: $hid, graph_id: $gid}) "
        "DETACH DELETE h "
        "RETURN $hid AS id"
    )
    return query, {"gid": graph_id, "hid": hyperedge_id, "by": removed_by}


# ── XRef (Phase 09 — ADR-0128) ──────────────────────────────────────────────


def build_create_xref(
    *,
    xref_id: str,
    source_metagraph_id: str,
    source_id: str,
    target_metagraph_id: str,
    target_role: str,
    target_id: str,
    ref_type: str,
    properties: Mapping[str, Any],
) -> Tuple[str, Dict[str, Any]]:
    """Create an :XRef anchor row for a cross-metagraph reference (ADR-0128).

    The row carries every field needed to round-trip the in-memory
    :class:`mindsos_core.models.xref.XRef`. The ``:XREF_OF`` edge
    links it to its source metagraph anchor for index-friendly
    lookups (M2 + RPB-3 forward-cascade).

    **Phase 09 P53 — 8 fields.** v3's ``target_stale`` and
    ``deprecated_at`` columns are NOT written; both ship in Phase 10
    with their setters.

    **MERGE-based** so the WAL ``xref_add`` replayer (PB-8) is
    idempotent on re-runs.
    """
    query = (
        "MERGE (m:Metagraph {id: $smid}) "
        "MERGE (x:XRef {id: $xid}) "
        "SET x.source_metagraph_id = $smid, x.source_id = $sid, "
        "    x.target_metagraph_id = $tmid, x.target_role = $trole, "
        "    x.target_id = $tid, x.ref_type = $ref_type, "
        "    x += $props "
        "MERGE (x)-[:XREF_OF]->(m) "
        "RETURN x.id AS id"
    )
    return query, {
        "xid": xref_id,
        "smid": source_metagraph_id,
        "sid": source_id,
        "tmid": target_metagraph_id,
        "trole": target_role,
        "tid": target_id,
        "ref_type": ref_type,
        "props": dict(properties),
    }


def build_remove_xref(xref_id: str) -> Tuple[str, Dict[str, Any]]:
    """DETACH DELETE the :XRef row + its :XREF_OF edge (idempotent).

    No tombstone row (XRefs aren't subject to soft-delete in Phase 09;
    see ADR-0128 + RPB-3 forward-cascade contract). The WAL
    ``xref_remove`` replayer re-runs this against the same xref_id
    safely (DETACH DELETE on a non-existent row is a no-op in
    FalkorDB).
    """
    query = (
        "MATCH (x:XRef {id: $xid}) "
        "DETACH DELETE x "
        "RETURN $xid AS id"
    )
    return query, {"xid": xref_id}


# ── instance persistence (consumed by mindsos_instances.persistence) ────────


def build_create_element_instance(
    instance_id: str,
    kind: str,
    metagraph_id: str,
    source_id: str,
    source_graph_id: Optional[str],
    overrides: Mapping[str, Any],
    label: Optional[str],
    extra_labels: Iterable[str] = (),
    member_ids: Optional[Sequence[str]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Create a dual-labelled instance node.

    Phase 06 P49 B / P25 A overrides — per ADR-0025 ``ov__`` prefix
    isolates instance overrides from Core metadata. Member edges
    materialise SubGraphInstance / GraphInstance selections (Phase 06
    P13 B triple).

    Per P11 A — ``_version`` initialised to 1.
    """
    kind_label = {
        "node": "NodeInstance",
        "edge": "EdgeInstance",
        "hyperedge": "HyperEdgeInstance",
        "subgraph": "SubGraphInstance",
        "graph": "GraphInstance",
        "metaedge": "MetaEdgeInstance",
        "metahyperedge": "MetaHyperEdgeInstance",
    }.get(kind)
    if kind_label is None:
        raise ValueError(f"Unknown ElementInstance kind: {kind!r}")
    validate_label_identifier(kind_label)
    for lbl in extra_labels:
        validate_label_identifier(lbl)
    extra = "".join(f":{lbl}" for lbl in extra_labels)

    query = (
        f"MERGE (i:ElementInstance:{kind_label}{extra} {{id: $iid}}) "
        "ON CREATE SET i._version = 1 "
        "SET i.kind = $kind, "
        "    i.metagraph_id = $mid, "
        "    i.source_id = $sid, "
        "    i.source_graph_id = $sgid, "
        "    i.label = $label, "
        "    i += $overrides_prefixed "
        "WITH i "
        "MATCH (m:Metagraph {id: $mid}) "
        "MERGE (i)-[:IN_METAGRAPH]->(m) "
    )
    if member_ids is not None:
        query += (
            "WITH i "
            "UNWIND $member_ids AS nid "
            "MATCH (n:Node {id: nid}) "
            "MERGE (i)-[:MEMBER]->(n) "
        )
    query += "RETURN i.id AS id, i._version AS version"

    overrides_prefixed = {f"ov__{k}": v for k, v in overrides.items()}
    params: Dict[str, Any] = {
        "iid": instance_id,
        "kind": kind,
        "mid": metagraph_id,
        "sid": source_id,
        "sgid": source_graph_id,
        "label": label,
        "overrides_prefixed": overrides_prefixed,
    }
    if member_ids is not None:
        params["member_ids"] = list(member_ids)
    return query, params


def build_create_composite_instance(
    instance_id: str,
    metagraph_id: str,
    member_instance_ids: Sequence[str],
    overrides: Mapping[str, Any],
    label: Optional[str],
) -> Tuple[str, Dict[str, Any]]:
    """Create a ``:CompositeInstance`` node and wire its member relationships.

    Members may be ``:ElementInstance`` or other ``:CompositeInstance``
    (generic MATCH). Per P11 A — ``_version`` initialised to 1.
    """
    query = (
        "MERGE (c:CompositeInstance {id: $iid}) "
        "ON CREATE SET c._version = 1 "
        "SET c.metagraph_id = $mid, c.label = $label, c += $overrides_prefixed "
        "WITH c "
        "MATCH (m:Metagraph {id: $mid}) "
        "MERGE (c)-[:IN_METAGRAPH]->(m) "
        "WITH c "
        "UNWIND $member_ids AS miid "
        "MATCH (x {id: miid}) "
        "WHERE x:ElementInstance OR x:CompositeInstance "
        "MERGE (c)-[:HAS_MEMBER]->(x) "
        "RETURN c.id AS id, c._version AS version"
    )
    overrides_prefixed = {f"ov__{k}": v for k, v in overrides.items()}
    return query, {
        "iid": instance_id,
        "mid": metagraph_id,
        "label": label,
        "overrides_prefixed": overrides_prefixed,
        "member_ids": list(member_instance_ids),
    }


__all__ = [
    "build_create_metagraph_anchor",
    "build_create_graph_anchor",
    "build_create_tombstone",
    "build_unwind_create_nodes",
    "build_unwind_create_edges",
    "build_unwind_create_hyperedges",
    "build_unwind_create_metaedges",
    "build_unwind_create_metahyperedges",
    "build_unwind_create_intergraph_edges",
    "build_unwind_create_intergraph_hyperedges",
    "build_update_node_properties",
    "build_update_edge_properties",
    "build_update_hyperedge_properties",
    "build_remove_node",
    "build_remove_edge",
    "build_remove_hyperedge",
    "build_create_xref",
    "build_remove_xref",
    "build_create_element_instance",
    "build_create_composite_instance",
]
