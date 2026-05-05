"""`mindsos graph` — Phase 04 L1 Graph elements + Schema integration CLI surface.

Subcommands (Phase 03 set + Phase 04 additions):

  mindsos graph create --name <NAME> [--role ROLE] [--schema NAME] [--json]
  mindsos graph inspect --name <NAME> [--json]
  mindsos graph add-node <VALUE> --name <NAME> --type <TYPE>
                         [--prop k=v]... [--node-id IRI] [--json]
  mindsos graph add-edge --name <NAME> --source <ID> --target <ID>
                         --type <REL_TYPE> [--label LABEL]
                         [--prop k=v]... [--edge-id ID] [--json]
  mindsos graph add-hyperedge --name <NAME> --member <ID> [--member <ID>]...
                              [--label LABEL] [--prop k=v]...
                              [--hyperedge-id ID] [--json]
  mindsos graph list-nodes --name <NAME> [--json]
  mindsos graph list-edges --name <NAME> [--json]
  mindsos graph list-hyperedges --name <NAME> [--json]
  mindsos graph list [--json]
  mindsos graph reset (--name <NAME> | --all) [--json]

Phase 04 additions:

  mindsos graph attach-schema --name <NAME> --schema <SCHEMA_NAME> [--json]
      Attach a previously-declared schema to an existing graph. Eager
      validation: every existing node + edge re-validated against the
      schema; first violation prints a structured error including the
      offending element id, then exits 1; the graph state file is NOT
      modified. Re-attach is permitted (replaces the previous schema);
      JSON output reports ``previous_schema``. If the new schema is
      strict AND has zero NodeTypes, a stderr warning is emitted (the
      graph cannot accept any further node adds).

  mindsos graph detach-schema --name <NAME> [--json]
      Clear ``schema_name`` from the graph's state file. Operates on
      the raw JSON dict (does NOT route through schema rehydration), so
      it works even when the referenced schema state file is missing —
      that's the primary recovery path for dangling-reference graphs.
      Exits 1 if no schema is currently attached.

  mindsos graph set-prop --name <NAME> (--node-id <ID> | --edge-id <ID>)
                          --prop k=v [--prop k2=v2 ...] [--replace] [--json]
      Schema-validated property update. Default merge; ``--replace``
      swaps the bag entirely BUT preserves cross-graph reference
      properties (``ref:*`` keys); user-supplied ``ref:*`` values
      overwrite existing ones on collision. There is no CLI path to
      DROP a ``ref:*`` key in Phase 04; recovery via hand-edit, or
      future Phase 09 XRef migration ships proper ref management.

Cross-invocation persistence: JSON state file at
``${MINDSOS_STATE_DIR or ~/.mindsos}/graph-<name>.json``. Phase 04 BUMPS
the on-disk version to v=2 (Phase 03 wrote v=1). Phase 04 binary accepts
both v=1 (legacy, no ``schema_name`` field) and v=2; writes v=2 on every
save. v=1 → v=2 migration is one-way: first Phase 04 mutation upgrades
the file; Phase 03 binary then refuses with the strict-version contract.

Phase 04 backward-compat for legacy v=1 graphs that contain
reserved-key or non-primitive properties (Phase 03 had no
``validate_user_properties`` enforcement): rehydration calls
``Graph.add_*`` with ``_validate=False`` so loads tolerate the legacy
data. Mutations (``set-prop``, fresh ``add-node``, ``attach-schema``
replay) keep the default ``_validate=True`` and continue to enforce
the user-property contract — recovery from poisoned legacy nodes is
via ``set-prop --replace``, which strips reserved keys.

Exit codes (PHASE_MAP Phase 03 row appendix #19; Phase 04 inherits +
extends):
  1 — domain errors (IdentityError, SchemaError, CypherError,
      UnknownTypeError, PropertyShapeError, malformed/missing state
      file, detach-schema on a graph with no schema, attach-schema
      with already-attached schema rejected by re-validation).
  2 — usage errors (missing required arg, malformed flag, empty
      ``--prop`` key, ``--node-id`` + ``--edge-id`` both passed,
      set-prop without either flag, reset without ``--name`` |
      ``--all``, invalid ``<name>`` regex).
"""

from __future__ import annotations

import json
from typing import Any, Optional

import typer

from mindsos_core import (
    CypherError,
    Graph,
    IdentityError,
    Node,
    PropertyShapeError,
    REF_PROPERTY_PREFIX,
    Schema,
    SchemaError,
    UnknownTypeError,
)
from mindsos_cli import state as state_mod
from mindsos_cli.commands.schema import _state_to_schema as _schema_state_to_schema


