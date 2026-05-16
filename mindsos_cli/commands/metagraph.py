"""``mindsos metagraph`` — Phase 05a base + Phase 05b extensions.

Subcommands (Phase 05a Q2 + CR-A locked + Phase 05b 5 new subcommands +
4-way set-prop mutex per Pushback 27-A):

  mindsos metagraph create --name <NAME> [--metagraph-id ID] [--prop k=v]... [--json]
  mindsos metagraph inspect --name <NAME> [--json]
  mindsos metagraph list [--json]
  mindsos metagraph reset (--name NAME | --all) [--force] [--yes] [--json]
  mindsos metagraph add-graph --name <MG> --graph <G> [--json]
  mindsos metagraph remove-graph --name <MG> --graph <G> [--json]
  mindsos metagraph add-metaedge --name <MG> --source-graph <G> --target-graph <G>
                                  --type <REL_TYPE> [--label L] [--prop k=v]...
                                  [--metaedge-id ID] [--json]
  mindsos metagraph remove-metaedge --name <MG> --metaedge-id <ID> [--json]
  mindsos metagraph add-metahyperedge --name <MG> --member <G> --member <G>
                                      [--member <G>...] --type <REL_TYPE>
                                      [--label L] [--prop k=v]...
                                      [--metahyperedge-id ID] [--json]
  mindsos metagraph remove-metahyperedge --name <MG> --metahyperedge-id <ID> [--json]
  mindsos metagraph set-prop --name <MG>
                              (--on-metagraph
                               | --metaedge-id <ID>
                               | --metahyperedge-id <ID>
                               | --intergraph-edge-id <ID>)         # P05b Pushback 27-A
                              --prop k=v [--prop k2=v2 ...] [--replace] [--json]
  mindsos metagraph list-metaedges --name <MG> [--json]
  mindsos metagraph list-metahyperedges --name <MG> [--json]
  # ── Phase 05b additions (ADR-0148 first draft) ──
  mindsos metagraph add-intergraph-edge --name <MG>
                                        --source-graph <G> --source-node <N>
                                        --target-graph <G> --target-node <N>
                                        --type <REL_TYPE>
                                        [--label L] [--prop k=v]...
                                        [--compositional]
                                        [--intergraph-edge-id ID] [--json]
  mindsos metagraph remove-intergraph-edge --name <MG> --intergraph-edge-id <ID> [--json]
  mindsos metagraph list-intergraph-edges --name <MG> [--json]
  mindsos metagraph attach-schema --name <MG> --schema <MS> [--json]
  mindsos metagraph detach-schema --name <MG> [--json]    # DMS-A unified command

Locked round 1-4 design picks reflected here:

* **P5** — ``reset --force`` and ``reset --all`` require ``--yes`` (or
  prompt confirmation when stdin is a TTY).
* **P10** — ``inspect`` / ``list`` JSON shapes locked (see helper docs).
* **P11** — Internal API uses graph_id strings; CLI accepts graph NAMES
  and translates name→graph_id at the boundary.
* **P15** — ``add-metaedge`` refuses self-loop; ``add-metahyperedge``
  refuses < 2 members (via Metagraph factory ``SchemaError``).
* **P17** — ``set-prop`` 3-way mutex: ``--on-metagraph | --metaedge-id |
  --metahyperedge-id``. ``--on-metagraph`` operates on the metagraph's
  own ADR-0130 property bag.
* **P18** — ``add-graph`` writes graph state file (back-pointer set)
  FIRST, then metagraph state file. Recovery on partial failure: DM-A
  (``mindsos graph detach-metagraph``).
* **Q5-A** — Eager id-collision check on ``add-graph`` (delegated to
  ``Metagraph.add_graph``).
* **Q6-A** — ``reset --name X`` orphan check: refuse with exit 1 if any
  graph state file references this metagraph; ``--force`` strips
  back-pointers from referenced graphs (warning to stderr).
* **N7-A** — ``add-graph`` refuses if the graph already has a non-null
  ``metagraph_name`` back-pointer (graph is metagraph-owned).
* **CR-A** — ``create`` accepts ``--prop k=v`` at create time (mirrors
  Phase 03 / 04 ``add-*`` precedent); ``--metagraph-id`` allowed.

Cross-invocation persistence: JSON state file at
``${MINDSOS_STATE_DIR or ~/.mindsos}/metagraph-<name>.json``. Phase 05a
introduces this state-file kind at v=1. Migration chain at
``mindsos_cli.migrations.metagraph`` (empty in 05a; future bumps in
05b / 05c / 10).

Exit codes:
  1 — domain errors (IdentityError, SchemaError, CypherError,
      PropertyShapeError, missing/malformed state file, refusals
      under Q4-B / Q5-A / Q6-A / N7-A / P15).
  2 — usage errors (missing required arg, malformed flag, mutex
      violations, invalid name, missing --yes for destructive).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import Any, List, Optional

import typer

from mindsos_core import (
    CompositionalImmutableError,
    CypherError,
    Graph,
    IdentityError,
    IntergraphHyperEdgeType,
    Metagraph,
    MetagraphSchema,
    PropertyShapeError,
    PropertyType,
    REF_PROPERTY_PREFIX,
    SchemaError,
    UnknownTypeError,
)
from mindsos_cli import state as state_mod
from mindsos_cli.commands.graph import (
    _load_or_die as _graph_load_or_die,
    _graph_to_state,
    _parse_props,
    _split_existing_refs,
    _state_to_graph as _graph_state_to_graph,
)


metagraph_app = typer.Typer(
    name="metagraph",
    help="L1 Metagraph + MetaEdge + MetaHyperEdge (Phase 05a).",
    no_args_is_help=True,
    add_completion=False,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _iso_or_null(value: Any) -> Any:
    """Phase 10 RR-8 — serialize ``datetime|None`` to ``str|None`` (ISO-8601)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return value  # already-string or unknown — pass through unchanged.


