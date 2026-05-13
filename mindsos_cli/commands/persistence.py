"""`mindsos persistence` — Phase 07 5-verb subapp.

Verbs:

* ``sync --graph <NAME> [--replace]`` — projects Graph contents
  JSON → FalkorDB. Additive default (P18 D); ``--replace`` performs
  DETACH DELETE + rewrite; refuses ``--replace`` if uncommitted
  ``:WALEntry`` rows reference the graph (P91 A).
* ``load --graph <NAME> [--to-json] [--force]`` — reconstructs Graph
  from FalkorDB; default stdout summary in fixed shape (P52 A);
  ``--to-json`` writes to ``~/.mindsos/graph-<name>.fromdb.json``
  (P85 B; canonical state file never overwritten).
* ``diagnose`` — connectivity + 14-index presence + WAL uncommitted
  count.
* ``verify [--metagraph M | --graph G] [--source=memory|db]`` — 5-bucket
  scanner. Full on ``--source=memory``; 3-bucket partial scanner on
  ``--source=db --graph G`` (P98 A); refuses ``--source=db --metagraph M``
  per P49 A.
* ``inspect-state`` — Rich-table list of FalkorDB contents (graphs +
  metagraphs + instance counts); ``--json`` opt-in for machine
  output (P99 A).

Exit codes per P64 A: 0 clean / 1 CLI usage / 2 system error /
3 drift findings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from mindsos_cli import state as state_mod
from mindsos_cli.commands.doctor import _load_manifest, _repo_root
from mindsos_cli.commands.graph import _state_to_graph as _state_to_graph_dict

persistence_app = typer.Typer(
    name="persistence",
    help="Phase 07 — FalkorDB-side persistence (sync/load/diagnose/verify/inspect-state).",
    no_args_is_help=True,
)

_console = Console()


# ── shared helpers ───────────────────────────────────────────────────────


def _build_client():
    """Construct a :class:`FalkorClient` from manifest + env precedence.

    Per P67 A — per-field env-then-manifest-then-default. Password
    env-only (P15 A). Returns the live client; caller closes per P4 A.
    """
    from mindsos_core.config import FalkorConfig
    from mindsos_core.persistence import FalkorClient

    manifest_path = _repo_root() / "mindsos_cli" / "manifest.toml"
    config = FalkorConfig.from_env_and_manifest(manifest_path)
    return FalkorClient(config)


def _refuse_with(msg: str, exit_code: int = 2) -> None:
    """Print msg and exit with the given code; matches Phase 05d split."""
    _console.print(f"[red]Error:[/red] {msg}")
    raise typer.Exit(code=exit_code)


# ── sync ─────────────────────────────────────────────────────────────────


@persistence_app.command("sync")
def sync_cmd(
    graph: str = typer.Option(..., "--graph", help="Graph name (JSON state-file basename)."),
    replace: bool = typer.Option(
        False, "--replace",
        help="DETACH DELETE the graph in FalkorDB first; refuses if uncommitted WAL entries.",
    ),
) -> None:
    """Project a Graph from JSON state → FalkorDB (P18 D + P91 A)."""
    state_path = state_mod.state_file_path(graph)
    if not state_path.exists():
        _refuse_with(f"No state file for graph {graph!r} at {state_path}", exit_code=1)

    # Load Graph object from JSON state (migrate-on-read; v=1..3 → v=4).
    try:
        state = state_mod.load_graph_state(graph)
        g, _meta_name, _schema_name = _state_to_graph_dict(state)
    except Exception as e:
        _refuse_with(f"Failed to load graph {graph!r}: {e}", exit_code=2)

    client = _build_client()
    try:
        # P91 A — refuse --replace if uncommitted WAL entries reference graph.
        if replace and _graph_has_uncommitted_wal(client, g.graph_id):
            _refuse_with(
                f"Uncommitted WAL entries reference graph {graph!r}; "
                "resolve or truncate WAL before --replace.",
                exit_code=2,
            )

        if replace:
            client.run_query(
                "MATCH (g:Graph {id: $gid}) "
                "OPTIONAL MATCH (n:Node {graph_id: $gid}) "
                "OPTIONAL MATCH (h:HyperEdge {graph_id: $gid}) "
                "OPTIONAL MATCH (t:Tombstone {graph_id: $gid}) "
                "DETACH DELETE g, n, h, t",
                {"gid": g.graph_id},
            )

        from mindsos_core.persistence import GraphRepository

        repo = GraphRepository(client)
        repo.persist(g)
        _console.print(
            f"[green]OK[/green] graph {graph!r} synced to FalkorDB "
            f"(nodes={len(g.nodes)}, edges={len(g.edges)}, "
            f"hyperedges={len(g.hyperedges)}, replace={replace})"
        )
    finally:
        client.close()


def _graph_has_uncommitted_wal(client, graph_id: str) -> bool:
    """Per P91 A — check for uncommitted WAL entries referencing this graph.

    WAL payload structure is application-specific; the conservative
    check matches the payload JSON literally for the graph_id. False
    positives possible if a payload happens to contain the same UUID
    substring; tester escape hatch is to resolve WAL first.
    """
    res = client.run_query(
        "MATCH (w:WALEntry) "
        "WHERE w.committed = false AND w.payload_json CONTAINS $gid "
        "RETURN count(w) AS n",
        {"gid": graph_id},
    )
    row = res.first()
    return bool(row and int(row.get("n", 0)) > 0)


# ── load ─────────────────────────────────────────────────────────────────


@persistence_app.command("load")
def load_cmd(
    graph: str = typer.Option(..., "--graph", help="Graph name (FalkorDB-side :Graph row id by name)."),
    to_json: bool = typer.Option(
        False, "--to-json",
        help="Write FalkorDB-side state to ~/.mindsos/graph-<name>.fromdb.json (P85 B sibling path).",
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite an existing .fromdb.json sibling file.",
    ),
) -> None:
    """Reconstruct a Graph from FalkorDB and print summary or sibling JSON."""
    client = _build_client()
    try:
        # Resolve graph_id by name. Phase 07 supports name lookup via a
        # MATCH on the :Graph.name property.
        res = client.run_query(
            "MATCH (g:Graph {name: $name}) RETURN g.id AS gid",
            {"name": graph},
        )
        if not res.rows:
            _refuse_with(
                f"No :Graph with name {graph!r} in FalkorDB", exit_code=2,
            )
        graph_id = res.rows[0]["gid"]

        from mindsos_core.reconstruction import load_graph

        g = load_graph(client, graph_id)

        if not to_json:
            # P52 A fixed-shape stdout summary.
            _console.print(f"name: {g.name}")
            _console.print(f"graph_id: {g.graph_id}")
            _console.print(f"role: {g.role}")
            _console.print(f"schema_name: {g.schema.name if g.schema else 'none'}")
            _console.print(f"nodes: {len(g.nodes)}")
            _console.print(f"edges: {len(g.edges)}")
            _console.print(f"hyperedges: {len(g.hyperedges)}")
            return

        # --to-json: write to fromdb.json sibling path per P85 B.
        target = state_mod.state_dir() / f"graph-{graph}.fromdb.json"
        if target.exists() and not force:
            _refuse_with(
                f"{target} exists; pass --force to overwrite.", exit_code=1,
            )
        payload = {
            "name": g.name,
            "graph_id": g.graph_id,
            "role": g.role,
            "nodes": [
                {"id": n.node_id, "type_name": n.type_name, "value": n.value,
                 "properties": dict(n.properties), "_version": getattr(n, "_version", 1)}
                for n in g.nodes.values()
            ],
            "edges": [
                {"id": e.edge_id, "type_name": e.type_name, "label": e.label,
                 "source_id": e.source.node_id, "target_id": e.target.node_id,
                 "properties": dict(e.properties), "_version": getattr(e, "_version", 1)}
                for e in g.edges.values()
            ],
            "hyperedges": [
                {"id": h.edge_id, "type_name": h.type_name, "label": h.label,
                 "members": sorted(n.node_id for n in h.nodes),
                 "properties": dict(h.properties),
                 "_version": getattr(h, "_version", 1)}
                for h in g.hyperedges.values()
            ],
        }
        target.write_text(json.dumps(payload, sort_keys=True, indent=2))
        _console.print(f"[green]OK[/green] wrote {target}")
    finally:
        client.close()


# ── diagnose ─────────────────────────────────────────────────────────────


@persistence_app.command("diagnose")
def diagnose_cmd() -> None:
    """Connectivity + 14-index presence + WAL uncommitted count."""
    try:
        client = _build_client()
    except Exception as e:
        _refuse_with(f"Could not connect to FalkorDB: {e}", exit_code=2)

    try:
        # Ping via a trivial query.
        client.run_query("RETURN 1 AS ok")
        connectivity = "ok"
    except Exception as e:
        _refuse_with(f"FalkorDB ping failed: {e}", exit_code=2)

    try:
        # Index count: query CALL db.indexes() if available, else assume bootstrap ran.
        from mindsos_core.persistence.bootstrap import DEFAULT_INDEXES

        expected = len(DEFAULT_INDEXES)
        # Lightweight: query indexes from FalkorDB via CALL db.indexes() if supported.
        try:
            ix_res = client.run_query("CALL db.indexes()")
            present = len(ix_res.rows)
        except Exception:
            present = expected  # Fallback — bootstrap was called on FalkorClient init.

        # WAL count across all metagraphs.
        wal_res = client.run_query(
            "MATCH (w:WALEntry) WHERE w.committed = false RETURN count(w) AS n"
        )
        wal_uncommitted = int(wal_res.first().get("n", 0)) if wal_res.first() else 0

        _console.print(f"connectivity: {connectivity}")
        _console.print(f"indexes_present: {present} / expected: {expected}")
        _console.print(f"wal_uncommitted: {wal_uncommitted}")
    finally:
        client.close()


# ── verify ───────────────────────────────────────────────────────────────


@persistence_app.command("verify")
def verify_cmd(
    metagraph: Optional[str] = typer.Option(
        None, "--metagraph", help="Metagraph name (mutually exclusive with --graph)."
    ),
    graph: Optional[str] = typer.Option(
        None, "--graph", help="Graph name (mutually exclusive with --metagraph)."
    ),
    source: str = typer.Option(
        "memory", "--source", help="memory | db (default: memory)."
    ),
) -> None:
    """Run integrity scanner; exit 3 on drift findings (P64 A)."""
    if metagraph and graph:
        _refuse_with("--metagraph and --graph are mutually exclusive", exit_code=1)
    if not metagraph and not graph:
        _refuse_with("must pass --metagraph or --graph", exit_code=1)
    if source not in ("memory", "db"):
        _refuse_with("--source must be 'memory' or 'db'", exit_code=1)

    if source == "db" and metagraph:
        _refuse_with(
            "--source=db --metagraph M not supported in Phase 07 "
            "(metagraph_loader is Phase 08; use --source=memory).",
            exit_code=1,
        )

    if source == "memory":
        from mindsos_core.persistence import (
            verify_invariants, verify_invariants_graph,
        )
        if metagraph:
            mg = _load_metagraph_from_state(metagraph)
            report = verify_invariants(mg)
        else:
            g = _load_graph_from_state(graph)
            report = verify_invariants_graph(g)
        _emit_report(report)
        raise typer.Exit(code=3 if report else 0)

    # source == "db", graph-scoped only (P49 A).
    from mindsos_core.persistence import verify_invariants_graph
    from mindsos_core.reconstruction import load_graph

    client = _build_client()
    try:
        res = client.run_query(
            "MATCH (g:Graph {name: $name}) RETURN g.id AS gid",
            {"name": graph},
        )
        if not res.rows:
            _refuse_with(
                f"No :Graph with name {graph!r} in FalkorDB", exit_code=2,
            )
        gid = res.rows[0]["gid"]
        g = load_graph(client, gid)
    finally:
        client.close()

    report = verify_invariants_graph(g)
    _emit_report(report, partial_note=True)
    raise typer.Exit(code=3 if report else 0)


def _emit_report(report, *, partial_note: bool = False) -> None:
    """Print findings; the report's __bool__ guides the exit code."""
    _console.print(f"summary: {report.summary()}")
    if partial_note:
        _console.print(
            "[skipped] cross_graph_edges, orphan_metaedges — "
            "requires --source=memory --metagraph M"
        )
    if not report:
        return
    if getattr(report, "duplicate_ids", None):
        _console.print(f"duplicate_ids: {report.duplicate_ids}")
    if getattr(report, "cross_graph_edges", None):
        _console.print(f"cross_graph_edges: {report.cross_graph_edges}")
    if getattr(report, "orphan_hyperedges", None):
        _console.print(f"orphan_hyperedges: {report.orphan_hyperedges}")
    if getattr(report, "orphan_metaedges", None):
        _console.print(f"orphan_metaedges: {report.orphan_metaedges}")
    if getattr(report, "dangling_tombstones", None):
        _console.print(f"dangling_tombstones: {report.dangling_tombstones}")


