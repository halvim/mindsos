"""`mindsos admin` — Phase 15a + Phase 16 Admin Layer CLI surface.

Sub-subgroup shape (Phase 15a PB-4a / PB-10 lock + Phase 16 PB-I1):

  mindsos admin import dolce --source PATH [--version V] [--json]
  mindsos admin import oewn --source PATH [--version V] [--json]
  mindsos admin import framenet --source PATH [--version V] [--json]
  mindsos admin promote list --metagraph NAME --role ROLE
                             [--node-type TYPE] [--json]
  mindsos admin promote similarity --metagraph NAME --role ROLE
                             [--node-type TYPE]
                             [--threshold-blocking F] [--threshold-review F]
                             [--json]

Import verbs (Phase 15a) instantiate a fresh
:class:`~mindsos_core.Metagraph` via :func:`mindsos_admin.bootstrap_global`,
run the requested importer, and print the
:class:`~mindsos_admin.ImportResult` (text by default; JSON on ``--json``).

Phase 15a does NOT persist the resulting Metagraph — per ADR-0043
(Accepted), I/O is the server's responsibility. The CLI verbs are
admin-side dry-runs producing an ImportResult summary. State-file
persistence of the imported Global is deferred to Phase 26 per Phase
14a round-3 lock; server-driven persistence ships at Phase 18+.

Promote verbs (Phase 16 — read-only) consume an EXISTING metagraph
state-file (loaded via :func:`mindsos_cli.state.load_metagraph_state` —
the Phase 09 reader). Per Phase 16 PB-I1, the CLI source is a
state-file (looked up by ``--metagraph NAME`` in ``~/.mindsos/``
following Phase 03+ convention). FalkorDB-direct sources defer to
Phase 26 alongside the state-file write surface.

Phase 16 does NOT ship a ``promote propose`` verb — the mutating
entry-point ``propose_for_promotion`` defers to Phase 24 per Phase 16
PB-1c reframe (the original PHASE_MAP §16 ``propose`` verb is
deferred alongside ``mindsos_admin/promotion.py``).

Phase 15b will add:
  mindsos admin import alignments --pairs P1,P2[,...] [--json]
  mindsos admin scan-schema [--role R] [--json]

Exit-code policy (parity with prior phases):
* exit 0 — success
* exit 1 — domain error (parse error, source missing, IRI builder
           rejection, similarity input mismatch, ...)
* exit 2 — usage error (missing required arg, state-file not found,
           role unknown to schema dispatch).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from mindsos_admin import (
    CandidateRef,
    DolceImporter,
    EmptyComparisonError,
    FrameNetImporter,
    ImportResult,
    OewnImporter,
    SimilarityReport,
    bootstrap_global,
    compute_similarity,
    list_candidates,
)
from mindsos_knowledge import KnowledgeError


admin_app = typer.Typer(
    name="admin",
    help=(
        "L2 Admin operations — importers (Phase 15a: dolce/oewn/framenet) "
        "+ promote read-only surface (Phase 16: list/similarity); "
        "Phase 15b adds alignments + scan-schema; Phase 24 adds promote propose."
    ),
    no_args_is_help=True,
    add_completion=False,
)

import_app = typer.Typer(
    name="import",
    help="Run a knowledge-source importer against a pinned dataset.",
    no_args_is_help=True,
    add_completion=False,
)
admin_app.add_typer(import_app, name="import")


def _emit(result: ImportResult, *, as_json: bool) -> None:
    """Print an ImportResult — JSON on ``as_json``, text otherwise."""
    if as_json:
        typer.echo(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        typer.echo(f"role={result.role}")
        typer.echo(f"version={result.version}")
        typer.echo(f"source={result.source}")
        typer.echo(f"imported_at={result.imported_at.isoformat()}")
        typer.echo("stats:")
        for key in sorted(result.stats):
            typer.echo(f"  {key}={result.stats[key]}")


def _run_single_importer(importer: object, source: Path) -> ImportResult:
    """Build a fresh Global with 6 named role-graphs ensured (PB-21
    parity with ``KnowledgeLayer.bootstrap()``); run the importer
    against it; return the :class:`ImportResult`.

    The Metagraph is discarded after the call (Phase 15a is dry-run;
    server persistence ships at Phase 18+ per ADR-0043).

    Phase 15a calibration: ``bootstrap_global([importer])`` returns
    only the populated Metagraph (no per-importer ImportResult). CLI
    callers want the result, so we use ``bootstrap_global(importers=())``
    for the 6-role Metagraph and call ``importer.run(mg, source)``
    explicitly. Phase 15b may add a ``bootstrap_global`` overload
    returning per-importer results.
    """
    mg = bootstrap_global(importers=())  # empty mg with 6 named roles ensured
    return importer.run(mg, source)  # type: ignore[attr-defined,no-any-return]


@import_app.command(
    name="dolce",
    help="Import DOLCE-DUL OWL into the `ontology` Global role-graph.",
)
def import_dolce(
    source: Path = typer.Option(
        ...,
        "--source",
        "-s",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to a DOLCE OWL file (RDF/XML, Turtle, etc.).",
    ),
    version: str = typer.Option(
        "4.1",
        "--version",
        "-v",
        help="Dataset version string. Default Phase 15a PB-6 pin (4.1).",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Emit ImportResult as JSON to stdout.",
    ),
) -> None:
    importer = DolceImporter(source=source, version=version)
    try:
        result = _run_single_importer(importer, source)
    except (KnowledgeError, ValueError, FileNotFoundError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1)
    _emit(result, as_json=as_json)


@import_app.command(
    name="oewn",
    help="Import Open English WordNet LMF into the `lexicon` Global role-graph.",
)
def import_oewn(
    source: Path = typer.Option(
        ...,
        "--source",
        "-s",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to an OEWN-LMF XML file.",
    ),
    version: str = typer.Option(
        "2024",
        "--version",
        "-v",
        help="Dataset version string. Default Phase 15a PB-6 pin (2024).",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Emit ImportResult as JSON to stdout.",
    ),
) -> None:
    importer = OewnImporter(source=source, version=version)
    try:
        result = _run_single_importer(importer, source)
    except (KnowledgeError, ValueError, FileNotFoundError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1)
    _emit(result, as_json=as_json)


@import_app.command(
    name="framenet",
    help="Import FrameNet XML (single-file or Berkeley dir layout) into `concepts`.",
)
def import_framenet(
    source: Path = typer.Option(
        ...,
        "--source",
        "-s",
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
        help=(
            "Path to a FrameNet XML file (synthetic single-file fixture) "
            "OR a directory containing `frame/*.xml` + `frRelation.xml` "
            "(Berkeley FrameNet 1.7 distribution layout)."
        ),
    ),
    version: str = typer.Option(
        "1.7",
        "--version",
        "-v",
        help="Dataset version string. Default Phase 15a PB-6 pin (1.7).",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Emit ImportResult as JSON to stdout.",
    ),
) -> None:
    importer = FrameNetImporter(source=source, version=version)
    try:
        result = _run_single_importer(importer, source)
    except (KnowledgeError, ValueError, FileNotFoundError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1)
    _emit(result, as_json=as_json)


# ── §Phase 16 — `mindsos admin promote` subgroup ───────────────────────


promote_app = typer.Typer(
    name="promote",
    help=(
        "Read-only similarity surface (Phase 16). "
        "`list` enumerates promotion candidates; `similarity` computes "
        "the ADR-0144 §Heuristic SimilarityReport. The mutating "
        "`propose` verb defers to Phase 24 per Phase 16 PB-1c."
    ),
    no_args_is_help=True,
    add_completion=False,
)
admin_app.add_typer(promote_app, name="promote")


def _load_metagraph_or_die(name: str):
    """Load + rehydrate a metagraph state-file by NAME.

    Mirrors :func:`mindsos_cli.commands.metagraph._load_or_die`. We
    import lazily to avoid CLI startup overhead when promote verbs
    aren't invoked.
    """
    from mindsos_cli.commands.metagraph import _load_or_die

    return _load_or_die(name)


def _emit_candidates(refs: list, *, as_json: bool) -> None:
    """Print a list of :class:`CandidateRef` — JSON on ``as_json``, text otherwise."""
    if as_json:
        payload = [
            {
                "node_id": r.node_id,
                "role": r.role,
                "node_type": r.node_type,
                "source_user_id": r.source_user_id,
            }
            for r in refs
        ]
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
    else:
        typer.echo(f"candidates={len(refs)}")
        for r in refs:
            typer.echo(f"  {r.node_type:24} {r.node_id}")


def _emit_similarity_report(report: SimilarityReport, *, as_json: bool) -> None:
    """Print a :class:`SimilarityReport` — JSON on ``as_json``, text otherwise."""
    if as_json:
        typer.echo(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        typer.echo(f"report_id={report.report_id}")
        typer.echo(f"threshold_blocking={report.threshold_blocking}")
        typer.echo(f"threshold_review={report.threshold_review}")
        typer.echo(f"findings={len(report.findings)}")
        for f in report.findings:
            tag = "[inter-candidate]" if f.matched_is_candidate else ""
            typer.echo(
                f"  {f.classification:8} score={f.score:.6f} "
                f"{f.candidate_id} -> {f.matched_id} {tag}".rstrip()
            )


@promote_app.command(
    name="list",
    help=(
        "Enumerate promotion candidates in a metagraph's role-graph. "
        "Default excludes ADR-0051 PROMOTED breadcrumbs."
    ),
)
def promote_list(
    metagraph: str = typer.Option(
        ...,
        "--metagraph",
        "-m",
        help=(
            "Metagraph state-file NAME (loaded from "
            "${MINDSOS_STATE_DIR or ~/.mindsos}/metagraph-<name>.json)."
        ),
    ),
    role: str = typer.Option(
        ...,
        "--role",
        "-r",
        help=(
            "Role-graph to scan (e.g. 'ontology', 'lexicon', 'concepts')."
        ),
    ),
    node_type: Optional[str] = typer.Option(
        None,
        "--node-type",
        "-t",
        help=(
            "Optional NodeType filter (e.g. 'Class', 'Synset', 'Frame'). "
            "Default: include every NodeType in the role-graph."
        ),
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Emit candidates as JSON to stdout.",
    ),
) -> None:
    mg = _load_metagraph_or_die(metagraph)
    try:
        refs = list_candidates(mg, role=role, node_type=node_type)
    except KnowledgeError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1)
    _emit_candidates(refs, as_json=as_json)


@promote_app.command(
    name="similarity",
    help=(
        "Compute the ADR-0144 §Heuristic SimilarityReport for the role's "
        "candidates against existing same-role same-NodeType nodes "
        "(intra-mg at Phase 16; Phase 24 audit gate adds cross-mg)."
    ),
)
def promote_similarity(
    metagraph: str = typer.Option(
        ...,
        "--metagraph",
        "-m",
        help=(
            "Metagraph state-file NAME (loaded from "
            "${MINDSOS_STATE_DIR or ~/.mindsos}/metagraph-<name>.json)."
        ),
    ),
    role: str = typer.Option(
        ...,
        "--role",
        "-r",
        help="Role-graph to scan (e.g. 'ontology', 'lexicon', 'concepts').",
    ),
    node_type: Optional[str] = typer.Option(
        None,
        "--node-type",
        "-t",
        help="Optional NodeType filter (same semantics as `list`).",
    ),
    threshold_blocking: float = typer.Option(
        0.85,
        "--threshold-blocking",
        help="ADR-0144 §Heuristic default; admin-tunable per call.",
    ),
    threshold_review: float = typer.Option(
        0.5,
        "--threshold-review",
        help="ADR-0144 §Heuristic default; admin-tunable per call.",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Emit SimilarityReport as JSON to stdout.",
    ),
) -> None:
    mg = _load_metagraph_or_die(metagraph)
    try:
        candidates = list_candidates(mg, role=role, node_type=node_type)
        report = compute_similarity(
            mg,
            candidates,
            role=role,
            threshold_blocking=threshold_blocking,
            threshold_review=threshold_review,
        )
    except EmptyComparisonError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1)
    except KnowledgeError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1)
    _emit_similarity_report(report, as_json=as_json)


def register_admin_app(parent: typer.Typer) -> None:
    """Wire `mindsos admin` into the top-level Typer app."""
    parent.add_typer(admin_app, name="admin")
