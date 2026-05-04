"""Top-level Typer app — wires subcommands."""

import typer

from mindsos_cli.commands.confirm_phase import confirm_phase
from mindsos_cli.commands.doctor import doctor
from mindsos_cli.commands.graph import register_graph_app
from mindsos_cli.commands.identity import register_identity_app
from mindsos_cli.commands.schema import register_schema_app
from mindsos_cli.commands.version import show_version

app = typer.Typer(
    name="mindsos",
    help="MindsOS command-line interface (Phase 04 — L1 Schema + Graph integration).",
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
app.command(
    name="confirm-phase",
    help="Generate or initialise a phase confirmation document.",
)(confirm_phase)
register_identity_app(app)
register_graph_app(app)
register_schema_app(app)