def _iso_to_datetime(value: Any) -> Any:
    """Phase 10 RR-8 — deserialize ``str|None`` to ``datetime|None``."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return None
    return None


def _metagraph_to_state(mg: Metagraph) -> dict:
    """Serialize a ``Metagraph`` to the v=3 state-file dict (P10 + 05b + 05c shape).

    Persistence keys metaedges/metahyperedges/intergraph_edges/
    intergraph_hyperedges by graph NAME (not graph_id) — readability
    and locality. The serializer translates id→name via ``mg.graphs``
    lookup. Per Phase 05a Q3-A ``member_graphs`` is sorted by graph_name
    for byte-stable output.

    Phase 05b additions (Pushback 18-A bump v=1 → v=2):
    * ``intergraph_edges`` array — sorted by edge_id; each entry stores
      source/target by graph NAME and node id.
    * ``schema_name`` reference to attached :class:`MetagraphSchema`
      state file (or null).

    Phase 05c additions (P14-A smaller-items fold bump v=2 → v=3):
    * ``intergraph_hyperedges`` array — sorted by edge_id; each entry
      stores anchors and members as ``[graph_name, node_id]`` pair lists
      (NOT canonicalized at serialization — the factory canonicalized
      at construction time per ``type.ordered``; the persisted form
      reflects what's in memory).

    Phase 09 additions (RR-7 + RR-8 + RR-12 + RR-18 bump v=3 → v=4):
    * ``xrefs`` array — sorted by xref_id for stable round-trip diffs;
      each entry is an 8-field dict (xref_id / source_metagraph_id /
      source_id / target_metagraph_id / target_role / target_id /
      ref_type / properties). P53 deferred fields (target_stale +
      deprecated_at) NOT serialized.

    Top-level lists byte-stable sorted (Phase 05a P10 pattern extended).
    """
    # contained_graphs sorted by graph name for byte-stable output.
    contained_graphs = sorted(g.name for g in mg.graphs.values())
    # id → name lookup for metaedge / metahyperedge / intergraph_*edge.
    id_to_name = {g.graph_id: g.name for g in mg.graphs.values()}
    metaedges = sorted(mg.metaedges.values(), key=lambda me: me.edge_id)
    metahyperedges = sorted(
        mg.metahyperedges.values(), key=lambda mhe: mhe.edge_id
    )
    intergraph_edges = sorted(
        mg.intergraph_edges.values(), key=lambda ie: ie.edge_id
    )
    intergraph_hyperedges = sorted(
        mg.intergraph_hyperedges.values(), key=lambda ihe: ihe.edge_id
    )
    return {
        "_state_version": state_mod.METAGRAPH_STATE_VERSION,
        "metagraph_id": mg.metagraph_id,
        "name": mg.name,
        "properties": dict(mg.properties),
        "schema_name": mg.schema_name,  # P05b — Pushback 11-A reference.
        "contained_graphs": contained_graphs,
        "metaedges": [
            {
                "edge_id": me.edge_id,
                "source_graph": id_to_name[me.source_graph_id],
                "target_graph": id_to_name[me.target_graph_id],
                "type_name": me.type_name,
                "label": me.label,
                "properties": dict(me.properties),
                # Phase 10 RR-19 — soft-delete fields (M11 v=5 extension).
                "deprecated_at": _iso_or_null(me.deprecated_at),
                "disputed_at": _iso_or_null(me.disputed_at),
            }
            for me in metaedges
        ],
        "metahyperedges": [
            {
                "edge_id": mhe.edge_id,
                "type_name": mhe.type_name,
                # Q3-A — sort by graph_name for byte-stable output.
                "member_graphs": sorted(
                    id_to_name[gid] for gid in mhe.graph_ids
                ),
                "label": mhe.label,
                "properties": dict(mhe.properties),
                # Phase 10 RR-19 — soft-delete fields.
                "deprecated_at": _iso_or_null(mhe.deprecated_at),
                "disputed_at": _iso_or_null(mhe.disputed_at),
            }
            for mhe in metahyperedges
        ],
        # P05b — Pushback 2-A: ``compositional`` top-level field on each
        # entry. Pushback 27-A ordering: source-side first, target-side
        # second, type/compositional/label/properties tail.
        "intergraph_edges": [
            {
                "edge_id": ie.edge_id,
                "source_graph": id_to_name[ie.source_graph_id],
                "source_node": ie.source_node_id,
                "target_graph": id_to_name[ie.target_graph_id],
                "target_node": ie.target_node_id,
                "type_name": ie.type_name,
                "compositional": ie.compositional,
                "label": ie.label,
                "properties": dict(ie.properties),
            }
            for ie in intergraph_edges
        ],
        # P05c — n-ary primitive (ADR-0148 amended). anchors / members
        # serialized as lists of [graph_name, node_id] pair-lists. Order
        # within each side preserves construction-order (post-
        # canonicalization in factory step 7 per type.ordered).
        "intergraph_hyperedges": [
            {
                "edge_id": ihe.edge_id,
                "anchors": [
                    [id_to_name[gid], nid] for (gid, nid) in ihe.anchors
                ],
                "members": [
                    [id_to_name[gid], nid] for (gid, nid) in ihe.members
                ],
                "type_name": ihe.type_name,
                "compositional": ihe.compositional,
                "label": ihe.label,
                "properties": dict(ihe.properties),
            }
            for ihe in intergraph_hyperedges
        ],
        # Phase 09 RR-8 — XRef shape; Phase 10 P53 reversal restores
        # ``target_stale`` + ``deprecated_at`` (10 fields total per
        # M11 v=5 + RR-19). Sorted by xref_id for stable round-trip diffs.
        "xrefs": sorted(
            (
                {
                    "xref_id": x.xref_id,
                    "source_metagraph_id": x.source_metagraph_id,
                    "source_id": x.source_id,
                    "target_metagraph_id": x.target_metagraph_id,
                    "target_role": x.target_role,
                    "target_id": x.target_id,
                    "ref_type": x.ref_type,
                    "properties": dict(x.properties),
                    # Phase 10 P53 reversal + RR-19.
                    "target_stale": x.target_stale,
                    "deprecated_at": _iso_or_null(x.deprecated_at),
                }
                for x in mg.xrefs.values()
            ),
            key=lambda d: d["xref_id"],
        ),
    }


def _state_to_metagraph(state: dict) -> Metagraph:
    """Rehydrate a ``Metagraph`` from a v=2 state-file dict (P05b shape).

    Walks ``contained_graphs`` (graph names) and loads each via
    ``mindsos_cli.state.load_graph_state`` → rehydrates → ``add_graph``.
    Each ``add_graph`` runs the ADR-0020 unification + Q5-A collision
    check (so corrupt states with id collisions surface here).

    For metaedges / metahyperedges / intergraph_edges: looks up
    source_graph / target_graph / member_graphs names in the metagraph's
    contained graphs to resolve graph_ids, then constructs the dataclass
    instances directly (bypassing the factory's CLI-friendly error UX
    since we're rehydrating known-valid persisted state).

    Phase 05b additions (Pushback 18-A v=2):

    * Walks ``intergraph_edges`` array; constructs :class:`IntergraphEdge`
      instances; registers ``edge_id`` in ``mg.identity``.
    * If ``schema_name`` is non-null, attempts to load the referenced
      :class:`MetagraphSchema` state file. On success, calls
      ``mg.attach_schema(ms, schema_name=...)`` (eager validation runs;
      raises if drift since previous attach). On FileNotFoundError, sets
      ``mg.schema_name`` to the dangling reference WITHOUT loading a
      schema (DMS-A recovery — Pushback 28-A — surfaces via subsequent
      schema-needing operations refusing with structured pointer to
      ``mindsos metagraph detach-schema``). The dangling reference path
      enables the unified detach-schema command's raw-JSON fallback.
    """
    from mindsos_core.models.intergraph_edge import IntergraphEdge
    from mindsos_core.models.intergraph_hyperedge import IntergraphHyperEdge
    from mindsos_core.models.metagraph import MetaEdge, MetaHyperEdge

    mg = Metagraph(
        name=state["name"],
        metagraph_id=state["metagraph_id"],
        properties=state.get("properties") or {},
    )
    # __init__ does NOT auto-register because metagraph_id was passed; do it.
    mg.identity.register(state["metagraph_id"])

    # Load + add each contained graph.
    for gname in state.get("contained_graphs") or []:
        try:
            g_state = state_mod.load_graph_state(gname)
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Metagraph {state['name']!r} references missing graph "
                f"{gname!r}: {e}"
            ) from e
        # Rehydrate the graph (returns (graph, schema_name, metagraph_name)).
        g, _schema_name, _mg_back = _graph_state_to_graph(g_state)
        mg.add_graph(g)

    # name → id lookup for metaedge / metahyperedge / intergraph_edge rehydration.
    name_to_id = {g.name: g.graph_id for g in mg.graphs.values()}

    for me_dict in state.get("metaedges") or []:
        me = MetaEdge(
            source_graph_id=name_to_id[me_dict["source_graph"]],
            target_graph_id=name_to_id[me_dict["target_graph"]],
            type_name=me_dict["type_name"],
            label=me_dict.get("label"),
            edge_id=me_dict["edge_id"],
            properties=dict(me_dict.get("properties") or {}),
        )
        # Phase 10 RR-18 — restore soft-delete fields directly (bypass
        # the public setter so dirty-tracking doesn't fire on rehydrate).
        me.deprecated_at = _iso_to_datetime(me_dict.get("deprecated_at"))
        me.disputed_at = _iso_to_datetime(me_dict.get("disputed_at"))
        mg.identity.register(me.edge_id)
        mg.metaedges[me.edge_id] = me

    for mhe_dict in state.get("metahyperedges") or []:
        graph_ids = [name_to_id[gname] for gname in mhe_dict["member_graphs"]]
        mhe = MetaHyperEdge(
            graph_ids=graph_ids,
            type_name=mhe_dict["type_name"],
            label=mhe_dict.get("label"),
            edge_id=mhe_dict["edge_id"],
            properties=dict(mhe_dict.get("properties") or {}),
        )
        # Phase 10 RR-18 — restore soft-delete fields.
        mhe.deprecated_at = _iso_to_datetime(mhe_dict.get("deprecated_at"))
        mhe.disputed_at = _iso_to_datetime(mhe_dict.get("disputed_at"))
        mg.identity.register(mhe.edge_id)
        mg.metahyperedges[mhe.edge_id] = mhe

    # Phase 05b — rehydrate intergraph_edges.
    for ie_dict in state.get("intergraph_edges") or []:
        ie = IntergraphEdge(
            source_graph_id=name_to_id[ie_dict["source_graph"]],
            source_node_id=ie_dict["source_node"],
            target_graph_id=name_to_id[ie_dict["target_graph"]],
            target_node_id=ie_dict["target_node"],
            type_name=ie_dict["type_name"],
            compositional=bool(ie_dict.get("compositional", False)),
            edge_id=ie_dict["edge_id"],
            label=ie_dict.get("label"),
            properties=dict(ie_dict.get("properties") or {}),
        )
        mg.identity.register(ie.edge_id)
        mg.intergraph_edges[ie.edge_id] = ie

    # Phase 05c — rehydrate intergraph_hyperedges. Persisted form stores
    # anchors / members as ``[graph_name, node_id]`` pair-lists; we
    # translate graph_name → graph_id at the boundary, then construct
    # the dataclass with already-canonicalized data (factory step 7
    # canonicalized at add-time; rehydration trusts the persisted
    # form). The ``__post_init__`` re-checks cardinality + overlap +
    # cypher regex per P32 belt-and-suspenders.
    for ihe_dict in state.get("intergraph_hyperedges") or []:
        anchors_t = tuple(
            (name_to_id[pair[0]], pair[1])
            for pair in ihe_dict["anchors"]
        )
        members_t = tuple(
            (name_to_id[pair[0]], pair[1])
            for pair in ihe_dict["members"]
        )
        ihe = IntergraphHyperEdge(
            anchors=anchors_t,
            members=members_t,
            type_name=ihe_dict["type_name"],
            compositional=bool(ihe_dict.get("compositional", False)),
            edge_id=ihe_dict["edge_id"],
            label=ihe_dict.get("label"),
            properties=dict(ihe_dict.get("properties") or {}),
        )
        mg.identity.register(ihe.edge_id)
        mg.intergraph_hyperedges[ihe.edge_id] = ihe

    # Phase 09 RR-18 — rehydrate XRef rows directly into mg.xrefs +
    # manually rebuild inverse indexes; bypass mg.add_xref (which would
    # trigger inline DB writes if _persist_client were set). Per
    # Phase 09 P64: leaves mg._xrefs_dirty EMPTY — state-file-shaped
    # data is by definition already-persisted, so the dirty set must
    # not be populated by deserialization.
    from mindsos_core.models.xref import XRef as _XRef

    for x_dict in state.get("xrefs") or []:
        xref = _XRef(
            xref_id=x_dict["xref_id"],
            source_metagraph_id=x_dict["source_metagraph_id"],
            source_id=x_dict["source_id"],
            target_metagraph_id=x_dict["target_metagraph_id"],
            target_role=x_dict["target_role"],
            target_id=x_dict["target_id"],
            ref_type=x_dict["ref_type"],
            properties=dict(x_dict.get("properties") or {}),
            # Phase 10 RR-18 + P53 reversal — restore Phase 10 fields.
            target_stale=bool(x_dict.get("target_stale") or False),
            deprecated_at=_iso_to_datetime(x_dict.get("deprecated_at")),
        )
        mg.identity.register(xref.xref_id)
        mg.xrefs[xref.xref_id] = xref
        mg._xrefs_by_source.setdefault(xref.source_id, set()).add(
            xref.xref_id
        )
        mg._xrefs_by_target.setdefault(
            (xref.target_metagraph_id, xref.target_id), set()
        ).add(xref.xref_id)
    # P64 explicit: deserialization MUST NOT mark anything dirty.
    mg._xrefs_dirty.clear()

    # Phase 05b — rehydrate schema_name reference + attach if present.
    schema_name = state.get("schema_name")
    if schema_name:
        try:
            ms_state = state_mod.load_metagraph_schema_state(schema_name)
        except FileNotFoundError:
            # DMS-A — dangling reference. Set schema_name without
            # loading the schema; subsequent schema-needing operations
            # will refuse with the structured pointer (Pushback 28-A).
            mg.schema_name = schema_name
            mg.schema = None
        except (ValueError, RuntimeError) as e:
            # Malformed schema state file — surface via a RuntimeError
            # at the caller boundary; CLI ``_load_or_die`` translates
            # to exit-1.
            raise RuntimeError(
                f"Metagraph {state['name']!r} references metagraph-schema "
                f"{schema_name!r} but the schema state file is malformed: "
                f"{e}. Recovery: 'mindsos metagraph detach-schema --name "
                f"{state['name']}' (DMS-A — Pushback 28-A)."
            ) from e
        else:
            ms = _state_to_metagraph_schema(ms_state)
            # mg.attach_schema runs eager validation; raises if drift.
            try:
                mg.attach_schema(ms, schema_name=schema_name)
            except (UnknownTypeError, PropertyShapeError) as e:
                raise RuntimeError(
                    f"Metagraph {state['name']!r} fails eager validation "
                    f"against schema {schema_name!r} (drift since previous "
                    f"attach? Pushback 23-A footgun): {e}. Recovery: "
                    f"'mindsos metagraph detach-schema --name "
                    f"{state['name']}' to clear the reference."
                ) from e

    return mg


def _metagraph_schema_to_state(ms: MetagraphSchema, *, name: str) -> dict:
    """Serialize a ``MetagraphSchema`` to the v=3 state-file dict (P05b + P05c + P05d).

    Per Pushback 24-hybrid + 18-A: the ``name`` is the basename (passed
    in by the CLI command since :class:`MetagraphSchema` is basename-keyed
    on disk and has no ``name`` field). All four vocab arrays byte-stable
    sorted by ``name``. Per-type frozensets serialized as sorted lists.

    Phase 05c additions:
    * ``intergraph_hyperedge_types`` array — same shape as
      ``intergraph_edge_types`` but with ``allowed_anchor_types`` /
      ``allowed_member_types`` / ``allowed_anchor_graphs`` /
      ``allowed_member_graphs`` instead of source/target, plus
      ``ordered: bool`` flag (default True per P18-A).

    Phase 05d additions (round-7 P31 A — schema state-file v=3):
    * ``meta_edge_types`` array — ``name`` + ``allowed_source_graphs`` +
      ``allowed_target_graphs`` + ``property_types`` + ``description``
      (no ``allowed_*_types``; metaedges connect graphs, not nodes).
    * ``meta_hyperedge_types`` array — ``name`` + ``allowed_member_graphs``
      + ``property_types`` + ``description`` (no ``ordered``; per P1 C
      MetaHyperEdge is graph-set semantics).
    """
    iet_sorted = sorted(
        ms.intergraph_edge_types.values(), key=lambda iet: iet.name
    )
    iht_sorted = sorted(
        ms.intergraph_hyperedge_types.values(), key=lambda iht: iht.name
    )
    met_sorted = sorted(
        ms.meta_edge_types.values(), key=lambda met: met.name
    )
    mht_sorted = sorted(
        ms.meta_hyperedge_types.values(), key=lambda mht: mht.name
    )
    return {
        "_state_version": state_mod.METAGRAPH_SCHEMA_STATE_VERSION,
        "name": name,
        "strict": ms.strict,
        "intergraph_edge_types": [
            {
                "name": iet.name,
                "allowed_source_types": sorted(iet.allowed_source_types),
                "allowed_target_types": sorted(iet.allowed_target_types),
                "allowed_source_graphs": sorted(iet.allowed_source_graphs),
                "allowed_target_graphs": sorted(iet.allowed_target_graphs),
                "property_types": {
                    k: v.value for k, v in iet.property_types.items()
                },
                "description": iet.description,
            }
            for iet in iet_sorted
        ],
        # P05c — ADR-0148 amended for n-ary primitive.
        "intergraph_hyperedge_types": [
            {
                "name": iht.name,
                "allowed_anchor_types": sorted(iht.allowed_anchor_types),
                "allowed_member_types": sorted(iht.allowed_member_types),
                "allowed_anchor_graphs": sorted(iht.allowed_anchor_graphs),
                "allowed_member_graphs": sorted(iht.allowed_member_graphs),
                "ordered": iht.ordered,
                "property_types": {
                    k: v.value for k, v in iht.property_types.items()
                },
                "description": iht.description,
            }
            for iht in iht_sorted
        ],
        # P05d — ADR-0014 third amendment (round-7 P31 A locked shape).
        "meta_edge_types": [
            {
                "name": met.name,
                "allowed_source_graphs": sorted(met.allowed_source_graphs),
                "allowed_target_graphs": sorted(met.allowed_target_graphs),
                "property_types": {
                    k: v.value for k, v in met.property_types.items()
                },
                "description": met.description,
            }
            for met in met_sorted
        ],
        "meta_hyperedge_types": [
            {
                "name": mht.name,
                "allowed_member_graphs": sorted(mht.allowed_member_graphs),
                "property_types": {
                    k: v.value for k, v in mht.property_types.items()
                },
                "description": mht.description,
            }
            for mht in mht_sorted
        ],
    }


def _state_to_metagraph_schema(state: dict) -> MetagraphSchema:
    """Rehydrate a :class:`MetagraphSchema` from a v=3 state-file dict (P05b + P05c + P05d).

    Mirror of Phase 04 :class:`Schema` rehydration: cast frozensets back
    from JSON arrays; ``PropertyType`` cast from ``.value`` strings;
    duplicate-name registration cannot fire on a clean state file.

    Phase 05c adds rehydration of ``intergraph_hyperedge_types`` from
    the v=2 state-file shape. v=1 state files (Phase 05b) load via the
    migration chain which populates ``intergraph_hyperedge_types: []``
    default — so the loop body below iterates an empty list on legacy
    inputs.

    Phase 05d adds rehydration of ``meta_edge_types`` +
    ``meta_hyperedge_types`` from the v=3 state-file shape (round-7
    P31 A locked shape — no fingerprint envelope, only the two new
    vocab arrays). v=2 state files (Phase 05c) load via the migration
    chain which populates both arrays as ``[]`` default.
    """
    from mindsos_core import (
        IntergraphEdgeType,
        IntergraphHyperEdgeType,
        MetaEdgeType,
        MetaHyperEdgeType,
    )

    ms = MetagraphSchema(strict=bool(state.get("strict", False)))
    for iet_dict in state.get("intergraph_edge_types") or []:
        prop_types_raw = iet_dict.get("property_types") or {}
        try:
            prop_types = {k: PropertyType(v) for k, v in prop_types_raw.items()}
        except ValueError as e:
            raise RuntimeError(
                f"MetagraphSchema rehydration: unrecognised PropertyType "
                f"value in intergraph_edge_type {iet_dict.get('name')!r}: {e}"
            ) from e
        iet = IntergraphEdgeType(
            name=iet_dict["name"],
            allowed_source_types=frozenset(iet_dict.get("allowed_source_types") or []),
            allowed_target_types=frozenset(iet_dict.get("allowed_target_types") or []),
            allowed_source_graphs=frozenset(iet_dict.get("allowed_source_graphs") or []),
            allowed_target_graphs=frozenset(iet_dict.get("allowed_target_graphs") or []),
            property_types=prop_types,
            description=iet_dict.get("description"),
        )
        ms.add_intergraph_edge_type(iet)
    # Phase 05c — rehydrate intergraph_hyperedge_types vocabulary.
    for iht_dict in state.get("intergraph_hyperedge_types") or []:
        prop_types_raw = iht_dict.get("property_types") or {}
        try:
            prop_types = {
                k: PropertyType(v) for k, v in prop_types_raw.items()
            }
        except ValueError as e:
            raise RuntimeError(
                f"MetagraphSchema rehydration: unrecognised PropertyType "
                f"value in intergraph_hyperedge_type "
                f"{iht_dict.get('name')!r}: {e}"
            ) from e
        iht = IntergraphHyperEdgeType(
            name=iht_dict["name"],
            allowed_anchor_types=frozenset(
                iht_dict.get("allowed_anchor_types") or []
            ),
            allowed_member_types=frozenset(
                iht_dict.get("allowed_member_types") or []
            ),
            allowed_anchor_graphs=frozenset(
                iht_dict.get("allowed_anchor_graphs") or []
            ),
            allowed_member_graphs=frozenset(
                iht_dict.get("allowed_member_graphs") or []
            ),
            # Per P18-A default = True; rehydration uses the persisted
            # value when present, falls back to True otherwise.
            ordered=bool(iht_dict.get("ordered", True)),
            property_types=prop_types,
            description=iht_dict.get("description"),
        )
        ms.add_intergraph_hyperedge_type(iht)
    # Phase 05d — rehydrate meta_edge_types vocabulary.
    for met_dict in state.get("meta_edge_types") or []:
        prop_types_raw = met_dict.get("property_types") or {}
        try:
            prop_types = {
                k: PropertyType(v) for k, v in prop_types_raw.items()
            }
        except ValueError as e:
            raise RuntimeError(
                f"MetagraphSchema rehydration: unrecognised PropertyType "
                f"value in meta_edge_type {met_dict.get('name')!r}: {e}"
            ) from e
        met = MetaEdgeType(
            name=met_dict["name"],
            allowed_source_graphs=frozenset(
                met_dict.get("allowed_source_graphs") or []
            ),
            allowed_target_graphs=frozenset(
                met_dict.get("allowed_target_graphs") or []
            ),
            property_types=prop_types,
            description=met_dict.get("description"),
        )
        ms.add_meta_edge_type(met)
    # Phase 05d — rehydrate meta_hyperedge_types vocabulary.
    for mht_dict in state.get("meta_hyperedge_types") or []:
        prop_types_raw = mht_dict.get("property_types") or {}
        try:
            prop_types = {
                k: PropertyType(v) for k, v in prop_types_raw.items()
            }
        except ValueError as e:
            raise RuntimeError(
                f"MetagraphSchema rehydration: unrecognised PropertyType "
                f"value in meta_hyperedge_type "
                f"{mht_dict.get('name')!r}: {e}"
            ) from e
        mht = MetaHyperEdgeType(
            name=mht_dict["name"],
            allowed_member_graphs=frozenset(
                mht_dict.get("allowed_member_graphs") or []
            ),
            property_types=prop_types,
            description=mht_dict.get("description"),
        )
        ms.add_meta_hyperedge_type(mht)
    return ms


def _load_or_die(name: str) -> Metagraph:
    """Load + rehydrate a metagraph; die with structured exit on failure."""
    try:
        state = state_mod.load_metagraph_state(name)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=2)
    except FileNotFoundError:
        path = _path_or_unknown(name)
        typer.echo(
            f"Metagraph {name!r} not found at {path}; "
            f"create it first with 'mindsos metagraph create --name {name}'",
            err=True,
        )
        raise typer.Exit(code=1)
    except RuntimeError as e:
        typer.echo(f"State file error: {e}", err=True)
        raise typer.Exit(code=1)
    try:
        return _state_to_metagraph(state)
    except IdentityError as e:
        typer.echo(
            f"IdentityError on metagraph load (corrupted state?): {e}",
            err=True,
        )
        raise typer.Exit(code=1)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)


def _save_or_die(name: str, mg: Metagraph) -> None:
    """Save metagraph state; die with structured exit on failure."""
    try:
        state_mod.save_metagraph_state(name, _metagraph_to_state(mg))
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=2)


def _path_or_unknown(name: str) -> str:
    try:
        return str(state_mod.metagraph_file_path(name))
    except ValueError:
        return "<unknown>"


def _resolve_graph_id_or_die(mg: Metagraph, graph_name: str) -> str:
    """Translate a graph name (CLI input) to graph_id (API input)."""
    for g in mg.graphs.values():
        if g.name == graph_name:
            return g.graph_id
    typer.echo(
        f"IdentityError: Graph {graph_name!r} not in metagraph {mg.name!r}",
        err=True,
    )
    raise typer.Exit(code=1)


def _confirm_destructive_or_die(*, label: str, yes: bool) -> None:
    """P5 — require explicit ``--yes`` for destructive operations.

    When ``--yes`` is missing, refuse with exit 2 + actionable message.
    Phase 05a does not prompt interactively (single-tester debug surface;
    consistent with existing reset patterns that fail-loudly rather than
    interactive-prompt).
    """
    if yes:
        return
    typer.echo(
        f"refusing {label}: this operation is destructive. Re-run with "
        f"--yes to confirm.",
        err=True,
    )
    raise typer.Exit(code=2)


# ---------------------------------------------------------------------------
# create (CR-A)
# ---------------------------------------------------------------------------


@metagraph_app.command("create")
def create_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    metagraph_id: Optional[str] = typer.Option(
        None, "--metagraph-id",
        help="Optional explicit metagraph id (UUID or IRI passthrough).",
    ),
    prop: List[str] = typer.Option(
        [], "--prop",
        help="Repeat: k=v initial property bag entries (CR-A; ADR-0130).",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Create an empty metagraph and write the initial state file."""
    try:
        path = state_mod.metagraph_file_path(name)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=2)
    if path.exists():
        typer.echo(
            f"IdentityError: Metagraph {name!r} already exists at {path}; "
            f"use 'mindsos metagraph reset --name {name} --yes' to clear.",
            err=True,
        )
        raise typer.Exit(code=1)
    props = _parse_props(prop or [])
    try:
        mg = Metagraph(
            name=name, metagraph_id=metagraph_id, properties=props,
        )
    except PropertyShapeError as e:
        typer.echo(f"PropertyShapeError: {e}", err=True)
        raise typer.Exit(code=1)
    _save_or_die(name, mg)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "name": mg.name,
                    "metagraph_id": mg.metagraph_id,
                    "properties": dict(mg.properties),
                    "state_file": str(path),
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"created: name={mg.name} metagraph_id={mg.metagraph_id} "
            f"properties={dict(mg.properties)}"
        )
        typer.echo(f"state_file={path}")