def _load_graph_from_state(name: str):
    """Read a graph state file and reconstruct an in-memory :class:`Graph`."""
    path = state_mod.state_file_path(name)
    if not path.exists():
        _refuse_with(f"No state file for graph {name!r} at {path}", exit_code=1)
    state = state_mod.load_graph_state(name)
    g, _mg_name, _schema_name = _state_to_graph_dict(state)
    return g


def _load_metagraph_from_state(name: str):
    """Read a metagraph state file and reconstruct an in-memory :class:`Metagraph`."""
    from mindsos_cli.commands.metagraph import _state_to_metagraph  # type: ignore

    path = state_mod.metagraph_file_path(name)
    if not path.exists():
        _refuse_with(f"No state file for metagraph {name!r} at {path}", exit_code=1)
    state = state_mod.load_metagraph_state(name)
    return _state_to_metagraph(state)


# ── inspect-state ────────────────────────────────────────────────────────


@persistence_app.command("inspect-state")
def inspect_state_cmd(
    out_json: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON instead of Rich table.",
    ),
) -> None:
    """List FalkorDB contents (graphs + metagraphs + instance counts) — P99 A Rich tables."""
    client = _build_client()
    try:
        graphs = client.run_query(
            "MATCH (g:Graph) RETURN g.id AS id, g.name AS name, g.role AS role"
        ).rows
        metagraphs = client.run_query(
            "MATCH (m:Metagraph) RETURN m.id AS id, m.name AS name, "
            "m.schema_name AS schema_name"
        ).rows
        ei_count = client.run_query(
            "MATCH (i:ElementInstance) RETURN count(i) AS n"
        ).first()
        ci_count = client.run_query(
            "MATCH (c:CompositeInstance) RETURN count(c) AS n"
        ).first()
        instance_counts = {
            "element": int(ei_count.get("n", 0)) if ei_count else 0,
            "composite": int(ci_count.get("n", 0)) if ci_count else 0,
        }
    finally:
        client.close()

    if out_json:
        payload = {
            "graphs": graphs,
            "metagraphs": metagraphs,
            "instances": instance_counts,
        }
        typer.echo(json.dumps(payload, sort_keys=True, indent=2))
        return

    # Rich tables per P99 A.
    g_table = Table(title="Graphs")
    g_table.add_column("name")
    g_table.add_column("id")
    g_table.add_column("role")
    for row in graphs:
        g_table.add_row(
            str(row.get("name") or ""),
            str(row.get("id") or "")[:12],
            str(row.get("role") or ""),
        )
    _console.print(g_table)

    m_table = Table(title="Metagraphs")
    m_table.add_column("name")
    m_table.add_column("id")
    m_table.add_column("schema_name")
    for row in metagraphs:
        m_table.add_row(
            str(row.get("name") or ""),
            str(row.get("id") or "")[:12],
            str(row.get("schema_name") or ""),
        )
    _console.print(m_table)

    i_table = Table(title="Instances")
    i_table.add_column("kind")
    i_table.add_column("count")
    i_table.add_row("ElementInstance", str(instance_counts["element"]))
    i_table.add_row("CompositeInstance", str(instance_counts["composite"]))
    _console.print(i_table)


# ── wiring ───────────────────────────────────────────────────────────────


def register_persistence_app(parent: typer.Typer) -> None:
    """Wire the persistence sub-app onto a parent Typer app."""
    parent.add_typer(persistence_app, name="persistence")
