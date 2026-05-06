"""``mindsos metagraph-schema`` — Phase 05b L1 MetagraphSchema subapp.

Subcommands (Phase 05b — Pushback 3-A new top-level subapp parallel to
``mindsos schema``):

  mindsos metagraph-schema create --name <NAME> [--strict] [--json]
  mindsos metagraph-schema inspect --name <NAME> [--json]
  mindsos metagraph-schema list [--json]
  mindsos metagraph-schema reset (--name NAME | --all) [--force] [--yes] [--json]
  mindsos metagraph-schema add-intergraph-edge-type
                                     --schema <NAME> --type-name <TYPE>
                                     [--allowed-source-type <NT>]...
                                     [--allowed-target-type <NT>]...
                                     [--allowed-source-graph <ROLE>]...
                                     [--allowed-target-graph <ROLE>]...
                                     [--prop-type k=<PROPTYPE>]...
                                     [--description STR]
                                     [--json]

Cross-invocation persistence: JSON state file at
``${MINDSOS_STATE_DIR or ~/.mindsos}/metagraph-schema-<name>.json``.
Phase 05b introduces this state-file kind at v=1. Migration chain at
``mindsos_cli.migrations.metagraph_schema`` (empty in 05b; future bumps
in 05c — adds 3 new vocabularies — and Phase 10).

Locked round 1-6 design picks reflected here:

* **Pushback 3-A** — top-level subapp parallel to ``mindsos schema``;
  bindings via ``mindsos metagraph attach-schema --schema MS`` /
  ``detach-schema``.
* **Pushback 5-A + 10-A** — ``MetagraphSchema(strict=False)`` ships
  from day one. ``--strict`` flag at create time mirrors Phase 04
  ``mindsos schema create --strict``.
* **Pushback 11-A** — schema reusable across N metagraphs (basename-keyed).
* **Pushback 20-A** — ``reset`` orphan check mirrors 05a Q6-A + Phase 04
  schema reset: walks every metagraph state file for ``schema_name``
  references; refuses without ``--force --yes``; with ``--force --yes``,
  strips ``schema_name`` back-pointers from referenced metagraphs.
* **Pushback 23-A** — ``add-intergraph-edge-type`` while schema is
  attached to N metagraphs: stderr warning listing every attached
  metagraph (carry-forward Phase 04 footgun).
* **Pushback 24-hybrid** — empty MetagraphSchema (no
  IntergraphEdgeType registered): attach succeeds with stderr warning;
  in strict mode, any pre-existing intergraph_edges fail (strict +
  empty vocab = empty allow-list).

Exit codes (parity with Phase 04 graph schema CLI):
  1 — domain errors (UnknownTypeError, CypherError, malformed state
      file, corrupt PropertyType vocab, orphan-bearing reset without
      --force).
  2 — usage errors (missing required arg, malformed --prop-type, empty
      key, reset without --name|--all, invalid <name> regex,
      destructive without --yes).
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional

import typer

from mindsos_core import (
    CypherError,
    IntergraphEdgeType,
    MetagraphSchema,
    PropertyType,
    UnknownTypeError,
)
from mindsos_cli import state as state_mod
from mindsos_cli.commands.metagraph import (
    _metagraph_schema_to_state,
    _state_to_metagraph_schema,
)


metagraph_schema_app = typer.Typer(
    name="metagraph-schema",
    help="L1 MetagraphSchema — declare IntergraphEdgeType vocab; "
         "attach to metagraphs via 'mindsos metagraph attach-schema' (Phase 05b).",
    no_args_is_help=True,
    add_completion=False,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _parse_prop_type(arg: str) -> tuple[str, PropertyType]:
    """Parse a single ``--prop-type k=<vocab>`` flag (mirror Phase 04 schema)."""
    if "=" not in arg:
        typer.echo(
            f"--prop-type expects 'k=v' form, got {arg!r}", err=True
        )
        raise typer.Exit(code=2)
    key, _, val = arg.partition("=")
    if not key:
        typer.echo(f"--prop-type key is empty in {arg!r}", err=True)
        raise typer.Exit(code=2)
    try:
        ptype = PropertyType(val)
    except ValueError:
        valid = ", ".join(p.value for p in PropertyType)
        typer.echo(
            f"--prop-type value {val!r} for key {key!r} not recognised. "
            f"Valid: {valid}.",
            err=True,
        )
        raise typer.Exit(code=2)
    return key, ptype


def _path_or_unknown(name: str) -> str:
    try:
        return str(state_mod.metagraph_schema_file_path(name))
    except ValueError:
        return "<unknown>"


def _load_or_die(name: str) -> MetagraphSchema:
    """Load + rehydrate a metagraph-schema; die with structured exit on failure."""
    try:
        state = state_mod.load_metagraph_schema_state(name)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=2)
    except FileNotFoundError:
        path = _path_or_unknown(name)
        typer.echo(
            f"MetagraphSchema {name!r} not found at {path}; create it "
            f"first with 'mindsos metagraph-schema create --name {name}'.",
            err=True,
        )
        raise typer.Exit(code=1)
    except RuntimeError as e:
        typer.echo(f"State file error: {e}", err=True)
        raise typer.Exit(code=1)
    try:
        return _state_to_metagraph_schema(state)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)


def _save_or_die(name: str, ms: MetagraphSchema) -> None:
    """Save metagraph-schema state; die with structured exit on failure."""
    try:
        state_mod.save_metagraph_schema_state(
            name, _metagraph_schema_to_state(ms, name=name),
        )
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=2)


def _confirm_destructive_or_die(*, label: str, yes: bool) -> None:
    """05a P5 inherited — require explicit ``--yes`` for destructive ops."""
    if yes:
        return
    typer.echo(
        f"refusing {label}: this operation is destructive. Re-run with "
        f"--yes to confirm.",
        err=True,
    )
    raise typer.Exit(code=2)


def _find_attached_metagraphs(schema_name: str) -> List[str]:
    """Walk every metagraph state file; return names of those attached to schema_name.

    Used for Pushback 20-A reset orphan check + Pushback 23-A schema-mutation
    warning. Reads metagraph state files raw (bypasses rehydration) so a
    DMS-A dangling-reference metagraph still surfaces as referencing the
    schema.
    """
    referencing: List[str] = []
    for mg_path in state_mod.iter_metagraph_files():
        try:
            mg_raw = json.loads(mg_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(mg_raw, dict):
            continue
        if mg_raw.get("schema_name") == schema_name:
            referencing.append(
                mg_raw.get("name") or mg_path.stem.removeprefix("metagraph-")
            )
    return referencing


# ---------------------------------------------------------------------------
# create (Pushback 5-A + 10-A — strict ships from day one)
# ---------------------------------------------------------------------------


@metagraph_schema_app.command("create")
def create_cmd(
    name: str = typer.Option(..., "--name", help="MetagraphSchema name."),
    strict: bool = typer.Option(
        False, "--strict",
        help="Pushback 5-A: when set, gates property-type validation "
             "for IntergraphEdge.properties. Default off.",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Create an empty metagraph-schema and write the initial state file."""
    try:
        path = state_mod.metagraph_schema_file_path(name)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=2)
    if path.exists():
        typer.echo(
            f"IdentityError: MetagraphSchema {name!r} already exists at "
            f"{path}; use 'mindsos metagraph-schema reset --name {name} "
            f"--yes' to clear.",
            err=True,
        )
        raise typer.Exit(code=1)
    ms = MetagraphSchema(strict=strict)
    _save_or_die(name, ms)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "name": name,
                    "strict": strict,
                    "intergraph_edge_types": [],
                    "state_file": str(path),
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"created: name={name} strict={strict} "
            f"intergraph_edge_types=0"
        )
        typer.echo(f"state_file={path}")


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------


