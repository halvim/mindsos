"""`mindsos admin` — Phase 15a Admin Layer CLI surface.

Sub-subgroup shape (Phase 15a PB-4a / PB-10 lock):

  mindsos admin import dolce --source PATH [--version V] [--json]
  mindsos admin import oewn --source PATH [--version V] [--json]
  mindsos admin import framenet --source PATH [--version V] [--json]

Each verb instantiates a fresh :class:`~mindsos_core.Metagraph` via
:func:`mindsos_admin.bootstrap_global`, runs the requested importer,
and prints the :class:`~mindsos_admin.ImportResult` (text by default;
JSON on ``--json``).

Phase 15a does NOT persist the resulting Metagraph — per ADR-0043
(Accepted), I/O is the server's responsibility. The CLI verbs are
admin-side dry-runs producing an ImportResult summary. State-file
persistence of the imported Global is deferred to Phase 26 per Phase
14a round-3 lock; server-driven persistence ships at Phase 18+.

Phase 15b will add:
  mindsos admin import alignments --pairs P1,P2[,...] [--json]
  mindsos admin scan-schema [--role R] [--json]

Exit-code policy (parity with prior phases):
* exit 0 — success
* exit 1 — domain error (parse error, source missing, IRI builder
           rejection, ...)
* exit 2 — usage error (missing required arg)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from mindsos_admin import (
    DolceImporter,
    FrameNetImporter,
    ImportResult,
    OewnImporter,
    bootstrap_global,
)
from mindsos_knowledge import KnowledgeError


admin_app = typer.Typer(
    name="admin",
    help=(
        "L2 Admin operations — importers (Phase 15a: dolce/oewn/framenet); "
        "Phase 15b adds alignments + scan-schema; Phase 16 adds promotion."
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


def register_admin_app(parent: typer.Typer) -> None:
    """Wire `mindsos admin` into the top-level Typer app."""
    parent.add_typer(admin_app, name="admin")