graph_app = typer.Typer(
    name="graph",
    help="L1 Graph elements + Phase 04 schema integration.",
    no_args_is_help=True,
    add_completion=False,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _parse_value(raw: str) -> Any:
    """Try ``json.loads(raw)``; on failure, treat as literal string."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _parse_props(props: list[str]) -> dict[str, Any]:
    """Parse repeated ``--prop k=v`` flags. Splits on first ``=`` only.

    Raises ``typer.Exit(2)`` on empty key (e.g. ``=value``).
    """
    out: dict[str, Any] = {}
    for arg in props:
        if "=" not in arg:
            typer.echo(
                f"--prop expects 'k=v' form, got {arg!r}", err=True
            )
            raise typer.Exit(code=2)
        key, _, val = arg.partition("=")
        if not key:
            typer.echo(
                f"--prop key is empty in {arg!r}", err=True
            )
            raise typer.Exit(code=2)
        out[key] = _parse_value(val)
    return out


def _load_schema_or_die(schema_name: str) -> Schema:
    """Load and rehydrate a referenced schema; structured exit on failure."""
    try:
        state = state_mod.load_schema_state(schema_name)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=2)
    except FileNotFoundError:
        path = _schema_path_or_unknown(schema_name)
        typer.echo(
            f"Schema {schema_name!r} not found at {path}; "
            f"create it first with 'mindsos schema create --name {schema_name}'",
            err=True,
        )
        raise typer.Exit(code=1)
    except RuntimeError as e:
        typer.echo(f"State file error: {e}", err=True)
        raise typer.Exit(code=1)
    return _schema_state_to_schema(state)


def _schema_path_or_unknown(name: str) -> str:
    try:
        return str(state_mod.schema_file_path(name))
    except ValueError:
        return "<unknown>"


def _graph_to_state(
    g: Graph,
    *,
    schema_name: Optional[str],
    metagraph_name: Optional[str] = None,
) -> dict:
    """Serialize a ``Graph`` to the v=4 state-file dict (Phase 05a).

    Phase 05a always writes v=4 (``GRAPH_STATE_VERSION``). Adds the
    ``metagraph_name`` back-pointer field (B2 lock); ``None`` for
    standalone graphs, set when the graph is owned by a metagraph.
    Sorts top-level lists by id for byte-stable output.
    """
    nodes = sorted(g.nodes.values(), key=lambda n: n.node_id)
    edges = sorted(g.edges.values(), key=lambda e: e.edge_id)
    hyperedges = sorted(g.hyperedges.values(), key=lambda h: h.edge_id)
    return {
        "_state_version": state_mod.GRAPH_STATE_VERSION,
        "graph_id": g.graph_id,
        "name": g.name,
        "role": g.role,
        "schema_name": schema_name,
        "metagraph_name": metagraph_name,
        "nodes": [
            {
                "node_id": n.node_id,
                "value": n.value,
                "type_name": n.type_name,
                "properties": dict(n.properties),
            }
            for n in nodes
        ],
        "edges": [
            {
                "edge_id": e.edge_id,
                "source_id": e.source.node_id,
                "target_id": e.target.node_id,
                "type_name": e.type_name,
                "label": e.label,
                "properties": dict(e.properties),
            }
            for e in edges
        ],
        "hyperedges": [
            {
                "edge_id": h.edge_id,
                "type_name": h.type_name,  # Phase 04-v2 — required field.
                "member_ids": sorted(n.node_id for n in h.nodes),
                "label": h.label,
                "properties": dict(h.properties),
            }
            for h in hyperedges
        ],
    }


def _state_to_graph(state: dict) -> tuple[Graph, Optional[str], Optional[str]]:
    """Rehydrate a ``Graph`` from a state-file dict (Phase 05a — v=4 current).

    Returns a ``(graph, schema_name_or_None, metagraph_name_or_None)``
    tuple. The caller is responsible for preserving both back-pointers
    round-trip on subsequent saves. Phase 05a ALWAYS writes v=4 on save;
    pre-v=4 files are forward-migrated by ``mindsos_cli.migrations.graph``
    before reaching this rehydrator (one-way migration).

    If the state file references a schema, the schema is loaded from
    its own state file and attached via ``Graph(..., schema=...)``.
    Schema-level checks (type registration, strict PropertyType maps)
    DO run on rehydration; user-property checks
    (``validate_user_properties`` — reserved keys, primitives only)
    are SKIPPED via ``_validate=False`` so legacy v=1 files with
    reserved-key or non-primitive properties (Phase 03 didn't validate)
    load cleanly. Mutations on those legacy properties surface the
    violation; recovery via ``set-prop --replace``.

    Uses public ``Graph.add_*`` methods with explicit ids (not the
    private ``_restore_*`` helpers, which are deferred to Phase 08).
    """
    schema_name = state.get("schema_name")
    metagraph_name = state.get("metagraph_name")
    schema: Optional[Schema] = None
    if schema_name is not None:
        schema = _load_schema_or_die(schema_name)
    g = Graph(
        name=state["name"],
        role=state.get("role"),
        graph_id=state["graph_id"],
        schema=schema,
    )
    # __init__ does NOT auto-register because graph_id was passed; register here.
    g.identity.register(state["graph_id"])
    for n in state.get("nodes", []):
        g.add_node(
            value=n["value"],
            type_name=n["type_name"],
            properties=dict(n.get("properties") or {}),
            node_id=n["node_id"],
            _validate=False,  # rehydration: tolerate legacy v=1 garbage
        )
    for e in state.get("edges", []):
        src = g.nodes[e["source_id"]]
        tgt = g.nodes[e["target_id"]]
        g.add_edge(
            source=src,
            target=tgt,
            type_name=e["type_name"],
            label=e.get("label"),
            properties=dict(e.get("properties") or {}),
            edge_id=e["edge_id"],
            _validate=False,
        )
    for h in state.get("hyperedges", []):
        members = [g.nodes[mid] for mid in h["member_ids"]]
        # Phase 04-v2 — populate SENT-1 sentinel for legacy v=1/v=2
        # hyperedges that pre-date the type_name field.
        type_name = h.get("type_name") or "UNSPECIFIED"
        g.add_hyperedge(
            nodes=members,
            type_name=type_name,
            label=h.get("label"),
            properties=dict(h.get("properties") or {}),
            edge_id=h["edge_id"],
            _validate=False,
        )
    return g, schema_name, metagraph_name


def _load_or_die(name: str) -> tuple[Graph, Optional[str], Optional[str]]:
    """Load and rehydrate a graph; die with structured exit on failure.

    Returns ``(graph, schema_name, metagraph_name)``. The caller must
    preserve both back-pointers round-trip on subsequent saves.
    """
    try:
        state = state_mod.load_graph_state(name)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=2)
    except FileNotFoundError:
        path = _path_or_unknown(name)
        typer.echo(
            f"Graph {name!r} not found at {path}; "
            f"create it first with 'mindsos graph create --name {name}'",
            err=True,
        )
        raise typer.Exit(code=1)
    except RuntimeError as e:
        typer.echo(f"State file error: {e}", err=True)
        raise typer.Exit(code=1)
    return _state_to_graph(state)


def _save_or_die(
    name: str,
    g: Graph,
    *,
    schema_name: Optional[str],
    metagraph_name: Optional[str] = None,
) -> None:
    try:
        state_mod.save_graph_state(
            name,
            _graph_to_state(
                g, schema_name=schema_name, metagraph_name=metagraph_name
            ),
        )
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=2)


def _refuse_if_metagraph_owned(
    name: str, metagraph_name: Optional[str], operation: str,
    *,
    suggested: Optional[str] = None,
) -> None:
    """Q4-B + P2 — refuse mutations on metagraph-owned graphs with a stderr suggestion.

    Standalone-graph CLI mutations (``add-node`` / ``add-edge`` /
    ``add-hyperedge`` / ``set-prop`` / ``update-hyperedge-type`` /
    ``attach-schema`` / ``detach-schema``) are refused when the graph
    has a non-null ``metagraph_name`` back-pointer. Reads (``inspect``,
    ``list-*``) WARN-and-show; mutations REFUSE-and-exit-1.

    Args:
        name: Graph name (for the error message).
        metagraph_name: The current back-pointer value; ``None`` means
            standalone (no refusal).
        operation: Human-readable operation tag for the error message.
        suggested: Optional ``mindsos metagraph ...`` invocation tester
            should use instead. Printed alongside the refusal per P2.
    """
    if metagraph_name is None:
        return
    msg = (
        f"Graph {name!r} is owned by metagraph {metagraph_name!r}; "
        f"{operation} via 'mindsos graph' is refused (Q4-B). "
        f"Route through the metagraph subapp instead, e.g.:"
    )
    typer.echo(msg, err=True)
    if suggested:
        typer.echo(f"    {suggested}", err=True)
    else:
        typer.echo(
            f"    mindsos metagraph <subcommand> --name {metagraph_name} ...",
            err=True,
        )
    typer.echo(
        f"  Or use 'mindsos graph detach-metagraph --name {name}' to "
        f"clear the back-pointer (DM-A recovery path; metagraph state "
        f"file MUST be missing or you will create a dangling reference).",
        err=True,
    )
    raise typer.Exit(code=1)


def _warn_if_metagraph_owned(
    name: str, metagraph_name: Optional[str], operation: str
) -> None:
    """Q4-B read-side — emit a stderr warning but continue (warn-and-show)."""
    if metagraph_name is None:
        return
    typer.echo(
        f"warning: graph {name!r} is owned by metagraph {metagraph_name!r}; "
        f"{operation} shows in-graph contents only. Use 'mindsos metagraph "
        f"inspect --name {metagraph_name}' for the full metagraph view.",
        err=True,
    )


def _path_or_unknown(name: str) -> str:
    try:
        return str(state_mod.state_file_path(name))
    except ValueError:
        return "<unknown>"


def _split_existing_refs(properties: dict[str, Any]) -> tuple[dict, dict]:
    """Split a property bag into (ref:* keys, non-ref keys).

    Used by ``set-prop --replace`` to preserve cross-graph reference
    properties across a replace (Phase 04 — Pick D).
    """
    refs: dict[str, Any] = {}
    rest: dict[str, Any] = {}
    for k, v in properties.items():
        if k.startswith(REF_PROPERTY_PREFIX):
            refs[k] = v
        else:
            rest[k] = v
    return refs, rest


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


@graph_app.command("create")
def create_cmd(
    name: str = typer.Option(..., "--name", help="Graph name."),
    role: Optional[str] = typer.Option(None, "--role", help="Optional semantic role."),
    schema_name: Optional[str] = typer.Option(
        None, "--schema",
        help="Optional schema name to attach at creation time. "
             "Schema must already exist (`mindsos schema create ...`).",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Create an empty graph and write the initial state file."""
    try:
        path = state_mod.state_file_path(name)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=2)
    if path.exists():
        typer.echo(
            f"IdentityError: Graph {name!r} already exists at {path}; "
            f"use 'mindsos graph reset --name {name}' to clear.",
            err=True,
        )
        raise typer.Exit(code=1)
    schema: Optional[Schema] = None
    if schema_name is not None:
        schema = _load_schema_or_die(schema_name)
    g = Graph(name=name, role=role, schema=schema)
    _save_or_die(name, g, schema_name=schema_name)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "name": g.name,
                    "role": g.role,
                    "graph_id": g.graph_id,
                    "schema_name": schema_name,
                    "state_file": str(path),
                },
                indent=2,
            )
        )
    else:
        schema_tag = f" schema={schema_name!r}" if schema_name else ""
        typer.echo(
            f"created: name={g.name} role={g.role!r} graph_id={g.graph_id}{schema_tag}"
        )
        typer.echo(f"state_file={path}")


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------


