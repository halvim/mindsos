"""``mindsos skill`` — skill-bundle install lifecycle (Phase 50; ADR-0183).

Verbs:

  mindsos skill install --manifest <path> [--json] [--persist]
  mindsos skill uninstall <name> [--json] [--persist]
  mindsos skill list [--json]
  mindsos skill activate [--json]

Session model mirrors the Phase 30-31 capacity CLI: **session-less,
Global-only** (the ADR-0080 bootstrap carve-out — same as `mindsos
admin import-*`). The ADR-0183 capability gate engages on the
server-session path; the CLI path is the admin's own machine. No
``--session-token`` flag yet (Phase 31 R2 PB-30(a) carry-forward).

State model: the Global metagraph is loaded from FalkorDB when
reachable and a ``global_knowledge`` metagraph exists there; otherwise
a fresh ``KnowledgeLayer.bootstrap()`` (useful for ``--json`` dry-run
exercises). ``--persist`` flushes the mutated Global back to FalkorDB
(MERGE-idempotent, the `admin import` precedent) — the install record's
structured ``value`` rides the ADR-0182 ``_value_json`` round-trip.

Activation (`skill activate`) is the design-log PB-4 v1 caller of
:func:`mindsos_server.skills.apply_installed_skills`: it builds a fresh
in-memory CapacityLayer (text builtins installed, mirroring `capacity
invoke`), re-runs the installed bundles' L3 installers, and reports.

Exit codes: 0 success; 1 rejected/refused/failed (reasons on stderr);
2 Typer usage error.
"""

from __future__ import annotations

import json as _json
from pathlib import Path
from typing import Any, Optional, Tuple

import typer

skill_app = typer.Typer(
    name="skill",
    help="Skill-bundle install lifecycle (Phase 50 — ADR-0183).",
    no_args_is_help=True,
)


def _build_kl_and_client() -> Tuple[Any, Optional[Any]]:
    """Global KL from Falkor when reachable, else fresh bootstrap."""
    from mindsos_knowledge import KnowledgeLayer

    try:
        from mindsos_core.config import FalkorConfig
        from mindsos_core.persistence.client import FalkorClient
        from mindsos_core.reconstruction import MetagraphLoader

        client = FalkorClient(FalkorConfig.from_env())
        loader = MetagraphLoader(client)
        mid = loader.find_by_name("global_knowledge")
        if mid is not None:
            return KnowledgeLayer(global_metagraph=loader.load(mid)), client
        return KnowledgeLayer.bootstrap(), client
    except Exception:
        return KnowledgeLayer.bootstrap(), None


def _build_cl() -> Any:
    from mindsos_capacity import CapacityLayer
    from mindsos_capacity.builtins.text import install_text_capacities

    cl = CapacityLayer()
    install_text_capacities(cl)
    return cl


def _persist_global(kl: Any, client: Any) -> bool:
    if client is None:
        return False
    from mindsos_core.persistence import MetagraphRepository

    MetagraphRepository(client).persist(kl.global_metagraph())
    return True


def _close(client: Any) -> None:
    if client is not None:
        try:
            client.close()
        except Exception:
            pass


