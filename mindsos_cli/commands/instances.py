"""`mindsos instances` — Phase 06 L1 Instancing CLI surface.

Four verbs per Phase 06 row §H + round-7 P53 A exit codes:

  mindsos instances instantiate-node --metagraph MG --template-id NID
                                     [--override key=val]...
                                     [--materialise] [--json]

  mindsos instances instantiate-edge --metagraph MG --template-id EID
                                     [--override key=val]...
                                     [--materialise] [--json]

  mindsos instances instantiate-hyperedge --metagraph MG
                                          --template-id HID
                                          [--override key=val]...
                                          [--materialise] [--json]

  mindsos instances compose --metagraph MG
                            --member-spec JSON [--member-spec JSON]...
                            [--bundle-override key=val]...
                            [--materialise] [--json]

``--override key=val`` and ``--bundle-override key=val`` parse value
as JSON fragments (P42 A). Strings need explicit JSON quoting:

  --override age=31              (parses as int 31)
  --override name='"Alicia"'     (parses as str "Alicia")
  --override member_ids='["N1","N2"]'   (parses as list; coerced to set
                                          per round-7 P57 A)

``--member-spec`` JSON shape:
  {"kind":"node","template_id":"...","overrides":{...}}

Exit codes (round-7 P53 A — adopts 05d split):
  0  success
  1  invariant violation (OverrideScopeError, SubGraphInvariantError,
     CompositeCycleError, CrossMetagraphCompositeError,
     DanglingTemplateError)
  2  resource-not-found (unknown metagraph, unknown template-id,
     IdentityError)
  3  reserved (no Phase 06 use)

Single-call demonstration semantics (P12 B + P8 B): each CLI invocation
creates instances in a fresh ``element_registry``, optionally
materialises, prints, and exits. No state-file persistence across
calls; container ``--rm`` destroys the in-memory state cleanly.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from typing import Any, Dict, List, Optional

import typer

from mindsos_core.exceptions import CoreError, IdentityError
from mindsos_instances import (
    CompositeCycleError,
    CompositeInstance,
    CrossMetagraphCompositeError,
    DanglingTemplateError,
    EdgeInstance,
    HyperEdgeInstance,
    NodeInstance,
    OverrideScopeError,
    SubGraphInvariantError,
    attach_registry,
    canonicalize,
)

# Re-use the metagraph state-loader.
from mindsos_cli.commands.metagraph import _load_or_die as _load_metagraph_or_die


def _load_or_die(name: str):
    """Phase 06 wrapper — Resource-not-found exits 2 per row §H (round-7
    P53 A). The underlying Phase 05 ``_load_or_die`` uses exit 1 for
    FileNotFoundError; we re-raise as exit 2 for the instances CLI.
    """
    try:
        return _load_metagraph_or_die(name)
    except typer.Exit as exc:
        code = getattr(exc, "exit_code", 1)
        if code == 1:
            raise typer.Exit(code=EXIT_NOT_FOUND)
        raise

instances_app = typer.Typer(
    name="instances",
    help="L1 Instancing — instantiate / materialise element instances + composites.",
    no_args_is_help=True,
    add_completion=False,
)


# ── exit codes (round-7 P53 A) ──────────────────────────────────────────────


EXIT_OK = 0
EXIT_INVARIANT = 1
EXIT_NOT_FOUND = 2


# ── override parsing (P42 A — JSON-fragment values) ─────────────────────────


def _parse_override_pairs(pairs: List[str]) -> Dict[str, Any]:
    """Parse a list of ``key=val`` strings where val is a JSON fragment.

    Raises ``typer.BadParameter`` (which Typer converts to exit code 2
    via the usage-error path; we intercept and re-emit as exit 1 in
    the verb handler).
    """
    out: Dict[str, Any] = {}
    for pair in pairs:
        if "=" not in pair:
            raise typer.BadParameter(
                f"override {pair!r} must be in 'key=val' form"
            )
        key, _, raw_val = pair.partition("=")
        if not key:
            raise typer.BadParameter(
                f"override {pair!r} has empty key"
            )
        try:
            value = json.loads(raw_val)
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(
                f"override {pair!r} value {raw_val!r} is not valid JSON "
                f"({exc.msg}). Strings must be quoted: --override "
                f"name='\"...\"' (P42 A)."
            )
        out[key] = value
    return out


# ── output formatting ───────────────────────────────────────────────────────


def _print_instance_json(instance: Any) -> None:
    """Print the instance's shape (not materialised)."""
    payload = {
        "kind": type(instance).KIND,
        "id": instance.id,
        "template_id": getattr(instance, "template_id", None),
        "metagraph_id": instance.metagraph_id,
        "overrides": canonicalize(getattr(instance, "overrides", {})),
    }
    if isinstance(instance, CompositeInstance):
        payload["bundle_overrides"] = canonicalize(instance.bundle_overrides)
        payload["member_ids"] = instance.member_ids()
        # CompositeInstance has no template_id; drop the field.
        payload.pop("template_id", None)
        payload.pop("overrides", None)
    typer.echo(json.dumps(payload, indent=2, default=str))


