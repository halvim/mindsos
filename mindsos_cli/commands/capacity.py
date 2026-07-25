"""`mindsos capacity` — L3 Capacity CLI surface (Phase 30-31).

Sub-subgroup shape:

  mindsos capacity find --start <ds_iri> --target <ds_iri>
                        [--max-depth N] [--json]
      [Phase 30] Run datastate-keyed BFS over the auto-discovered
      TYPE_COMPAT graph (ADR-0071); print the shortest pipeline by
      capacity count. Default human-readable arrow chain; ``--json``
      emits the verbose Pipeline shape (steps + dataflow edges).

  mindsos capacity problem-trace tail [--limit N] [--json]
      [Phase 30] Peek at the most-recent N ProblemTraceRecords on the
      current CapacityLayer's sink (default N=10). Peek-only — does
      NOT drain (L4 lifecycle owns drain per ADR-0074).

  mindsos capacity invoke <iri>
                          (--input-json '<json>' | --input-file <path>)
                          [--json] [--task-id <id>]
      [Phase 31] Invoke a registered Capacity by IRI. The CLI builds
      a fresh in-memory layer, auto-installs text builtins (R0 PB-ε
      opt-in but CLI's fresh-layer init calls it — only family at
      Phase 31; future families flagged via ``--install-builtins``
      per R3 PB-29 deferral), parses inputs from ``--input-json`` XOR
      ``--input-file``, and prints the InvocationResult envelope.

      Default --human; ``--json`` emits the full InvocationResult
      envelope as JSON (R1 PB-15 lock).

**Phase 30-31 CLI is Global-only.** No ``--session-token`` flag yet
(R2 PB-30(a) lock; carry-forward). All operations target Global.

**Exit code policy:**

* exit 0 — success (and ALWAYS when ``--json`` is supplied — R0 PB-7
  hybrid lock; the envelope's ``success`` bool carries failure)
* exit 1 — L3 invariant raise (``PipelineNotFoundError`` from ``find``;
  ``CapacityRegistrationError`` from ``invoke`` for unknown IRI)
* exit 2 — Typer usage error (missing arg, mutex flag conflict)
* exit 3 — invoke envelope failure on --human (``InvocationResult.success
  == False``; the bound implementation raised). R5 PB-61 → Phase 31
  R3 PB-32 lock.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from typing import Any, Mapping, Optional

import typer

from mindsos_capacity import (
    CapacityLayer,
    CapacityRegistrationError,
    InvocationResult,
    Pipeline,
    PipelineNotFoundError,
    ProblemTraceRecord,
    find_pipeline,
)
from mindsos_capacity.builtins import install_text_capacities


capacity_app = typer.Typer(
    name="capacity",
    help=(
        "L3 Capacity — BFS pipeline finder + problem-trace tail. "
        "Phase 30 ships read-only verbs against a fresh in-memory "
        "layer (Global only); ``invoke`` arrives at Phase 31."
    ),
    no_args_is_help=True,
    add_completion=False,
)


problem_trace_app = typer.Typer(
    name="problem-trace",
    help="Peek at recent ProblemTraceRecords on the current layer.",
    no_args_is_help=True,
    add_completion=False,
)
capacity_app.add_typer(problem_trace_app, name="problem-trace")


def _construct_global_layer() -> CapacityLayer:
    """Build a fresh empty CapacityLayer (Global only).

    Phase 30 R2 PB-27(a) lock — CLI is programmer-facing this phase;
    real-user workflows that need registered capacities arrive at
    Phase 31 (text builtins auto-register) or Phase 26b-style Falkor
    bootstrap when it lands.
    """
    return CapacityLayer()


def _pipeline_to_dict(pipeline: Pipeline) -> dict:
    """Render a Pipeline (converging DAG) as a verbose JSON-ready dict.

    R2 PB-33(a); updated for the DAG shape (ADR-0071 §am-2): plural
    ``start_datastates`` and explicit dataflow ``edges`` replace the old
    linear ``start_datastate`` / per-step ``via_datastate``.
    """
    return {
        "start_datastates": list(pipeline.start_datastates),
        "target_datastate": pipeline.target_datastate,
        "length": len(pipeline),
        "steps": [
            {
                "capacity_iri": step.capacity_iri,
                "input_datastates": list(step.input_datastates),
                "output_datastates": list(step.output_datastates),
            }
            for step in pipeline.steps
        ],
        "edges": [
            {
                "producer": edge.producer,
                "consumer": edge.consumer,
                "datastate": edge.datastate,
            }
            for edge in pipeline.edges
        ],
    }


def _pipeline_to_human(pipeline: Pipeline) -> str:
    """Render a Pipeline as an arrow chain for human-readable output.

    The BFS back-compat path (``find_pipeline``) yields a degenerate-
    linear DAG, so the topologically-ordered ``steps`` read as a chain.
    """
    starts = ", ".join(pipeline.start_datastates)
    if not pipeline.steps:
        return f"{starts} (already at target; 0 capacities)"
    chain = [starts]
    for step in pipeline.steps:
        chain.append(step.capacity_iri)
        chain.append(step.output_datastates[0] if step.output_datastates else "?")
    chain[-1] = pipeline.target_datastate
    return " -> ".join(chain)


def _record_to_dict(record: ProblemTraceRecord) -> dict:
    """Render a ProblemTraceRecord as a JSON-ready dict."""
    return {
        "entry_id": record.entry_id,
        "timestamp": record.timestamp,
        "task_id": record.request_id,
        "error_kind": record.error_kind,
        "step_id": record.step_id,
        "mm_ref": record.mm_ref,
        "capacity_iri": record.capacity_iri,
        "payload": dict(record.payload),
    }


@capacity_app.command("find")
def find_cmd(
    start: str = typer.Option(
        ...,
        "--start",
        help="DataState IRI to start from.",
    ),
    target: str = typer.Option(
        ...,
        "--target",
        help="DataState IRI to reach.",
    ),
    max_depth: int = typer.Option(
        8,
        "--max-depth",
        help="Maximum BFS path length (capacity count).",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit verbose Pipeline JSON instead of arrow chain.",
    ),
) -> None:
    """Find the shortest capacity chain from ``--start`` to ``--target``.

    Constructs a fresh in-memory Global ``CapacityLayer`` per invocation
    (Phase 30 CLI is programmer-facing this phase). On an empty layer
    the BFS will exhaust immediately — exit 1 + ``PipelineNotFoundError``.

    Exit 0 on success; exit 1 on no path found.
    """
    layer = _construct_global_layer()
    try:
        pipeline = find_pipeline(
            layer,
            start_datastate=start,
            target_datastate=target,
            max_depth=max_depth,
        )
    except PipelineNotFoundError as exc:
        if json_out:
            print(json.dumps({"error": "PipelineNotFoundError", "message": str(exc)}))
        else:
            print(f"PipelineNotFoundError: {exc}", file=sys.stderr)
        raise typer.Exit(code=1)

    if json_out:
        print(json.dumps(_pipeline_to_dict(pipeline)))
    else:
        print(_pipeline_to_human(pipeline))


@problem_trace_app.command("tail")
def problem_trace_tail_cmd(
    limit: int = typer.Option(
        10,
        "--limit",
        help="Maximum records to return (most recent).",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit JSON list of records (default is human summary).",
    ),
) -> None:
    """Peek at the N most-recent ProblemTraceRecords (does NOT drain).

    Constructs a fresh in-memory CapacityLayer per invocation, so the
    sink is always empty at Phase 30. The verb exists to lock the
    surface; a real consumer arrives when CLI gets stateful (Phase 31+
    Falkor-backed bootstrap per R2 PB-27 deferred).

    Exit 0 always.
    """
    layer = _construct_global_layer()
    records = layer.problem_trace.records()
    tail = records[-limit:] if limit > 0 else []

    if json_out:
        print(json.dumps([_record_to_dict(r) for r in tail]))
    else:
        if not tail:
            print("(no problem-trace records)")
        else:
            for r in tail:
                print(
                    f"[{r.timestamp:.3f}] {r.error_kind}  task={r.task_id} "
                    f"step={r.step_id or '-'}  cap={r.capacity_iri or '-'}"
                )


# ── Phase 31 — invoke verb (ADR-0072 envelope; hybrid exit codes) ─────


def _construct_invoke_layer() -> CapacityLayer:
    """Build a fresh in-memory Global ``CapacityLayer`` with text + write builtins.

    Phase 34 (R4 §am-impl-4 + carry-forward #6): the CLI helper now
    constructs a fresh :class:`KnowledgeLayer` and passes it to
    :class:`CapacityLayer` so the Phase 33 write capacities
    (``consolidate`` + ``trace``) can read ``context["kl"]`` at
    invocation time. Without the KL, write-capacity bodies raise
    ``RuntimeError`` per R3 PB-F.

    **Limitation (R2 PB-E):** KL is fresh-per-CLI-process; writes do
    NOT persist across CLI invocations. Production callers (server
    orchestrator) construct ``CapacityLayer`` with a persistent KL.
    """
    from mindsos_capacity.builtins.consolidate import (
        install_consolidate_capacities,
    )
    from mindsos_capacity.builtins.trace import install_trace_capacities
    from mindsos_knowledge import KnowledgeLayer

    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_text_capacities(layer)
    install_consolidate_capacities(layer)
    install_trace_capacities(layer)
    return layer


def _exception_to_dict(exc: BaseException) -> dict:
    """Serialise an Exception for --json envelope output (R1 PB-15 + R3 PB-28)."""
    return {"type": exc.__class__.__name__, "message": str(exc)}


def _write_outcome_to_dict(outcome) -> dict:
    """Serialise a WriteResult or ProblemTraceRecord for --json envelope (Phase 34).

    Phase 34 R1 PB-E + R4 §am-impl-9: ``InvocationResult.write_outcome``
    holds either a :class:`WriteResult` (success path) or
    :class:`ProblemTraceRecord` (future Phase 36+ clause-1 flip). Both
    are dataclasses; render via ``dataclasses.asdict`` with datetime
    iso-format coercion.
    """
    from dataclasses import asdict
    from datetime import datetime

    d = asdict(outcome)
    d["__type__"] = type(outcome).__name__
    # Coerce any datetime field (e.g., WriteResult.written_at) to ISO.
    for k, v in list(d.items()):
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


def _invocation_result_to_dict(result: InvocationResult) -> dict:
    """Render InvocationResult as a --json-ready dict (full envelope; R1 PB-15)."""
    out = {
        "success": result.success,
        "outputs": dict(result.outputs),
        "duration_ms": result.duration_ms,
        "trace": dict(result.trace),
        "error": _exception_to_dict(result.error) if result.error is not None else None,
        "signals": list(result.signals),
    }
    if result.write_outcome is not None:
        out["write_outcome"] = _write_outcome_to_dict(result.write_outcome)
    return out


def _invocation_result_to_human(result: InvocationResult) -> str:
    """Render InvocationResult as a brief human summary."""
    if result.success:
        if result.write_outcome is not None:
            # Phase 34 — write capacity success path.
            iri = getattr(result.write_outcome, "iri", "<no-iri>")
            return (
                f"success  duration_ms={result.duration_ms:.3f}  "
                f"write_outcome.iri={iri!r}"
            )
        out_keys = list(result.outputs.keys())
        return (
            f"success  duration_ms={result.duration_ms:.3f}  "
            f"outputs={out_keys}"
        )
    return (
        f"FAILED  duration_ms={result.duration_ms:.3f}  "
        f"error={result.error.__class__.__name__}: {result.error}"
    )


@capacity_app.command("invoke")
def invoke_cmd(
    iri: str = typer.Argument(
        ...,
        help="Capacity IRI to invoke (e.g. capacity:perception:text.space_split).",
    ),
    input_json: Optional[str] = typer.Option(
        None,
        "--input-json",
        help=(
            "JSON string mapping input DataState IRI → value. "
            "Mutually exclusive with --input-file."
        ),
    ),
    input_file: Optional[str] = typer.Option(
        None,
        "--input-file",
        help=(
            "Path to JSON file mapping input DataState IRI → value. "
            "Mutually exclusive with --input-json."
        ),
    ),
    request_id: Optional[str] = typer.Option(
        None,
        "--task-id",
        help="Optional task id (enables problem-trace emission on failure).",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit full InvocationResult envelope as JSON (exit 0 always).",
    ),
) -> None:
    """Invoke a registered Capacity by IRI with concrete inputs.

    Builds a fresh in-memory layer with text builtins installed (Phase
    31 ships text family only; future families via
    ``--install-builtins`` per R3 PB-29 deferral).

    Exit semantics (R0 PB-7 hybrid lock):

    * ``--json`` always exits 0; the envelope's ``success`` field
      carries failure semantics.
    * ``--human`` (default): exit 0 on success; exit 1 on L3 invariant
      raise (unknown IRI); exit 2 on Typer usage error; exit 3 on
      envelope failure (the bound implementation raised).
    """
    # Mutex check (R1 PB-14 lock).
    if input_json is not None and input_file is not None:
        msg = "--input-json and --input-file are mutually exclusive"
        if json_out:
            print(json.dumps({"error": "UsageError", "message": msg}))
            raise typer.Exit(code=0)
        print(f"UsageError: {msg}", file=sys.stderr)
        raise typer.Exit(code=2)
    if input_json is None and input_file is None:
        msg = "exactly one of --input-json or --input-file is required"
        if json_out:
            print(json.dumps({"error": "UsageError", "message": msg}))
            raise typer.Exit(code=0)
        print(f"UsageError: {msg}", file=sys.stderr)
        raise typer.Exit(code=2)

    # Parse inputs.
    try:
        if input_json is not None:
            raw = input_json
        else:
            with open(input_file, "r", encoding="utf-8") as fh:
                raw = fh.read()
        inputs: Mapping[str, Any] = json.loads(raw)
        if not isinstance(inputs, dict):
            raise ValueError("inputs JSON must be an object")
    except (ValueError, OSError) as exc:
        msg = f"failed to parse inputs: {exc}"
        if json_out:
            print(json.dumps({"error": exc.__class__.__name__, "message": msg}))
            raise typer.Exit(code=0)
        print(f"UsageError: {msg}", file=sys.stderr)
        raise typer.Exit(code=2)

    # Build layer + invoke.
    layer = _construct_invoke_layer()
    try:
        result = layer.invoke(iri, inputs, request_id=request_id)
    except CapacityRegistrationError as exc:
        if json_out:
            print(
                json.dumps(
                    {
                        "error": exc.__class__.__name__,
                        "message": str(exc),
                    }
                )
            )
            raise typer.Exit(code=0)
        print(f"{exc.__class__.__name__}: {exc}", file=sys.stderr)
        raise typer.Exit(code=1)

    # Output.
    if json_out:
        print(json.dumps(_invocation_result_to_dict(result)))
        raise typer.Exit(code=0)
    print(_invocation_result_to_human(result))
    if not result.success:
        raise typer.Exit(code=3)


def register_capacity_app(parent: typer.Typer) -> None:
    """Register the ``capacity`` subapp on the root Typer."""
    parent.add_typer(capacity_app, name="capacity")