@skill_app.command(name="install", help="Install a skill bundle from a TOML manifest.")
def skill_install(
    manifest: Path = typer.Option(
        ...,
        "--manifest",
        "-m",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to the bundle manifest.toml.",
    ),
    persist: bool = typer.Option(
        False,
        "--persist",
        help="Flush the mutated Global metagraph back to FalkorDB.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON."),
) -> None:
    from mindsos_server.skills import (
        SkillInstallError,
        SkillInstallRejectedError,
        install_skill,
        parse_manifest,
    )
    from mindsos_server.skills.manifest import ManifestError

    kl, client = _build_kl_and_client()
    try:
        try:
            m = parse_manifest(manifest)
            result = install_skill(m, kl=kl, cl=_build_cl())
        except (ManifestError, SkillInstallRejectedError, SkillInstallError) as e:
            typer.echo(f"install rejected/failed: {e}", err=True)
            raise typer.Exit(code=1)
        persisted = _persist_global(kl, client) if persist else False
        payload = {
            "bundle_name": result.bundle_name,
            "bundle_version": result.bundle_version,
            "bundle_digest": result.bundle_digest,
            "no_op": result.no_op,
            "l2_written": list(result.l2_written),
            "installers_run": list(result.installers_run),
            "record_iri": result.record.iri if result.record else None,
            "persisted": persisted,
        }
        if as_json:
            typer.echo(_json.dumps(payload, indent=2, sort_keys=True))
        else:
            for key in sorted(payload):
                typer.echo(f"{key}={payload[key]}")
    finally:
        _close(client)


@skill_app.command(name="uninstall", help="De-install a bundle (deprecate, never delete).")
def skill_uninstall(
    name: str = typer.Argument(..., help="Bundle name to de-install."),
    persist: bool = typer.Option(
        False,
        "--persist",
        help="Flush the mutated Global metagraph back to FalkorDB.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON."),
) -> None:
    from mindsos_server.skills import (
        SkillUninstallRefusedError,
        uninstall_skill,
    )

    kl, client = _build_kl_and_client()
    try:
        try:
            result = uninstall_skill(name, kl=kl)
        except SkillUninstallRefusedError as e:
            typer.echo(f"uninstall refused: {e}", err=True)
            raise typer.Exit(code=1)
        persisted = _persist_global(kl, client) if persist else False
        payload = {
            "bundle_name": result.bundle_name,
            "bundle_version": result.bundle_version,
            "deprecated_node_ids": list(result.deprecated_node_ids),
            "record_iri": result.record.iri,
            "persisted": persisted,
        }
        if as_json:
            typer.echo(_json.dumps(payload, indent=2, sort_keys=True))
        else:
            for key in sorted(payload):
                typer.echo(f"{key}={payload[key]}")
    finally:
        _close(client)


@skill_app.command(name="list", help="List bundle states (latest record per bundle).")
def skill_list(
    as_json: bool = typer.Option(False, "--json", help="Emit JSON."),
) -> None:
    from mindsos_server.skills import latest_records_by_bundle

    kl, client = _build_kl_and_client()
    try:
        latest = latest_records_by_bundle(kl)
        rows = [
            {
                "bundle_name": v.bundle_name,
                "bundle_version": v.bundle_version,
                "status": v.status,
                "recorded_at": v.recorded_at,
                "seq": v.seq,
            }
            for v in sorted(latest.values(), key=lambda v: v.seq)
        ]
        if as_json:
            typer.echo(_json.dumps({"bundles": rows}, indent=2, sort_keys=True))
        elif not rows:
            typer.echo("no skill bundles recorded")
        else:
            for row in rows:
                typer.echo(
                    f"{row['bundle_name']}@{row['bundle_version']} "
                    f"status={row['status']} seq={row['seq']}"
                )
    finally:
        _close(client)


@skill_app.command(
    name="activate",
    help="Re-run installed bundles' L3 installers on a fresh layer (ADR-0183 §6 stage 2).",
)
def skill_activate(
    as_json: bool = typer.Option(False, "--json", help="Emit JSON."),
) -> None:
    from mindsos_server.skills import apply_installed_skills

    kl, client = _build_kl_and_client()
    try:
        activated = apply_installed_skills(_build_cl(), kl)
        if as_json:
            typer.echo(
                _json.dumps({"activated": list(activated)}, indent=2)
            )
        else:
            typer.echo(
                "activated: " + (", ".join(activated) if activated else "(none)")
            )
    finally:
        _close(client)


def register_skill_app(parent: typer.Typer) -> None:
    """Register the ``skill`` subapp on the root Typer."""
    parent.add_typer(skill_app, name="skill")
