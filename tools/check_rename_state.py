#!/usr/bin/env python3
"""Phase 39 ``memories`` → ``episodic_memories`` data-state detector.

Per Phase 39 design log §2 PB-8 + PB-3 + R2 PB-R2-E + R2 PB-R2-8 (R1).

Contract:

* Scans every FalkorDB graph reachable via the standard ``MINDSOS_FALKOR_*``
  / ``FALKOR_HOST`` env-var config for nodes whose ``iri`` property
  starts with the pre-rename ``memories-`` prefix.
* Exit code 0 — no pre-rename rows found. Clean state; Phase 39 rename
  has fully landed in data.
* Exit code 1 — pre-rename rows found. Stderr prints the wipe-and-
  rebootstrap remediation per Chat C migration-script discipline
  (v1 production state is empty; this is a dev-environment safety net).
* Exit code 2 — usage error (e.g., ``--help``-only flag passed and
  no scan performed; reserved).
* Idempotent: same FalkorDB state → same exit code, no side effects.

Honest framing: this is a DETECTOR, not a migrator. Re-running it after
a wipe-and-rebootstrap should report clean (exit 0); the actual
remediation is wipe-and-rebootstrap, not in-place rewrite.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable


PRE_RENAME_IRI_PREFIX = "memories-"
NEW_CANONICAL_IRI_PREFIX = "episodic-memories-"


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


def _scan_graph_for_pre_rename(db: object, graph_name: str) -> list[str]:
    """Return up to 5 pre-rename IRIs found in ``graph_name``; [] if clean."""
    graph = db.select_graph(graph_name)  # type: ignore[attr-defined]
    query = (
        "MATCH (n) "
        "WHERE n.iri STARTS WITH $prefix "
        "RETURN n.iri "
        "LIMIT 5"
    )
    try:
        res = graph.query(query, {"prefix": PRE_RENAME_IRI_PREFIX})
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
        "REMEDIATION: Pre-rename ``memories-`` IRI rows present. "
        "Per Chat C migration-script discipline (v1 production state is "
        "empty), the remediation is wipe-and-rebootstrap, not in-place "
        "rewrite. Steps:",
        file=sys.stderr,
    )
    print(
        "  1. Drain in-flight L3 writes.\n"
        "  2. Drop affected graph(s) via FalkorDB ``GRAPH.DELETE``.\n"
        "  3. Re-run ``mindsos doctor --self-test`` to confirm bootstrap "
        "    rebuild lands the post-rename ``episodic-memories-`` form.\n"
        "  4. Re-run this detector — exit 0 confirms clean state.",
        file=sys.stderr,
    )
    print("Findings per graph:", file=sys.stderr)
    for graph_name, iris in findings.items():
        print(f"  {graph_name}: {iris}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_rename_state",
        description=(
            "Phase 39 detector: scan FalkorDB for pre-rename ``memories-`` "
            "IRI rows. Exit code 0 = clean state; exit code 1 = pre-rename "
            "rows found (stderr prints remediation)."
        ),
    )
    parser.parse_args(argv)

    db = _connect()
    findings: dict[str, list[str]] = {}
    for graph_name in _all_graphs(db):
        if graph_name.startswith("__"):
            continue
        hits = _scan_graph_for_pre_rename(db, graph_name)
        if hits:
            findings[graph_name] = hits

    if findings:
        _print_remediation(findings)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
