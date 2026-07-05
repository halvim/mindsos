"""``mindsos brain`` — the resident-brain REPL.

One long-lived process holds a single live :class:`~mindsos_server.boot.Stack`.
The user tasks it (``task``) and probes it live (``ls`` / ``datastate`` /
``caps`` / ``verify``); state accrues in-process across commands. The
user's Local is persisted to Falkor on ``save`` / ``quit`` (durable mode).

Verb dispatch is a pure ``BrainREPL.dispatch(line) -> str`` so the loop is
testable headless. ``loop()`` is the thin stdin front end.
"""

from __future__ import annotations

import json
from typing import Any, List

import typer

brain_app = typer.Typer(
    name="brain",
    help="Resident-brain REPL — task and probe one live instance.",
)

_HELP = """\
verbs:
  ls [category]        list capabilities (optionally one category)
  datastate [iri]      list datastates; with IRI show its producers/consumers
  caps                 list capabilities with their consumes/produces wiring
  verify               structural catalog check (dangling / orphan / terminal)
  invoke <iri> [json]  dispatch one capability; json maps datastate-iri -> value
  task <text>          run the six-phase lifecycle over <text>
  save                 persist this user's Local to Falkor
  reset                wipe run-state (episodic memory), keep learned params
  help                 show this
  quit                 save then exit"""


class BrainREPL:
    """Stateful verb dispatcher over one held :class:`Stack`."""

    def __init__(self, stack: Any) -> None:
        self.stack = stack

    def dispatch(self, line: str) -> str:
        """Execute one verb line; return the rendered output."""
        parts = line.strip().split()
        if not parts:
            return ""
        verb, args = parts[0], parts[1:]
        handler = getattr(self, f"_do_{verb}", None)
        if handler is None:
            return f"unknown verb: {verb!r} (try 'help')"
        return handler(args)

    # ── probe verbs ───────────────────────────────────────────────────

    def _do_ls(self, args: List[str]) -> str:
        view = self.stack.global_view()
        category = args[0] if args else None
        iris = sorted(n.node_id for n in view.iter_capacities(category))
        if not iris:
            return f"(no capabilities{' in ' + category if category else ''})"
        header = f"{len(iris)} capabilit{'y' if len(iris) == 1 else 'ies'}"
        return header + ":\n" + "\n".join(f"  {i}" for i in iris)

    def _do_datastate(self, args: List[str]) -> str:
        view = self.stack.global_view()
        if not args:
            iris = sorted(n.node_id for n in view.iter_datastates())
            if not iris:
                return "(no datastates)"
            return f"{len(iris)} datastates:\n" + "\n".join(f"  {i}" for i in iris)
        iri = args[0]
        if view.get_datastate(iri) is None:
            return f"no such datastate: {iri!r}"
        producers = sorted(n.node_id for n in view.producers_of(iri))
        consumers = sorted(n.node_id for n in view.consumers_of(iri))
        out = [iri]
        out.append("  produced by: " + (", ".join(producers) if producers else "(none)"))
        out.append("  consumed by: " + (", ".join(consumers) if consumers else "(none)"))
        return "\n".join(out)

    def _do_caps(self, args: List[str]) -> str:
        view = self.stack.global_view()
        lines: List[str] = []
        for n in sorted(view.iter_capacities(), key=lambda n: n.node_id):
            iri = n.node_id
            ins = sorted(view.inputs_of(iri))
            outs = sorted(view.outputs_of(iri))
            lines.append(iri)
            lines.append("    consumes: " + (", ".join(ins) if ins else "(none)"))
            lines.append("    produces: " + (", ".join(outs) if outs else "(none)"))
        return "\n".join(lines) if lines else "(no capabilities)"

    def _do_verify(self, args: List[str]) -> str:
        from mindsos_capacity.catalog_check import catalog_check

        r = catalog_check(self.stack.global_view())
        lines = [
            f"catalog: {r.capacities} capabilities, {r.datastates} datastates",
            f"  status: {'OK' if r.ok else 'ORPHANS'}",
            f"  sources: {len(r.sources)}  sinks: {len(r.sinks)}  orphans: {len(r.orphans)}",
        ]
        if r.orphans:
            lines.append("  orphan datastates: " + ", ".join(r.orphans))
        return "\n".join(lines)

    # ── task + persistence verbs ──────────────────────────────────────

    def _do_invoke(self, args: List[str]) -> str:
        if not args:
            return "usage: invoke <cap_iri> [json-inputs]"
        cap_iri = args[0]
        view = self.stack.global_view()
        if view.get_capacity(cap_iri) is None:
            return f"no such capability: {cap_iri!r}"
        raw = " ".join(args[1:]).strip() or "{}"
        try:
            inputs = json.loads(raw)
        except json.JSONDecodeError as e:
            return f"bad json inputs: {e}"
        if not isinstance(inputs, dict):
            return "inputs must be a JSON object (datastate-iri -> value)"
        try:
            result = self.stack.dispatcher.dispatch(cap_iri, inputs)
        except Exception as e:
            return f"invoke error: {type(e).__name__}: {e}"
        if not result.success:
            return f"invoke failed: {result.error}"
        if getattr(result, "needs_input", None) is not None:
            return f"needs input: {result.needs_input}"
        outs = dict(result.outputs)
        if not outs:
            return "ok (no outputs / write capability)"
        return "outputs:\n" + "\n".join(f"  {k} = {v!r}" for k, v in outs.items())

    def _do_task(self, args: List[str]) -> str:
        if not args:
            return "usage: task <text>"
        text = " ".join(args)
        outcome = self.stack.orch.run_lifecycle({"text": text})
        return f"task: {outcome.status}"

    def _do_save(self, args: List[str]) -> str:
        if self.stack.persister is None:
            return "save: no persister (ephemeral)"
        self.stack.save()
        return f"saved Local for {self.stack.user!r}"

    def _do_reset(self, args: List[str]) -> str:
        p = self.stack.persister
        if p is None or not hasattr(p, "reset_run_state"):
            return "reset: unsupported (ephemeral)"
        existed = p.reset_run_state(self.stack.user)
        return "run-state wiped" if existed else "(no Local to reset)"

    def _do_help(self, args: List[str]) -> str:
        return _HELP

    # `quit` is handled by the loop (needs to break); dispatch echoes intent.
    def _do_quit(self, args: List[str]) -> str:
        return ""


