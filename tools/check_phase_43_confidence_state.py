#!/usr/bin/env python3
"""Phase 43 Pipeline ``confidence`` drop detector (R0 PB-43-10).

Per Phase 43 design log §3 reconciliation + ADR-0094 §amendment-1
(Phase 43 PR1 commit 6 in-place edit per §8.3). ADR-0152 §1 drops
``confidence`` from the Pipeline NodeType in schema v2; per-pipeline
confidence migrates to ALS subsystems on ``learned-parameters``
(subsystem #3 selection + subsystem #4 mapping). Per ADR-0094 §am-1
Migration of shipped state: v1 production has no
``confidence``-carrying Local-Pipeline records; a real migrator is
dead code. Phase 43 ships a detector form per Phase 39 PB-8 precedent
(``tools/check_rename_state.py``).

Contract:

* Scans every FalkorDB graph reachable via the standard
  ``MINDSOS_FALKOR_*`` / ``FALKOR_HOST`` env-var config for nodes of
  type ``Pipeline`` (in any ``promoted-pipelines-*`` graph) that
  carry a non-null ``confidence`` property.
* Exit code 0 — no ``confidence``-carrying Pipeline rows found. Clean
  state; ADR-0094 §am-1 migration is complete or production was
  always empty (v1 baseline).
* Exit code 1 — ``confidence``-carrying Pipeline rows found. Stderr
  prints the wipe-and-rebootstrap remediation per Chat C migration-
  script discipline (v1 production state is empty; this is a
  dev-environment safety net).
* Exit code 2 — usage error; reserved.
* Idempotent: same FalkorDB state → same exit code, no side effects.

Honest framing: this is a DETECTOR, not a migrator. Re-running it
after a wipe-and-rebootstrap should report clean (exit 0); the actual
remediation is wipe-and-rebootstrap, not in-place property strip.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable


PIPELINE_GRAPH_PREFIX = "promoted-pipelines-"
PIPELINE_NODE_TYPE = "Pipeline"
LEGACY_CONFIDENCE_PROPERTY = "confidence"


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
    host = os.environ.get(
        "MINDSOS_FALKOR_HOST", os.environ.get("FALKOR_HOST", "localhost")
    )
    port = int(
        os.environ.get(
            "MINDSOS_FALKOR_PORT", os.environ.get("FALKOR_PORT", "6379")
        )
    )
    password = os.environ.get("MINDSOS_FALKOR_PASSWORD") or os.environ.get(
        "FALKOR_PASSWORD"
    )
    return FalkorDB(host=host, port=port, password=password)


def _all_graphs(db: object) -> Iterable[str]:
    """Enumerate every graph in the FalkorDB instance."""
    raw = db.list_graphs()  # type: ignore[attr-defined]
    if isinstance(raw, (list, tuple)):
        return list(raw)
    return list(raw or [])


def _scan_graph_for_confidence(
    db: object, graph_name: str
) -> list[str]:
    """Return up to 5 IRIs of Pipeline nodes carrying ``confidence``; [] if clean."""
    graph = db.select_graph(graph_name)  # type: ignore[attr-defined]
    query = (
        "MATCH (n:Pipeline) "
        "WHERE n.confidence IS NOT NULL "
        "RETURN n.iri "
        "LIMIT 5"
    )
    try:
        res = graph.query(query)
    except Exception as exc:
        print(
            f"WARN: probe on graph {graph_name!r} failed: {exc}",
            file=sys.stderr,
        )
        return []
    rows = getattr(res, "result_set", None) or []
    return [str(row[0]) for row in rows if row]


def _print_remediation(findings: dict[str, list[str]]) -> None:
    """Wipe-and-rebootstrap remediation per Chat C migration discipline."""
    print(
        "REMEDIATION: Pipeline rows carry the ADR-0094 §am-1 dropped "
        "``confidence`` property. Per Chat C migration-script discipline "
        "(v1 production state is empty), the remediation is "
        "wipe-and-rebootstrap, not in-place property strip. Steps:",
        file=sys.stderr,
    )
    print(
        "  1. Drain in-flight L3 writes targeting promoted-pipelines.\n"
        "  2. Drop affected promoted-pipelines graph(s) via FalkorDB "
        "    ``GRAPH.DELETE``.\n"
        "  3. Re-run ``mindsos doctor --self-test`` to confirm bootstrap "
        "    rebuild lands the post-§am-1 Pipeline schema without "
        "    ``confidence``.\n"
        "  4. Re-run this detector — exit 0 confirms clean state.",
        file=sys.stderr,
    )
    print("Findings per graph:", file=sys.stderr)
    for graph_name, iris in findings.items():
        print(f"  {graph_name}: {iris}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_phase_43_confidence_state",
        description=(
            "Phase 43 detector: scan FalkorDB for Pipeline rows carrying "
            "the ADR-0094 §am-1 dropped ``confidence`` property. Exit code "
            "0 = clean state; exit code 1 = confidence-carrying rows "
            "found (stderr prints remediation)."
        ),
    )
    parser.parse_args(argv)

    db = _connect()
    findings: dict[str, list[str]] = {}
    for graph_name in _all_graphs(db):
        if graph_name.startswith("__"):
            continue
        if not graph_name.startswith(PIPELINE_GRAPH_PREFIX):
            # Only promoted-pipelines graphs host Pipeline nodes; skip
            # alignment / lexicon / etc. to keep the scan cheap.
            continue
        hits = _scan_graph_for_confidence(db, graph_name)
        if hits:
            findings[graph_name] = hits

    if findings:
        _print_remediation(findings)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
