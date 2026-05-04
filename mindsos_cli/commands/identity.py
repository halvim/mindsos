"""`mindsos identity` — Phase 02 L1 Identity CLI surface.

Subcommands:

  mindsos identity strategies [--json]
      Enumerate the three shipped IdStrategy implementations.

  mindsos identity mint --strategy {uuid4|uuid5|iri} [--kind KIND]
                        [--seed JSON|@PATH] [--json]
      Mint a fresh id under the chosen strategy. ``--strategy`` is
      required (per ADR-0131 — the CLI must not silently default-pin
      a strategy).

  mindsos identity registry [--scope NAME] [--state-file PATH]
                            [--register ID]... [--list] [--clear]
                            [--json]
      Exercise an IdentityRegistry. Persists to a JSON state file
      across invocations so the duplicate-rejection path can be
      reproduced interactively. Debug-only — not a substitute for
      the metagraph-scoped registry that Phase 05 will exercise.

All subcommands respect ``--json`` for structured output. Errors print
to stderr and exit non-zero (PHASE_MAP §1 "CLI conventions").

IRI parsing is **out of scope** for Phase 02. Per ADR-0035 + the row's
risk note, Core treats ``node_id`` as opaque; IRI structural parsing
lives in L2 (``mindsos_knowledge``) and ships in Phase 12.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

import typer

from mindsos_core import (
    IRIPassthroughStrategy,
    IdentityError,
    IdentityRegistry,
    UUID4Strategy,
    UUID5FromContentStrategy,
    generate_uuid,
)


identity_app = typer.Typer(
    name="identity",
    help="L1 Identity primitives — mint ids, inspect a registry, list strategies.",
    no_args_is_help=True,
    add_completion=False,
)


# ---------------------------------------------------------------------------
# strategies
# ---------------------------------------------------------------------------


_STRATEGY_DESCRIPTIONS = (
    {
        "name": "uuid4",
        "class": "mindsos_core.UUID4Strategy",
        "deterministic": False,
        "ignores_content": True,
        "description": (
            "Default strategy — non-deterministic UUID4 per call. Content is "
            "ignored. Matches the historical mindsos_core behaviour."
        ),
    },
    {
        "name": "uuid5",
        "class": "mindsos_core.UUID5FromContentStrategy",
        "deterministic": True,
        "ignores_content": False,
        "description": (
            "Deterministic UUID5 derived from canonical (kind, content) under "
            "NAMESPACE_MINDSOS. Same content + kind always yields the same id. "
            "Not safe under release auto-upgrade — content-addressable ids "
            "change with content."
        ),
    },
    {
        "name": "iri",
        "class": "mindsos_core.IRIPassthroughStrategy",
        "deterministic": True,
        "ignores_content": False,
        "description": (
            "Returns content['iri'] verbatim when supplied (KL importer "
            "convention). Falls back to UUID4 when no 'iri' key is present. "
            "Phase 02 does not parse the IRI — it is treated as opaque."
        ),
    },
)


@identity_app.command(
    name="strategies",
    help="Enumerate the three shipped IdStrategy implementations.",
)
def strategies_cmd(
    json_out: bool = typer.Option(
        False, "--json", help="Emit JSON instead of human text."
    ),
) -> None:
    """List supported IdStrategy implementations (ADR-0131)."""
    if json_out:
        typer.echo(json.dumps({"strategies": list(_STRATEGY_DESCRIPTIONS)}, indent=2))
        return
    for spec in _STRATEGY_DESCRIPTIONS:
        typer.echo(
            f"{spec['name']:<6} {spec['class']}\n"
            f"    deterministic: {spec['deterministic']}, "
            f"ignores_content: {spec['ignores_content']}\n"
            f"    {spec['description']}"
        )


# ---------------------------------------------------------------------------
# mint
# ---------------------------------------------------------------------------


def _resolve_seed(raw: Optional[str]) -> Optional[dict[str, Any]]:
    """Parse ``--seed`` either as inline JSON or ``@PATH`` to a JSON file."""
    if raw is None:
        return None
    text = raw
    if raw.startswith("@"):
        path = Path(raw[1:])
        if not path.exists():
            typer.echo(f"--seed file not found: {path}", err=True)
            raise typer.Exit(code=2)
        text = path.read_text()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        typer.echo(f"--seed is not valid JSON: {exc}", err=True)
        raise typer.Exit(code=2)
    if not isinstance(parsed, dict):
        typer.echo(
            f"--seed must decode to a JSON object, got {type(parsed).__name__}",
            err=True,
        )
        raise typer.Exit(code=2)
    return parsed


def _instantiate_strategy(name: str):
    if name == "uuid4":
        return UUID4Strategy()
    if name == "uuid5":
        return UUID5FromContentStrategy()
    if name == "iri":
        return IRIPassthroughStrategy()
    typer.echo(
        f"unknown --strategy {name!r}. Valid: uuid4, uuid5, iri.",
        err=True,
    )
    raise typer.Exit(code=2)


@identity_app.command(
    name="mint",
    help="Mint a fresh id under the chosen IdStrategy. --strategy is required.",
)
def mint_cmd(
    strategy: Optional[str] = typer.Option(
        None,
        "--strategy",
        help="One of: uuid4, uuid5, iri. No default — must be explicit.",
    ),
    kind: str = typer.Option(
        "node",
        "--kind",
        help="Element kind label (advisory; UUID4 ignores it).",
    ),
    seed: Optional[str] = typer.Option(
        None,
        "--seed",
        help="JSON object (inline or '@PATH'). Required for uuid5; optional for iri.",
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Emit JSON instead of human text."
    ),
) -> None:
    """Mint a fresh id."""
    if strategy is None:
        typer.echo(
            "--strategy is required. Choose one of: uuid4, uuid5, iri. "
            "(ADR-0131: the CLI must not silently default-pin a strategy.)",
            err=True,
        )
        raise typer.Exit(code=2)

    strat = _instantiate_strategy(strategy)
    content = _resolve_seed(seed)

    try:
        new_id = strat.generate(kind, content)
    except IdentityError as exc:
        typer.echo(f"IdentityError: {exc}", err=True)
        raise typer.Exit(code=1)

    payload = {
        "id": new_id,
        "strategy": strategy,
        "kind": kind,
        "content": content,
    }
    if json_out:
        typer.echo(json.dumps(payload, indent=2))
    else:
        typer.echo(new_id)


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------


def _default_state_dir() -> Path:
    """Return the default state directory: $MINDSOS_STATE_DIR or ~/.mindsos.

    Inside the test container, ``$MINDSOS_STATE_DIR`` may be set to a
    tmpfs-mounted path; outside it defaults to the user's home.
    """
    val = os.environ.get("MINDSOS_STATE_DIR")
    if val:
        return Path(val)
    return Path.home() / ".mindsos"


def _state_file_for(scope: str, override: Optional[Path]) -> Path:
    if override is not None:
        return override
    return _default_state_dir() / f"identity-registry-{scope}.json"


def _load_state(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        typer.echo(f"state file corrupt: {path}: {exc}", err=True)
        raise typer.Exit(code=1)
    ids = data.get("ids") if isinstance(data, dict) else None
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        typer.echo(
            f"state file shape unexpected: {path}: expected dict with 'ids' "
            "list of strings.",
            err=True,
        )
        raise typer.Exit(code=1)
    return ids


def _write_state(path: Path, ids: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"ids": sorted(ids)}, indent=2) + "\n")


@identity_app.command(
    name="registry",
    help="Exercise an IdentityRegistry. State persists across invocations via a JSON file.",
)
def registry_cmd(
    scope: str = typer.Option(
        "default",
        "--scope",
        help="Logical scope name (defaults state-file path).",
    ),
    register: list[str] = typer.Option(
        [],
        "--register",
        help="Register an id. Repeatable. Duplicate within the scope exits non-zero.",
    ),
    list_: bool = typer.Option(
        False, "--list", help="Print the current registered ids."
    ),
    clear: bool = typer.Option(
        False, "--clear", help="Empty the scope's registry."
    ),
    state_file: Optional[Path] = typer.Option(
        None,
        "--state-file",
        help="Override the state-file path (default: $MINDSOS_STATE_DIR or ~/.mindsos).",
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Emit JSON instead of human text."
    ),
) -> None:
    """Inspect / mutate an IdentityRegistry persisted to a JSON state file."""
    path = _state_file_for(scope, state_file)
    ids = _load_state(path)

    registry = IdentityRegistry()
    for uid in ids:
        # `register` raises on duplicate; we trust prior writes were clean,
        # but the load_state path validates types.
        try:
            registry.register(uid)
        except IdentityError as exc:
            typer.echo(
                f"state file invariant violated: {path} contains duplicate {uid!r}: "
                f"{exc}",
                err=True,
            )
            raise typer.Exit(code=1)

    actions: list[str] = []

    if clear:
        registry.clear()
        actions.append("clear")

    for uid in register:
        try:
            registry.register(uid)
            actions.append(f"register:{uid}")
        except IdentityError as exc:
            typer.echo(f"IdentityError: {exc}", err=True)
            # Persist nothing on duplicate — the registry's pre-duplicate
            # state is what's already on disk; we exit without rewriting.
            raise typer.Exit(code=1)

    # Persist on any state-changing action.
    if clear or register:
        _write_state(path, sorted(registry.ids))

    if list_ or json_out:
        listed = sorted(registry.ids)
        if json_out:
            typer.echo(
                json.dumps(
                    {
                        "scope": scope,
                        "state_file": str(path),
                        "ids": listed,
                        "count": len(listed),
                        "actions": actions,
                    },
                    indent=2,
                )
            )
        else:
            typer.echo(f"scope={scope} state_file={path} count={len(listed)}")
            for uid in listed:
                typer.echo(f"  {uid}")
        return

    if not actions:
        typer.echo(
            "No action requested. Use --register, --list, or --clear.",
            err=True,
        )
        raise typer.Exit(code=2)

    if not json_out:
        for action in actions:
            typer.echo(f"ok: {action}")


# ---------------------------------------------------------------------------
# Compatibility for app.py
# ---------------------------------------------------------------------------


def register_identity_app(parent: typer.Typer) -> None:
    """Wire the identity sub-app onto a parent Typer app."""
    parent.add_typer(identity_app, name="identity")