def loop(repl: BrainREPL) -> None:
    """Read-eval-print until EOF or ``quit``."""
    typer.echo("MindsOS resident brain. Type 'help', 'quit' to exit.")
    while True:
        try:
            line = input("brain> ").strip()
        except (EOFError, KeyboardInterrupt):
            typer.echo("")
            line = "quit"
        if line in ("quit", "exit"):
            out = repl._do_save([])
            typer.echo(out)
            typer.echo("bye")
            return
        if not line:
            continue
        typer.echo(repl.dispatch(line))


@brain_app.callback(invoke_without_command=True)
def brain(
    user: str = typer.Option("default", "--user", "-u", help="Local user this brain serves."),
    ephemeral: bool = typer.Option(
        False, "--ephemeral", help="In-memory only (no Falkor, no persistence)."
    ),
) -> None:
    """Boot one resident brain and drop into the REPL."""
    from mindsos_server.boot import boot_brain

    client = None
    if not ephemeral:
        from mindsos_core.config import FalkorConfig
        from mindsos_core.persistence.client import FalkorClient

        client = FalkorClient(FalkorConfig.from_env())
    try:
        stack = boot_brain(client, user=user)
        loop(BrainREPL(stack))
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


def register_brain_app(parent: typer.Typer) -> None:
    """Register the ``brain`` subapp on the root Typer."""
    parent.add_typer(brain_app, name="brain")


__all__ = ["BrainREPL", "loop", "brain_app", "register_brain_app"]