@graph_app.command("inspect")
def inspect_cmd(
    name: str = typer.Option(..., "--name", help="Graph name."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Report counts + role + graph_id + attached schema for the named graph."""
    g, schema_name, metagraph_name = _load_or_die(name)
    # Q4-B — warn-and-show on read for metagraph-owned graphs.
    _warn_if_metagraph_owned(name, metagraph_name, "inspect")
    summary = {
        "name": g.name,
        "role": g.role,
        "graph_id": g.graph_id,
        "schema_name": schema_name,
        "metagraph_name": metagraph_name,
        "schema_strict": (g.schema.strict if g.schema is not None else None),
        "counts": {
            "nodes": len(g.nodes),
            "edges": len(g.edges),
            "hyperedges": len(g.hyperedges),
        },
        "state_file": str(state_mod.state_file_path(name)),
    }
    if json_out:
        typer.echo(json.dumps(summary, indent=2))
    else:
        typer.echo(
            f"name={g.name} role={g.role!r} graph_id={g.graph_id} "
            f"schema={schema_name!r} strict={summary['schema_strict']} "
            f"metagraph={metagraph_name!r}"
        )
        typer.echo(
            f"nodes={summary['counts']['nodes']} "
            f"edges={summary['counts']['edges']} "
            f"hyperedges={summary['counts']['hyperedges']}"
        )
        typer.echo(f"state_file={summary['state_file']}")


# ---------------------------------------------------------------------------
# add-node
# ---------------------------------------------------------------------------


@graph_app.command("add-node")
def add_node_cmd(
    value: str = typer.Argument(..., help="Primary display value (JSON-or-string)."),
    name: str = typer.Option(..., "--name", help="Graph name."),
    type_name: str = typer.Option(..., "--type", help="Node type name."),
    prop: list[str] = typer.Option(
        [], "--prop", help="Repeat: k=v (JSON-or-string value)."
    ),
    node_id: Optional[str] = typer.Option(
        None, "--node-id", help="Optional explicit node id (IRI passthrough)."
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Add a node to the named graph."""
    g, schema_name, metagraph_name = _load_or_die(name)
    # Q4-B + P2 — refuse mutation on metagraph-owned graphs.
    _refuse_if_metagraph_owned(
        name, metagraph_name, "add-node",
        suggested=(
            "(metagraph-owned graphs do not yet have an in-place add-node "
            "subcommand; detach via 'mindsos graph detach-metagraph "
            f"--name {name}' to mutate standalone, OR add the node before "
            "joining the metagraph)"
        ),
    )
    parsed_value = _parse_value(value)
    props = _parse_props(prop or [])
    try:
        node = g.add_node(
            value=parsed_value,
            type_name=type_name,
            properties=props,
            node_id=node_id,
        )
    except IdentityError as e:
        typer.echo(f"IdentityError: {e}", err=True)
        raise typer.Exit(code=1)
    except UnknownTypeError as e:
        typer.echo(f"UnknownTypeError: {e}", err=True)
        raise typer.Exit(code=1)
    except PropertyShapeError as e:
        typer.echo(f"PropertyShapeError: {e}", err=True)
        raise typer.Exit(code=1)
    _save_or_die(name, g, schema_name=schema_name, metagraph_name=metagraph_name)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "node_id": node.node_id,
                    "value": node.value,
                    "type_name": node.type_name,
                    "properties": dict(node.properties),
                },
                indent=2,
            )
        )
    else:
        typer.echo(f"ok: added node id={node.node_id} type={node.type_name!r}")


