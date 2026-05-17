"""`mindsos knowledge` — Phase 12 L2 Knowledge CLI surface.

Sub-subgroup shape (locked in PB-16):

  mindsos knowledge iri build --role R --version V [...] [--json]
      Build an IRI for the given role + kwargs. Per-role kwarg surface
      mirrors the underlying builder signatures (PB-9 / PB-2 lock).

  mindsos knowledge iri parse <iri> [--json]
      Decompose an IRI into role / source / version / kind / body.

  mindsos knowledge iri validate <iri> [--json]
      Yes/no probe for `is_version_qualified_iri`.

  mindsos knowledge ref-types --list [--json]
      Enumerate REF_TYPES (ADR-0047 open vocabulary).

  mindsos knowledge roles --list [--json] [--seed-only|--upper-only]
      Enumerate role constants split by SEED_ROLES vs UPPER_LAYER_ROLES.

Exit-code policy (parity with prior phases):
* exit 0 — success
* exit 1 — domain error (`RefFormatError`, unknown role, etc.)
* exit 2 — usage error (missing required arg, bad role, bad --kind etc.)
"""

from __future__ import annotations

import json
import sys
from typing import Optional

import typer

from mindsos_knowledge import (
    ALL_ROLES,
    REF_TYPES,
    ROLE_CAPACITY_STATE,
    ROLE_CONCEPTS,
    ROLE_LEXICON,
    ROLE_MEMORIES,
    ROLE_ONTOLOGY,
    ROLE_PROBLEM_TRACE,
    ROLE_PROMOTED_PIPELINES,
    ROLE_TASK_PATTERNS,
    RefFormatError,
    SEED_ROLES,
    UPPER_LAYER_ROLES,
    capacity_snapshot_iri,
    dolce_iri,
    framenet_fe_iri,
    framenet_frame_iri,
    framenet_lu_iri,
    is_version_qualified_iri,
    memory_iri,
    oewn_lemma_iri,
    oewn_sense_iri,
    oewn_synset_iri,
    parse_iri,
    pipeline_iri,
    pipeline_step_iri,
    problem_trace_iri,
    subgoal_template_iri,
    task_pattern_iri,
)


knowledge_app = typer.Typer(
    name="knowledge",
    help=(
        "L2 Knowledge primitives — build / parse / validate IRIs, "
        "enumerate REF_TYPES + roles."
    ),
    no_args_is_help=True,
    add_completion=False,
)

iri_app = typer.Typer(
    name="iri",
    help="Build, parse, or validate a version-qualified L2 IRI.",
    no_args_is_help=True,
    add_completion=False,
)
knowledge_app.add_typer(iri_app, name="iri")


# ── builder dispatch table ─────────────────────────────────────────────
# Each row: role → (builder, required-kwargs tuple).
# CLI maps `--<kwarg>` flags into the builder's positional kwargs.

_BUILDERS = {
    ROLE_ONTOLOGY: (dolce_iri, ("version", "fragment")),
    ROLE_LEXICON: {  # multi-kind role
        "synset": (oewn_synset_iri, ("version", "synset-id", "pos")),
        "sense": (oewn_sense_iri, ("version", "sense-id")),
        "lemma": (oewn_lemma_iri, ("version", "lemma", "pos")),
    },
    ROLE_CONCEPTS: {
        "frame": (framenet_frame_iri, ("version", "frame-id")),
        "lu": (framenet_lu_iri, ("version", "lu-id")),
        "fe": (framenet_fe_iri, ("version", "frame-id", "fe-id")),
    },
    ROLE_PROMOTED_PIPELINES: {
        "pipeline": (pipeline_iri, ("version", "pipeline-id")),
        "step": (pipeline_step_iri, ("version", "pipeline-id", "step-id")),
    },
    ROLE_TASK_PATTERNS: {
        "pattern": (task_pattern_iri, ("version", "pattern-id")),
        "subgoal": (
            subgoal_template_iri,
            ("version", "pattern-id", "subgoal-id"),
        ),
    },
    ROLE_MEMORIES: {
        "memory": (memory_iri, ("version", "user-id", "memory-id")),
    },
    ROLE_PROBLEM_TRACE: {
        "entry": (problem_trace_iri, ("version", "trace-id")),
    },
    ROLE_CAPACITY_STATE: {
        "snapshot": (
            capacity_snapshot_iri,
            ("version", "user-id", "capacity-iri", "taken-at"),
        ),
    },
}


def _kwarg_to_attr(name: str) -> str:
    """`'pipeline-id'` → `'pipeline_id'`."""
    return name.replace("-", "_")


# ── iri build ──────────────────────────────────────────────────────────


