"""`mindsos knowledge` — Phase 12 + Phase 13 L2 Knowledge CLI surface.

Sub-subgroup shape (Phase 12 PB-16; Phase 13 PB-6 extension):

  mindsos knowledge iri build --role R --version V [...] [--json]
  mindsos knowledge iri parse <iri> [--json]
  mindsos knowledge iri validate <iri> [--json]
  mindsos knowledge ref-types --list [--json]
  mindsos knowledge roles --list [--json] [--seed-only|--upper-only]

Phase 13 additions:

  mindsos knowledge schema show --role <role> [--json]
      Print the role schema's NodeTypes / EdgeTypes / HyperEdgeTypes
      / strict flag. Handles ``alignment:<a>:<b>`` prefix.

  mindsos knowledge schema validate --role <role> --graph-file <path>
                                    [--json] [--exit-zero]
      Load a graph state-file, build the role schema, run L1 structural
      validation (NodeType registration + EdgeType endpoint type check
      + HyperEdgeType member type check). Phase 13 ships the structural
      pass only; semantic validation (cross-role refs etc.) ships in
      Phase 36 (ADR-0139). Exit 1 on violation; ``--exit-zero``
      surfaces violations in JSON without failing exit code.

Phase 13 CLI uses canonical state-file keys ``node_id`` / ``edge_id``
per `feedback_state_file_key_canonicalization.md` (B-11-T2 lock).

Exit-code policy (parity with prior phases):
* exit 0 — success
* exit 1 — domain error (`RefFormatError`, `UnknownRoleError`,
           schema-validation violation, missing state-file, ...)
* exit 2 — usage error (missing required arg, bad role, ...)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from mindsos_core import UnknownTypeError

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
    UnknownRoleError,
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
    schema_for_role,
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

# Phase 13 — schema sub-subgroup per PB-6.
schema_app = typer.Typer(
    name="schema",
    help="Show or validate a role-graph schema (Phase 13).",
    no_args_is_help=True,
    add_completion=False,
)
knowledge_app.add_typer(schema_app, name="schema")


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


# ── schema show ────────────────────────────────────────────────────────


@schema_app.command(
    name="show", help="Print the role-graph schema (NodeTypes / EdgeTypes / HyperEdgeTypes)."
)
def schema_show_cmd(
    role: str = typer.Option(
        ..., "--role", help="Role name; or 'alignment:<a>:<b>' for an alignment graph."
    ),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    try:
        schema = schema_for_role(role)
    except UnknownRoleError as exc:
        typer.echo(f"UnknownRoleError: {exc}", err=True)
        raise typer.Exit(code=1)

    payload = {
        "role": role,
        "strict": schema.strict,
        "node_types": sorted(schema.node_types),
        "edge_types": sorted(schema.edge_types),
        "hyperedge_types": sorted(schema.hyperedge_types),
    }
    if json_out:
        typer.echo(json.dumps(payload, indent=2))
        return

    typer.echo(f"role            {role}")
    typer.echo(f"strict          {schema.strict}")
    typer.echo(f"node_types      ({len(payload['node_types'])}) " + ", ".join(payload["node_types"]))
    typer.echo(f"edge_types      ({len(payload['edge_types'])}) " + ", ".join(payload["edge_types"]))
    typer.echo(
        f"hyperedge_types ({len(payload['hyperedge_types'])}) "
        + ", ".join(payload["hyperedge_types"])
    )


# ── schema validate ────────────────────────────────────────────────────


def _load_graph_state(path: Path) -> dict:
    """Load a graph state-file. Phase 13 — structural validation only."""
    if not path.exists():
        typer.echo(f"State file not found: {path}", err=True)
        raise typer.Exit(code=1)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        typer.echo(f"State file is not valid JSON: {exc}", err=True)
        raise typer.Exit(code=1)


def _structural_validate(schema, state: dict) -> list[dict]:
    """Run the L1 structural pass over a state-file dict.

    Canonical state-file keys per ``feedback_state_file_key_canonicalization.md``:
    ``node_id``, ``edge_id``, ``source_id``, ``target_id``, ``type_name``,
    ``member_ids``. Phase 13 ships structural-only; Phase 36 adds semantic.

    Returns a list of violation dicts.
    """
    violations: list[dict] = []

    # Build node-id → type_name lookup for edge endpoint checks. Use
    # canonical ``node_id`` key per B-11-T2 lock.
    node_type_by_id: dict[str, str] = {}
    for n in state.get("nodes") or []:
        nid = n["node_id"]
        tname = n["type_name"]
        node_type_by_id[nid] = tname
        if tname not in schema.node_types:
            violations.append(
                {
                    "kind": "unknown_node_type",
                    "node_id": nid,
                    "type_name": tname,
                }
            )

    for e in state.get("edges") or []:
        eid = e["edge_id"]
        et = e["type_name"]
        if et not in schema.edge_types:
            violations.append(
                {"kind": "unknown_edge_type", "edge_id": eid, "type_name": et}
            )
            continue
        src_tn = node_type_by_id.get(e["source_id"])
        tgt_tn = node_type_by_id.get(e["target_id"])
        if src_tn is None or tgt_tn is None:
            violations.append(
                {
                    "kind": "dangling_endpoint",
                    "edge_id": eid,
                    "source_id": e["source_id"],
                    "target_id": e["target_id"],
                }
            )
            continue
        try:
            schema.validate_edge(et, src_tn, tgt_tn)
        except UnknownTypeError as exc:
            violations.append(
                {
                    "kind": "edge_endpoint_mismatch",
                    "edge_id": eid,
                    "type_name": et,
                    "source_type": src_tn,
                    "target_type": tgt_tn,
                    "detail": str(exc),
                }
            )

    for h in state.get("hyperedges") or []:
        heid = h["edge_id"]
        het = h.get("type_name") or "UNSPECIFIED"
        if het not in schema.hyperedge_types:
            violations.append(
                {
                    "kind": "unknown_hyperedge_type",
                    "edge_id": heid,
                    "type_name": het,
                }
            )
            continue
        member_types: list[str] = []
        dangling = False
        for mid in h.get("member_ids") or []:
            mtn = node_type_by_id.get(mid)
            if mtn is None:
                dangling = True
                break
            member_types.append(mtn)
        if dangling:
            violations.append(
                {
                    "kind": "hyperedge_dangling_member",
                    "edge_id": heid,
                    "members": h.get("member_ids") or [],
                }
            )
            continue
        try:
            schema.validate_hyperedge(het, member_types)
        except UnknownTypeError as exc:
            violations.append(
                {
                    "kind": "hyperedge_member_mismatch",
                    "edge_id": heid,
                    "type_name": het,
                    "member_types": member_types,
                    "detail": str(exc),
                }
            )

    return violations


@schema_app.command(
    name="validate",
    help=(
        "Validate a graph state-file against the role schema. "
        "Phase 13 ships L1 structural validation only — semantic checks "
        "(cross-role refs etc.) ship in Phase 36 per ADR-0139."
    ),
)
def schema_validate_cmd(
    role: str = typer.Option(
        ..., "--role", help="Role name; or 'alignment:<a>:<b>' for an alignment graph."
    ),
    graph_file: Path = typer.Option(
        ..., "--graph-file", help="Path to a graph state-file (JSON)."
    ),
    json_out: bool = typer.Option(False, "--json"),
    exit_zero: bool = typer.Option(
        False, "--exit-zero", help="Surface violations in output but exit 0."
    ),
) -> None:
    try:
        schema = schema_for_role(role)
    except UnknownRoleError as exc:
        typer.echo(f"UnknownRoleError: {exc}", err=True)
        raise typer.Exit(code=1)

    state = _load_graph_state(graph_file)
    violations = _structural_validate(schema, state)

    payload = {
        "role": role,
        "graph_file": str(graph_file),
        "ok": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }
    if json_out:
        typer.echo(json.dumps(payload, indent=2))
    else:
        if not violations:
            typer.echo(f"OK — {role} schema validates {graph_file}")
        else:
            typer.echo(
                f"VIOLATIONS — {role} schema rejects {graph_file} "
                f"({len(violations)} violations)"
            )
            for v in violations:
                typer.echo(f"  - {v['kind']}: {v}")

    if violations and not exit_zero:
        raise typer.Exit(code=1)


# ── Phase 17 retirement — versions enumerator ──────────────────────────
#
# `mindsos knowledge versions [--role R]` — per ADR-0150 §amendment-3.
# IRI-scan: walks the named role-graph (or all role-graphs when
# `--role` omitted) of a metagraph state-file and reports the distinct
# `parse_iri(node_id).version` values observed.
#
# Phase 14 PB-13 commitment partially closed: `versions` shipped;
# `active-version` verb dropped per PB-15 vacuum (no graph-level
# active-version state to surface).


def _load_metagraph_or_die(name: str):
    """Load + rehydrate a metagraph state-file by NAME.

    Mirrors :func:`mindsos_cli.commands.admin._load_metagraph_or_die`.
    Lazy import to keep CLI startup cheap when `versions` isn't called.
    """
    from mindsos_cli.commands.metagraph import _load_or_die

    return _load_or_die(name)


@knowledge_app.command(
    name="versions",
    help=(
        "Enumerate distinct IRI-string versions present in a "
        "metagraph's role-graph(s). Per ADR-0150 §amendment-3 — "
        "version lives in IRI strings, not in graph-layer state."
    ),
)
def knowledge_versions(
    metagraph: str = typer.Option(
        ...,
        "--metagraph",
        "-m",
        help=(
            "Metagraph state-file NAME (loaded from "
            "${MINDSOS_STATE_DIR or ~/.mindsos}/metagraph-<name>.json)."
        ),
    ),
    role: Optional[str] = typer.Option(
        None,
        "--role",
        "-r",
        help=(
            "Optional role filter (e.g. 'ontology'). Omit to enumerate "
            "every role-graph in the metagraph."
        ),
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Emit `{role: [versions]}` as JSON to stdout.",
    ),
) -> None:
    from mindsos_knowledge.metagraph_view import MetagraphView

    mg = _load_metagraph_or_die(metagraph)
    view = MetagraphView(mg)
    roles_to_scan = sorted(view.roles()) if role is None else [role]

    out: dict[str, list[str]] = {}
    for r in roles_to_scan:
        out[r] = sorted(view.versions_in_role(r))

    if as_json:
        typer.echo(json.dumps(out, indent=2, sort_keys=True))
    else:
        for r in roles_to_scan:
            versions = out[r]
            if versions:
                typer.echo(f"{r}: {', '.join(versions)}")
            else:
                typer.echo(f"{r}: (no version-qualified IRIs)")


# ── registration ──────────────────────────────────────────────────────


def register_knowledge_app(parent: typer.Typer) -> None:
    """Wire the knowledge sub-app onto a parent Typer app."""
    parent.add_typer(knowledge_app, name="knowledge")
