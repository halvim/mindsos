"""`mindsos graph` — Phase 03 L1 Graph elements CLI surface.

Subcommands:

  mindsos graph create --name <NAME> [--role ROLE] [--json]
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

Cross-invocation persistence: JSON state file at
``${MINDSOS_STATE_DIR or ~/.mindsos}/graph-<name>.json``. Each command
reloads, mutates, writes back. Same compose ``--rm`` gotcha as Phase 02
identity-registry — documented; mitigation = host venv or bind-mount.

Exit codes (PHASE_MAP Phase 03 row appendix #19):
  1 — domain errors (IdentityError, SchemaError, CypherError, malformed
      state file).
  2 — usage errors (missing required arg, malformed flag, empty --prop
      key, reset without --name | --all, invalid <name> regex).
"""

from __future__ import annotations

import json
import sys
from typing import Any, Optional

import typer

from mindsos_core import (
    CypherError,
    Edge,
    Graph,
    HyperEdge,
    IdentityError,
    Node,
    SchemaError,
)
from mindsos_cli import state as state_mod


graph_app = typer.Typer(
    name="graph",
    help="L1 Graph elements — create, inspect, build, list, reset.",
    no_args_is_help=True,
    add_completion=False,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _parse_value(raw: str) -> Any:
    """Try ``json.loads(raw)``; on failure, treat as literal string.

    Same rule applied to ``<VALUE>`` in ``add-node`` and to ``--prop k=v``
    values. ``42`` -> int, ``true`` -> bool, ``[1,2]`` -> list, ``Alice``
    -> string, ``[bad`` -> string ``[bad`` (documented limitation).
    """
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


def _graph_to_state(g: Graph) -> dict:
    """Serialize a ``Graph`` to the v1 state-file dict.

    Sorts top-level lists by id for byte-stable output.
    HyperEdge member ids canonicalised (sorted) before serialization.
    """
    nodes = sorted(g.nodes.values(), key=lambda n: n.node_id)
    edges = sorted(g.edges.values(), key=lambda e: e.edge_id)
    hyperedges = sorted(g.hyperedges.values(), key=lambda h: h.edge_id)
    return {
        "_state_version": state_mod.STATE_VERSION,
        "graph_id": g.graph_id,
        "name": g.name,
        "role": g.role,
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
                "member_ids": sorted(n.node_id for n in h.nodes),
                "label": h.label,
                "properties": dict(h.properties),
            }
            for h in hyperedges
        ],
    }


def _state_to_graph(state: dict) -> Graph:
    """Rehydrate a ``Graph`` from a v1 state-file dict.

    Uses public ``Graph.add_*`` methods with explicit ids (not the private
    ``_restore_*`` helpers, which are deferred to Phase 08).
    """
    g = Graph(
        name=state["name"],
        role=state.get("role"),
        graph_id=state["graph_id"],
    )
    # Avoid double-registering graph_id (Graph.__init__ registered it
    # because we passed graph_id=...; actually __init__ only registers
    # when graph_id is None). Phase 03 contract: state-file graph_id is
    # explicit, so __init__ does NOT auto-register; register here.
    g.identity.register(state["graph_id"])
    for n in state.get("nodes", []):
        g.add_node(
            value=n["value"],
            type_name=n["type_name"],
            properties=dict(n.get("properties") or {}),
            node_id=n["node_id"],
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
        )
    for h in state.get("hyperedges", []):
        members = [g.nodes[mid] for mid in h["member_ids"]]
        g.add_hyperedge(
            nodes=members,
            label=h.get("label"),
            properties=dict(h.get("properties") or {}),
            edge_id=h["edge_id"],
        )
    return g


def _load_or_die(name: str) -> Graph:
    """Load and rehydrate a graph; die with structured exit on failure."""
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


def _save_or_die(name: str, g: Graph) -> None:
    try:
        state_mod.save_graph_state(name, _graph_to_state(g))
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=2)


def _path_or_unknown(name: str) -> str:
    """Return the state-file path or '<unknown>' if name is invalid."""
    try:
        return str(state_mod.state_file_path(name))
    except ValueError:
        return "<unknown>"


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


@graph_app.command("create")
def create_cmd(
    name: str = typer.Option(..., "--name", help="Graph name."),
    role: Optional[str] = typer.Option(None, "--role", help="Optional semantic role."),
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
    g = Graph(name=name, role=role)
    _save_or_die(name, g)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "name": g.name,
                    "role": g.role,
                    "graph_id": g.graph_id,
                    "state_file": str(path),
                },
                indent=2,
            )
        )
    else:
        typer.echo(f"created: name={g.name} role={g.role!r} graph_id={g.graph_id}")
        typer.echo(f"state_file={path}")


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------


@graph_app.command("inspect")
def inspect_cmd(
    name: str = typer.Option(..., "--name", help="Graph name."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Report counts + role + graph_id for the named graph."""
    g = _load_or_die(name)
    summary = {
        "name": g.name,
        "role": g.role,
        "graph_id": g.graph_id,
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
        typer.echo(f"name={g.name} role={g.role!r} graph_id={g.graph_id}")
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
    g = _load_or_die(name)
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
    _save_or_die(name, g)
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
    g = _load_or_die(name)
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
    _save_or_die(name, g)
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
    """Add an n-ary hyperedge across the named members."""
    g = _load_or_die(name)
    members = list(member or [])
    # Resolve members to Node objects; collect unknown ids for batch report.
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
            label=label,
            properties=props,
            edge_id=hyperedge_id,
        )
    except SchemaError as e:
        typer.echo(f"SchemaError: {e}", err=True)
        raise typer.Exit(code=1)
    except IdentityError as e:
        typer.echo(f"IdentityError: {e}", err=True)
        raise typer.Exit(code=1)
    _save_or_die(name, g)
    sorted_member_ids = sorted(n.node_id for n in he.nodes)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "edge_id": he.edge_id,
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
            f"members={sorted_member_ids} label={he.label!r}"
        )


# ---------------------------------------------------------------------------
# list-nodes / list-edges / list-hyperedges
# ---------------------------------------------------------------------------


@graph_app.command("list-nodes")
def list_nodes_cmd(
    name: str = typer.Option(..., "--name", help="Graph name."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """List nodes in the named graph (sorted by node_id)."""
    g = _load_or_die(name)
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
    g = _load_or_die(name)
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
    g = _load_or_die(name)
    hyperedges = sorted(g.hyperedges.values(), key=lambda h: h.edge_id)
    if json_out:
        typer.echo(
            json.dumps(
                [
                    {
                        "edge_id": h.edge_id,
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
    """Enumerate every graph in $MINDSOS_STATE_DIR (sorted by name)."""
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
                typer.echo(
                    f"  name={e['name']!r}  role={e['role']!r}  "
                    f"graph_id={e['graph_id']}  "
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
