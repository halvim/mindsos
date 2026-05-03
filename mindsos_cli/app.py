"""Top-level Typer app — wires subcommands."""

import typer

from mindsos_cli.commands.doctor import doctor
from mindsos_cli.commands.version import show_version

app = typer.Typer(
    name="mindsos",
    help="MindsOS command-line interface (Phase 00 — runtime infrastructure).",
    no_args_is_help=True,
    add_completion=False,
)
app.command(name="version", help="Print version, git SHA, and image build hash.")(
    show_version
)
app.command(
    name="doctor",
    help="Smoke-check runtime; with --self-test, verify pin parity vs manifest.toml.",
)(doctor)
