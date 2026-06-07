#!/usr/bin/env python3
"""Phase 42 bipartite-topology data-state detector (ADR-0156).

Per Phase 42 design log §5 PB-7 (ground-first: migrator -> detector).

Contract:

* Scans every FalkorDB graph reachable via the standard ``MINDSOS_FALKOR_*``
  / ``FALKOR_HOST`` env-var config for capacity nodes that still carry the
  pre-bipartite ``inputs`` / ``outputs`` node-property lists. Under
  ADR-0156 ``_CapacityBase.to_properties`` no longer serialises those
  lists; the produces/consumes IntergraphEdges are the single source of
  truth, emitted at ``register_capacity`` time.
* Exit code 0 — no pre-bipartite rows found. Clean state.
* Exit code 1 — pre-bipartite rows found. Stderr prints the wipe-and-
  rebootstrap remediation.
* Idempotent: same FalkorDB state -> same exit code, no side effects.

Honest framing: this is a DETECTOR, not a migrator. The shipped v1
``CapacityLayer`` is in-memory-first — the Global L3 metagraph is rebuilt
at process start via ``bootstrap.create_global`` + the idempotent
``install_*`` capacity installers, which now run the bipartite
``register_capacity`` and emit produces/consumes edges natively. There is
no persisted Global capacity state to rewrite in-place; the remediation
for any stray pre-bipartite rows (dev environments) is wipe-and-
rebootstrap, mirroring ``check_rename_state`` (Phase 39) and
``check_phase_43_confidence_state`` (Phase 43).
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable

#: Capacity node types carrying the retired inputs/outputs property lists.
CAPACITY_NODE_TYPES = ("Capacity", "Monitor", "Adapter")


def _connect() -> object:
    """Connect to FalkorDB. Lazy import keeps ``--help`` cheap."""
    try:
        from falkordb import FalkorDB  # type: ignore
    except ImportError as exc:
        print(
            "ERROR: 'falkordb' package not installed. "
            "Install with: pip install falkordb",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    host = os.environ.get("MINDSOS_FALKOR_HOST", os.environ.get("FALKOR_HOST", "localhost"))
    port = int(os.environ.get("MINDSOS_FALKOR_PORT", os.environ.get("FALKOR_PORT", "6379")))
    password = os.environ.get("MINDSOS_FALKOR_PASSWORD") or os.environ.get("FALKOR_PASSWORD")
    return FalkorDB(host=host, port=port, password=password)


def _all_graphs(db: object) -> Iterable[str]:
    """Enumerate every graph in the FalkorDB instance."""
    raw = db.list_graphs()  # type: ignore[attr-defined]
    if isinstance(raw, (list, tuple)):
        return list(raw)
    return list(raw or [])


def _scan_graph_for_pre_bipartite(db: object, graph_name: str) -> list[str]:
    """Return up to 5 capacity-node ids still carrying inputs/outputs; [] if clean."""
    graph = db.select_graph(graph_name)  # type: ignore[attr-defined]
    query = (
        "MATCH (n) "
        "WHERE (n.inputs IS NOT NULL OR n.outputs IS NOT NULL) "
        "AND n.node_type IN $cap_types "
        "RETURN coalesce(n.iri, n.name) "
        "LIMIT 5"
    )
    try:
        res = graph.query(query, {"cap_types": list(CAPACITY_NODE_TYPES)})
    except Exception as exc:
        print(
            f"WARN: probe on graph {graph_name!r} failed: {exc}",
            file=sys.stderr,
        )
        return []
    rows = getattr(res, "result_set", None) or []
    return [str(row[0]) for row in rows if row]


def _print_remediation(findings: dict[str, list[str]]) -> None:
    """Wipe-and-rebootstrap remediation (no persisted Global capacity state at v1)."""
    print(
        "REMEDIATION: Capacity nodes still carry the pre-bipartite "
        "``inputs``/``outputs`` property lists. Per ADR-0156 the bipartite "
        "PRODUCES/CONSUMES IntergraphEdges are the single source of truth; "
        "the v1 CapacityLayer is in-memory-first with no persisted Global "
        "capacity state, so the remediation is wipe-and-rebootstrap, not "
        "in-place rewrite. Steps:",
        file=sys.stderr,
    )
    print(
        "  1. Drain in-flight L3 writes.\n"
        "  2. Drop affected graph(s) via FalkorDB ``GRAPH.DELETE``.\n"
        "  3. Re-bootstrap + re-run the ``install_*`` capacity installers; "
        "    the bipartite ``register_capacity`` emits produces/consumes "
        "    edges and omits inputs/outputs from node properties.\n"
        "  4. Re-run this detector — exit 0 confirms clean state.",
        file=sys.stderr,
    )
    print("Findings per graph:", file=sys.stderr)
    for graph_name, ids in findings.items():
        print(f"  {graph_name}: {ids}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_phase_42_bipartite_state",
        description=(
            "Phase 42 detector: scan FalkorDB for capacity nodes still "
            "carrying pre-bipartite inputs/outputs property lists. Exit "
            "code 0 = clean state; exit code 1 = pre-bipartite rows found "
            "(stderr prints remediation)."
        ),
    )
    parser.parse_args(argv)

    db = _connect()
    findings: dict[str, list[str]] = {}
    for graph_name in _all_graphs(db):
        if graph_name.startswith("__"):
            continue
        hits = _scan_graph_for_pre_bipartite(db, graph_name)
        if hits:
            findings[graph_name] = hits

    if findings:
        _print_remediation(findings)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
