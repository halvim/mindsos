"""Top-level Typer app — wires subcommands."""

import typer

from mindsos_cli.commands.admin import register_admin_app
from mindsos_cli.commands.confirm_phase import confirm_phase
from mindsos_cli.commands.doctor import doctor
from mindsos_cli.commands.graph import register_graph_app
from mindsos_cli.commands.identity import register_identity_app
from mindsos_cli.commands.instances import register_instances_app
from mindsos_cli.commands.knowledge import register_knowledge_app
from mindsos_cli.commands.metagraph import register_metagraph_app
from mindsos_cli.commands.metagraph_schema import register_metagraph_schema_app
from mindsos_cli.commands.persistence import register_persistence_app
from mindsos_cli.commands.schema import register_schema_app
from mindsos_cli.commands.version import show_version

app = typer.Typer(
    name="mindsos",
    help=(
        "MindsOS command-line interface "
        "(Phase 08 — L1 Reconstruction: MetagraphLoader + iter_load_graph "
        "(streaming) + load_metagraph + InstanceLoader (sibling-package "
        "after_load observer subscriber) + first L1 WAL consumer "
        "(recover-on-load) + 3 new exception classes (RefreshUnsafeError "
        "/ WALReplayerMissingError / RoleMismatchError) + `mindsos "
        "persistence sync --metagraph M` + `load --metagraph M` "
        "(9-line summary; --to-json sibling) + `verify --source=db "
        "--metagraph M` unblock + `--graph G | --metagraph M` mutex; "
        "inherits L1 Persistence / Instancing / IntergraphEdge / "
        "MetagraphSchema / Metagraph / Schema / Graph)."
    ),
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
register_metagraph_app(app)
register_metagraph_schema_app(app)
register_instances_app(app)
register_knowledge_app(app)
register_persistence_app(app)
# Phase 15a — NEW `mindsos admin` group (importers + future scanner/promotion).
register_admin_app(app)
