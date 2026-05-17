"""`mindsos schema` — Phase 04-v2 L1 Schema CLI surface.

Subcommands:

  mindsos schema create --name <NAME> [--strict] [--json]
  mindsos schema add-node-type --schema <NAME> --type-name <TYPE>
                               [--prop-type k=<PROPTYPE>]...
                               [--description TEXT] [--json]
  mindsos schema add-edge-type --schema <NAME> --type-name <REL_TYPE>
                               [--allowed-source <NODE_TYPE>]...
                               [--allowed-target <NODE_TYPE>]...
                               [--prop-type k=<PROPTYPE>]...
                               [--description TEXT] [--json]
  mindsos schema add-hyperedge-type --schema <NAME> --type-name <REL_TYPE>
                                    [--allowed-member <NODE_TYPE>]...
                                    [--prop-type k=<PROPTYPE>]...
                                    [--description TEXT] [--json]
  mindsos schema inspect --name <NAME> [--json]
  mindsos schema list [--json]
  mindsos schema reset (--name <NAME> | --all) [--force] [--json]

Cross-invocation persistence: JSON state file at
``${MINDSOS_STATE_DIR or ~/.mindsos}/schema-<name>.json`` (parity with
the Phase 03 graph state file pattern). Schema state files use
``_state_version: 1`` (``SCHEMA_STATE_VERSION``) — Phase 04 introduced
this kind, so there's no migration story for schemas.

Property-type vocabulary (8 variants, parity with the parent project):
``string``, ``int``, ``float``, ``bool``, ``list[string]``, ``list[int]``,
``list[float]``, ``list[bool]``. Pass via ``--prop-type k=<vocab-value>``.
Unrecognised vocab → exit 2 with a structured error.

Orphan check on ``reset`` (Phase 04 — Pick F + NEW3):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Both ``--name <X>`` and ``--all`` walk every ``graph-*.json`` in the
state dir; if ANY graph references a schema being deleted (via its
``schema_name`` field), reset refuses with exit 1 and lists the
referencing graphs. ``--force`` overrides the check (the user accepts
the resulting dangling references; recovery via
``mindsos graph detach-schema``).

Exit codes (parity with Phase 03 graph CLI):
  1 — domain errors (UnknownTypeError, CypherError, malformed state
      file, corrupt PropertyType vocab in state file, orphan-bearing
      reset without ``--force``).
  2 — usage errors (missing required arg, malformed --prop-type, empty
      key, reset without ``--name`` | ``--all``, invalid ``<name>`` regex).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import typer

from mindsos_core import (
    CypherError,
    EdgeType,
    HyperEdgeType,
    NodeType,
    PropertyType,
    Schema,
    UnknownTypeError,
)
from mindsos_cli import state as state_mod


schema_app = typer.Typer(
    name="schema",
    help="L1 Schema — declare NodeType / EdgeType, optional strict typing.",
    no_args_is_help=True,
    add_completion=False,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _parse_prop_type(arg: str) -> tuple[str, PropertyType]:
    """Parse a single ``--prop-type k=<vocab>`` flag.

    Raises ``typer.Exit(2)`` on:
      - missing ``=``
      - empty key
      - vocab value not in ``PropertyType`` (lookup by `.value`).
    """
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


def _parse_prop_types(args: List[str]) -> Dict[str, PropertyType]:
    """Parse repeated ``--prop-type k=v`` flags into a dict."""
    out: Dict[str, PropertyType] = {}
    for arg in args:
        key, ptype = _parse_prop_type(arg)
        out[key] = ptype
    return out


def _schema_to_state(name: str, schema: Schema) -> dict:
    """Serialize a ``Schema`` to the v=2 state-file dict (Phase 04-v2).

    Sorts top-level lists by ``name``; sorts ``allowed_sources`` /
    ``allowed_targets`` / ``allowed_member_types``; serialises
    ``PropertyType`` via ``.value``. Always writes
    ``_state_version: SCHEMA_STATE_VERSION`` (= 2 in Phase 04-v2).
    """
    node_types = sorted(schema.node_types.values(), key=lambda nt: nt.name)
    edge_types = sorted(schema.edge_types.values(), key=lambda et: et.name)
    hyperedge_types = sorted(
        schema.hyperedge_types.values(), key=lambda het: het.name
    )
    return {
        "_state_version": state_mod.SCHEMA_STATE_VERSION,
        "name": name,
        "strict": schema.strict,
        "node_types": [
            {
                "name": nt.name,
                "property_types": {k: v.value for k, v in nt.property_types.items()},
                "description": nt.description,
            }
            for nt in node_types
        ],
        "edge_types": [
            {
                "name": et.name,
                "allowed_sources": sorted(et.allowed_sources),
                "allowed_targets": sorted(et.allowed_targets),
                "property_types": {k: v.value for k, v in et.property_types.items()},
                "description": et.description,
            }
            for et in edge_types
        ],
        # Phase 04-v2 — HyperEdgeType vocabulary added.
        "hyperedge_types": [
            {
                "name": het.name,
                "allowed_member_types": sorted(het.allowed_member_types),
                "property_types": {
                    k: v.value for k, v in het.property_types.items()
                },
                "description": het.description,
            }
            for het in hyperedge_types
        ],
    }


def _state_to_schema(state: dict) -> Schema:
    """Rehydrate a ``Schema`` from a v1 state-file dict.

    Phase 04 — NEW2: corrupt ``PropertyType`` vocab values raise
    :class:`RuntimeError` (caught upstream and converted to exit 1)
    rather than crashing with a bare ``ValueError`` traceback.
    """
    schema = Schema(strict=bool(state.get("strict", False)))
    valid_vocab = ", ".join(p.value for p in PropertyType)

    def _ptype(raw_value: Any, *, scope: str, type_name: str, key: str) -> PropertyType:
        try:
            return PropertyType(raw_value)
        except (ValueError, KeyError) as exc:
            raise RuntimeError(
                f"Schema state file contains unrecognised PropertyType "
                f"{raw_value!r} for {scope} type {type_name!r} key {key!r}. "
                f"Valid: {valid_vocab}."
            ) from exc

    for nt_dict in state.get("node_types", []) or []:
        nt_name = nt_dict.get("name", "<unknown>")
        property_types = {
            k: _ptype(v, scope="node", type_name=nt_name, key=k)
            for k, v in (nt_dict.get("property_types") or {}).items()
        }
        schema.add_node_type(
            NodeType(
                name=nt_name,
                property_types=property_types,
                description=nt_dict.get("description"),
            )
        )
    for et_dict in state.get("edge_types", []) or []:
        et_name = et_dict.get("name", "<unknown>")
        property_types = {
            k: _ptype(v, scope="edge", type_name=et_name, key=k)
            for k, v in (et_dict.get("property_types") or {}).items()
        }
        schema.add_edge_type(
            EdgeType(
                name=et_name,
                allowed_sources=frozenset(et_dict.get("allowed_sources") or []),
                allowed_targets=frozenset(et_dict.get("allowed_targets") or []),
                property_types=property_types,
                description=et_dict.get("description"),
            )
        )
    # Phase 04-v2 — HyperEdgeType vocabulary. Tolerates v=1 schema state
    # files (missing ``hyperedge_types`` field treated as empty list).
    for het_dict in state.get("hyperedge_types", []) or []:
        het_name = het_dict.get("name", "<unknown>")
        property_types = {
            k: _ptype(v, scope="hyperedge", type_name=het_name, key=k)
            for k, v in (het_dict.get("property_types") or {}).items()
        }
        schema.add_hyperedge_type(
            HyperEdgeType(
                name=het_name,
                allowed_member_types=frozenset(
                    het_dict.get("allowed_member_types") or []
                ),
                property_types=property_types,
                description=het_dict.get("description"),
            )
        )
    return schema


def _load_or_die(name: str) -> Schema:
    """Load and rehydrate a schema; die with structured exit on failure."""
    try:
        state = state_mod.load_schema_state(name)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=2)
    except FileNotFoundError:
        path = _path_or_unknown(name)
        typer.echo(
            f"Schema {name!r} not found at {path}; "
            f"create it first with 'mindsos schema create --name {name}'",
            err=True,
        )
        raise typer.Exit(code=1)
    except RuntimeError as e:
        typer.echo(f"State file error: {e}", err=True)
        raise typer.Exit(code=1)
    try:
        return _state_to_schema(state)
    except RuntimeError as e:
        # NEW2 — corrupt PropertyType vocab in state file.
        typer.echo(f"State file error: {e}", err=True)
        raise typer.Exit(code=1)


def _save_or_die(name: str, schema: Schema) -> None:
    try:
        state_mod.save_schema_state(name, _schema_to_state(name, schema))
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=2)


def _path_or_unknown(name: str) -> str:
    try:
        return str(state_mod.schema_file_path(name))
    except ValueError:
        return "<unknown>"


def _find_orphan_referencers(schema_names: set[str]) -> dict[str, str]:
    """Walk every ``graph-*.json`` in the state dir; collect graphs that
    reference any schema in ``schema_names`` via their ``schema_name``
    field.

    Returns a mapping ``{graph_name: schema_name_referenced}``. Reads
    JSON directly (NOT via ``load_graph_state``) so corrupt graph files
    don't block the orphan check — they're skipped with a stderr warning.
    """
    referencers: dict[str, str] = {}
    for path in state_mod.iter_state_files():
        try:
            raw = path.read_text(encoding="utf-8")
            state = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            typer.echo(
                f"warning: skipping unreadable graph state file {path} "
                f"during orphan check.",
                err=True,
            )
            continue
        if not isinstance(state, dict):
            continue
        ref = state.get("schema_name")
        if ref in schema_names:
            graph_name = state.get("name") or path.stem.removeprefix("graph-")
            referencers[graph_name] = ref
    return referencers


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


@schema_app.command("create")
def create_cmd(
    name: str = typer.Option(..., "--name", help="Schema name."),
    strict: bool = typer.Option(
        False, "--strict", help="Enforce per-type PropertyType maps on add / update."
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Create an empty schema and write the initial state file."""
    try:
        path = state_mod.schema_file_path(name)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=2)
    if path.exists():
        typer.echo(
            f"IdentityError: Schema {name!r} already exists at {path}; "
            f"use 'mindsos schema reset --name {name}' to clear.",
            err=True,
        )
        raise typer.Exit(code=1)
    schema = Schema(strict=strict)
    _save_or_die(name, schema)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "name": name,
                    "strict": schema.strict,
                    "node_types": [],
                    "edge_types": [],
                    "state_file": str(path),
                },
                indent=2,
            )
        )
    else:
        typer.echo(f"created: name={name} strict={schema.strict}")
        typer.echo(f"state_file={path}")