# ---------------------------------------------------------------------------
# add-edge
# ---------------------------------------------------------------------------


@graph_app.command("add-edge")
def add_edge_cmd(
    name: str = typer.Option(..., "--name", help="Graph name."),
    source: str = typer.Option(..., "--source", help="Source node id."),
    target: str = typer.Option(..., "--target", help="Target node id."),
    type_name: str = typer.Option(
        ..., "--type", help="Cypher rel-type (must match ^[A-Z][A-Z0-9_]{0,63}$)."
    ),
    label: Optional[str] = typer.Option(None, "--label", help="Optional label."),
    prop: list[str] = typer.Option(
        [], "--prop", help="Repeat: k=v (JSON-or-string value)."
    ),
    edge_id: Optional[str] = typer.Option(
        None, "--edge-id", help="Optional explicit edge id."
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Add a directed edge between two nodes in the named graph."""
    g, schema_name, metagraph_name = _load_or_die(name)
    _refuse_if_metagraph_owned(
        name, metagraph_name, "add-edge",
        suggested=(
            "(metagraph-owned graphs require detach via 'mindsos graph "
            f"detach-metagraph --name {name}' before standalone mutation)"
        ),
    )
    if source not in g.nodes:
        typer.echo(
            f"IdentityError: Source node {source!r} not in graph {name!r}",
            err=True,
        )
        raise typer.Exit(code=1)
    if target not in g.nodes:
        typer.echo(
            f"IdentityError: Target node {target!r} not in graph {name!r}",
            err=True,
        )
        raise typer.Exit(code=1)
    src = g.nodes[source]
    tgt = g.nodes[target]
    props = _parse_props(prop or [])
    try:
        edge = g.add_edge(
            source=src,
            target=tgt,
            type_name=type_name,
            label=label,
            properties=props,
            edge_id=edge_id,
        )
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
    _save_or_die(name, g, schema_name=schema_name, metagraph_name=metagraph_name)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "edge_id": edge.edge_id,
                    "source_id": edge.source.node_id,
                    "target_id": edge.target.node_id,
                    "type_name": edge.type_name,
                    "label": edge.label,
                    "properties": dict(edge.properties),
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"ok: added edge id={edge.edge_id} "
            f"{source} -[{edge.type_name}]-> {target}"
        )


# ---------------------------------------------------------------------------
# add-hyperedge
# ---------------------------------------------------------------------------


@graph_app.command("add-hyperedge")
def add_hyperedge_cmd(
    name: str = typer.Option(..., "--name", help="Graph name."),
    type_name: str = typer.Option(
        ..., "--type", help="Hyperedge relationship type (Phase 04-v2 — required)."
    ),
    member: list[str] = typer.Option(
        [], "--member", help="Repeat: a node id to include in the hyperedge."
    ),
    label: Optional[str] = typer.Option(None, "--label", help="Optional label."),
    prop: list[str] = typer.Option(
        [], "--prop", help="Repeat: k=v (JSON-or-string value)."
    ),
    hyperedge_id: Optional[str] = typer.Option(
        None, "--hyperedge-id", help="Optional explicit hyperedge id."
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Add an n-ary hyperedge across the named members.

    Phase 04-v2 — ``--type`` is required; cypher rel-type regex applies
    (ADR-0021). When a strict schema is attached, the type must be
    registered as a HyperEdgeType and every member's type must be in
    the type's ``allowed_member_types``.
    """
    g, schema_name, metagraph_name = _load_or_die(name)
    _refuse_if_metagraph_owned(
        name, metagraph_name, "add-hyperedge",
        suggested=(
            "(metagraph-owned graphs require detach via 'mindsos graph "
            f"detach-metagraph --name {name}' before standalone mutation)"
        ),
    )
    members = list(member or [])
    resolved: list[Node] = []
    for mid in members:
        if mid not in g.nodes:
            typer.echo(
                f"IdentityError: HyperEdge member {mid!r} not in graph {name!r}",
                err=True,
            )
            raise typer.Exit(code=1)
        resolved.append(g.nodes[mid])
    props = _parse_props(prop or [])
    try:
        he = g.add_hyperedge(
            nodes=resolved,
            type_name=type_name,
            label=label,
            properties=props,
            edge_id=hyperedge_id,
        )
    except SchemaError as e:
        typer.echo(f"SchemaError: {e}", err=True)
        raise typer.Exit(code=1)
    except CypherError as e:
        typer.echo(f"CypherError: {e}", err=True)
        raise typer.Exit(code=1)
    except UnknownTypeError as e:
        typer.echo(f"UnknownTypeError: {e}", err=True)
        raise typer.Exit(code=1)
    except IdentityError as e:
        typer.echo(f"IdentityError: {e}", err=True)
        raise typer.Exit(code=1)
    except PropertyShapeError as e:
        typer.echo(f"PropertyShapeError: {e}", err=True)
        raise typer.Exit(code=1)
    _save_or_die(name, g, schema_name=schema_name, metagraph_name=metagraph_name)
    sorted_member_ids = sorted(n.node_id for n in he.nodes)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "edge_id": he.edge_id,
                    "type_name": he.type_name,
                    "member_ids": sorted_member_ids,
                    "label": he.label,
                    "properties": dict(he.properties),
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"ok: added hyperedge id={he.edge_id} "
            f"type={he.type_name!r} "
            f"members={sorted_member_ids} label={he.label!r}"
        )


# ---------------------------------------------------------------------------
# update-hyperedge-type (Phase 04-v2 — UHT-1 legacy migration recovery)
# ---------------------------------------------------------------------------


@graph_app.command("update-hyperedge-type")
def update_hyperedge_type_cmd(
    name: str = typer.Option(..., "--name", help="Graph name."),
    hyperedge_id: str = typer.Option(
        ..., "--hyperedge-id", help="Hyperedge id whose type_name to update."
    ),
    new_type_name: str = typer.Option(
        ..., "--type", help="New hyperedge type_name (cypher rel-type regex applies)."
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Update a hyperedge's ``type_name`` (Phase 04-v2 — UHT-1 recovery path).

    Designed for legacy migration: pre-v=3 hyperedges load with the
    SENT-1 sentinel ``"UNSPECIFIED"`` and need a path to receive a real
    type_name. Cypher rel-type regex per ADR-0021 applies. Schema check
    if attached: type must be registered AND every member's node type
    must be in ``allowed_member_types``.

    Asymmetric note: Edge.type_name and Node.type_name remain immutable
    (no ``update-edge-type`` / ``update-node-type`` ships). HyperEdge
    receives this surface solely as a Phase 04-v2 legacy-migration path.
    """
    g, schema_name, metagraph_name = _load_or_die(name)
    _refuse_if_metagraph_owned(
        name, metagraph_name, "update-hyperedge-type",
        suggested=(
            "(metagraph-owned graphs require detach via 'mindsos graph "
            f"detach-metagraph --name {name}' before standalone mutation)"
        ),
    )
    he = g.hyperedges.get(hyperedge_id)
    if he is None:
        typer.echo(
            f"IdentityError: Unknown hyperedge id: {hyperedge_id!r}",
            err=True,
        )
        raise typer.Exit(code=1)
    previous_type_name = he.type_name
    try:
        g.update_hyperedge_type(hyperedge_id, new_type_name)
    except CypherError as e:
        typer.echo(f"CypherError: {e}", err=True)
        raise typer.Exit(code=1)
    except UnknownTypeError as e:
        typer.echo(f"UnknownTypeError: {e}", err=True)
        raise typer.Exit(code=1)
    except IdentityError as e:
        typer.echo(f"IdentityError: {e}", err=True)
        raise typer.Exit(code=1)
    _save_or_die(name, g, schema_name=schema_name, metagraph_name=metagraph_name)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "hyperedge_id": hyperedge_id,
                    "previous_type_name": previous_type_name,
                    "new_type_name": new_type_name,
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"ok: updated hyperedge id={hyperedge_id} "
            f"type {previous_type_name!r} -> {new_type_name!r}"
        )


# ---------------------------------------------------------------------------
# attach-schema (Phase 04)
# ---------------------------------------------------------------------------


@graph_app.command("attach-schema")
def attach_schema_cmd(
    name: str = typer.Option(..., "--name", help="Graph name."),
    schema_name: str = typer.Option(..., "--schema", help="Schema name to attach."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Attach a schema to an existing graph with eager validation.

    Every existing node and edge is re-validated against the schema. The
    first violation prints a structured error including the offending
    element id and exits 1; the graph state file is NOT modified.

    Re-attach is permitted: if a schema is already attached, the new one
    replaces it (after eager re-validation against the new schema). The
    JSON output reports ``previous_schema``.

    If the new schema is strict AND has zero NodeTypes, a stderr warning
    is emitted (the graph cannot accept any further node adds).
    """
    g, previous_schema, metagraph_name = _load_or_die(name)
    _refuse_if_metagraph_owned(
        name, metagraph_name, "attach-schema",
        suggested=(
            "(schema attachment on metagraph-owned graphs is deferred to "
            "Phase 14 via the metagraph subapp; detach first if you need "
            "standalone schema operations)"
        ),
    )
    new_schema = _load_schema_or_die(schema_name)

    # Eager validation: rebuild a fresh schema-attached Graph by replaying
    # every node + edge + hyperedge through the validation hooks. Each
    # element is wrapped to attach the offending element id to the error.
    validator = Graph(
        name=g.name,
        role=g.role,
        graph_id=g.graph_id,
        schema=new_schema,
    )
    # Graph.__init__ skips graph_id registration when graph_id is passed
    # explicitly; the validator's identity is a fresh empty registry.
    validator.identity.register(validator.graph_id)

    def _validation_exit(kind: str, elt_id: str, exc: Exception) -> None:
        typer.echo(
            f"{kind} {elt_id}: {type(exc).__name__}: {exc} — schema "
            f"{schema_name!r} NOT attached to graph {name!r}; existing "
            f"data does not conform.",
            err=True,
        )
        raise typer.Exit(code=1)

    for n in sorted(g.nodes.values(), key=lambda x: x.node_id):
        try:
            validator.add_node(
                value=n.value,
                type_name=n.type_name,
                properties=dict(n.properties),
                node_id=n.node_id,
            )
        except (UnknownTypeError, PropertyShapeError, IdentityError, SchemaError) as exc:
            _validation_exit("node", n.node_id, exc)

    for e in sorted(g.edges.values(), key=lambda x: x.edge_id):
        try:
            src = validator.nodes[e.source.node_id]
            tgt = validator.nodes[e.target.node_id]
            validator.add_edge(
                source=src,
                target=tgt,
                type_name=e.type_name,
                label=e.label,
                properties=dict(e.properties),
                edge_id=e.edge_id,
            )
        except (
            CypherError,
            UnknownTypeError,
            PropertyShapeError,
            IdentityError,
            SchemaError,
        ) as exc:
            _validation_exit("edge", e.edge_id, exc)

    for h in sorted(g.hyperedges.values(), key=lambda x: x.edge_id):
        try:
            members = [validator.nodes[m.node_id] for m in h.nodes]
            validator.add_hyperedge(
                nodes=members,
                type_name=h.type_name,  # Phase 04-v2 — schema validation extends.
                label=h.label,
                properties=dict(h.properties),
                edge_id=h.edge_id,
            )
        except (
            CypherError,
            UnknownTypeError,
            PropertyShapeError,
            IdentityError,
            SchemaError,
        ) as exc:
            _validation_exit("hyperedge", h.edge_id, exc)

    # Validation passed — persist the original graph (data is unchanged)
    # with the new schema_name reference.
    g.schema = new_schema
    _save_or_die(name, g, schema_name=schema_name, metagraph_name=metagraph_name)

    # Empty-strict-schema footgun warning (Phase 04 — Pick G).
    if new_schema.strict and len(new_schema.node_types) == 0:
        typer.echo(
            f"warning: schema {schema_name!r} is strict but declares zero "
            f"NodeTypes; subsequent 'graph add-node' calls will reject every "
            f"type with UnknownTypeError. Add NodeTypes via 'mindsos schema "
            f"add-node-type --schema {schema_name} --type-name <NAME>' or "
            f"'mindsos graph detach-schema --name {name}'.",
            err=True,
        )

    if json_out:
        typer.echo(
            json.dumps(
                {
                    "name": name,
                    "schema_name": schema_name,
                    "previous_schema": previous_schema,
                    "strict": new_schema.strict,
                    "validated": {
                        "nodes": len(g.nodes),
                        "edges": len(g.edges),
                        "hyperedges": len(g.hyperedges),
                    },
                },
                indent=2,
            )
        )
    else:
        prev_tag = (
            f" (replaced previous={previous_schema!r})"
            if previous_schema is not None
            else ""
        )
        typer.echo(
            f"ok: attached schema={schema_name!r} (strict={new_schema.strict}) "
            f"to graph={name!r}{prev_tag}; validated {len(g.nodes)} node(s), "
            f"{len(g.edges)} edge(s), {len(g.hyperedges)} hyperedge(s)."
        )


# ---------------------------------------------------------------------------
# detach-schema (Phase 04)
# ---------------------------------------------------------------------------


@graph_app.command("detach-schema")
def detach_schema_cmd(
    name: str = typer.Option(..., "--name", help="Graph name."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Clear ``schema_name`` from the graph's state file.

    Operates on the raw JSON dict rather than routing through schema
    rehydration, so it works EVEN WHEN the referenced schema state file
    has been deleted. This is the primary recovery path for a graph
    with a dangling schema reference.

    Exits 1 if no schema is currently attached (idempotent-no-op refused
    per the Phase 03 fail-loudly pattern).
    """
    try:
        path = state_mod.state_file_path(name)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=2)

    # Raw load — bypasses _load_or_die / _state_to_graph so a dangling
    # schema reference doesn't block the recovery.
    try:
        state = state_mod.load_graph_state(name)
    except FileNotFoundError:
        typer.echo(
            f"Graph {name!r} not found at {path}; nothing to detach.",
            err=True,
        )
        raise typer.Exit(code=1)
    except RuntimeError as e:
        typer.echo(f"State file error: {e}", err=True)
        raise typer.Exit(code=1)

    previous_schema = state.get("schema_name")
    if previous_schema is None:
        typer.echo(
            f"Graph {name!r} has no schema attached; nothing to detach.",
            err=True,
        )
        raise typer.Exit(code=1)

    state["schema_name"] = None
    # Always upgrade to current version on write (one-way migration). The
    # migration chain has already migrated to v=4 on load, so this is a
    # no-op other than the explicit version stamp.
    state["_state_version"] = state_mod.GRAPH_STATE_VERSION
    state_mod.save_graph_state(name, state)

    if json_out:
        typer.echo(
            json.dumps(
                {
                    "name": name,
                    "previous_schema": previous_schema,
                    "schema_name": None,
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"ok: detached schema={previous_schema!r} from graph={name!r}"
        )


# ---------------------------------------------------------------------------
# detach-metagraph (Phase 05a — DM-A recovery path)
# ---------------------------------------------------------------------------


@graph_app.command("detach-metagraph")
def detach_metagraph_cmd(
    name: str = typer.Option(..., "--name", help="Graph name."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Clear ``metagraph_name`` from the graph's state file (DM-A — Phase 05a).

    Recovery path symmetric with ``detach-schema``: operates on the raw
    JSON dict (does NOT route through metagraph rehydration), so it
    works EVEN WHEN the referenced metagraph state file has been deleted
    or is otherwise unreadable. Primary recovery for a graph with a
    dangling back-pointer (e.g., after ``mindsos metagraph reset --force
    --yes`` orphaned the back-pointer, OR after manual deletion of the
    metagraph state file).

    **Warning:** if the referenced metagraph state file STILL EXISTS and
    references this graph, running ``detach-metagraph`` creates an
    inconsistency — the metagraph thinks it owns this graph but the
    graph no longer back-points. The fix in that case is
    ``mindsos metagraph remove-graph --name <metagraph> --graph <graph>``,
    not ``detach-metagraph``. Use this command only when the metagraph
    state is gone or unrecoverable.

    Exits 1 if no back-pointer is currently set (idempotent-no-op
    refused per the Phase 03 fail-loudly pattern).
    """
    try:
        path = state_mod.state_file_path(name)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=2)

    # Raw load — bypasses _load_or_die / _state_to_graph so a dangling
    # schema reference (or other rehydration failure) doesn't block the
    # recovery. Migration chain still runs (forward-fills metagraph_name
    # field for pre-v=4 files; populates with None default).
    try:
        state = state_mod.load_graph_state(name)
    except FileNotFoundError:
        typer.echo(
            f"Graph {name!r} not found at {path}; nothing to detach.",
            err=True,
        )
        raise typer.Exit(code=1)
    except RuntimeError as e:
        typer.echo(f"State file error: {e}", err=True)
        raise typer.Exit(code=1)

    previous_metagraph = state.get("metagraph_name")
    if previous_metagraph is None:
        typer.echo(
            f"Graph {name!r} has no metagraph back-pointer; nothing to detach.",
            err=True,
        )
        raise typer.Exit(code=1)

    state["metagraph_name"] = None
    state["_state_version"] = state_mod.GRAPH_STATE_VERSION
    state_mod.save_graph_state(name, state)

    if json_out:
        typer.echo(
            json.dumps(
                {
                    "name": name,
                    "previous_metagraph": previous_metagraph,
                    "metagraph_name": None,
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"ok: detached metagraph={previous_metagraph!r} back-pointer "
            f"from graph={name!r}"
        )


# ---------------------------------------------------------------------------
# set-prop (Phase 04)
# ---------------------------------------------------------------------------


@graph_app.command("set-prop")
def set_prop_cmd(
    name: str = typer.Option(..., "--name", help="Graph name."),
    node_id: Optional[str] = typer.Option(
        None, "--node-id", help="Node id to update."
    ),
    edge_id: Optional[str] = typer.Option(
        None, "--edge-id", help="Edge id to update."
    ),
    hyperedge_id: Optional[str] = typer.Option(
        None, "--hyperedge-id",
        help="Hyperedge id to update (Phase 04-v2 — added to mutex).",
    ),
    prop: list[str] = typer.Option(
        [], "--prop", help="Repeat: k=v (JSON-or-string). Required."
    ),
    replace: bool = typer.Option(
        False, "--replace",
        help="Swap the property bag entirely (preserves ref:* keys; "
             "user-supplied ref:* values overwrite existing ones). "
             "Default merges via dict.update.",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Update a node, edge, or hyperedge's property bag (schema-validated when attached).

    Phase 04-v2 — 3-way mutex: exactly ONE of ``--node-id`` / ``--edge-id``
    / ``--hyperedge-id`` must be supplied (no zero, no two, no three).

    --replace semantics (Phase 04 — Pick D + N5):
      The non-ref portion of the existing bag is dropped; the user-supplied
      properties are stored. Cross-graph reference properties (``ref:*``
      keys) in the existing bag are PRESERVED unless the user explicitly
      provides a replacement (user ``ref:*`` values win on collision).
      There is no CLI path to DROP a ref key in Phase 04 — recovery via
      hand-edit, or future Phase 09 XRef migration.
    """
    # Phase 04-v2 — 3-way mutex (extends Phase 04's 2-way).
    n_set = sum(1 for x in (node_id, edge_id, hyperedge_id) if x is not None)
    if n_set != 1:
        typer.echo(
            "Specify exactly one of --node-id, --edge-id, or --hyperedge-id.",
            err=True,
        )
        raise typer.Exit(code=2)
    if not prop:
        typer.echo(
            "set-prop requires at least one --prop k=v.", err=True
        )
        raise typer.Exit(code=2)
    user_props = _parse_props(prop)
    g, schema_name, metagraph_name = _load_or_die(name)
    _refuse_if_metagraph_owned(
        name, metagraph_name, "set-prop",
        suggested=(
            "(use 'mindsos metagraph set-prop --name <metagraph> "
            "--metaedge-id <id> ...' for metagraph-scoped properties; "
            "graph-internal element properties on metagraph-owned "
            f"graphs require detach via 'mindsos graph detach-metagraph "
            f"--name {name}' first)"
        ),
    )
    try:
        if node_id is not None:
            existing = g.nodes[node_id].properties if node_id in g.nodes else None
            props_to_apply = _build_replace_bag(existing, user_props) if replace else user_props
            elt = g.update_node_properties(node_id, props_to_apply, replace=replace)
            kind, kind_id, type_name = "node", elt.node_id, elt.type_name
        elif edge_id is not None:
            existing = g.edges[edge_id].properties if edge_id in g.edges else None
            props_to_apply = _build_replace_bag(existing, user_props) if replace else user_props
            elt = g.update_edge_properties(edge_id, props_to_apply, replace=replace)
            kind, kind_id, type_name = "edge", elt.edge_id, elt.type_name
        else:
            assert hyperedge_id is not None  # mypy
            existing = (
                g.hyperedges[hyperedge_id].properties
                if hyperedge_id in g.hyperedges else None
            )
            props_to_apply = _build_replace_bag(existing, user_props) if replace else user_props
            elt = g.update_hyperedge_properties(
                hyperedge_id, props_to_apply, replace=replace
            )
            kind, kind_id, type_name = "hyperedge", elt.edge_id, elt.type_name
    except IdentityError as e:
        typer.echo(f"IdentityError: {e}", err=True)
        raise typer.Exit(code=1)
    except UnknownTypeError as e:
        typer.echo(f"UnknownTypeError: {e}", err=True)
        raise typer.Exit(code=1)
    except PropertyShapeError as e:
        typer.echo(f"PropertyShapeError: {e}", err=True)
        raise typer.Exit(code=1)
    _save_or_die(name, g, schema_name=schema_name, metagraph_name=metagraph_name)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "kind": kind,
                    "id": kind_id,
                    "type_name": type_name,
                    "properties": dict(elt.properties),
                    "replace": replace,
                },
                indent=2,
            )
        )
    else:
        verb = "replaced" if replace else "merged"
        typer.echo(
            f"ok: {verb} {kind} id={kind_id} type={type_name!r} "
            f"properties={dict(elt.properties)}"
        )


def _build_replace_bag(
    existing: Optional[dict[str, Any]], user_props: dict[str, Any]
) -> dict[str, Any]:
    """Build the replacement bag: existing-refs preserved, user wins on collision.

    Phase 04 — Pick D + N5. Non-ref keys from existing are DROPPED (the
    user is replacing them). Ref keys (``ref:*``) from existing are
    PRESERVED unless the user supplies a new value for the same key —
    user values always win.
    """
    if not existing:
        return dict(user_props)
    existing_refs, _ = _split_existing_refs(existing)
    # User properties win on collision; existing refs fill in the gaps.
    return {**existing_refs, **user_props}


# ---------------------------------------------------------------------------
# list-nodes / list-edges / list-hyperedges
# ---------------------------------------------------------------------------


@graph_app.command("list-nodes")
def list_nodes_cmd(
    name: str = typer.Option(..., "--name", help="Graph name."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """List nodes in the named graph (sorted by node_id)."""
    g, _schema, metagraph_name = _load_or_die(name)
    _warn_if_metagraph_owned(name, metagraph_name, "list-nodes")
    nodes = sorted(g.nodes.values(), key=lambda n: n.node_id)
    if json_out:
        typer.echo(
            json.dumps(
                [
                    {
                        "node_id": n.node_id,
                        "value": n.value,
                        "type_name": n.type_name,
                        "properties": dict(n.properties),
                    }
                    for n in nodes
                ],
                indent=2,
            )
        )
    else:
        for n in nodes:
            typer.echo(f"{n.node_id}  type={n.type_name!r}  value={n.value!r}")


@graph_app.command("list-edges")
def list_edges_cmd(
    name: str = typer.Option(..., "--name", help="Graph name."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """List edges in the named graph (sorted by edge_id)."""
    g, _schema, metagraph_name = _load_or_die(name)
    _warn_if_metagraph_owned(name, metagraph_name, "list-edges")
    edges = sorted(g.edges.values(), key=lambda e: e.edge_id)
    if json_out:
        typer.echo(
            json.dumps(
                [
                    {
                        "edge_id": e.edge_id,
                        "source_id": e.source.node_id,
                        "target_id": e.target.node_id,
                        "type_name": e.type_name,
                        "label": e.label,
                        "properties": dict(e.properties),
                    }
                    for e in edges
                ],
                indent=2,
            )
        )
    else:
        for e in edges:
            typer.echo(
                f"{e.edge_id}  {e.source.node_id} -[{e.type_name}]-> "
                f"{e.target.node_id}  label={e.label!r}"
            )


@graph_app.command("list-hyperedges")
def list_hyperedges_cmd(
    name: str = typer.Option(..., "--name", help="Graph name."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """List hyperedges in the named graph (sorted by edge_id)."""
    g, _schema, metagraph_name = _load_or_die(name)
    _warn_if_metagraph_owned(name, metagraph_name, "list-hyperedges")
    hyperedges = sorted(g.hyperedges.values(), key=lambda h: h.edge_id)
    if json_out:
        typer.echo(
            json.dumps(
                [
                    {
                        "edge_id": h.edge_id,
                        "type_name": h.type_name,  # Phase 04-v2.
                        "member_ids": sorted(n.node_id for n in h.nodes),
                        "label": h.label,
                        "properties": dict(h.properties),
                    }
                    for h in hyperedges
                ],
                indent=2,
            )
        )
    else:
        for h in hyperedges:
            members = sorted(n.node_id for n in h.nodes)
            typer.echo(
                f"{h.edge_id}  members={members}  label={h.label!r}"
            )


# ---------------------------------------------------------------------------
# list (graphs)
# ---------------------------------------------------------------------------


@graph_app.command("list")
def list_graphs_cmd(
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Enumerate every graph in $MINDSOS_STATE_DIR (sorted by name).

    Note (Phase 04 — Pick P3): this command DELIBERATELY bypasses
    ``load_graph_state``'s strict version check. It reads the JSON
    directly so that future-version files (e.g. v=3 written by a
    later phase) still appear in the listing rather than getting
    hidden — better UX to show "exists, possibly newer" than to omit.
    Mutating commands (``inspect``, ``add-*``, etc.) DO use the strict
    loader and will refuse forward-version files cleanly.
    """
    entries: list[dict] = []
    for path in state_mod.iter_state_files():
        try:
            raw = path.read_text(encoding="utf-8")
            state = json.loads(raw)
        except (OSError, json.JSONDecodeError) as e:
            entries.append(
                {
                    "path": str(path),
                    "error": f"unreadable: {e}",
                }
            )
            continue
        if not isinstance(state, dict):
            entries.append({"path": str(path), "error": "non-dict top-level"})
            continue
        entries.append(
            {
                "name": state.get("name"),
                "role": state.get("role"),
                "graph_id": state.get("graph_id"),
                "schema_name": state.get("schema_name"),
                "metagraph_name": state.get("metagraph_name"),
                "state_version": state.get("_state_version"),
                "counts": {
                    "nodes": len(state.get("nodes") or []),
                    "edges": len(state.get("edges") or []),
                    "hyperedges": len(state.get("hyperedges") or []),
                },
                "path": str(path),
            }
        )
    if json_out:
        typer.echo(
            json.dumps(
                {"state_dir": str(state_mod.state_dir()), "graphs": entries},
                indent=2,
            )
        )
    else:
        typer.echo(f"state_dir={state_mod.state_dir()}")
        if not entries:
            typer.echo("(no graphs)")
            return
        for e in entries:
            if "error" in e:
                typer.echo(f"  {e['path']}  ERROR: {e['error']}")
            else:
                c = e["counts"]
                schema_tag = (
                    f"  schema={e['schema_name']!r}" if e.get("schema_name") else ""
                )
                metagraph_tag = (
                    f"  metagraph={e['metagraph_name']!r}"
                    if e.get("metagraph_name") else ""
                )
                typer.echo(
                    f"  name={e['name']!r}  role={e['role']!r}  "
                    f"graph_id={e['graph_id']}  v={e['state_version']}"
                    f"{schema_tag}{metagraph_tag}  "
                    f"nodes={c['nodes']} edges={c['edges']} hyperedges={c['hyperedges']}"
                )


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------


@graph_app.command("reset")
def reset_cmd(
    name: Optional[str] = typer.Option(
        None, "--name", help="Graph name to reset."
    ),
    all_: bool = typer.Option(
        False, "--all", help="Reset every graph in $MINDSOS_STATE_DIR."
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Delete the named state file or every graph state file."""
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

    deleted: list[str] = []
    if name:
        # Q4-B + P2 — refuse reset on metagraph-owned graphs.
        try:
            existing = state_mod.load_graph_state(name)
        except (FileNotFoundError, RuntimeError, ValueError):
            existing = None
        if existing is not None and existing.get("metagraph_name") is not None:
            typer.echo(
                f"Graph {name!r} is owned by metagraph "
                f"{existing['metagraph_name']!r}; reset via 'mindsos graph' "
                f"is refused (Q4-B). Use 'mindsos metagraph remove-graph "
                f"--name {existing['metagraph_name']} --graph {name}' to "
                f"remove cleanly, OR 'mindsos graph detach-metagraph "
                f"--name {name}' first to clear the back-pointer.",
                err=True,
            )
            raise typer.Exit(code=1)
        try:
            state_mod.delete_state_file(name)
        except ValueError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=2)
        except FileNotFoundError:
            path = _path_or_unknown(name)
            typer.echo(
                f"Graph {name!r} not found at {path}; "
                f"nothing to reset.",
                err=True,
            )
            raise typer.Exit(code=1)
        deleted.append(name)
    else:
        # --all
        for path in list(state_mod.iter_state_files()):
            path.unlink()
            deleted.append(path.stem.removeprefix("graph-"))

    if json_out:
        typer.echo(
            json.dumps(
                {"deleted": sorted(deleted), "count": len(deleted)},
                indent=2,
            )
        )
    else:
        for n in sorted(deleted):
            typer.echo(f"ok: deleted graph={n!r}")
        typer.echo(f"count: {len(deleted)}")


# ---------------------------------------------------------------------------
# Compatibility for app.py
# ---------------------------------------------------------------------------


def register_graph_app(parent: typer.Typer) -> None:
    """Wire the graph sub-app onto a parent Typer app."""
    parent.add_typer(graph_app, name="graph")