@iri_app.command(name="build", help="Build a version-qualified IRI for the given role.")
def iri_build_cmd(
    role: str = typer.Option(..., "--role", help="One of ALL_ROLES."),
    kind: Optional[str] = typer.Option(
        None,
        "--kind",
        help="Sub-kind for multi-kind roles (e.g. synset / pipeline / snapshot).",
    ),
    version: Optional[str] = typer.Option(None, "--version"),
    fragment: Optional[str] = typer.Option(None, "--fragment"),
    synset_id: Optional[str] = typer.Option(None, "--synset-id"),
    sense_id: Optional[str] = typer.Option(None, "--sense-id"),
    lemma: Optional[str] = typer.Option(None, "--lemma"),
    pos: Optional[str] = typer.Option(None, "--pos"),
    frame_id: Optional[str] = typer.Option(None, "--frame-id"),
    lu_id: Optional[str] = typer.Option(None, "--lu-id"),
    fe_id: Optional[str] = typer.Option(None, "--fe-id"),
    pipeline_id: Optional[str] = typer.Option(None, "--pipeline-id"),
    step_id: Optional[str] = typer.Option(None, "--step-id"),
    pattern_id: Optional[str] = typer.Option(None, "--pattern-id"),
    subgoal_id: Optional[str] = typer.Option(None, "--subgoal-id"),
    user_id: Optional[str] = typer.Option(None, "--user-id"),
    memory_id: Optional[str] = typer.Option(None, "--memory-id"),
    trace_id: Optional[str] = typer.Option(None, "--trace-id"),
    capacity_iri: Optional[str] = typer.Option(None, "--capacity-iri"),
    taken_at: Optional[str] = typer.Option(None, "--taken-at"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    if role not in ALL_ROLES:
        typer.echo(
            f"Unknown role {role!r}; expected one of {sorted(ALL_ROLES)}.",
            err=True,
        )
        raise typer.Exit(code=2)

    spec = _BUILDERS[role]

    if isinstance(spec, dict):
        # Multi-kind role.
        if kind is None:
            typer.echo(
                f"Role {role!r} requires --kind (one of {sorted(spec)}).",
                err=True,
            )
            raise typer.Exit(code=2)
        if kind not in spec:
            typer.echo(
                f"Unknown --kind {kind!r} for role {role!r}; "
                f"expected one of {sorted(spec)}.",
                err=True,
            )
            raise typer.Exit(code=2)
        builder, kwargs = spec[kind]
    else:
        if kind is not None:
            typer.echo(
                f"Role {role!r} has no sub-kind; drop --kind.",
                err=True,
            )
            raise typer.Exit(code=2)
        builder, kwargs = spec

    # Resolve the kwarg values from CLI flags. All locals are in scope.
    flags = locals()
    args = []
    missing = []
    for k in kwargs:
        attr = _kwarg_to_attr(k)
        val = flags.get(attr)
        if val is None:
            missing.append(f"--{k}")
        args.append(val)
    if missing:
        typer.echo(
            f"Missing required flag(s) for role={role}"
            + (f" kind={kind}" if kind else "")
            + f": {' '.join(missing)}",
            err=True,
        )
        raise typer.Exit(code=2)

    try:
        iri = builder(*args)
    except RefFormatError as exc:
        typer.echo(f"RefFormatError: {exc}", err=True)
        raise typer.Exit(code=1)

    if json_out:
        typer.echo(json.dumps({"iri": iri, "role": role, "kind": kind}, indent=2))
    else:
        typer.echo(iri)


# ── iri parse ──────────────────────────────────────────────────────────


@iri_app.command(name="parse", help="Decompose a version-qualified IRI.")
def iri_parse_cmd(
    iri: str = typer.Argument(...),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    try:
        parsed = parse_iri(iri)
    except RefFormatError as exc:
        typer.echo(f"RefFormatError: {exc}", err=True)
        raise typer.Exit(code=1)

    payload = {
        "full": parsed.full,
        "role": parsed.role,
        "source": parsed.source,
        "version": parsed.version,
        "kind": parsed.kind,
        "body": parsed.body,
    }
    if json_out:
        typer.echo(json.dumps(payload, indent=2))
    else:
        for key in ("full", "role", "source", "version", "kind", "body"):
            typer.echo(f"{key:<8} {payload[key]!r}")


# ── iri validate ───────────────────────────────────────────────────────


@iri_app.command(
    name="validate", help="Probe is_version_qualified_iri; exit 0 if valid, 1 if not."
)
def iri_validate_cmd(
    iri: str = typer.Argument(...),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    ok = is_version_qualified_iri(iri)
    if json_out:
        typer.echo(json.dumps({"iri": iri, "valid": ok}, indent=2))
    else:
        typer.echo("valid" if ok else "invalid")
    raise typer.Exit(code=0 if ok else 1)


# ── ref-types --list ───────────────────────────────────────────────────


@knowledge_app.command(name="ref-types", help="Enumerate REF_TYPES (ADR-0047).")
def ref_types_cmd(
    list_flag: bool = typer.Option(False, "--list", help="List the vocabulary."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    if not list_flag:
        typer.echo("Missing required flag: --list", err=True)
        raise typer.Exit(code=2)
    payload = sorted(REF_TYPES)
    if json_out:
        typer.echo(json.dumps({"ref_types": payload}, indent=2))
    else:
        for t in payload:
            typer.echo(t)


# ── roles --list ───────────────────────────────────────────────────────


@knowledge_app.command(
    name="roles", help="Enumerate role constants (SEED_ROLES + UPPER_LAYER_ROLES)."
)
def roles_cmd(
    list_flag: bool = typer.Option(False, "--list", help="List the roles."),
    seed_only: bool = typer.Option(False, "--seed-only"),
    upper_only: bool = typer.Option(False, "--upper-only"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    if not list_flag:
        typer.echo("Missing required flag: --list", err=True)
        raise typer.Exit(code=2)
    if seed_only and upper_only:
        typer.echo("--seed-only and --upper-only are mutually exclusive.", err=True)
        raise typer.Exit(code=2)

    if seed_only:
        roles_set = SEED_ROLES
    elif upper_only:
        roles_set = UPPER_LAYER_ROLES
    else:
        roles_set = ALL_ROLES

    if json_out:
        payload = {
            "roles": [
                {"name": r, "tier": "seed" if r in SEED_ROLES else "upper"}
                for r in sorted(roles_set)
            ]
        }
        typer.echo(json.dumps(payload, indent=2))
    else:
        for r in sorted(roles_set):
            tier = "seed" if r in SEED_ROLES else "upper"
            typer.echo(f"{r:<22} {tier}")


# ── registration ──────────────────────────────────────────────────────


def register_knowledge_app(parent: typer.Typer) -> None:
    """Wire the knowledge sub-app onto a parent Typer app."""
    parent.add_typer(knowledge_app, name="knowledge")
