"""`mindsos version` — prints semver, git SHA, and image build hash."""

from __future__ import annotations

import json
import os

import typer

from mindsos_cli import __version__


def show_version(
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of text."),
) -> None:
    """Print the MindsOS CLI version, git SHA, and image build hash.

    git_sha and image_hash are baked into the image at build time via Docker
    build args (MINDSOS_GIT_SHA, MINDSOS_IMAGE_HASH). Outside the image, both
    fall back to "unknown".
    """
    info = {
        "version": __version__,
        "git_sha": os.environ.get("MINDSOS_GIT_SHA", "unknown"),
        "image_hash": os.environ.get("MINDSOS_IMAGE_HASH", "unknown"),
    }
    if json_out:
        typer.echo(json.dumps(info, indent=2))
    else:
        typer.echo(f"mindsos {info['version']}")
        typer.echo(f"  git_sha:    {info['git_sha']}")
        typer.echo(f"  image_hash: {info['image_hash']}")