# ---------------------------------------------------------------------------
# add-node-type
# ---------------------------------------------------------------------------


@schema_app.command("add-node-type")
def add_node_type_cmd(
    schema_name: str = typer.Option(..., "--schema", help="Schema name."),
    type_name: str = typer.Option(..., "--type-name", help="Node type name."),
    prop_type: List[str] = typer.Option(
        [], "--prop-type", help="Repeat: k=<vocab>. Vocab: string|int|float|bool|list[string]|list[int]|list[float]|list[bool]."
    ),
    description: Optional[str] = typer.Option(
        None, "--description", help="Optional human-readable description."
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Register a NodeType on the named schema."""
    schema = _load_or_die(schema_name)
    property_types = _parse_prop_types(prop_type or [])
    try:
        nt = schema.add_node_type(
            NodeType(
                name=type_name,
                property_types=property_types,
                description=description,
            )
        )
    except UnknownTypeError as e:
        typer.echo(f"UnknownTypeError: {e}", err=True)
        raise typer.Exit(code=1)
    _save_or_die(schema_name, schema)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "name": nt.name,
                    "property_types": {k: v.value for k, v in nt.property_types.items()},
                    "description": nt.description,
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"ok: added node type name={nt.name!r} "
            f"property_types={{{', '.join(f'{k}={v.value}' for k, v in nt.property_types.items())}}}"
        )


# ---------------------------------------------------------------------------
# add-edge-type
# ---------------------------------------------------------------------------


@schema_app.command("add-edge-type")
def add_edge_type_cmd(
    schema_name: str = typer.Option(..., "--schema", help="Schema name."),
    type_name: str = typer.Option(
        ..., "--type-name", help="Edge type / Cypher rel-type (must match ^[A-Z][A-Z0-9_]{0,63}$)."
    ),
    allowed_source: List[str] = typer.Option(
        [], "--allowed-source", help="Repeat: a NodeType name allowed as edge source. Empty = any."
    ),
    allowed_target: List[str] = typer.Option(
        [], "--allowed-target", help="Repeat: a NodeType name allowed as edge target. Empty = any."
    ),
    prop_type: List[str] = typer.Option(
        [], "--prop-type", help="Repeat: k=<vocab> (same vocab as add-node-type)."
    ),
    description: Optional[str] = typer.Option(
        None, "--description", help="Optional human-readable description."
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Register an EdgeType on the named schema."""
    schema = _load_or_die(schema_name)
    property_types = _parse_prop_types(prop_type or [])
    try:
        et = schema.add_edge_type(
            EdgeType(
                name=type_name,
                allowed_sources=frozenset(allowed_source or []),
                allowed_targets=frozenset(allowed_target or []),
                property_types=property_types,
                description=description,
            )
        )
    except CypherError as e:
        typer.echo(f"CypherError: {e}", err=True)
        raise typer.Exit(code=1)
    except UnknownTypeError as e:
        typer.echo(f"UnknownTypeError: {e}", err=True)
        raise typer.Exit(code=1)
    _save_or_die(schema_name, schema)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "name": et.name,
                    "allowed_sources": sorted(et.allowed_sources),
                    "allowed_targets": sorted(et.allowed_targets),
                    "property_types": {k: v.value for k, v in et.property_types.items()},
                    "description": et.description,
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"ok: added edge type name={et.name!r} "
            f"sources={sorted(et.allowed_sources)} "
            f"targets={sorted(et.allowed_targets)}"
        )


# ---------------------------------------------------------------------------
# add-hyperedge-type (Phase 04-v2 — ADR-0017 / MC-2 / HET-1 / AME-1)
# ---------------------------------------------------------------------------


@schema_app.command("add-hyperedge-type")
def add_hyperedge_type_cmd(
    schema_name: str = typer.Option(..., "--schema", help="Schema name."),
    type_name: str = typer.Option(
        ..., "--type-name",
        help="HyperEdge type / Cypher rel-type (must match ^[A-Z][A-Z0-9_]{0,63}$).",
    ),
    allowed_member: List[str] = typer.Option(
        [], "--allowed-member",
        help="Repeat: a NodeType name allowed as hyperedge member. "
             "Empty = any (AME-1; mirrors EdgeType allowed_sources / "
             "allowed_targets precedent).",
    ),
    prop_type: List[str] = typer.Option(
        [], "--prop-type",
        help="Repeat: k=<vocab> (same 8-variant PropertyType vocabulary as "
             "add-edge-type).",
    ),
    description: Optional[str] = typer.Option(
        None, "--description", help="Optional human-readable description."
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Register a HyperEdgeType on the named schema (Phase 04-v2).

    ``--type-name`` validates against the cypher rel-type regex per
    ADR-0021 (the SENT-1 sentinel ``UNSPECIFIED`` is a deliberate fit).
    ``--allowed-member`` may be empty (AME-1 lock); under non-strict the
    type accepts any member, under strict the type rejects all members
    until allowed-members are populated.

    No cardinality bounds (HET-1 lock); symmetric across all members.
    """
    schema = _load_or_die(schema_name)
    property_types = _parse_prop_types(prop_type or [])
    try:
        het = schema.add_hyperedge_type(
            HyperEdgeType(
                name=type_name,
                allowed_member_types=frozenset(allowed_member or []),
                property_types=property_types,
                description=description,
            )
        )
    except CypherError as e:
        typer.echo(f"CypherError: {e}", err=True)
        raise typer.Exit(code=1)
    except UnknownTypeError as e:
        typer.echo(f"UnknownTypeError: {e}", err=True)
        raise typer.Exit(code=1)
    _save_or_die(schema_name, schema)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "name": het.name,
                    "allowed_member_types": sorted(het.allowed_member_types),
                    "property_types": {
                        k: v.value for k, v in het.property_types.items()
                    },
                    "description": het.description,
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"ok: added hyperedge type name={het.name!r} "
            f"members={sorted(het.allowed_member_types)} "
            f"(empty=any per AME-1)"
        )


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------


@schema_app.command("inspect")
def inspect_cmd(
    name: str = typer.Option(..., "--name", help="Schema name."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Report the strictness and registered types of the named schema."""
    schema = _load_or_die(name)
    summary: Dict[str, Any] = {
        "name": name,
        "strict": schema.strict,
        "node_types": [
            {
                "name": nt.name,
                "property_types": {k: v.value for k, v in nt.property_types.items()},
                "description": nt.description,
            }
            for nt in sorted(schema.node_types.values(), key=lambda x: x.name)
        ],
        "edge_types": [
            {
                "name": et.name,
                "allowed_sources": sorted(et.allowed_sources),
                "allowed_targets": sorted(et.allowed_targets),
                "property_types": {k: v.value for k, v in et.property_types.items()},
                "description": et.description,
            }
            for et in sorted(schema.edge_types.values(), key=lambda x: x.name)
        ],
        # Phase 04-v2 — HyperEdgeType vocabulary in inspect output.
        "hyperedge_types": [
            {
                "name": het.name,
                "allowed_member_types": sorted(het.allowed_member_types),
                "property_types": {
                    k: v.value for k, v in het.property_types.items()
                },
                "description": het.description,
            }
            for het in sorted(schema.hyperedge_types.values(), key=lambda x: x.name)
        ],
        "state_file": str(state_mod.schema_file_path(name)),
    }
    if json_out:
        typer.echo(json.dumps(summary, indent=2))
    else:
        typer.echo(f"name={name} strict={schema.strict}")
        typer.echo(f"state_file={summary['state_file']}")
        typer.echo(f"node_types ({len(summary['node_types'])}):")
        for nt in summary["node_types"]:
            typer.echo(
                f"  {nt['name']!r}  property_types={nt['property_types']}"
            )
        typer.echo(f"edge_types ({len(summary['edge_types'])}):")
        for et in summary["edge_types"]:
            typer.echo(
                f"  {et['name']!r}  sources={et['allowed_sources']} "
                f"targets={et['allowed_targets']} "
                f"property_types={et['property_types']}"
            )
        typer.echo(f"hyperedge_types ({len(summary['hyperedge_types'])}):")
        for het in summary["hyperedge_types"]:
            typer.echo(
                f"  {het['name']!r}  members={het['allowed_member_types']} "
                f"property_types={het['property_types']}"
            )


# ---------------------------------------------------------------------------
# list (schemas)
# ---------------------------------------------------------------------------


@schema_app.command("list")
def list_schemas_cmd(
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Enumerate every schema in $MINDSOS_STATE_DIR (sorted by name).

    Note (Phase 04 — Pick P3): this command DELIBERATELY bypasses
    ``load_schema_state``'s strict version check (parity with
    ``mindsos graph list``). Reads JSON directly so future-version
    files still appear in the listing rather than being hidden.
    Mutating commands DO use the strict loader.
    """
    entries: List[dict] = []
    for path in state_mod.iter_schema_files():
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
                "strict": state.get("strict", False),
                "state_version": state.get("_state_version"),
                "counts": {
                    "node_types": len(state.get("node_types") or []),
                    "edge_types": len(state.get("edge_types") or []),
                    "hyperedge_types": len(state.get("hyperedge_types") or []),
                },
                "path": str(path),
            }
        )
    if json_out:
        typer.echo(
            json.dumps(
                {"state_dir": str(state_mod.state_dir()), "schemas": entries},
                indent=2,
            )
        )
    else:
        typer.echo(f"state_dir={state_mod.state_dir()}")
        if not entries:
            typer.echo("(no schemas)")
            return
        for e in entries:
            if "error" in e:
                typer.echo(f"  {e['path']}  ERROR: {e['error']}")
            else:
                c = e["counts"]
                typer.echo(
                    f"  name={e['name']!r}  strict={e['strict']}  "
                    f"v={e['state_version']}  "
                    f"node_types={c['node_types']} edge_types={c['edge_types']}"
                )


# ---------------------------------------------------------------------------
# reset (Phase 04 — orphan check + --force)
# ---------------------------------------------------------------------------


@schema_app.command("reset")
def reset_cmd(
    name: Optional[str] = typer.Option(
        None, "--name", help="Schema name to reset."
    ),
    all_: bool = typer.Option(
        False, "--all", help="Reset every schema in $MINDSOS_STATE_DIR."
    ),
    force: bool = typer.Option(
        False, "--force",
        help="Override the orphan check; proceed even if graphs reference "
             "the schema(s) being deleted. Resulting graphs will have "
             "dangling schema_name references; recover via "
             "'mindsos graph detach-schema'.",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Delete the named schema state file or every schema state file.

    Orphan check (Phase 04 — Pick F + NEW3): walks every graph state
    file and refuses with exit 1 if any graph references the schema(s)
    being deleted. ``--force`` overrides; resulting graphs will need
    ``mindsos graph detach-schema`` to recover.
    """
    if name and all_:
        typer.echo("--name and --all are mutually exclusive.", err=True)
        raise typer.Exit(code=2)
    if not name and not all_:
        typer.echo(
            "Specify either --name <NAME> or --all (no accidental wipes).",
            err=True,
        )
        raise typer.Exit(code=2)

    # Resolve which schemas are being deleted (for the orphan check).
    if name:
        try:
            path = state_mod.schema_file_path(name)
        except ValueError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=2)
        if not path.exists():
            typer.echo(
                f"Schema {name!r} not found at {path}; nothing to reset.",
                err=True,
            )
            raise typer.Exit(code=1)
        targeted = {name}
    else:
        targeted = {
            p.stem.removeprefix("schema-")
            for p in state_mod.iter_schema_files()
        }

    # Orphan check — always compute (used for --force warning too).
    orphan_referencers = _find_orphan_referencers(targeted)
    if orphan_referencers and not force:
        typer.echo(
            f"Refusing to reset: {len(orphan_referencers)} graph(s) "
            f"reference schema(s) being deleted. Run with --force to "
            f"proceed (graphs will need 'mindsos graph detach-schema' "
            f"to recover):",
            err=True,
        )
        for graph_name, schema_ref in sorted(orphan_referencers.items()):
            typer.echo(
                f"  graph={graph_name!r} → schema={schema_ref!r}",
                err=True,
            )
        raise typer.Exit(code=1)

    # Proceed with deletion.
    deleted: List[str] = []
    if name:
        try:
            state_mod.delete_schema_state_file(name)
        except FileNotFoundError:
            # Race: file vanished between existence check and delete.
            pass
        deleted.append(name)
    else:
        for path in list(state_mod.iter_schema_files()):
            path.unlink()
            deleted.append(path.stem.removeprefix("schema-"))

    if json_out:
        typer.echo(
            json.dumps(
                {
                    "deleted": sorted(deleted),
                    "count": len(deleted),
                    "force": force,
                    "orphan_referencers": orphan_referencers,
                },
                indent=2,
            )
        )
    else:
        for n in sorted(deleted):
            typer.echo(f"ok: deleted schema={n!r}")
        typer.echo(f"count: {len(deleted)}")
        if force and orphan_referencers:
            typer.echo(
                f"warning: {len(orphan_referencers)} graph(s) now have "
                f"dangling schema_name references; run "
                f"'mindsos graph detach-schema' on each to recover.",
                err=True,
            )


# ---------------------------------------------------------------------------
# Phase 11 — `migrate-check` (ADR-0134 §scanner)
# ---------------------------------------------------------------------------


@schema_app.command("migrate-check")
def migrate_check_cmd(
    old: Optional[str] = typer.Option(
        None, "--old",
        help=(
            "Old schema name (resolved against $MINDSOS_STATE_DIR or "
            "~/.mindsos/schema-<name>.json). Mutually exclusive with "
            "--old-file."
        ),
    ),
    old_file: Optional[str] = typer.Option(
        None, "--old-file",
        help=(
            "Path to an old-schema state file at any location. Mutually "
            "exclusive with --old."
        ),
    ),
    new: Optional[str] = typer.Option(
        None, "--new",
        help=(
            "New schema name (state-dir resolved). When omitted, the "
            "scanner uses the new schema already attached to the target "
            "Graph (--graph) / each contained Graph (--metagraph). When "
            "specified, applies the new schema explicitly to every "
            "scanned Graph regardless of graph.schema_name."
        ),
    ),
    graph: Optional[str] = typer.Option(
        None, "--graph",
        help=(
            "Graph state-file name (state-dir resolved). Mutually "
            "exclusive with --metagraph."
        ),
    ),
    metagraph: Optional[str] = typer.Option(
        None, "--metagraph",
        help=(
            "Metagraph state-file name. Walks every contained graph; "
            "per PB-17 C policy warning emits when graph.schema_name "
            "differs from --old's name. Mutually exclusive with --graph."
        ),
    ),
    detail: str = typer.Option(
        "summary", "--detail",
        help=(
            "summary (default) — one aggregate entry per "
            "(kind, type_name, property). each — one entry per "
            "offending element. See ADR-0134 §scanner / PB-8 A."
        ),
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Emit JSON to stdout instead of Rich table."
    ),
    exit_zero: bool = typer.Option(
        False, "--exit-zero",
        help=(
            "Exit 0 even when violations are detected. Default exits 1 "
            "on any violations (CI-friendly per PB-15)."
        ),
    ),
) -> None:
    """Phase 11 ADR-0134 — scan persisted data for violations vs the new schema.

    Detection-only (PB-1 A); never mutates. Reports nodes/edges/hyperedges
    whose persisted shape no longer satisfies the new schema's
    constraints. Exit-1 on any violations unless ``--exit-zero``.
    """
    from mindsos_core.schema import (
        SchemaMigrationError,
        migrate_from,
    )

    if (old is None) == (old_file is None):
        typer.echo(
            "Specify exactly one of --old <NAME> or --old-file <PATH>.",
            err=True,
        )
        raise typer.Exit(code=2)
    if (graph is None) == (metagraph is None):
        typer.echo(
            "Specify exactly one of --graph <NAME> or --metagraph <NAME>.",
            err=True,
        )
        raise typer.Exit(code=2)
    if detail not in ("summary", "each"):
        typer.echo(
            f"--detail must be 'summary' or 'each'; got {detail!r}",
            err=True,
        )
        raise typer.Exit(code=2)

    # Resolve OLD schema.
    if old is not None:
        old_schema = _load_or_die(old)
        old_name = old
    else:
        # --old-file path; bypass state_mod's basename-based lookup.
        from pathlib import Path
        path = Path(old_file).expanduser()
        if not path.exists():
            typer.echo(f"Old schema file not found: {path}", err=True)
            raise typer.Exit(code=1)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            typer.echo(f"Failed to read --old-file: {exc}", err=True)
            raise typer.Exit(code=1)
        try:
            old_schema = _state_to_schema(raw)
        except RuntimeError as e:
            typer.echo(f"Old schema file error: {e}", err=True)
            raise typer.Exit(code=1)
        old_name = raw.get("name") or path.stem.removeprefix("schema-")

    # Optionally resolve NEW schema (state-dir lookup; --old-file
    # equivalent for new is deferred — Phase 11 scope kept tight).
    new_schema = None
    if new is not None:
        new_schema = _load_or_die(new)

    # Load the target (Graph or Metagraph).
    target = _load_migrate_check_target(graph=graph, metagraph=metagraph)

    # Scan.
    try:
        violations = migrate_from(
            old_schema,
            target,
            new=new_schema,
            detail=detail,
            old_schema_name=old_name,
        )
    except SchemaMigrationError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)

    # Build summary payload.
    payload = {
        "schema": {
            "old": old_name,
            "new": new if new is not None else "<attached>",
        },
        "scope": {
            "graph": graph,
            "metagraph": metagraph,
        },
        "detail": detail,
        "violation_count": len(violations),
        "violations": [
            {
                "kind": v.kind,
                "type_name": v.type_name,
                "graph_id": v.graph_id,
                "property_name": v.property_name,
                "element_id": v.element_id,
                "count": v.count,
                "detail": v.detail,
            }
            for v in violations
        ],
    }

    if json_out:
        typer.echo(json.dumps(payload, sort_keys=True, indent=2))
    else:
        _console.print(
            f"schema: old={payload['schema']['old']!r} "
            f"new={payload['schema']['new']!r}"
        )
        _console.print(
            f"scope: graph={graph!r} metagraph={metagraph!r} detail={detail!r}"
        )
        _console.print(f"violation_count: {len(violations)}")
        for v in violations:
            _console.print(
                f"  {v.kind} type={v.type_name!r} "
                f"prop={v.property_name!r} "
                f"graph={v.graph_id!r} count={v.count}"
            )

    if violations and not exit_zero:
        raise typer.Exit(code=1)


def _load_migrate_check_target(
    *, graph: Optional[str], metagraph: Optional[str]
):
    """Resolve the ``Graph`` or ``Metagraph`` named by the CLI flags.

    Reads from the state dir; rehydrates via existing migration chain
    (Phase 05a graph state v=4 / Phase 10 v=5; metagraph parity).
    """
    if graph is not None:
        try:
            state = state_mod.load_graph_state(graph)
        except FileNotFoundError:
            typer.echo(
                f"Graph state file not found for {graph!r}", err=True
            )
            raise typer.Exit(code=1)
        except (ValueError, RuntimeError) as e:
            typer.echo(f"Graph state file error: {e}", err=True)
            raise typer.Exit(code=1)
        from mindsos_cli.migrations.graph import migrate as _g_migrate
        from mindsos_core.models.graph import Graph
        _g_migrate(state)
        g = Graph(name=state["name"], graph_id=state.get("graph_id"))
        for n in state.get("nodes", []):
            g.add_node(
                value=n.get("value"),
                type_name=n["type_name"],
                properties=dict(n.get("properties", {})),
                node_id=n.get("id"),
                _validate=False,
            )
        nodes_by_id = {n.node_id: n for n in g.nodes.values()}
        for e in state.get("edges", []):
            src = nodes_by_id.get(e["source_id"])
            tgt = nodes_by_id.get(e["target_id"])
            if src is None or tgt is None:
                continue
            g.add_edge(
                source=src, target=tgt,
                type_name=e["type_name"],
                label=e.get("label"),
                properties=dict(e.get("properties", {})),
                edge_id=e.get("id"),
                _validate=False,
            )
        for h in state.get("hyperedges", []):
            members = [
                nodes_by_id[mid] for mid in h.get("members", [])
                if mid in nodes_by_id
            ]
            if not members:
                continue
            g.add_hyperedge(
                nodes=members,
                type_name=h.get("type_name", "UNSPECIFIED"),
                label=h.get("label"),
                properties=dict(h.get("properties", {})),
                edge_id=h.get("id"),
                _validate=False,
            )
        return g
    # Metagraph path — rehydrate via metagraph CLI's existing helper.
    try:
        mg_state = state_mod.load_metagraph_state(metagraph)
    except FileNotFoundError:
        typer.echo(
            f"Metagraph state file not found for {metagraph!r}", err=True
        )
        raise typer.Exit(code=1)
    except (ValueError, RuntimeError) as e:
        typer.echo(f"Metagraph state file error: {e}", err=True)
        raise typer.Exit(code=1)
    from mindsos_cli.commands.metagraph import _state_to_metagraph
    return _state_to_metagraph(mg_state)


# ---------------------------------------------------------------------------
# Compatibility for app.py
# ---------------------------------------------------------------------------


def register_schema_app(parent: typer.Typer) -> None:
    """Wire the schema sub-app onto a parent Typer app."""
    parent.add_typer(schema_app, name="schema")