@metagraph_schema_app.command("inspect")
def inspect_cmd(
    name: str = typer.Option(..., "--name", help="MetagraphSchema name."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Report the schema's vocabulary + counts for the named metagraph-schema.

    JSON shape:

        {
          "name": "<n>",
          "strict": <bool>,
          "counts": {"intergraph_edge_types": int},
          "intergraph_edge_types": [...sorted by name],
          "_state_version": int,
          "state_file": "<path>",
          "attached_metagraphs": [...sorted names]
        }
    """
    ms = _load_or_die(name)
    iet_sorted = sorted(
        ms.intergraph_edge_types.values(), key=lambda iet: iet.name
    )
    summary = {
        "name": name,
        "strict": ms.strict,
        "counts": {
            "intergraph_edge_types": len(ms.intergraph_edge_types),
        },
        "intergraph_edge_types": [
            {
                "name": iet.name,
                "allowed_source_types": sorted(iet.allowed_source_types),
                "allowed_target_types": sorted(iet.allowed_target_types),
                "allowed_source_graphs": sorted(iet.allowed_source_graphs),
                "allowed_target_graphs": sorted(iet.allowed_target_graphs),
                "property_types": {
                    k: v.value for k, v in iet.property_types.items()
                },
                "description": iet.description,
            }
            for iet in iet_sorted
        ],
        "_state_version": state_mod.METAGRAPH_SCHEMA_STATE_VERSION,
        "state_file": str(state_mod.metagraph_schema_file_path(name)),
        "attached_metagraphs": sorted(_find_attached_metagraphs(name)),
    }
    if json_out:
        typer.echo(json.dumps(summary, indent=2))
    else:
        typer.echo(f"name={name} strict={ms.strict}")
        typer.echo(
            f"intergraph_edge_types={summary['counts']['intergraph_edge_types']}"
        )
        for iet in iet_sorted:
            typer.echo(
                f"  {iet.name}: source_types="
                f"{sorted(iet.allowed_source_types) or 'any'} "
                f"target_types={sorted(iet.allowed_target_types) or 'any'} "
                f"source_graphs={sorted(iet.allowed_source_graphs) or 'any'} "
                f"target_graphs={sorted(iet.allowed_target_graphs) or 'any'}"
            )
        typer.echo(f"attached_metagraphs={summary['attached_metagraphs']}")
        typer.echo(f"state_file={summary['state_file']}")


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@metagraph_schema_app.command("list")
def list_schemas_cmd(
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Enumerate every metagraph-schema in $MINDSOS_STATE_DIR.

    Like ``mindsos metagraph list``, this command bypasses the strict
    version check (Phase 04 P3 inherited) so future-version schema
    state files appear in the listing rather than getting hidden.

    JSON shape:

        {
          "state_dir": "<path>",
          "metagraph_schemas": [
            {"name", "strict", "intergraph_edge_types_count",
             "_state_version", "path"}, ...
          ]
        }
    """
    entries: list[dict] = []
    for path in state_mod.iter_metagraph_schema_files():
        try:
            raw = path.read_text(encoding="utf-8")
            state = json.loads(raw)
        except (OSError, json.JSONDecodeError) as e:
            entries.append({"path": str(path), "error": f"unreadable: {e}"})
            continue
        if not isinstance(state, dict):
            entries.append({"path": str(path), "error": "non-dict top-level"})
            continue
        entries.append(
            {
                "name": state.get("name"),
                "strict": bool(state.get("strict", False)),
                "intergraph_edge_types_count": len(
                    state.get("intergraph_edge_types") or []
                ),
                "_state_version": state.get("_state_version"),
                "path": str(path),
            }
        )
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "state_dir": str(state_mod.state_dir()),
                    "metagraph_schemas": entries,
                },
                indent=2,
            )
        )
    else:
        typer.echo(f"state_dir={state_mod.state_dir()}")
        if not entries:
            typer.echo("(no metagraph-schemas)")
            return
        for e in entries:
            if "error" in e:
                typer.echo(f"  {e['path']}  ERROR: {e['error']}")
            else:
                typer.echo(
                    f"  name={e['name']!r}  strict={e['strict']}  "
                    f"v={e['_state_version']}  "
                    f"intergraph_edge_types={e['intergraph_edge_types_count']}"
                )


