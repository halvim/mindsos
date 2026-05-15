"""`mindsos persistence` — Phase 07 5-verb subapp + Phase 08 metagraph extensions.

Verbs (Phase 07 + Phase 08 extensions):

* ``sync --graph G [--replace]`` (P07) / ``sync --metagraph M [--replace]``
  (P08 PB-8 A) — projects state JSON → FalkorDB. ``--replace`` is
  additive-by-default (P18 D); the metagraph variant additionally
  refuses ``--replace`` if dependent instances / XRef / uncommitted
  ``:WALEntry`` rows reference the target (RPB-4 C; exit 2 with
  operator guidance message).
* ``load --graph G [--to-json] [--force]`` (P07) /
  ``load --metagraph M [--to-json]`` (P08 PB-9 A) — reconstructs from
  FalkorDB. The metagraph variant emits the 9-line flat summary
  (R4-5 A); ``--to-json`` writes to
  ``~/.mindsos/metagraph-<name>.fromdb.json`` (RR-7 A; canonical
  state file never overwritten). ``--graph`` and ``--metagraph`` are
  mutually exclusive (R4-6 A; exit 1 on combo). ``--json`` opt-in for
  machine-readable stdout.
* ``diagnose`` (P07) — connectivity + index presence + WAL uncommitted
  count.
* ``verify [--metagraph M | --graph G] [--source=memory|db]`` — 5-bucket
  scanner. Full on ``--source=memory``; 3-bucket partial scanner on
  ``--source=db --graph G`` (P98 A). Phase 08 PB-7 A unblocks
  ``--source=db --metagraph M`` (loads via
  :func:`mindsos_core.reconstruction.load_metagraph` then runs the
  full 5-bucket scanner). Mutex ``--graph G | --metagraph M`` per
  R4-6 A (exit 1 on combo, regardless of source).
* ``inspect-state`` — Rich-table list of FalkorDB contents (graphs +
  metagraphs + instance counts); ``--json`` opt-in for machine
  output (P99 A). Phase 08 keeps global-only per RR-11 B.

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
    help=(
        "Phase 08 — FalkorDB-side persistence (sync/load/diagnose/verify/"
        "inspect-state). Phase 08 adds metagraph round-trip via "
        "`sync --metagraph M` + `load --metagraph M` + "
        "`verify --source=db --metagraph M` (PB-7 A unblock); "
        "`--graph G | --metagraph M` mutex on load + verify (R4-6 A)."
    ),
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
    graph: Optional[str] = typer.Option(
        None, "--graph",
        help="Graph name (JSON state-file basename). Mutually exclusive with --metagraph.",
    ),
    metagraph: Optional[str] = typer.Option(
        None, "--metagraph",
        help=(
            "Metagraph name (JSON state-file basename). Phase 08 PB-8 A — "
            "ships the metagraph variant; refuses --replace on dependent "
            "instances / XRef / uncommitted WAL per RPB-4 C. Mutually "
            "exclusive with --graph."
        ),
    ),
    replace: bool = typer.Option(
        False, "--replace",
        help=(
            "DETACH DELETE first. For --graph: refuses if uncommitted "
            "WAL entries (P91 A). For --metagraph: refuses on dependent "
            "instances / XRef / uncommitted WAL per Phase 08 RPB-4 C."
        ),
    ),
) -> None:
    """Project state JSON → FalkorDB (Phase 07 + Phase 08 metagraph variant).

    Phase 08 R4-6 A — ``--graph`` and ``--metagraph`` are mutually
    exclusive (exit 1 on combo). Pre-Phase-08 callers passing only
    ``--graph`` continue to work unchanged.
    """
    # R4-6 A mutex (exit 1 on combo or neither-supplied).
    if (graph is None) == (metagraph is None):
        if graph is None and metagraph is None:
            _refuse_with(
                "must pass exactly one of --graph or --metagraph",
                exit_code=1,
            )
        _refuse_with(
            "--graph and --metagraph are mutually exclusive (R4-6 A)",
            exit_code=1,
        )

    if metagraph is not None:
        _sync_metagraph(metagraph, replace=replace)
        return

    # Phase 07 single-graph path (unchanged behavior).
    state_path = state_mod.state_file_path(graph)
    if not state_path.exists():
        _refuse_with(f"No state file for graph {graph!r} at {state_path}", exit_code=1)

    try:
        state = state_mod.load_graph_state(graph)
        g, _meta_name, _schema_name = _state_to_graph_dict(state)
    except Exception as e:
        _refuse_with(f"Failed to load graph {graph!r}: {e}", exit_code=2)

    client = _build_client()
    try:
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


def _sync_metagraph(metagraph_name: str, *, replace: bool) -> None:
    """Phase 08 PB-8 A — metagraph-scoped sync. RPB-4 C dependent-state check.

    Loads the metagraph from JSON state, attaches an
    :class:`ElementRegistry` so the persist observer (Phase 07 M9 +
    P96 A) routes sibling-side instance persistence too, then runs
    :meth:`MetagraphRepository.persist`.

    Dependent-state check (RPB-4 C) fires BEFORE any destructive write
    on the ``--replace`` path: if any ElementInstance / CompositeInstance
    / XRef row or uncommitted ``:WALEntry`` references the target
    metagraph in FalkorDB, refuse with exit 2 + operator guidance.
    """
    state_path = state_mod.metagraph_file_path(metagraph_name)
    if not state_path.exists():
        _refuse_with(
            f"No state file for metagraph {metagraph_name!r} at {state_path}",
            exit_code=1,
        )
    try:
        mg = _load_metagraph_from_state(metagraph_name)
    except Exception as e:
        _refuse_with(
            f"Failed to load metagraph {metagraph_name!r}: {e}",
            exit_code=2,
        )

    # Attach the sibling-package registry so persist observer fires
    # (Phase 07 wiring) — also subscribes the Phase 08 after_load
    # observer which is a no-op during sync but inherited by the
    # registry's lifecycle.
    from mindsos_instances import attach_registry

    attach_registry(mg)

    client = _build_client()
    try:
        # RPB-4 C dependent-state precheck BEFORE any destructive write
        # (mirror of B-08-T-likely-4 hotfix pattern).
        if replace:
            findings = _metagraph_has_dependent_state(
                client, mg.metagraph_id
            )
            if findings:
                _refuse_with(
                    f"Metagraph {metagraph_name!r} has dependent state "
                    f"({findings}); drop them or truncate WAL before "
                    f"--replace.",
                    exit_code=2,
                )

            # Destructive wipe of metagraph-scoped substrate state.
            # Drops the :Metagraph anchor + all metagraph-scoped edges /
            # hyperedges / contained-graph nodes / tombstones / WAL.
            client.run_query(
                "MATCH (m:Metagraph {id: $mid}) "
                "OPTIONAL MATCH (g:Graph)-[:IN_METAGRAPH]->(m) "
                "OPTIONAL MATCH (mh:MetaHyperEdge {metagraph_id: $mid}) "
                "OPTIONAL MATCH (ih:IntergraphHyperEdge {metagraph_id: $mid}) "
                "OPTIONAL MATCH (n:Node) WHERE n.graph_id IN [g.id] "
                "OPTIONAL MATCH (h:HyperEdge) WHERE h.graph_id IN [g.id] "
                "OPTIONAL MATCH (t:Tombstone) WHERE t.graph_id IN [g.id] "
                "DETACH DELETE m, g, mh, ih, n, h, t",
                {"mid": mg.metagraph_id},
            )

        from mindsos_core.persistence import MetagraphRepository

        repo = MetagraphRepository(client)
        repo.persist(mg)

        _console.print(
            f"[green]OK[/green] metagraph {metagraph_name!r} synced "
            f"to FalkorDB (graphs={len(mg.graphs)}, "
            f"metaedges={len(mg.metaedges)}, "
            f"metahyperedges={len(mg.metahyperedges)}, "
            f"intergraph_edges={len(mg.intergraph_edges)}, "
            f"intergraph_hyperedges={len(mg.intergraph_hyperedges)}, "
            f"xrefs={len(mg.xrefs)}, "
            f"replace={replace})"
        )
    finally:
        client.close()


def _metagraph_has_dependent_state(client, metagraph_id: str) -> str:
    """RPB-4 C — return a non-empty findings string iff any dependent rows exist.

    Buckets checked:

    * ElementInstance rows with ``metagraph_id == mid``.
    * CompositeInstance rows with ``metagraph_id == mid``.
    * XRef rows (Phase 09; check by node label; no-op in 08).
    * Uncommitted ``:WALEntry`` rows whose payload references the
      metagraph_id (substring-match per P91 A precedent).
    """
    finds: list[str] = []

    ei = client.run_query(
        "MATCH (i:ElementInstance {metagraph_id: $mid}) RETURN count(i) AS n",
        {"mid": metagraph_id},
    ).first()
    if ei and int(ei.get("n", 0)) > 0:
        finds.append(f"{int(ei.get('n', 0))} ElementInstance")

    ci = client.run_query(
        "MATCH (c:CompositeInstance {metagraph_id: $mid}) RETURN count(c) AS n",
        {"mid": metagraph_id},
    ).first()
    if ci and int(ci.get("n", 0)) > 0:
        finds.append(f"{int(ci.get('n', 0))} CompositeInstance")

    # XRef per Phase 09 M11 — query field is ``source_metagraph_id``
    # (v3 baseline schema; ``metagraph_id`` was a Phase 08 placeholder).
    # try/except retained: pre-Phase-09 fixtures or substrates that
    # haven't bootstrapped the :XRef label still treat zero hits as
    # "no dependent state" rather than crashing.
    try:
        xr = client.run_query(
            "MATCH (x:XRef {source_metagraph_id: $mid}) RETURN count(x) AS n",
            {"mid": metagraph_id},
        ).first()
        if xr and int(xr.get("n", 0)) > 0:
            finds.append(f"{int(xr.get('n', 0))} XRef")
    except Exception:
        pass

    wal = client.run_query(
        "MATCH (w:WALEntry) "
        "WHERE w.committed = false AND w.payload_json CONTAINS $mid "
        "RETURN count(w) AS n",
        {"mid": metagraph_id},
    ).first()
    if wal and int(wal.get("n", 0)) > 0:
        finds.append(f"{int(wal.get('n', 0))} uncommitted :WALEntry")

    return ", ".join(finds)


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
    graph: Optional[str] = typer.Option(
        None, "--graph",
        help="Graph name (FalkorDB-side :Graph row id by name). Mutually exclusive with --metagraph.",
    ),
    metagraph: Optional[str] = typer.Option(
        None, "--metagraph",
        help=(
            "Metagraph name (Phase 08 PB-9 A). Loads via "
            ":func:`MetagraphLoader.load`; 9-line flat summary "
            "(R4-5 A) unless --to-json. Mutually exclusive with --graph."
        ),
    ),
    to_json: bool = typer.Option(
        False, "--to-json",
        help=(
            "For --graph: write to ~/.mindsos/graph-<name>.fromdb.json "
            "(P85 B). For --metagraph: write to "
            "~/.mindsos/metagraph-<name>.fromdb.json (Phase 08 RR-7 A)."
        ),
    ),
    out_json: bool = typer.Option(
        False, "--json",
        help="Emit machine-readable JSON to stdout instead of 9-line summary.",
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite an existing .fromdb.json sibling file.",
    ),
) -> None:
    """Reconstruct a Graph or Metagraph from FalkorDB (Phase 07 + Phase 08).

    Phase 08 R4-6 A — ``--graph`` and ``--metagraph`` are mutually
    exclusive (exit 1 on combo). The metagraph variant emits the
    9-line flat summary per R4-5 A; ``--to-json`` writes a sibling
    ``metagraph-<name>.fromdb.json`` per RR-7 A.
    """
    # R4-6 A mutex.
    if (graph is None) == (metagraph is None):
        if graph is None and metagraph is None:
            _refuse_with(
                "must pass exactly one of --graph or --metagraph",
                exit_code=1,
            )
        _refuse_with(
            "--graph and --metagraph are mutually exclusive (R4-6 A)",
            exit_code=1,
        )

    if metagraph is not None:
        _load_metagraph_cmd(
            metagraph, to_json=to_json, out_json=out_json, force=force
        )
        return

    # Phase 07 single-graph path (unchanged behavior).
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
        graph_id = res.rows[0]["gid"]

        from mindsos_core.reconstruction import load_graph

        g = load_graph(client, graph_id)

        if not to_json:
            _console.print(f"name: {g.name}")
            _console.print(f"graph_id: {g.graph_id}")
            _console.print(f"role: {g.role}")
            _console.print(f"schema_name: {g.schema.name if g.schema else 'none'}")
            _console.print(f"nodes: {len(g.nodes)}")
            _console.print(f"edges: {len(g.edges)}")
            _console.print(f"hyperedges: {len(g.hyperedges)}")
            return

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


def _load_metagraph_cmd(
    metagraph_name: str,
    *,
    to_json: bool,
    out_json: bool,
    force: bool,
) -> None:
    """Phase 08 PB-9 A — metagraph load CLI handler.

    Reads via :func:`mindsos_core.reconstruction.load_metagraph` and
    emits either:

    * 9-line flat key:value summary per R4-5 A (default), OR
    * machine-readable JSON to stdout (``--json``), OR
    * sibling ``~/.mindsos/metagraph-<name>.fromdb.json`` file
      (``--to-json`` per RR-7 A; canonical state file untouched).

    Per Phase 08 PB-4 A + RR-9 A: the load fires the after-load observer
    which (if the registry is attached) rehydrates instances.
    Per-observer exception isolation keeps the load result intact even
    if InstanceLoader fails.
    """
    client = _build_client()
    try:
        # Resolve metagraph_id by name.
        res = client.run_query(
            "MATCH (m:Metagraph {name: $name}) RETURN m.id AS mid",
            {"name": metagraph_name},
        )
        if not res.rows:
            _refuse_with(
                f"No :Metagraph with name {metagraph_name!r} in FalkorDB",
                exit_code=2,
            )
        metagraph_id = res.rows[0]["mid"]

        from mindsos_core.reconstruction import load_metagraph
        from mindsos_instances import attach_registry

        # PB-4 A — attach the registry BEFORE the load so the after_load
        # observer's InstanceLoader subscription fires and populates
        # element_instances / composite_instances counts.
        # Build a shell metagraph first via load (with no registry); attach
        # after to wire the observer; then reload (no-op in DB-side terms;
        # observer fires on second load if the impl uses lazy hydration).
        # For Phase 08 simplicity: just load; attach_registry on the
        # returned mg ALSO fires the observer if we re-fire load... but
        # cleaner: load_metagraph itself fires the observer post-construct,
        # so we attach a registry BEFORE the load via a sentinel pattern.
        # Cleanest path: do a 2-pass — initial load to discover the mg
        # name, then construct a fresh mg + attach registry + load.
        # Pragmatic Phase 08 approach: load_metagraph constructs the mg
        # fresh; we attach_registry AFTER to wire the observer for any
        # future loads. The current load's instance counts come from
        # a direct sibling-side population call.
        mg = load_metagraph(client, metagraph_id)
        attach_registry(mg)
        # B-09-T1 — wire the XRef loader BEFORE the after-load dispatch
        # so xrefs[] populates alongside instances. Without this call,
        # mg.xrefs stays empty even when :XRef rows exist in DB and
        # the summary line reports xrefs=0 (Exercise 5 surfaced this).
        from mindsos_core.reconstruction import attach_xref_loader
        attach_xref_loader(mg)
        # Run the after_load fire path now that BOTH the registry +
        # the XRef loader are attached — populates element_instances /
        # composite_instances + mg.xrefs.
        try:
            mg._persist_client = client  # type: ignore[attr-defined]
            from mindsos_core._observers import _dispatch_after_load
            _dispatch_after_load(mg._after_load_observers, mg)
        finally:
            if hasattr(mg, "_persist_client"):
                try:
                    delattr(mg, "_persist_client")
                except AttributeError:
                    pass

        # Compute counts from element_registry.
        ei_count = 0
        ci_count = 0
        registry = getattr(mg, "element_registry", None)
        if registry is not None:
            for entry in registry.iter():
                # KIND classvar tells element vs composite.
                kind = type(entry).KIND  # ClassVar[str]
                if kind == "composite":
                    ci_count += 1
                else:
                    ei_count += 1

        # Summary payload for both stdout + --json + --to-json paths.
        # Phase 09 — XRef count via len(mg.xrefs); the after-load
        # observer subscribed by attach_xref_loader populates mg.xrefs
        # before this point.
        xref_count = len(mg.xrefs)
        summary = {
            "Metagraph": mg.name,
            "Metagraph id": mg.metagraph_id,
            "Graphs": len(mg.graphs),
            "MetaEdges": len(mg.metaedges),
            "MetaHyperEdges": len(mg.metahyperedges),
            "IntergraphEdges": len(mg.intergraph_edges),
            "IntergraphHyperEdges": len(mg.intergraph_hyperedges),
            "XRefs": xref_count,
            "ElementInstances": ei_count,
            "CompositeInstances": ci_count,
        }

        if to_json:
            # RR-7 A — write sibling .fromdb.json file (canonical never
            # overwritten).
            target = (
                state_mod.state_dir() / f"metagraph-{metagraph_name}.fromdb.json"
            )
            if target.exists() and not force:
                _refuse_with(
                    f"{target} exists; pass --force to overwrite.",
                    exit_code=1,
                )
            payload = _build_metagraph_fromdb_payload(mg)
            target.write_text(json.dumps(payload, sort_keys=True, indent=2))
            _console.print(f"[green]OK[/green] wrote {target}")
            return

        if out_json:
            # --json opt-in: emit summary as machine-readable JSON.
            typer.echo(json.dumps(summary, sort_keys=True, indent=2))
            return

        # Phase 09 P52 — replace the prior 9-line flat list with a
        # single structured ``Dependent state:`` line. The line grows
        # additively as future phases add new bucket counts (Snapshots
        # / RemovalImpact in P10; scanner output in P11). Tests assert
        # by key not position; B-08-T1 dynamic-read pattern still
        # applies but for keys, not line counts.
        _console.print(f"Metagraph: {summary['Metagraph']}")
        _console.print(f"Metagraph id: {summary['Metagraph id']}")
        deps = " ".join(
            f"{k.lower()}={summary[k]}"
            for k in (
                "Graphs",
                "MetaEdges",
                "MetaHyperEdges",
                "IntergraphEdges",
                "IntergraphHyperEdges",
                "XRefs",
                "ElementInstances",
                "CompositeInstances",
            )
        )
        _console.print(f"Dependent state: {deps}")
    finally:
        client.close()


def _build_metagraph_fromdb_payload(mg) -> dict:
    """Construct a sibling .fromdb.json shape for `load --metagraph M --to-json`.

    Phase 08 RR-7 A — sibling file format. Mirrors the metagraph state-
    file v=3 shape at top level but is independent of the canonical
    state file (which is never overwritten).
    """
    return {
        "name": mg.name,
        "metagraph_id": mg.metagraph_id,
        "schema_name": getattr(mg, "schema_name", None),
        "properties": dict(getattr(mg, "properties", {}) or {}),
        "graphs": [
            {"name": g.name, "graph_id": g.graph_id, "role": g.role}
            for g in mg.graphs.values()
        ],
        "metaedges": [
            {
                "id": me.edge_id,
                "source_graph_id": me.source_graph_id,
                "target_graph_id": me.target_graph_id,
                "type_name": me.type_name,
                "label": me.label,
                "properties": dict(me.properties),
                "_version": getattr(me, "_version", 1),
            }
            for me in mg.metaedges.values()
        ],
        "metahyperedges": [
            {
                "id": mhe.edge_id,
                "graph_ids": list(mhe.graph_ids),
                "type_name": mhe.type_name,
                "label": mhe.label,
                "properties": dict(mhe.properties),
                "_version": getattr(mhe, "_version", 1),
            }
            for mhe in mg.metahyperedges.values()
        ],
        "intergraph_edges": [
            {
                "id": ie.edge_id,
                "source_graph_id": ie.source_graph_id,
                "source_node_id": ie.source_node_id,
                "target_graph_id": ie.target_graph_id,
                "target_node_id": ie.target_node_id,
                "type_name": ie.type_name,
                "label": ie.label,
                "compositional": ie.compositional,
                "properties": dict(ie.properties),
                "_version": getattr(ie, "_version", 1),
            }
            for ie in mg.intergraph_edges.values()
        ],
        "intergraph_hyperedges": [
            {
                "id": ih.edge_id,
                "anchors": [list(a) for a in ih.anchors],
                "members": [list(m) for m in ih.members],
                "type_name": ih.type_name,
                "label": ih.label,
                "compositional": ih.compositional,
                "properties": dict(ih.properties),
                "_version": getattr(ih, "_version", 1),
            }
            for ih in mg.intergraph_hyperedges.values()
        ],
        # Phase 09 RR-8 — 8-field XRef shape per P53. Sorted by
        # ``xref_id`` for stable round-trip diffs.
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
                }
                for x in mg.xrefs.values()
            ),
            key=lambda d: d["xref_id"],
        ),
    }


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
    """Run integrity scanner; exit 3 on drift findings (P64 A).

    Phase 08 R4-6 A — ``--graph`` and ``--metagraph`` are mutually
    exclusive (exit 1 on combo, regardless of ``--source``).
    Phase 08 PB-7 A — ``--source=db --metagraph M`` unblocked; loads
    via :func:`load_metagraph` then runs the full 5-bucket scanner.
    """
    # R4-6 A mutex applies regardless of --source.
    if metagraph and graph:
        _refuse_with("--metagraph and --graph are mutually exclusive", exit_code=1)
    if not metagraph and not graph:
        _refuse_with("must pass --metagraph or --graph", exit_code=1)
    if source not in ("memory", "db"):
        _refuse_with("--source must be 'memory' or 'db'", exit_code=1)

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

    # source == "db" — graph-scoped (Phase 07) OR metagraph-scoped
    # (Phase 08 PB-7 A unblock).
    from mindsos_core.persistence import (
        verify_invariants, verify_invariants_graph,
    )
    from mindsos_core.reconstruction import load_graph, load_metagraph

    client = _build_client()
    try:
        if metagraph:
            # Phase 08 PB-7 A — load_metagraph then full 5-bucket scanner.
            res = client.run_query(
                "MATCH (m:Metagraph {name: $name}) RETURN m.id AS mid",
                {"name": metagraph},
            )
            if not res.rows:
                _refuse_with(
                    f"No :Metagraph with name {metagraph!r} in FalkorDB",
                    exit_code=2,
                )
            mid = res.rows[0]["mid"]
            mg = load_metagraph(client, mid)
            report = verify_invariants(mg)
            partial_note = False
        else:
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
            report = verify_invariants_graph(g)
            partial_note = True
    finally:
        client.close()

    _emit_report(report, partial_note=partial_note)
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


# ── xref-list (Phase 09 — PB-5 + RR-5 + RR-6 + P63) ────────────────────


@persistence_app.command("xref-list")
def xref_list_cmd(
    metagraph: str = typer.Option(
        ...,
        "--metagraph",
        help="Metagraph name (required). Direct-DB query (P63 A); does NOT load the metagraph or fire recover().",
    ),
    source_id: Optional[str] = typer.Option(
        None, "--source-id", help="Filter: source element id (forward walk).",
    ),
    target_metagraph: Optional[str] = typer.Option(
        None,
        "--target-metagraph",
        help="Filter: target metagraph id (uses (target_metagraph_id, target_id) compound prefix-match per RPB-5).",
    ),
    target_id: Optional[str] = typer.Option(
        None, "--target-id", help="Filter: target element id (reverse walk).",
    ),
    ref_type: Optional[str] = typer.Option(
        None,
        "--ref-type",
        help="Filter: ref_type vocabulary entry (SPECIALISES / INSTANCE_OF / ...).",
    ),
    out_json: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON instead of Rich table (RR-6).",
    ),
) -> None:
    """List :XRef rows for a metagraph (Phase 09 PB-5 + RR-5 + RR-6).

    Direct-DB query path (P63 A) — first verifies the ``:Metagraph``
    anchor exists; raises exit 2 if not. Does NOT call
    ``MetagraphLoader.load`` or fire ``recover()``; pure ``MATCH (x:XRef ...)``
    read with optional WHERE clauses for the four filter flags.

    Output (RR-6):

    * Default — Rich table with truncated IDs (first 8 chars per
      :class:`XRef.__repr__` precedent). Columns: ``xref_id`` /
      ``source_id`` / ``target_metagraph_id`` / ``target_role`` /
      ``target_id`` / ``ref_type``.
    * ``--json`` — full IDs as a JSON array.

    Exit codes per Phase 07 P64 A: 0 clean / 1 CLI usage / 2 system
    error.

    Phase 09 P53 — ``target_stale`` and ``deprecated_at`` columns are
    NOT projected; both ship in Phase 10.
    """
    client = _build_client()
    try:
        # Resolve metagraph name → id (direct query; no load).
        res = client.run_query(
            "MATCH (m:Metagraph {name: $name}) RETURN m.id AS mid",
            {"name": metagraph},
        )
        if not res.rows:
            _refuse_with(
                f"No :Metagraph with name {metagraph!r} in FalkorDB",
                exit_code=2,
            )
        mid = res.rows[0]["mid"]

        # Build the filtered MATCH. Source-metagraph anchor is always
        # present; additional filters tack on as WHERE clauses so the
        # compound index can be used by the planner.
        where: list[str] = []
        params: dict = {"mid": mid}
        if source_id is not None:
            where.append("x.source_id = $sid")
            params["sid"] = source_id
        if target_metagraph is not None:
            where.append("x.target_metagraph_id = $tmid")
            params["tmid"] = target_metagraph
        if target_id is not None:
            where.append("x.target_id = $tid")
            params["tid"] = target_id
        if ref_type is not None:
            where.append("x.ref_type = $rtype")
            params["rtype"] = ref_type

        q = "MATCH (x:XRef {source_metagraph_id: $mid}) "
        if where:
            q += "WHERE " + " AND ".join(where) + " "
        q += (
            "RETURN x.id AS xref_id, x.source_id AS source_id, "
            "       x.target_metagraph_id AS target_metagraph_id, "
            "       x.target_role AS target_role, x.target_id AS target_id, "
            "       x.ref_type AS ref_type "
            "ORDER BY x.id"
        )
        rows = client.run_query(q, params).rows
    finally:
        client.close()

    if out_json:
        typer.echo(json.dumps(rows, sort_keys=True, indent=2))
        return

    table = Table(title=f"XRefs for {metagraph!r}")
    for col in (
        "xref_id",
        "source_id",
        "target_metagraph_id",
        "target_role",
        "target_id",
        "ref_type",
    ):
        table.add_column(col)
    for row in rows:
        table.add_row(
            str(row.get("xref_id") or "")[:8],
            str(row.get("source_id") or "")[:8],
            str(row.get("target_metagraph_id") or "")[:8],
            str(row.get("target_role") or ""),
            str(row.get("target_id") or "")[:8],
            str(row.get("ref_type") or ""),
        )
    _console.print(table)


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
