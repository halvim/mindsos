"""``mindsos metagraph`` — Phase 05a L1 Metagraph subapp.

Subcommands (Q2 + CR-A locked):

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
                              (--on-metagraph | --metaedge-id <ID> | --metahyperedge-id <ID>)
                              --prop k=v [--prop k2=v2 ...] [--replace] [--json]
  mindsos metagraph list-metaedges --name <MG> [--json]
  mindsos metagraph list-metahyperedges --name <MG> [--json]

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
from typing import Any, List, Optional

import typer

from mindsos_core import (
    CypherError,
    Graph,
    IdentityError,
    Metagraph,
    PropertyShapeError,
    REF_PROPERTY_PREFIX,
    SchemaError,
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


def _metagraph_to_state(mg: Metagraph) -> dict:
    """Serialize a ``Metagraph`` to the v=1 state-file dict (P10 shape).

    Persistence keys metaedges by graph NAME (not graph_id) — readability
    and locality. The serializer translates id→name via ``mg.graphs``
    lookup. ``member_graphs`` sorted by graph_name (Q3-A) for byte-stable
    output. Top-level lists sorted by edge_id (metaedges + metahyperedges)
    and by name (contained_graphs).
    """
    # contained_graphs sorted by graph name for byte-stable output.
    contained_graphs = sorted(g.name for g in mg.graphs.values())
    # id → name lookup for metaedge / metahyperedge serialization.
    id_to_name = {g.graph_id: g.name for g in mg.graphs.values()}
    metaedges = sorted(mg.metaedges.values(), key=lambda me: me.edge_id)
    metahyperedges = sorted(
        mg.metahyperedges.values(), key=lambda mhe: mhe.edge_id
    )
    return {
        "_state_version": state_mod.METAGRAPH_STATE_VERSION,
        "metagraph_id": mg.metagraph_id,
        "name": mg.name,
        "properties": dict(mg.properties),
        "contained_graphs": contained_graphs,
        "metaedges": [
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
            }
            for mhe in metahyperedges
        ],
    }


def _state_to_metagraph(state: dict) -> Metagraph:
    """Rehydrate a ``Metagraph`` from a v=1 state-file dict.

    Walks ``contained_graphs`` (graph names) and loads each via
    ``mindsos_cli.state.load_graph_state`` → rehydrates → ``add_graph``.
    Each ``add_graph`` runs the ADR-0020 unification + Q5-A collision
    check (so corrupt states with id collisions surface here).

    For metaedges: looks up source_graph / target_graph names in the
    metagraph's contained graphs to resolve graph_ids, then constructs
    MetaEdge instances directly (bypassing the factory's CLI-friendly
    error UX since we're rehydrating known-valid persisted state).
    """
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

    # name → id lookup for metaedge / metahyperedge rehydration.
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
        mg.identity.register(mhe.edge_id)
        mg.metahyperedges[mhe.edge_id] = mhe

    return mg


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

    P10 JSON shape:

        {
          "name": "<n>",
          "metagraph_id": "<uuid>",
          "properties": {...},
          "contained_graphs": [...sorted graph names],
          "counts": {
            "graphs": int,
            "metaedges": int,
            "metahyperedges": int
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
        "contained_graphs": contained_graph_names,
        "counts": {
            "graphs": len(mg.graphs),
            "metaedges": len(mg.metaedges),
            "metahyperedges": len(mg.metahyperedges),
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
        typer.echo(
            f"graphs={summary['counts']['graphs']} "
            f"metaedges={summary['counts']['metaedges']} "
            f"metahyperedges={summary['counts']['metahyperedges']}"
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

    P10 JSON shape:

        {
          "state_dir": "<path>",
          "metagraphs": [
            {
              "name": "<n>", "metagraph_id": "<uuid>",
              "contained_graphs_count": int,
              "metaedges_count": int,
              "metahyperedges_count": int,
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
                "contained_graphs_count": len(state.get("contained_graphs") or []),
                "metaedges_count": len(state.get("metaedges") or []),
                "metahyperedges_count": len(state.get("metahyperedges") or []),
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
    # Remove from metagraph (cascades).
    try:
        mg.remove_graph(graph_id)
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
                    "contained_graphs_count": len(mg.graphs),
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"ok: removed graph={graph!r} from metagraph={name!r}; "
            f"cascaded {incident_meta} metaedge(s) + {incident_mhe} "
            f"metahyperedge(s); contained_graphs_count={len(mg.graphs)}"
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
# set-prop (P17 — 3-way mutex incl. --on-metagraph)
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
    prop: List[str] = typer.Option(
        [], "--prop", help="Repeat: k=v. Required.",
    ),
    replace: bool = typer.Option(
        False, "--replace",
        help="Swap the property bag entirely (preserves ref:* keys).",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Update a metaedge / metahyperedge / metagraph property bag (P17).

    3-way mutex: exactly ONE of ``--on-metagraph`` / ``--metaedge-id`` /
    ``--metahyperedge-id`` must be supplied.

    --replace semantics: non-ref portion of existing bag dropped; ref:*
    keys preserved unless overridden by user-supplied values (Phase 04
    Pick D + N5 inherited).
    """
    n_set = sum(
        1 for x in (on_metagraph, metaedge_id, metahyperedge_id)
        if (x is True if isinstance(x, bool) else x is not None)
    )
    if n_set != 1:
        typer.echo(
            "Specify exactly one of --on-metagraph, --metaedge-id, or "
            "--metahyperedge-id (P17 3-way mutex).",
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
        else:
            assert metahyperedge_id is not None  # mypy
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


def register_metagraph_app(parent: typer.Typer) -> None:
    """Wire the metagraph sub-app onto a parent Typer app."""
    parent.add_typer(metagraph_app, name="metagraph")