# ---------------------------------------------------------------------------
# inspect (P10 shape)
# ---------------------------------------------------------------------------


@metagraph_app.command("inspect")
def inspect_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Report counts + properties + contained-graphs for the named metagraph.

    P10 JSON shape (extended in 05b + 05c per Pushback 18-A v=2 bump
    and P14-A smaller-items-fold v=3 bump):

        {
          "name": "<n>",
          "metagraph_id": "<uuid>",
          "properties": {...},
          "schema_name": "<name|null>",                # P05b
          "contained_graphs": [...sorted graph names],
          "counts": {
            "graphs": int,
            "metaedges": int,
            "metahyperedges": int,
            "intergraph_edges": int,                   # P05b
            "intergraph_hyperedges": int               # P05c
          },
          "_state_version": int,
          "state_file": "<path>"
        }
    """
    mg = _load_or_die(name)
    contained_graph_names = sorted(g.name for g in mg.graphs.values())
    summary = {
        "name": mg.name,
        "metagraph_id": mg.metagraph_id,
        "properties": dict(mg.properties),
        "schema_name": mg.schema_name,
        "contained_graphs": contained_graph_names,
        "counts": {
            "graphs": len(mg.graphs),
            "metaedges": len(mg.metaedges),
            "metahyperedges": len(mg.metahyperedges),
            "intergraph_edges": len(mg.intergraph_edges),
            "intergraph_hyperedges": len(mg.intergraph_hyperedges),
        },
        "_state_version": state_mod.METAGRAPH_STATE_VERSION,
        "state_file": str(state_mod.metagraph_file_path(name)),
    }
    if json_out:
        typer.echo(json.dumps(summary, indent=2))
    else:
        typer.echo(
            f"name={mg.name} metagraph_id={mg.metagraph_id}"
        )
        typer.echo(f"properties={dict(mg.properties)}")
        typer.echo(f"schema_name={mg.schema_name!r}")
        typer.echo(
            f"graphs={summary['counts']['graphs']} "
            f"metaedges={summary['counts']['metaedges']} "
            f"metahyperedges={summary['counts']['metahyperedges']} "
            f"intergraph_edges={summary['counts']['intergraph_edges']} "
            f"intergraph_hyperedges={summary['counts']['intergraph_hyperedges']}"
        )
        typer.echo(f"contained={contained_graph_names}")
        typer.echo(f"state_file={summary['state_file']}")


# ---------------------------------------------------------------------------
# list (P10 shape)
# ---------------------------------------------------------------------------


@metagraph_app.command("list")
def list_metagraphs_cmd(
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Enumerate every metagraph in $MINDSOS_STATE_DIR (sorted by name).

    Like ``mindsos graph list``, this command bypasses the strict version
    check (Pick P3 inherited) so future-version metagraph state files
    appear in the listing rather than getting hidden. Mutating commands
    (``inspect``, ``add-*``, etc.) DO use the strict loader.

    P10 JSON shape (extended in 05b + 05c per Pushback 18-A v=2 bump
    and P14-A smaller-items-fold v=3 bump):

        {
          "state_dir": "<path>",
          "metagraphs": [
            {
              "name": "<n>", "metagraph_id": "<uuid>",
              "schema_name": "<name|null>",          # P05b
              "contained_graphs_count": int,
              "metaedges_count": int,
              "metahyperedges_count": int,
              "intergraph_edges_count": int,         # P05b
              "intergraph_hyperedges_count": int,    # P05c
              "_state_version": int,
              "path": "<path>"
            }, ...
          ]
        }
    """
    entries: list[dict] = []
    for path in state_mod.iter_metagraph_files():
        try:
            raw = path.read_text(encoding="utf-8")
            state = json.loads(raw)
        except (OSError, json.JSONDecodeError) as e:
            entries.append(
                {"path": str(path), "error": f"unreadable: {e}"}
            )
            continue
        if not isinstance(state, dict):
            entries.append({"path": str(path), "error": "non-dict top-level"})
            continue
        entries.append(
            {
                "name": state.get("name"),
                "metagraph_id": state.get("metagraph_id"),
                "schema_name": state.get("schema_name"),
                "contained_graphs_count": len(state.get("contained_graphs") or []),
                "metaedges_count": len(state.get("metaedges") or []),
                "metahyperedges_count": len(state.get("metahyperedges") or []),
                "intergraph_edges_count": len(state.get("intergraph_edges") or []),
                "intergraph_hyperedges_count": len(
                    state.get("intergraph_hyperedges") or []
                ),
                "_state_version": state.get("_state_version"),
                "path": str(path),
            }
        )
    if json_out:
        typer.echo(
            json.dumps(
                {"state_dir": str(state_mod.state_dir()), "metagraphs": entries},
                indent=2,
            )
        )
    else:
        typer.echo(f"state_dir={state_mod.state_dir()}")
        if not entries:
            typer.echo("(no metagraphs)")
            return
        for e in entries:
            if "error" in e:
                typer.echo(f"  {e['path']}  ERROR: {e['error']}")
            else:
                typer.echo(
                    f"  name={e['name']!r}  metagraph_id={e['metagraph_id']}  "
                    f"v={e['_state_version']}  "
                    f"graphs={e['contained_graphs_count']} "
                    f"metaedges={e['metaedges_count']} "
                    f"metahyperedges={e['metahyperedges_count']}"
                )