def _print_materialised_json(core_obj_or_tree: Any) -> None:
    """Print the materialised object as JSON.

    For element-instance subclasses, ``core_obj_or_tree`` is a Core
    dataclass — we run ``asdict`` + canonicalize for stable output.
    For composites, ``core_obj_or_tree`` is already a recursive dict.
    """
    if isinstance(core_obj_or_tree, dict):
        # Already a composite tree; canonicalize for stability.
        payload = canonicalize(core_obj_or_tree)
    else:
        payload = canonicalize(asdict(core_obj_or_tree))
    typer.echo(json.dumps(payload, indent=2, default=str))


def _handle_error(exc: Exception) -> "typer.Exit":
    """Convert a Phase 06 exception to the canonical exit code."""
    if isinstance(
        exc,
        (
            OverrideScopeError,
            SubGraphInvariantError,
            CompositeCycleError,
            CrossMetagraphCompositeError,
            DanglingTemplateError,
        ),
    ):
        typer.echo(f"{type(exc).__name__}: {exc}", err=True)
        return typer.Exit(code=EXIT_INVARIANT)
    if isinstance(exc, IdentityError):
        typer.echo(f"IdentityError: {exc}", err=True)
        return typer.Exit(code=EXIT_NOT_FOUND)
    typer.echo(f"{type(exc).__name__}: {exc}", err=True)
    return typer.Exit(code=EXIT_INVARIANT)


# ── verb: instantiate-node ──────────────────────────────────────────────────


@instances_app.command("instantiate-node")
def instantiate_node(
    metagraph: str = typer.Option(
        ..., "--metagraph", help="Metagraph name (state-file)."
    ),
    template_id: str = typer.Option(
        ..., "--template-id", help="ID of the template Node."
    ),
    override: List[str] = typer.Option(
        [], "--override", help="Override key=val (JSON-fragment value)."
    ),
    materialise: bool = typer.Option(
        False,
        "--materialise",
        help="Print materialised Node JSON instead of instance shape.",
    ),
) -> None:
    """Create a ``NodeInstance``; print its JSON shape (or materialise)."""
    try:
        overrides = _parse_override_pairs(override)
    except typer.BadParameter as exc:
        typer.echo(f"InvalidOverride: {exc.message}", err=True)
        raise typer.Exit(code=EXIT_INVARIANT)

    mg = _load_or_die(metagraph)
    reg = attach_registry(mg)
    try:
        # Round-7 P58 A — template must exist somewhere in the metagraph.
        _ = _ensure_node_template(mg, template_id)
        instance = NodeInstance(
            metagraph_id=mg.metagraph_id,
            template_id=template_id,
            overrides=overrides,
            _registry=reg,
        )
        reg.add(instance)
        if materialise:
            _print_materialised_json(instance.materialise(mg))
        else:
            _print_instance_json(instance)
    except CoreError as exc:
        raise _handle_error(exc)


# ── verb: instantiate-edge ──────────────────────────────────────────────────


@instances_app.command("instantiate-edge")
def instantiate_edge(
    metagraph: str = typer.Option(..., "--metagraph"),
    template_id: str = typer.Option(..., "--template-id"),
    override: List[str] = typer.Option([], "--override"),
    materialise: bool = typer.Option(False, "--materialise"),
) -> None:
    """Create an ``EdgeInstance``."""
    try:
        overrides = _parse_override_pairs(override)
    except typer.BadParameter as exc:
        typer.echo(f"InvalidOverride: {exc.message}", err=True)
        raise typer.Exit(code=EXIT_INVARIANT)

    mg = _load_or_die(metagraph)
    reg = attach_registry(mg)
    try:
        _ensure_edge_template(mg, template_id)
        instance = EdgeInstance(
            metagraph_id=mg.metagraph_id,
            template_id=template_id,
            overrides=overrides,
            _registry=reg,
        )
        reg.add(instance)
        if materialise:
            _print_materialised_json(instance.materialise(mg))
        else:
            _print_instance_json(instance)
    except CoreError as exc:
        raise _handle_error(exc)


# ── verb: instantiate-hyperedge ─────────────────────────────────────────────


@instances_app.command("instantiate-hyperedge")
def instantiate_hyperedge(
    metagraph: str = typer.Option(..., "--metagraph"),
    template_id: str = typer.Option(..., "--template-id"),
    override: List[str] = typer.Option([], "--override"),
    materialise: bool = typer.Option(False, "--materialise"),
) -> None:
    """Create a ``HyperEdgeInstance``."""
    try:
        overrides = _parse_override_pairs(override)
    except typer.BadParameter as exc:
        typer.echo(f"InvalidOverride: {exc.message}", err=True)
        raise typer.Exit(code=EXIT_INVARIANT)

    mg = _load_or_die(metagraph)
    reg = attach_registry(mg)
    try:
        _ensure_hyperedge_template(mg, template_id)
        instance = HyperEdgeInstance(
            metagraph_id=mg.metagraph_id,
            template_id=template_id,
            overrides=overrides,
            _registry=reg,
        )
        reg.add(instance)
        if materialise:
            _print_materialised_json(instance.materialise(mg))
        else:
            _print_instance_json(instance)
    except CoreError as exc:
        raise _handle_error(exc)