# ---------------------------------------------------------------------------
# reset (Pushback 20-A orphan check; mirror 05a Q6-A + Phase 04 schema reset)
# ---------------------------------------------------------------------------


@metagraph_schema_app.command("reset")
def reset_cmd(
    name: Optional[str] = typer.Option(
        None, "--name", help="MetagraphSchema name to reset.",
    ),
    all_: bool = typer.Option(
        False, "--all",
        help="Reset every metagraph-schema in $MINDSOS_STATE_DIR.",
    ),
    force: bool = typer.Option(
        False, "--force",
        help="Pushback 20-A: when --name set, strip schema_name "
             "back-pointers from any metagraphs that reference this "
             "schema (warning emitted). Without --force, refuses if "
             "any metagraph references the target.",
    ),
    yes: bool = typer.Option(
        False, "--yes",
        help="P5 inherited: required for --force OR --all (destructive).",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Delete the named metagraph-schema state file or every schema state file."""
    if name and all_:
        typer.echo("--name and --all are mutually exclusive.", err=True)
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
        try:
            target_path = state_mod.metagraph_schema_file_path(name)
        except ValueError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=2)
        if not target_path.exists():
            typer.echo(
                f"MetagraphSchema {name!r} not found at {target_path}; "
                f"nothing to reset.",
                err=True,
            )
            raise typer.Exit(code=1)
        # Pushback 20-A — orphan check across metagraph state files.
        referencing = _find_attached_metagraphs(name)
        if referencing and not force:
            typer.echo(
                f"refusing reset: metagraph-schema {name!r} is referenced "
                f"by {len(referencing)} metagraph(s): "
                f"{sorted(referencing)!r}. Use 'mindsos metagraph "
                f"detach-schema --name <MG>' on each, OR re-run with "
                f"--force --yes to strip schema_name back-pointers "
                f"(Pushback 20-A).",
                err=True,
            )
            raise typer.Exit(code=1)
        if referencing and force:
            typer.echo(
                f"warning: --force stripping schema_name back-pointers "
                f"from {len(referencing)} metagraph(s): "
                f"{sorted(referencing)!r}. The metagraphs become "
                f"un-validated; existing intergraph_edges retain their "
                f"type_names but are no longer schema-checked.",
                err=True,
            )
            for mg_name in referencing:
                try:
                    mg_state = state_mod.load_metagraph_state(mg_name)
                    mg_state["schema_name"] = None
                    mg_state["_state_version"] = (
                        state_mod.METAGRAPH_STATE_VERSION
                    )
                    state_mod.save_metagraph_state(mg_name, mg_state)
                    stripped_back_pointers.append(mg_name)
                except (FileNotFoundError, ValueError, RuntimeError) as e:
                    typer.echo(
                        f"warning: could not strip back-pointer from "
                        f"metagraph {mg_name!r}: {e}",
                        err=True,
                    )
        try:
            state_mod.delete_metagraph_schema_state_file(name)
        except FileNotFoundError:
            pass
        deleted.append(name)
    else:
        # --all (gated by --yes above).
        for path in list(state_mod.iter_metagraph_schema_files()):
            ms_name = path.stem.removeprefix("metagraph-schema-")
            referencing = _find_attached_metagraphs(ms_name)
            for mg_name in referencing:
                try:
                    mg_state = state_mod.load_metagraph_state(mg_name)
                    mg_state["schema_name"] = None
                    mg_state["_state_version"] = (
                        state_mod.METAGRAPH_STATE_VERSION
                    )
                    state_mod.save_metagraph_state(mg_name, mg_state)
                    stripped_back_pointers.append(mg_name)
                except (FileNotFoundError, ValueError, RuntimeError):
                    pass
            path.unlink()
            deleted.append(ms_name)

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
            typer.echo(f"ok: deleted metagraph-schema={n!r}")
        if stripped_back_pointers:
            typer.echo(
                f"stripped schema_name back-pointers from: "
                f"{sorted(stripped_back_pointers)!r}"
            )
        typer.echo(f"count: {len(deleted)}")


# ---------------------------------------------------------------------------
# add-intergraph-edge-type (Pushback 23-A — stderr warning if attached)
# ---------------------------------------------------------------------------


@metagraph_schema_app.command("add-intergraph-edge-type")
def add_intergraph_edge_type_cmd(
    schema: str = typer.Option(..., "--schema", help="MetagraphSchema name."),
    type_name: str = typer.Option(
        ..., "--type-name",
        help="Cypher rel-type (must match ^[A-Z][A-Z0-9_]{0,63}$ per ADR-0021).",
    ),
    allowed_source_type: List[str] = typer.Option(
        [], "--allowed-source-type",
        help="Repeat: NodeType.name allowed as source. Empty = any.",
    ),
    allowed_target_type: List[str] = typer.Option(
        [], "--allowed-target-type",
        help="Repeat: NodeType.name allowed as target. Empty = any.",
    ),
    allowed_source_graph: List[str] = typer.Option(
        [], "--allowed-source-graph",
        help="Repeat: Graph.role allowed as source graph. Empty = any role.",
    ),
    allowed_target_graph: List[str] = typer.Option(
        [], "--allowed-target-graph",
        help="Repeat: Graph.role allowed as target graph. Empty = any role.",
    ),
    prop_type: List[str] = typer.Option(
        [], "--prop-type",
        help="Repeat: k=<vocab>. Vocab is one of "
             "string/int/float/bool/list[string]/list[int]/list[float]/list[bool].",
    ),
    description: Optional[str] = typer.Option(
        None, "--description", help="Optional human-readable description.",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Register an :class:`IntergraphEdgeType` on the named schema.

    Per Pushback 23-A, if the schema is currently attached to one or
    more metagraphs, a stderr warning lists them — schema mutation is
    a Phase 04 carry-forward footgun: attached metagraphs do NOT
    re-validate against the new vocabulary until the tester re-attaches.

    Per Pushback 4-A, ``--allowed-source-graph`` / ``--allowed-target-graph``
    are role-based (compared against ``Graph.role``); empty means any
    role accepted; ``role=None`` graphs are unmatchable when the
    constraint is non-empty.
    """
    ms = _load_or_die(schema)
    prop_types: Dict[str, PropertyType] = {}
    for pt_arg in prop_type or []:
        k, v = _parse_prop_type(pt_arg)
        prop_types[k] = v
    iet = IntergraphEdgeType(
        name=type_name,
        allowed_source_types=frozenset(allowed_source_type or []),
        allowed_target_types=frozenset(allowed_target_type or []),
        allowed_source_graphs=frozenset(allowed_source_graph or []),
        allowed_target_graphs=frozenset(allowed_target_graph or []),
        property_types=prop_types,
        description=description,
    )
    try:
        ms.add_intergraph_edge_type(iet)
    except CypherError as e:
        typer.echo(f"CypherError: {e}", err=True)
        raise typer.Exit(code=1)
    except UnknownTypeError as e:
        typer.echo(f"UnknownTypeError: {e}", err=True)
        raise typer.Exit(code=1)

    # Pushback 23-A — stderr warning if attached.
    attached = _find_attached_metagraphs(schema)
    if attached:
        typer.echo(
            f"warning: schema {schema!r} is currently attached to "
            f"{len(attached)} metagraph(s): {sorted(attached)!r}. "
            f"Adding {type_name!r} does NOT trigger re-validation; "
            f"existing intergraph_edges in those metagraphs may now "
            f"violate the (extended) schema. Run 'mindsos metagraph "
            f"attach-schema --name <MG> --schema {schema}' on each to "
            f"surface drift (Pushback 23-A footgun).",
            err=True,
        )

    _save_or_die(schema, ms)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "schema": schema,
                    "type_name": iet.name,
                    "allowed_source_types": sorted(iet.allowed_source_types),
                    "allowed_target_types": sorted(iet.allowed_target_types),
                    "allowed_source_graphs": sorted(iet.allowed_source_graphs),
                    "allowed_target_graphs": sorted(iet.allowed_target_graphs),
                    "property_types": {
                        k: v.value for k, v in iet.property_types.items()
                    },
                    "description": iet.description,
                    "attached_metagraphs": sorted(attached),
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"ok: registered IntergraphEdgeType {iet.name!r} on schema "
            f"{schema!r} (attached to {len(attached)} metagraph(s))"
        )


def register_metagraph_schema_app(parent: typer.Typer) -> None:
    """Wire the metagraph-schema sub-app onto a parent Typer app."""
    parent.add_typer(metagraph_schema_app, name="metagraph-schema")