# ---------------------------------------------------------------------------
# reset (Q6-A + P5)
# ---------------------------------------------------------------------------


@metagraph_app.command("reset")
def reset_cmd(
    name: Optional[str] = typer.Option(
        None, "--name", help="Metagraph name to reset.",
    ),
    all_: bool = typer.Option(
        False, "--all", help="Reset every metagraph in $MINDSOS_STATE_DIR.",
    ),
    force: bool = typer.Option(
        False, "--force",
        help="Q6-A: when --name set, strip the back-pointer from any "
             "graphs that reference this metagraph (warning emitted). "
             "Without --force, reset refuses if any graph references "
             "the target metagraph.",
    ),
    yes: bool = typer.Option(
        False, "--yes",
        help="P5: required for --force OR --all (destructive operations).",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Delete the named metagraph state file or every metagraph state file.

    Q6-A — when --name is set:
      - Walks every ``graph-*.json`` checking the ``metagraph_name``
        back-pointer.
      - If any graph references this metagraph: refuse (exit 1) UNLESS
        ``--force`` is passed; with ``--force --yes``, strip back-pointers
        from referenced graphs (warning emitted on stderr).

    P5 — ``--force`` and ``--all`` require ``--yes`` (no accidental wipes).
    """
    if name and all_:
        typer.echo(
            "--name and --all are mutually exclusive.", err=True
        )
        raise typer.Exit(code=2)
    if not name and not all_:
        typer.echo(
            "Specify either --name <NAME> or --all (no accidental wipes).",
            err=True,
        )
        raise typer.Exit(code=2)
    if all_:
        _confirm_destructive_or_die(label="reset --all", yes=yes)
    if force:
        _confirm_destructive_or_die(label="reset --force", yes=yes)

    deleted: list[str] = []
    stripped_back_pointers: list[str] = []

    if name:
        # Q6-A — orphan check.
        try:
            target_path = state_mod.metagraph_file_path(name)
        except ValueError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=2)
        if not target_path.exists():
            typer.echo(
                f"Metagraph {name!r} not found at {target_path}; "
                f"nothing to reset.",
                err=True,
            )
            raise typer.Exit(code=1)
        # Walk every graph-*.json; collect references.
        referencing_graphs: list[str] = []
        for graph_path in state_mod.iter_state_files():
            try:
                graph_raw = json.loads(
                    graph_path.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(graph_raw, dict):
                continue
            if graph_raw.get("metagraph_name") == name:
                referencing_graphs.append(graph_raw.get("name") or graph_path.stem)
        if referencing_graphs and not force:
            typer.echo(
                f"refusing reset: metagraph {name!r} is referenced by "
                f"{len(referencing_graphs)} graph(s): "
                f"{sorted(referencing_graphs)!r}. Use 'mindsos metagraph "
                f"remove-graph --name {name} --graph <G>' to clean each "
                f"reference, OR re-run with --force --yes to strip the "
                f"back-pointers (Q6-A).",
                err=True,
            )
            raise typer.Exit(code=1)
        if referencing_graphs and force:
            typer.echo(
                f"warning: --force stripping back-pointers from "
                f"{len(referencing_graphs)} graph(s): "
                f"{sorted(referencing_graphs)!r}. The graphs become "
                f"standalone (identity registries DO NOT split back; "
                f"if two graphs collided in this metagraph's unified "
                f"registry, the collision survives at the file level).",
                err=True,
            )
            for gname in referencing_graphs:
                try:
                    gstate = state_mod.load_graph_state(gname)
                    gstate["metagraph_name"] = None
                    gstate["_state_version"] = state_mod.GRAPH_STATE_VERSION
                    state_mod.save_graph_state(gname, gstate)
                    stripped_back_pointers.append(gname)
                except (FileNotFoundError, ValueError, RuntimeError) as e:
                    typer.echo(
                        f"warning: could not strip back-pointer from "
                        f"graph {gname!r}: {e}",
                        err=True,
                    )
        try:
            state_mod.delete_metagraph_state_file(name)
        except FileNotFoundError:
            pass
        deleted.append(name)
    else:
        # --all (already gated by --yes above).
        for path in list(state_mod.iter_metagraph_files()):
            mg_name = path.stem.removeprefix("metagraph-")
            # Strip back-pointers from any graph referencing this metagraph.
            for graph_path in state_mod.iter_state_files():
                try:
                    graph_raw = json.loads(
                        graph_path.read_text(encoding="utf-8")
                    )
                except (OSError, json.JSONDecodeError):
                    continue
                if not isinstance(graph_raw, dict):
                    continue
                if graph_raw.get("metagraph_name") == mg_name:
                    gname = graph_raw.get("name") or graph_path.stem
                    try:
                        graph_raw["metagraph_name"] = None
                        graph_raw["_state_version"] = state_mod.GRAPH_STATE_VERSION
                        state_mod.save_graph_state(gname, graph_raw)
                        stripped_back_pointers.append(gname)
                    except (ValueError, RuntimeError):
                        pass
            path.unlink()
            deleted.append(mg_name)

    if json_out:
        typer.echo(
            json.dumps(
                {
                    "deleted": sorted(deleted),
                    "count": len(deleted),
                    "stripped_back_pointers": sorted(stripped_back_pointers),
                },
                indent=2,
            )
        )
    else:
        for n in sorted(deleted):
            typer.echo(f"ok: deleted metagraph={n!r}")
        if stripped_back_pointers:
            typer.echo(
                f"stripped back-pointers from: {sorted(stripped_back_pointers)!r}"
            )
        typer.echo(f"count: {len(deleted)}")


# ---------------------------------------------------------------------------
# add-graph (Q5-A + N7-A + P18)
# ---------------------------------------------------------------------------


@metagraph_app.command("add-graph")
def add_graph_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    graph: str = typer.Option(..., "--graph", help="Graph name to add."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Add a graph to the metagraph (Q5-A + N7-A + P18).

    Two-file write order (P18): graph state file (back-pointer set)
    FIRST, then metagraph state file. On metagraph-save failure, the
    graph has a dangling back-pointer; recovery via 'mindsos graph
    detach-metagraph --name <graph>' (DM-A).

    N7-A — refuses with exit 1 if the graph already has a non-null
    ``metagraph_name`` back-pointer (graph is already metagraph-owned).
    Recovery: ``mindsos metagraph remove-graph`` from the prior owner
    first, OR ``mindsos graph detach-metagraph`` if the prior owner's
    state file is missing (DM-A).

    Q5-A — eager id-collision check delegated to ``Metagraph.add_graph``.
    The check walks every currently-contained graph's element ids; if
    the candidate graph carries an id that collides with the metagraph's
    unified registry, refusal is structured as ``IdentityError`` with
    the colliding id surfaced.

    P16 — post-call, ``g.identity is mg.identity`` (shared reference).
    ``g.id_strategy`` is left untouched.
    """
    # Load metagraph (must already exist).
    mg = _load_or_die(name)
    # Load candidate graph.
    g, g_schema_name, g_back_pointer = _graph_load_or_die(graph)
    # N7-A — refuse if graph already metagraph-owned.
    if g_back_pointer is not None:
        typer.echo(
            f"IdentityError: graph {graph!r} is already owned by metagraph "
            f"{g_back_pointer!r}. Run 'mindsos metagraph remove-graph "
            f"--name {g_back_pointer} --graph {graph}' first, OR "
            f"'mindsos graph detach-metagraph --name {graph}' if the "
            f"prior owner's state file is missing (DM-A).",
            err=True,
        )
        raise typer.Exit(code=1)
    # Add to metagraph (delegates Q5-A + ADR-0020 unification).
    try:
        mg.add_graph(g)
    except IdentityError as e:
        typer.echo(f"IdentityError: {e}", err=True)
        raise typer.Exit(code=1)
    # P18 — graph state file written FIRST (back-pointer set), then
    # metagraph state file. Recovery on metagraph-save failure: DM-A.
    try:
        from mindsos_cli.commands.graph import _save_or_die as _graph_save_or_die
        _graph_save_or_die(
            graph, g, schema_name=g_schema_name, metagraph_name=name,
        )
    except typer.Exit:
        # Graph save failed before any metagraph state changed; nothing
        # to roll back. Re-raise.
        raise
    except Exception as e:
        typer.echo(
            f"failed to write graph back-pointer for {graph!r}: {e}",
            err=True,
        )
        raise typer.Exit(code=1)
    # Now save metagraph (may fail; if so, graph has dangling back-pointer).
    try:
        _save_or_die(name, mg)
    except typer.Exit:
        typer.echo(
            f"warning: graph {graph!r} has back-pointer set but metagraph "
            f"save failed. Run 'mindsos graph detach-metagraph --name "
            f"{graph}' (DM-A) to recover.",
            err=True,
        )
        raise

    if json_out:
        typer.echo(
            json.dumps(
                {
                    "metagraph": name,
                    "graph": graph,
                    "graph_id": g.graph_id,
                    "metagraph_id": mg.metagraph_id,
                    "contained_graphs_count": len(mg.graphs),
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"ok: added graph={graph!r} (id={g.graph_id}) to "
            f"metagraph={name!r}; contained_graphs_count={len(mg.graphs)}"
        )


# ---------------------------------------------------------------------------
# remove-graph
# ---------------------------------------------------------------------------


@metagraph_app.command("remove-graph")
def remove_graph_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    graph: str = typer.Option(..., "--graph", help="Graph name to remove."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Remove a contained graph and clear its back-pointer.

    P19 — always cascades incident metaedges + metahyperedges (no
    --no-cascade flag in 05a; Phase 10 reintroduces with RemovalImpact).

    Two-file write: clears the graph's back-pointer (graph state file
    save) AND removes the graph + cascaded metaedges from the metagraph
    state file. Order: metagraph save first, then graph back-pointer
    clear. On graph-save failure, the metagraph thinks the graph is
    gone but the graph still has a back-pointer — recovery via DM-A.
    """
    mg = _load_or_die(name)
    graph_id = _resolve_graph_id_or_die(mg, graph)
    # Capture incident edge counts before removal for reporting.
    incident_meta = sum(
        1 for me in mg.metaedges.values()
        if me.source_graph_id == graph_id or me.target_graph_id == graph_id
    )
    incident_mhe = sum(
        1 for mhe in mg.metahyperedges.values()
        if graph_id in mhe.graph_ids
    )
    incident_ie = sum(
        1 for ie in mg.intergraph_edges.values()
        if ie.source_graph_id == graph_id or ie.target_graph_id == graph_id
    )
    incident_ihe = sum(
        1 for ihe in mg.intergraph_hyperedges.values()
        if any(gid == graph_id for (gid, _) in ihe.anchors)
        or any(gid == graph_id for (gid, _) in ihe.members)
    )
    # Remove from metagraph (cascades). Pushback 17-A (extended in 05c) —
    # atomic precheck raises CompositionalImmutableError BEFORE any
    # mutation if any incident intergraph_edge OR intergraph_hyperedge
    # has compositional=True. Catch both error classes for a clean
    # stderr + exit 1 (no traceback).
    try:
        mg.remove_graph(graph_id)
    except CompositionalImmutableError as e:
        typer.echo(f"CompositionalImmutableError: {e}", err=True)
        raise typer.Exit(code=1)
    except IdentityError as e:
        typer.echo(f"IdentityError: {e}", err=True)
        raise typer.Exit(code=1)

    # Clear back-pointer on the graph state file. Use raw load so a
    # rehydration failure doesn't block the recovery.
    try:
        gstate = state_mod.load_graph_state(graph)
        gstate["metagraph_name"] = None
        gstate["_state_version"] = state_mod.GRAPH_STATE_VERSION
        state_mod.save_graph_state(graph, gstate)
    except FileNotFoundError:
        # Graph state file gone — already standalone in effect; continue.
        typer.echo(
            f"warning: graph state file for {graph!r} is missing; "
            f"metagraph removal proceeded.",
            err=True,
        )
    except (ValueError, RuntimeError) as e:
        typer.echo(
            f"warning: failed to clear graph back-pointer for {graph!r}: {e}. "
            f"Run 'mindsos graph detach-metagraph --name {graph}' (DM-A) "
            f"to recover.",
            err=True,
        )

    # Save metagraph.
    _save_or_die(name, mg)

    if json_out:
        typer.echo(
            json.dumps(
                {
                    "metagraph": name,
                    "graph": graph,
                    "cascaded_metaedges": incident_meta,
                    "cascaded_metahyperedges": incident_mhe,
                    "cascaded_intergraph_edges": incident_ie,
                    "cascaded_intergraph_hyperedges": incident_ihe,
                    "contained_graphs_count": len(mg.graphs),
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"ok: removed graph={graph!r} from metagraph={name!r}; "
            f"cascaded {incident_meta} metaedge(s) + {incident_mhe} "
            f"metahyperedge(s) + {incident_ie} intergraph_edge(s) + "
            f"{incident_ihe} intergraph_hyperedge(s); "
            f"contained_graphs_count={len(mg.graphs)}"
        )


# ---------------------------------------------------------------------------
# add-metaedge (P11 + P15)
# ---------------------------------------------------------------------------


@metagraph_app.command("add-metaedge")
def add_metaedge_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    source_graph: str = typer.Option(
        ..., "--source-graph", help="Source graph name (must be contained).",
    ),
    target_graph: str = typer.Option(
        ..., "--target-graph", help="Target graph name (must differ from source).",
    ),
    type_name: str = typer.Option(
        ..., "--type",
        help="Cypher rel-type (must match ^[A-Z][A-Z0-9_]{0,63}$).",
    ),
    label: Optional[str] = typer.Option(None, "--label", help="Optional label."),
    prop: List[str] = typer.Option(
        [], "--prop", help="Repeat: k=v.",
    ),
    metaedge_id: Optional[str] = typer.Option(
        None, "--metaedge-id", help="Optional explicit edge id.",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Add a directed metaedge between two contained graphs.

    P15 — refuses self-loop (source == target).
    """
    mg = _load_or_die(name)
    src_id = _resolve_graph_id_or_die(mg, source_graph)
    tgt_id = _resolve_graph_id_or_die(mg, target_graph)
    props = _parse_props(prop or [])
    try:
        me = mg.add_metaedge(
            source_graph_id=src_id,
            target_graph_id=tgt_id,
            type_name=type_name,
            label=label,
            properties=props,
        )
        # Allow caller-supplied edge_id by overriding post-construction.
        if metaedge_id is not None and metaedge_id != me.edge_id:
            mg.identity.unregister(me.edge_id)
            del mg.metaedges[me.edge_id]
            try:
                mg.identity.register(metaedge_id)
            except IdentityError as e:
                # Re-register the auto-id to recover.
                mg.identity.register(me.edge_id)
                mg.metaedges[me.edge_id] = me
                raise IdentityError(str(e))
            me.edge_id = metaedge_id
            mg.metaedges[metaedge_id] = me
    except SchemaError as e:
        typer.echo(f"SchemaError: {e}", err=True)
        raise typer.Exit(code=1)
    except CypherError as e:
        typer.echo(f"CypherError: {e}", err=True)
        raise typer.Exit(code=1)
    except IdentityError as e:
        typer.echo(f"IdentityError: {e}", err=True)
        raise typer.Exit(code=1)
    except PropertyShapeError as e:
        typer.echo(f"PropertyShapeError: {e}", err=True)
        raise typer.Exit(code=1)
    except UnknownTypeError as e:
        # Phase 05d hotfix B-05d-T2: schema-attached path raises
        # UnknownTypeError on vocab gap or role-constraint violation;
        # mirror sibling 05b/05c add-* handlers' clean-exit pattern.
        typer.echo(f"UnknownTypeError: {e}", err=True)
        raise typer.Exit(code=1)
    _save_or_die(name, mg)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "edge_id": me.edge_id,
                    "source_graph": source_graph,
                    "target_graph": target_graph,
                    "type_name": me.type_name,
                    "label": me.label,
                    "properties": dict(me.properties),
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"ok: added metaedge id={me.edge_id} "
            f"{source_graph} -[{me.type_name}]-> {target_graph}"
        )


# ---------------------------------------------------------------------------
# remove-metaedge
# ---------------------------------------------------------------------------


@metagraph_app.command("remove-metaedge")
def remove_metaedge_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    metaedge_id: str = typer.Option(
        ..., "--metaedge-id", help="Metaedge id to remove.",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Remove a metaedge by id."""
    mg = _load_or_die(name)
    try:
        mg.remove_metaedge(metaedge_id)
    except IdentityError as e:
        typer.echo(f"IdentityError: {e}", err=True)
        raise typer.Exit(code=1)
    _save_or_die(name, mg)
    if json_out:
        typer.echo(
            json.dumps({"metaedge_id": metaedge_id, "removed": True}, indent=2)
        )
    else:
        typer.echo(f"ok: removed metaedge id={metaedge_id}")


# ---------------------------------------------------------------------------
# add-metahyperedge (P11 + P15)
# ---------------------------------------------------------------------------


@metagraph_app.command("add-metahyperedge")
def add_metahyperedge_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    type_name: str = typer.Option(
        ..., "--type",
        help="Cypher rel-type (must match ^[A-Z][A-Z0-9_]{0,63}$).",
    ),
    member: List[str] = typer.Option(
        [], "--member",
        help="Repeat: graph name (≥ 2 required per P15).",
    ),
    label: Optional[str] = typer.Option(None, "--label", help="Optional label."),
    prop: List[str] = typer.Option([], "--prop", help="Repeat: k=v."),
    metahyperedge_id: Optional[str] = typer.Option(
        None, "--metahyperedge-id", help="Optional explicit edge id.",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Add an n-ary metahyperedge across ≥ 2 contained graphs.

    P15 — refuses < 2 members.
    """
    mg = _load_or_die(name)
    member_ids = [_resolve_graph_id_or_die(mg, m) for m in (member or [])]
    props = _parse_props(prop or [])
    try:
        mhe = mg.add_metahyperedge(
            graph_ids=member_ids,
            type_name=type_name,
            label=label,
            properties=props,
        )
        if metahyperedge_id is not None and metahyperedge_id != mhe.edge_id:
            mg.identity.unregister(mhe.edge_id)
            del mg.metahyperedges[mhe.edge_id]
            try:
                mg.identity.register(metahyperedge_id)
            except IdentityError as e:
                mg.identity.register(mhe.edge_id)
                mg.metahyperedges[mhe.edge_id] = mhe
                raise IdentityError(str(e))
            mhe.edge_id = metahyperedge_id
            mg.metahyperedges[metahyperedge_id] = mhe
    except SchemaError as e:
        typer.echo(f"SchemaError: {e}", err=True)
        raise typer.Exit(code=1)
    except CypherError as e:
        typer.echo(f"CypherError: {e}", err=True)
        raise typer.Exit(code=1)
    except IdentityError as e:
        typer.echo(f"IdentityError: {e}", err=True)
        raise typer.Exit(code=1)
    except PropertyShapeError as e:
        typer.echo(f"PropertyShapeError: {e}", err=True)
        raise typer.Exit(code=1)
    except UnknownTypeError as e:
        # Phase 05d hotfix B-05d-T2: schema-attached path raises
        # UnknownTypeError on vocab gap or role-constraint violation.
        typer.echo(f"UnknownTypeError: {e}", err=True)
        raise typer.Exit(code=1)
    _save_or_die(name, mg)
    # Q3-A — sort by graph_name for byte-stable output.
    id_to_name = {g.graph_id: g.name for g in mg.graphs.values()}
    member_names_sorted = sorted(id_to_name[gid] for gid in mhe.graph_ids)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "edge_id": mhe.edge_id,
                    "type_name": mhe.type_name,
                    "member_graphs": member_names_sorted,
                    "label": mhe.label,
                    "properties": dict(mhe.properties),
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"ok: added metahyperedge id={mhe.edge_id} "
            f"type={mhe.type_name!r} members={member_names_sorted}"
        )


# ---------------------------------------------------------------------------
# remove-metahyperedge
# ---------------------------------------------------------------------------


@metagraph_app.command("remove-metahyperedge")
def remove_metahyperedge_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    metahyperedge_id: str = typer.Option(
        ..., "--metahyperedge-id", help="Metahyperedge id to remove.",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Remove a metahyperedge by id."""
    mg = _load_or_die(name)
    try:
        mg.remove_metahyperedge(metahyperedge_id)
    except IdentityError as e:
        typer.echo(f"IdentityError: {e}", err=True)
        raise typer.Exit(code=1)
    _save_or_die(name, mg)
    if json_out:
        typer.echo(
            json.dumps(
                {"metahyperedge_id": metahyperedge_id, "removed": True}, indent=2
            )
        )
    else:
        typer.echo(f"ok: removed metahyperedge id={metahyperedge_id}")


# ---------------------------------------------------------------------------
# set-prop (P17 — 3-way mutex; Phase 05b Pushback 27-A — extends to 4-way)
# ---------------------------------------------------------------------------


@metagraph_app.command("set-prop")
def set_prop_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    on_metagraph: bool = typer.Option(
        False, "--on-metagraph",
        help="P17: operate on the metagraph's own ADR-0130 property bag.",
    ),
    metaedge_id: Optional[str] = typer.Option(
        None, "--metaedge-id", help="Metaedge id to update.",
    ),
    metahyperedge_id: Optional[str] = typer.Option(
        None, "--metahyperedge-id", help="Metahyperedge id to update.",
    ),
    intergraph_edge_id: Optional[str] = typer.Option(
        None, "--intergraph-edge-id",
        help="P05b Pushback 27-A: IntergraphEdge id to update. "
             "Refuses if edge.compositional=True (design §4.3 + Pushback 6-A).",
    ),
    intergraph_hyperedge_id: Optional[str] = typer.Option(
        None, "--intergraph-hyperedge-id",
        help="P05c smaller-items fold: IntergraphHyperEdge id to update. "
             "Refuses if hyperedge.compositional=True (design §4.3 + "
             "P05b Pushback 6-A carry-forward).",
    ),
    prop: List[str] = typer.Option(
        [], "--prop", help="Repeat: k=v. Required.",
    ),
    replace: bool = typer.Option(
        False, "--replace",
        help="Swap the property bag entirely (preserves ref:* keys).",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Update a metaedge / metahyperedge / intergraph_edge / intergraph_hyperedge / metagraph property bag.

    Phase 05c — extends Pushback 27-A's 4-way mutex to 5-way (smaller-
    items fold). Exactly ONE of ``--on-metagraph`` / ``--metaedge-id`` /
    ``--metahyperedge-id`` / ``--intergraph-edge-id`` /
    ``--intergraph-hyperedge-id`` must be supplied. Compositional
    intergraph edges/hyperedges refuse with
    :class:`CompositionalImmutableError` (design §4.3 + Pushback 6-A —
    recovery via metagraph reset).

    --replace semantics: non-ref portion of existing bag dropped; ref:*
    keys preserved unless overridden by user-supplied values (Phase 04
    Pick D + N5 inherited).
    """
    n_set = sum(
        1 for x in (
            on_metagraph, metaedge_id, metahyperedge_id,
            intergraph_edge_id, intergraph_hyperedge_id,
        )
        if (x is True if isinstance(x, bool) else x is not None)
    )
    if n_set != 1:
        typer.echo(
            "Specify exactly one of --on-metagraph, --metaedge-id, "
            "--metahyperedge-id, --intergraph-edge-id, or "
            "--intergraph-hyperedge-id "
            "(Pushback 27-A extended to 5-way in P05c).",
            err=True,
        )
        raise typer.Exit(code=2)
    if not prop:
        typer.echo("set-prop requires at least one --prop k=v.", err=True)
        raise typer.Exit(code=2)
    user_props = _parse_props(prop)
    mg = _load_or_die(name)
    try:
        if on_metagraph:
            existing = dict(mg.properties)
            props_to_apply = (
                _build_replace_bag(existing, user_props) if replace else user_props
            )
            from mindsos_core import validate_user_properties
            new_props = validate_user_properties(
                props_to_apply, scope="metagraph"
            )
            if replace:
                mg.properties = dict(new_props)
            else:
                mg.properties = {**mg.properties, **new_props}
            kind = "metagraph"
            kind_id = mg.metagraph_id
            type_name = None
            applied_props = dict(mg.properties)
        elif metaedge_id is not None:
            existing = (
                mg.metaedges[metaedge_id].properties
                if metaedge_id in mg.metaedges else None
            )
            props_to_apply = (
                _build_replace_bag(existing, user_props) if replace else user_props
            )
            me = mg.update_metaedge_properties(
                metaedge_id, props_to_apply, replace=replace,
            )
            kind, kind_id, type_name = "metaedge", me.edge_id, me.type_name
            applied_props = dict(me.properties)
        elif metahyperedge_id is not None:
            existing = (
                mg.metahyperedges[metahyperedge_id].properties
                if metahyperedge_id in mg.metahyperedges else None
            )
            props_to_apply = (
                _build_replace_bag(existing, user_props) if replace else user_props
            )
            mhe = mg.update_metahyperedge_properties(
                metahyperedge_id, props_to_apply, replace=replace,
            )
            kind, kind_id, type_name = (
                "metahyperedge", mhe.edge_id, mhe.type_name
            )
            applied_props = dict(mhe.properties)
        elif intergraph_edge_id is not None:
            # Phase 05b — intergraph edge target.
            existing = (
                mg.intergraph_edges[intergraph_edge_id].properties
                if intergraph_edge_id in mg.intergraph_edges else None
            )
            props_to_apply = (
                _build_replace_bag(existing, user_props) if replace else user_props
            )
            ie = mg.update_intergraph_edge_properties(
                intergraph_edge_id, props_to_apply, replace=replace,
            )
            kind, kind_id, type_name = (
                "intergraph_edge", ie.edge_id, ie.type_name
            )
            applied_props = dict(ie.properties)
        else:
            # Phase 05c — intergraph hyperedge target. Routes through
            # ``update_intergraph_hyperedge`` with ``properties=...``
            # (anchors / members retained); ``replace_properties`` flag
            # mirrors the 4-way ``replace`` semantic.
            assert intergraph_hyperedge_id is not None  # mypy
            existing = (
                mg.intergraph_hyperedges[intergraph_hyperedge_id].properties
                if intergraph_hyperedge_id in mg.intergraph_hyperedges
                else None
            )
            props_to_apply = (
                _build_replace_bag(existing, user_props) if replace else user_props
            )
            ihe = mg.update_intergraph_hyperedge(
                intergraph_hyperedge_id,
                properties=props_to_apply,
                replace_properties=replace,
            )
            kind, kind_id, type_name = (
                "intergraph_hyperedge", ihe.edge_id, ihe.type_name
            )
            applied_props = dict(ihe.properties)
    except CompositionalImmutableError as e:
        typer.echo(f"CompositionalImmutableError: {e}", err=True)
        raise typer.Exit(code=1)
    except IdentityError as e:
        typer.echo(f"IdentityError: {e}", err=True)
        raise typer.Exit(code=1)
    except PropertyShapeError as e:
        typer.echo(f"PropertyShapeError: {e}", err=True)
        raise typer.Exit(code=1)
    _save_or_die(name, mg)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "kind": kind,
                    "id": kind_id,
                    "type_name": type_name,
                    "properties": applied_props,
                    "replace": replace,
                },
                indent=2,
            )
        )
    else:
        verb = "replaced" if replace else "merged"
        typer.echo(
            f"ok: {verb} {kind} id={kind_id} properties={applied_props}"
        )


def _build_replace_bag(
    existing: Optional[dict], user_props: dict
) -> dict:
    """Build the replacement bag: existing ``ref:*`` preserved, user wins on collision.

    Phase 04 — Pick D + N5 (inherited via mindsos_cli.commands.graph).
    """
    if not existing:
        return dict(user_props)
    existing_refs, _ = _split_existing_refs(existing)
    return {**existing_refs, **user_props}


# ---------------------------------------------------------------------------
# list-metaedges
# ---------------------------------------------------------------------------


@metagraph_app.command("list-metaedges")
def list_metaedges_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """List metaedges in the named metagraph (sorted by edge_id)."""
    mg = _load_or_die(name)
    id_to_name = {g.graph_id: g.name for g in mg.graphs.values()}
    metaedges = sorted(mg.metaedges.values(), key=lambda me: me.edge_id)
    if json_out:
        typer.echo(
            json.dumps(
                [
                    {
                        "edge_id": me.edge_id,
                        "source_graph": id_to_name[me.source_graph_id],
                        "target_graph": id_to_name[me.target_graph_id],
                        "type_name": me.type_name,
                        "label": me.label,
                        "properties": dict(me.properties),
                    }
                    for me in metaedges
                ],
                indent=2,
            )
        )
    else:
        for me in metaedges:
            typer.echo(
                f"{me.edge_id}  "
                f"{id_to_name[me.source_graph_id]} -[{me.type_name}]-> "
                f"{id_to_name[me.target_graph_id]}  label={me.label!r}"
            )


# ---------------------------------------------------------------------------
# list-metahyperedges
# ---------------------------------------------------------------------------


@metagraph_app.command("list-metahyperedges")
def list_metahyperedges_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """List metahyperedges in the named metagraph (sorted by edge_id)."""
    mg = _load_or_die(name)
    id_to_name = {g.graph_id: g.name for g in mg.graphs.values()}
    metahyperedges = sorted(
        mg.metahyperedges.values(), key=lambda mhe: mhe.edge_id
    )
    if json_out:
        typer.echo(
            json.dumps(
                [
                    {
                        "edge_id": mhe.edge_id,
                        "type_name": mhe.type_name,
                        "member_graphs": sorted(
                            id_to_name[gid] for gid in mhe.graph_ids
                        ),
                        "label": mhe.label,
                        "properties": dict(mhe.properties),
                    }
                    for mhe in metahyperedges
                ],
                indent=2,
            )
        )
    else:
        for mhe in metahyperedges:
            members = sorted(id_to_name[gid] for gid in mhe.graph_ids)
            typer.echo(
                f"{mhe.edge_id}  type={mhe.type_name!r} "
                f"members={members}  label={mhe.label!r}"
            )


# ---------------------------------------------------------------------------
# Compatibility for app.py
# ---------------------------------------------------------------------------


# ===========================================================================
# Phase 05b additions (ADR-0148 first draft) — 5 new subcommands.
# ===========================================================================


# ---------------------------------------------------------------------------
# add-intergraph-edge (Pushback 16-A 14-step + Pushback 22-A compositional)
# ---------------------------------------------------------------------------


@metagraph_app.command("add-intergraph-edge")
def add_intergraph_edge_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    source_graph: str = typer.Option(
        ..., "--source-graph",
        help="Source graph name (must be contained; != target-graph).",
    ),
    source_node: str = typer.Option(
        ..., "--source-node",
        help="Source node id (must exist in source graph).",
    ),
    target_graph: str = typer.Option(
        ..., "--target-graph",
        help="Target graph name (must be contained; != source-graph).",
    ),
    target_node: str = typer.Option(
        ..., "--target-node",
        help="Target node id (must exist in target graph).",
    ),
    type_name: str = typer.Option(
        ..., "--type",
        help="Cypher rel-type (must match ^[A-Z][A-Z0-9_]{0,63}$ per ADR-0021).",
    ),
    label: Optional[str] = typer.Option(
        None, "--label", help="Optional human-readable label.",
    ),
    prop: List[str] = typer.Option(
        [], "--prop", help="Repeat: k=v.",
    ),
    compositional: bool = typer.Option(
        False, "--compositional",
        help="Pushback 2-A: identity-bearing flag. Default False; "
             "immutable post-create (Pushback 22-A); refuses removal "
             "and property mutation (design §4.3 + Pushback 6-A).",
    ),
    intergraph_edge_id: Optional[str] = typer.Option(
        None, "--intergraph-edge-id",
        help="Optional explicit edge id (mints via mg.mint_id otherwise).",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Add a directed binary node↔node intergraph edge.

    Implements the Pushback 16-A 14-step validation order. Per the
    locked Pushback 1-C scope, the source/target graphs MUST differ
    (use ``mindsos graph add-edge`` for same-graph edges via the
    metagraph subapp's Q4-B mediation pattern).
    """
    mg = _load_or_die(name)
    src_id = _resolve_graph_id_or_die(mg, source_graph)
    tgt_id = _resolve_graph_id_or_die(mg, target_graph)
    props = _parse_props(prop or [])
    try:
        edge = mg.add_intergraph_edge(
            source_graph_id=src_id,
            source_node_id=source_node,
            target_graph_id=tgt_id,
            target_node_id=target_node,
            type_name=type_name,
            compositional=compositional,
            label=label,
            properties=props,
            edge_id=intergraph_edge_id,
        )
    except SchemaError as e:
        typer.echo(f"SchemaError: {e}", err=True)
        raise typer.Exit(code=1)
    except CypherError as e:
        typer.echo(f"CypherError: {e}", err=True)
        raise typer.Exit(code=1)
    except IdentityError as e:
        typer.echo(f"IdentityError: {e}", err=True)
        raise typer.Exit(code=1)
    except UnknownTypeError as e:
        typer.echo(f"UnknownTypeError: {e}", err=True)
        raise typer.Exit(code=1)
    except PropertyShapeError as e:
        typer.echo(f"PropertyShapeError: {e}", err=True)
        raise typer.Exit(code=1)
    _save_or_die(name, mg)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "edge_id": edge.edge_id,
                    "source_graph": source_graph,
                    "source_node": edge.source_node_id,
                    "target_graph": target_graph,
                    "target_node": edge.target_node_id,
                    "type_name": edge.type_name,
                    "compositional": edge.compositional,
                    "label": edge.label,
                    "properties": dict(edge.properties),
                },
                indent=2,
            )
        )
    else:
        marker = " compositional" if edge.compositional else ""
        typer.echo(
            f"ok: added intergraph_edge id={edge.edge_id}{marker} "
            f"{source_graph}.{edge.source_node_id} "
            f"-[{edge.type_name}]-> "
            f"{target_graph}.{edge.target_node_id}"
        )


# ---------------------------------------------------------------------------
# remove-intergraph-edge (refuses on compositional per Pushback 6-A)
# ---------------------------------------------------------------------------


@metagraph_app.command("remove-intergraph-edge")
def remove_intergraph_edge_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    intergraph_edge_id: str = typer.Option(
        ..., "--intergraph-edge-id",
        help="Intergraph edge id to remove. Refuses if compositional=True.",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Remove an intergraph edge by id; refuses on compositional."""
    mg = _load_or_die(name)
    try:
        mg.remove_intergraph_edge(intergraph_edge_id)
    except CompositionalImmutableError as e:
        typer.echo(f"CompositionalImmutableError: {e}", err=True)
        raise typer.Exit(code=1)
    except IdentityError as e:
        typer.echo(f"IdentityError: {e}", err=True)
        raise typer.Exit(code=1)
    _save_or_die(name, mg)
    if json_out:
        typer.echo(
            json.dumps(
                {"intergraph_edge_id": intergraph_edge_id, "removed": True},
                indent=2,
            )
        )
    else:
        typer.echo(f"ok: removed intergraph_edge id={intergraph_edge_id}")


# ---------------------------------------------------------------------------
# list-intergraph-edges
# ---------------------------------------------------------------------------


@metagraph_app.command("list-intergraph-edges")
def list_intergraph_edges_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """List every intergraph edge in the named metagraph (sorted by edge_id).

    JSON shape (Phase 05b):

        {
          "metagraph": "<name>",
          "intergraph_edges": [
            {"edge_id", "source_graph", "source_node",
             "target_graph", "target_node",
             "type_name", "compositional",
             "label", "properties"}, ...
          ]
        }
    """
    mg = _load_or_die(name)
    id_to_name = {g.graph_id: g.name for g in mg.graphs.values()}
    entries = sorted(mg.intergraph_edges.values(), key=lambda ie: ie.edge_id)
    payload = {
        "metagraph": mg.name,
        "intergraph_edges": [
            {
                "edge_id": ie.edge_id,
                "source_graph": id_to_name[ie.source_graph_id],
                "source_node": ie.source_node_id,
                "target_graph": id_to_name[ie.target_graph_id],
                "target_node": ie.target_node_id,
                "type_name": ie.type_name,
                "compositional": ie.compositional,
                "label": ie.label,
                "properties": dict(ie.properties),
            }
            for ie in entries
        ],
    }
    if json_out:
        typer.echo(json.dumps(payload, indent=2))
    else:
        typer.echo(f"metagraph={mg.name} count={len(entries)}")
        if not entries:
            typer.echo("(no intergraph edges)")
            return
        for ie in entries:
            marker = " compositional" if ie.compositional else ""
            typer.echo(
                f"  id={ie.edge_id}{marker} "
                f"{id_to_name[ie.source_graph_id]}.{ie.source_node_id} "
                f"-[{ie.type_name}]-> "
                f"{id_to_name[ie.target_graph_id]}.{ie.target_node_id} "
                f"label={ie.label!r}"
            )


# ---------------------------------------------------------------------------
# attach-schema (Pushbacks 7-A + 12-A + 19-B + 29-A + 32-A/D)
# ---------------------------------------------------------------------------


@metagraph_app.command("attach-schema")
def attach_schema_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    schema: str = typer.Option(
        ..., "--schema",
        help="MetagraphSchema basename to attach (must exist as a "
             "metagraph-schema-<name>.json state file).",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Attach a MetagraphSchema; eager-validate every existing intergraph_edge.

    Pushback 12-A: refuses if a *different* schema is already attached
    (tester runs ``detach-schema`` first). Re-attaching the same schema
    re-runs eager validation (Pushback 32-D — surfaces drift since
    previous attach per Pushback 23-A footgun).

    Pushback 7-A + 9-A + 29-A: eager validation walks every existing
    intergraph_edge against the schema's :class:`IntergraphEdgeType`
    vocabulary. First violation refuses; metagraph state file unchanged.
    Existing metaedges/metahyperedges are NOT validated in 05b
    (Pushback 9-A — vocab not yet in MetagraphSchema until 05c).

    Pushback 19-B: stderr warning if the schema references roles that
    no contained graph satisfies.

    JSON output (Pushback 30-A):

        {
          "metagraph": "<name>",
          "previous_schema": "<name|null>",
          "new_schema": "<name>",
          "validated_intergraph_edges": <count>
        }
    """
    mg = _load_or_die(name)
    # Load schema state file.
    try:
        ms_state = state_mod.load_metagraph_schema_state(schema)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=2)
    except FileNotFoundError:
        typer.echo(
            f"MetagraphSchema {schema!r} not found. Create with "
            f"'mindsos metagraph-schema create --name {schema}'.",
            err=True,
        )
        raise typer.Exit(code=1)
    except RuntimeError as e:
        typer.echo(f"State file error: {e}", err=True)
        raise typer.Exit(code=1)
    try:
        ms = _state_to_metagraph_schema(ms_state)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)

    # Pushback 19-B — stderr warning on role gaps (non-blocking).
    contained_roles = {g.role for g in mg.graphs.values() if g.role is not None}
    referenced_roles: set[str] = set()
    for iet in ms.intergraph_edge_types.values():
        referenced_roles.update(iet.allowed_source_graphs)
        referenced_roles.update(iet.allowed_target_graphs)
    unmet = referenced_roles - contained_roles
    if unmet:
        typer.echo(
            f"warning: schema {schema!r} references roles {sorted(unmet)!r} "
            f"not satisfied by any contained graph; intergraph edges of "
            f"types using these constraints will refuse until matching "
            f"graphs are added (Pushback 19-B).",
            err=True,
        )

    previous_schema = mg.schema_name
    try:
        mg.attach_schema(ms, schema_name=schema)
    except IdentityError as e:
        typer.echo(f"IdentityError: {e}", err=True)
        raise typer.Exit(code=1)
    except UnknownTypeError as e:
        typer.echo(f"UnknownTypeError: {e}", err=True)
        raise typer.Exit(code=1)
    except PropertyShapeError as e:
        typer.echo(f"PropertyShapeError: {e}", err=True)
        raise typer.Exit(code=1)

    _save_or_die(name, mg)

    validated_count = len(mg.intergraph_edges)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "metagraph": mg.name,
                    "previous_schema": previous_schema,
                    "new_schema": schema,
                    "validated_intergraph_edges": validated_count,
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"ok: attached schema={schema!r} to metagraph={mg.name!r} "
            f"(previous={previous_schema!r}; validated "
            f"{validated_count} intergraph_edge(s))"
        )


# ---------------------------------------------------------------------------
# detach-schema (DMS-A — Pushback 28-A unified command)
# ---------------------------------------------------------------------------


@metagraph_app.command("detach-schema")
def detach_schema_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Detach the currently-attached MetagraphSchema (DMS-A unified command).

    Per Pushback 28-A, this command operates in two modes via internal
    fallback:

    1. **Normal path**: rehydrate the metagraph through
       ``_state_to_metagraph`` (which carries the schema attachment if
       the schema state file is present + well-formed). On success, call
       ``mg.detach_schema()`` and persist; refuses with exit 1 if no
       schema attached.

    2. **Raw-JSON fallback (DMS-A)**: if rehydration fails because the
       referenced schema state file is missing OR malformed, operate on
       the metagraph state file directly: clear ``schema_name`` →
       ``None``, write atomically, bypass schema rehydration. Recovery
       for the Pushback 28-A stale-reference case.

    Note that if the schema state file is *missing* (FileNotFoundError),
    ``_state_to_metagraph`` already handles that gracefully — it sets
    ``mg.schema_name`` to the dangling reference and ``mg.schema = None``
    without raising. The normal path then detaches cleanly. Only the
    *malformed* schema case (or load errors) trips the raw-JSON fallback.
    """
    # Pre-flight: load the metagraph state file as raw JSON to check for
    # both the existence and the schema_name reference. We use this
    # parsed dict for both the normal path (via _state_to_metagraph)
    # and the raw-JSON fallback (direct mutation + re-write).
    try:
        raw_state = state_mod.load_metagraph_state(name)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=2)
    except FileNotFoundError:
        path = _path_or_unknown(name)
        typer.echo(
            f"Metagraph {name!r} not found at {path}.", err=True,
        )
        raise typer.Exit(code=1)
    except RuntimeError as e:
        typer.echo(f"State file error: {e}", err=True)
        raise typer.Exit(code=1)

    raw_schema_name = raw_state.get("schema_name")
    if raw_schema_name is None:
        typer.echo(
            f"IdentityError: metagraph {name!r} has no schema attached; "
            f"nothing to detach.",
            err=True,
        )
        raise typer.Exit(code=1)

    used_raw_fallback = False
    try:
        mg = _state_to_metagraph(raw_state)
    except RuntimeError as e:
        # Malformed schema state file or eager-validation drift on load.
        # DMS-A raw-JSON fallback: mutate the state dict in place,
        # clear schema_name, write atomically, bypass rehydration.
        typer.echo(
            f"warning: rehydration failed ({e}); falling back to raw-JSON "
            f"detach (DMS-A — Pushback 28-A).",
            err=True,
        )
        previous = raw_schema_name
        raw_state["schema_name"] = None
        # Ensure version bump on disk (idempotent on v=2; defensive).
        raw_state["_state_version"] = state_mod.METAGRAPH_STATE_VERSION
        try:
            state_mod.save_metagraph_state(name, raw_state)
        except ValueError as save_err:
            typer.echo(str(save_err), err=True)
            raise typer.Exit(code=2)
        used_raw_fallback = True
    else:
        # Normal path — rehydration succeeded; ``mg.schema_name`` matches
        # raw_schema_name (or could be None if _state_to_metagraph had a
        # FileNotFoundError that set the dangling ref — either way,
        # detach handles it).
        previous = mg.detach_schema()
        if previous is None:
            # Edge case: state file said schema_name was set but
            # _state_to_metagraph left mg.schema_name as None. Use
            # raw_schema_name as the canonical previous value.
            previous = raw_schema_name
            mg.schema_name = None  # idempotent
        _save_or_die(name, mg)

    if json_out:
        typer.echo(
            json.dumps(
                {
                    "metagraph": name,
                    "previous_schema": previous,
                    "detached": True,
                    "used_raw_fallback": used_raw_fallback,
                },
                indent=2,
            )
        )
    else:
        suffix = " (DMS-A raw-JSON fallback)" if used_raw_fallback else ""
        typer.echo(
            f"ok: detached schema={previous!r} from metagraph={name!r}{suffix}"
        )


# ===========================================================================
# Phase 05c additions (ADR-0148 amended for n-ary) — 4 new subcommands.
# ===========================================================================


def _pair_repeated_flags(
    graphs: List[str], nodes: List[str], side: str,
) -> List[tuple[str, str]]:
    """Pair ``--<side>-graph G`` / ``--<side>-node N`` flags by index (P4-A).

    Mismatched counts refuse with structured error. ``side`` is
    ``"anchor"`` or ``"member"`` for error-text disambiguation.
    """
    if len(graphs) != len(nodes):
        typer.echo(
            f"P4-A paired-flags mismatch: got {len(graphs)} "
            f"--{side}-graph flag(s) and {len(nodes)} --{side}-node "
            f"flag(s); each --{side}-graph must pair with one "
            f"--{side}-node by index.",
            err=True,
        )
        raise typer.Exit(code=2)
    return [(g, n) for g, n in zip(graphs, nodes)]


# ---------------------------------------------------------------------------
# add-intergraph-hyperedge (P14-A 16-step + P4-A paired flags + P8-A refusal)
# ---------------------------------------------------------------------------


@metagraph_app.command("add-intergraph-hyperedge")
def add_intergraph_hyperedge_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    anchor_graph: List[str] = typer.Option(
        [], "--anchor-graph",
        help="Repeat: anchor graph name. Pairs by index with "
             "--anchor-node (P4-A). Must be a contained graph.",
    ),
    anchor_node: List[str] = typer.Option(
        [], "--anchor-node",
        help="Repeat: anchor node id. Paired by index with "
             "--anchor-graph (P4-A).",
    ),
    member_graph: List[str] = typer.Option(
        [], "--member-graph",
        help="Repeat: member graph name. Pairs by index with "
             "--member-node (P4-A).",
    ),
    member_node: List[str] = typer.Option(
        [], "--member-node",
        help="Repeat: member node id. Paired by index with "
             "--member-graph (P4-A).",
    ),
    type_name: str = typer.Option(
        ..., "--type",
        help="Cypher rel-type (must match ^[A-Z][A-Z0-9_]{0,63}$ per ADR-0021).",
    ),
    label: Optional[str] = typer.Option(
        None, "--label", help="Optional human-readable label.",
    ),
    prop: List[str] = typer.Option(
        [], "--prop", help="Repeat: k=v.",
    ),
    compositional: bool = typer.Option(
        False, "--compositional",
        help="P05b Pushback 2-A precedent: identity-bearing flag. "
             "Default False; immutable post-create (P2-refined). "
             "Refused alongside ordered=False types at validation step "
             "10 (P8-A).",
    ),
    intergraph_hyperedge_id: Optional[str] = typer.Option(
        None, "--intergraph-hyperedge-id",
        help="Optional explicit edge id (mints via mg.mint_id otherwise).",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Add an n-ary intergraph hyperedge (P14-A 16-step validation order).

    Per Phase 05c P4-A, ``--anchor-graph`` / ``--anchor-node`` flags
    repeat and pair by index. Symmetric for ``--member-*``. Mismatched
    counts refuse with exit 2 BEFORE any mutation. Graph names are
    translated to graph_ids at this CLI boundary; the factory does the
    rest (canonicalization per ``type.ordered``, cardinality on canonical,
    overlap, P8-A refusal, schema validation when attached).
    """
    mg = _load_or_die(name)
    # P4-A — pair the repeated flags BEFORE name-resolution so the
    # mismatch error fires before we touch the metagraph.
    raw_anchors = _pair_repeated_flags(
        anchor_graph or [], anchor_node or [], side="anchor"
    )
    raw_members = _pair_repeated_flags(
        member_graph or [], member_node or [], side="member"
    )
    # Resolve graph_name → graph_id (factory takes graph_id strings).
    anchors = [
        (_resolve_graph_id_or_die(mg, g), n) for (g, n) in raw_anchors
    ]
    members = [
        (_resolve_graph_id_or_die(mg, g), n) for (g, n) in raw_members
    ]
    props = _parse_props(prop or [])
    try:
        ihe = mg.add_intergraph_hyperedge(
            anchors=anchors,
            members=members,
            type_name=type_name,
            compositional=compositional,
            label=label,
            properties=props,
            intergraph_hyperedge_id=intergraph_hyperedge_id,
        )
    except SchemaError as e:
        typer.echo(f"SchemaError: {e}", err=True)
        raise typer.Exit(code=1)
    except CypherError as e:
        typer.echo(f"CypherError: {e}", err=True)
        raise typer.Exit(code=1)
    except IdentityError as e:
        typer.echo(f"IdentityError: {e}", err=True)
        raise typer.Exit(code=1)
    except UnknownTypeError as e:
        typer.echo(f"UnknownTypeError: {e}", err=True)
        raise typer.Exit(code=1)
    except PropertyShapeError as e:
        typer.echo(f"PropertyShapeError: {e}", err=True)
        raise typer.Exit(code=1)
    _save_or_die(name, mg)
    # Translate id→name for output.
    id_to_name = {g.graph_id: g.name for g in mg.graphs.values()}
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "intergraph_hyperedge_id": ihe.edge_id,
                    "anchors": [
                        [id_to_name[gid], nid] for (gid, nid) in ihe.anchors
                    ],
                    "members": [
                        [id_to_name[gid], nid] for (gid, nid) in ihe.members
                    ],
                    "type_name": ihe.type_name,
                    "compositional": ihe.compositional,
                    "label": ihe.label,
                    "properties": dict(ihe.properties),
                },
                indent=2,
            )
        )
    else:
        marker = " compositional" if ihe.compositional else ""
        a_render = ", ".join(
            f"{id_to_name[gid]}.{nid}" for (gid, nid) in ihe.anchors
        )
        m_render = ", ".join(
            f"{id_to_name[gid]}.{nid}" for (gid, nid) in ihe.members
        )
        typer.echo(
            f"ok: added intergraph_hyperedge id={ihe.edge_id}{marker} "
            f"anchors=[{a_render}] -[{ihe.type_name}]-> "
            f"members=[{m_render}]"
        )


# ---------------------------------------------------------------------------
# remove-intergraph-hyperedge (refuses on compositional per P05b Pushback 6-A)
# ---------------------------------------------------------------------------


@metagraph_app.command("remove-intergraph-hyperedge")
def remove_intergraph_hyperedge_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    intergraph_hyperedge_id: str = typer.Option(
        ..., "--intergraph-hyperedge-id",
        help="Intergraph hyperedge id. Refuses if compositional=True "
             "(design §4.3).",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Remove an intergraph hyperedge by id; refuses on compositional."""
    mg = _load_or_die(name)
    try:
        mg.remove_intergraph_hyperedge(intergraph_hyperedge_id)
    except CompositionalImmutableError as e:
        typer.echo(f"CompositionalImmutableError: {e}", err=True)
        raise typer.Exit(code=1)
    except IdentityError as e:
        typer.echo(f"IdentityError: {e}", err=True)
        raise typer.Exit(code=1)
    _save_or_die(name, mg)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "intergraph_hyperedge_id": intergraph_hyperedge_id,
                    "removed": True,
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"ok: removed intergraph_hyperedge id={intergraph_hyperedge_id}"
        )


# ---------------------------------------------------------------------------
# update-intergraph-hyperedge (P10-C replace-only structural + P19-A refusal)
# ---------------------------------------------------------------------------


@metagraph_app.command("update-intergraph-hyperedge")
def update_intergraph_hyperedge_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    intergraph_hyperedge_id: str = typer.Option(
        ..., "--intergraph-hyperedge-id",
        help="Hyperedge id to update. Refuses if compositional=True.",
    ),
    anchor_graph: List[str] = typer.Option(
        [], "--anchor-graph",
        help="Repeat: replacement anchor graph name. Pairs by index "
             "with --anchor-node (P4-A). Omit ALL anchor flags to "
             "retain current anchors.",
    ),
    anchor_node: List[str] = typer.Option(
        [], "--anchor-node",
        help="Repeat: replacement anchor node id. Pairs with "
             "--anchor-graph by index.",
    ),
    member_graph: List[str] = typer.Option(
        [], "--member-graph",
        help="Repeat: replacement member graph name. Omit ALL member "
             "flags to retain current members.",
    ),
    member_node: List[str] = typer.Option(
        [], "--member-node",
        help="Repeat: replacement member node id.",
    ),
    prop: List[str] = typer.Option(
        [], "--prop",
        help="Repeat: k=v. With --replace-properties, replaces entire "
             "bag; otherwise merges with existing.",
    ),
    replace_properties: bool = typer.Option(
        False, "--replace-properties",
        help="P10-C: when set, replace the properties bag entirely "
             "(preserves ref:* keys per Phase 04 Pick D pattern). "
             "Without the flag, properties merge with existing.",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Replace anchors / members / properties on an intergraph hyperedge (P10-C).

    Per P10-C, this is a single combined verb covering structural and
    property replacement. Anchors and members are ALWAYS replace-only
    (anchors=None retains current iff zero --anchor-* flags are given;
    same for members). Properties merge by default; ``--replace-properties``
    swaps entirely (preserving ref:*).

    Per P19-A, refusal of updates that would collapse to 1-to-1
    cardinality fires from the model layer at validation step 8 with
    structured error pointing to the remove-and-add workaround (loses
    edge_id stability across the type boundary).

    Per P20-A, update under detached schema validates structurally only
    (cardinality, overlap, regex; NO schema/role/property-type check).
    """
    mg = _load_or_die(name)
    # Resolve raw paired-flags. If both lists are empty, the field is
    # "retain current" (passed as None to the factory).
    if not anchor_graph and not anchor_node:
        anchors_arg: Optional[List[tuple[str, str]]] = None
    else:
        raw_anchors = _pair_repeated_flags(
            anchor_graph or [], anchor_node or [], side="anchor"
        )
        anchors_arg = [
            (_resolve_graph_id_or_die(mg, g), n) for (g, n) in raw_anchors
        ]
    if not member_graph and not member_node:
        members_arg: Optional[List[tuple[str, str]]] = None
    else:
        raw_members = _pair_repeated_flags(
            member_graph or [], member_node or [], side="member"
        )
        members_arg = [
            (_resolve_graph_id_or_die(mg, g), n) for (g, n) in raw_members
        ]
    if not prop:
        props_arg: Optional[dict] = None
    else:
        props_arg = _parse_props(prop)
    try:
        ihe = mg.update_intergraph_hyperedge(
            intergraph_hyperedge_id,
            anchors=anchors_arg,
            members=members_arg,
            properties=props_arg,
            replace_properties=replace_properties,
        )
    except CompositionalImmutableError as e:
        typer.echo(f"CompositionalImmutableError: {e}", err=True)
        raise typer.Exit(code=1)
    except SchemaError as e:
        typer.echo(f"SchemaError: {e}", err=True)
        raise typer.Exit(code=1)
    except CypherError as e:
        typer.echo(f"CypherError: {e}", err=True)
        raise typer.Exit(code=1)
    except IdentityError as e:
        typer.echo(f"IdentityError: {e}", err=True)
        raise typer.Exit(code=1)
    except UnknownTypeError as e:
        typer.echo(f"UnknownTypeError: {e}", err=True)
        raise typer.Exit(code=1)
    except PropertyShapeError as e:
        typer.echo(f"PropertyShapeError: {e}", err=True)
        raise typer.Exit(code=1)
    _save_or_die(name, mg)
    id_to_name = {g.graph_id: g.name for g in mg.graphs.values()}
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "intergraph_hyperedge_id": ihe.edge_id,
                    "anchors": [
                        [id_to_name[gid], nid] for (gid, nid) in ihe.anchors
                    ],
                    "members": [
                        [id_to_name[gid], nid] for (gid, nid) in ihe.members
                    ],
                    "type_name": ihe.type_name,
                    "compositional": ihe.compositional,
                    "label": ihe.label,
                    "properties": dict(ihe.properties),
                    "replaced_anchors": anchors_arg is not None,
                    "replaced_members": members_arg is not None,
                    "replaced_properties": replace_properties,
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"ok: updated intergraph_hyperedge id={ihe.edge_id} "
            f"(anchors={'replaced' if anchors_arg is not None else 'retained'}, "
            f"members={'replaced' if members_arg is not None else 'retained'}, "
            f"properties={'replaced' if replace_properties else 'merged'})"
        )


# ---------------------------------------------------------------------------
# list-intergraph-hyperedges
# ---------------------------------------------------------------------------


@metagraph_app.command("list-intergraph-hyperedges")
def list_intergraph_hyperedges_cmd(
    name: str = typer.Option(..., "--name", help="Metagraph name."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """List every intergraph hyperedge (sorted by edge_id).

    JSON shape (Phase 05c):

        {
          "metagraph": "<name>",
          "intergraph_hyperedges": [
            {"intergraph_hyperedge_id",
             "anchors": [[gname, node_id], ...],
             "members": [[gname, node_id], ...],
             "type_name", "compositional",
             "label", "properties"}, ...
          ]
        }
    """
    mg = _load_or_die(name)
    id_to_name = {g.graph_id: g.name for g in mg.graphs.values()}
    entries = sorted(
        mg.intergraph_hyperedges.values(), key=lambda ihe: ihe.edge_id,
    )
    payload = {
        "metagraph": mg.name,
        "intergraph_hyperedges": [
            {
                "intergraph_hyperedge_id": ihe.edge_id,
                "anchors": [
                    [id_to_name[gid], nid] for (gid, nid) in ihe.anchors
                ],
                "members": [
                    [id_to_name[gid], nid] for (gid, nid) in ihe.members
                ],
                "type_name": ihe.type_name,
                "compositional": ihe.compositional,
                "label": ihe.label,
                "properties": dict(ihe.properties),
            }
            for ihe in entries
        ],
    }
    if json_out:
        typer.echo(json.dumps(payload, indent=2))
    else:
        typer.echo(f"metagraph={mg.name} count={len(entries)}")
        if not entries:
            typer.echo("(no intergraph hyperedges)")
            return
        for ihe in entries:
            marker = " compositional" if ihe.compositional else ""
            a_render = ", ".join(
                f"{id_to_name[gid]}.{nid}" for (gid, nid) in ihe.anchors
            )
            m_render = ", ".join(
                f"{id_to_name[gid]}.{nid}" for (gid, nid) in ihe.members
            )
            typer.echo(
                f"  id={ihe.edge_id}{marker} "
                f"anchors=[{a_render}] -[{ihe.type_name}]-> "
                f"members=[{m_render}] label={ihe.label!r}"
            )


def register_metagraph_app(parent: typer.Typer) -> None:
    """Wire the metagraph sub-app onto a parent Typer app."""
    parent.add_typer(metagraph_app, name="metagraph")