# ── verb: compose (P41 A — inline JSON member-specs) ────────────────────────


@instances_app.command("compose")
def compose(
    metagraph: str = typer.Option(..., "--metagraph"),
    member_spec: List[str] = typer.Option(
        [],
        "--member-spec",
        help='Inline JSON spec, repeatable: \'{"kind":"node",'
        '"template_id":"...","overrides":{...}}\'',
    ),
    bundle_override: List[str] = typer.Option(
        [],
        "--bundle-override",
        help="Composite-level user property override key=val "
        "(JSON-fragment value).",
    ),
    materialise: bool = typer.Option(False, "--materialise"),
) -> None:
    """Create a ``CompositeInstance``; members built inline from
    ``--member-spec`` JSON; bundle-level user properties from
    ``--bundle-override``.
    """
    try:
        bundle_overrides = _parse_override_pairs(bundle_override)
    except typer.BadParameter as exc:
        typer.echo(f"InvalidBundleOverride: {exc.message}", err=True)
        raise typer.Exit(code=EXIT_INVARIANT)

    parsed_specs: List[Dict[str, Any]] = []
    for raw in member_spec:
        try:
            spec = json.loads(raw)
        except json.JSONDecodeError as exc:
            typer.echo(
                f"InvalidMemberSpec: --member-spec value is not valid "
                f"JSON ({exc.msg})",
                err=True,
            )
            raise typer.Exit(code=EXIT_INVARIANT)
        if not isinstance(spec, dict):
            typer.echo(
                "InvalidMemberSpec: --member-spec must be a JSON "
                "object with kind+template_id+optional overrides",
                err=True,
            )
            raise typer.Exit(code=EXIT_INVARIANT)
        parsed_specs.append(spec)

    mg = _load_or_die(metagraph)
    reg = attach_registry(mg)
    try:
        comp = CompositeInstance(
            metagraph_id=mg.metagraph_id,
            bundle_overrides=bundle_overrides,
            _registry=reg,
        )
        reg.add(comp)
        for spec in parsed_specs:
            kind = spec.get("kind")
            tid = spec.get("template_id")
            ov = spec.get("overrides") or {}
            if kind == "node":
                _ensure_node_template(mg, tid)
                member = NodeInstance(
                    metagraph_id=mg.metagraph_id,
                    template_id=tid,
                    overrides=ov,
                    _registry=reg,
                )
            elif kind == "edge":
                _ensure_edge_template(mg, tid)
                member = EdgeInstance(
                    metagraph_id=mg.metagraph_id,
                    template_id=tid,
                    overrides=ov,
                    _registry=reg,
                )
            elif kind == "hyperedge":
                _ensure_hyperedge_template(mg, tid)
                member = HyperEdgeInstance(
                    metagraph_id=mg.metagraph_id,
                    template_id=tid,
                    overrides=ov,
                    _registry=reg,
                )
            else:
                typer.echo(
                    f"InvalidMemberSpec: kind {kind!r} not supported "
                    f"in compose verb (allowed: node, edge, hyperedge).",
                    err=True,
                )
                raise typer.Exit(code=EXIT_INVARIANT)
            reg.add(member)
            comp.add_member(member, _registry=reg)
        if materialise:
            _print_materialised_json(comp.materialise(mg))
        else:
            _print_instance_json(comp)
    except CoreError as exc:
        raise _handle_error(exc)


# ── private helpers ─────────────────────────────────────────────────────────


def _ensure_node_template(mg, tid: str) -> None:
    if tid is None:
        raise IdentityError("template_id is required")
    for g in mg.graphs.values():
        if tid in g.nodes:
            return
    raise IdentityError(
        f"Node template {tid!r} not found in any contained graph of "
        f"metagraph {mg.name!r}."
    )


def _ensure_edge_template(mg, tid: str) -> None:
    if tid is None:
        raise IdentityError("template_id is required")
    for g in mg.graphs.values():
        if tid in g.edges:
            return
    raise IdentityError(
        f"Edge template {tid!r} not found in any contained graph of "
        f"metagraph {mg.name!r}."
    )


def _ensure_hyperedge_template(mg, tid: str) -> None:
    if tid is None:
        raise IdentityError("template_id is required")
    for g in mg.graphs.values():
        if tid in g.hyperedges:
            return
    raise IdentityError(
        f"HyperEdge template {tid!r} not found in any contained graph "
        f"of metagraph {mg.name!r}."
    )


# ── registration helper ─────────────────────────────────────────────────────


def register_instances_app(parent: typer.Typer) -> None:
    """Wire the instances sub-app onto a parent Typer app."""
    parent.add_typer(instances_app, name="instances")
