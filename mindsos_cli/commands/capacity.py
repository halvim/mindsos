"""`mindsos capacity` — Phase 30 L3 Capacity CLI surface.

Sub-subgroup shape (Phase 30 R0 PB-6 + R3 PB-36 lock):

  mindsos capacity find --start <ds_iri> --target <ds_iri>
                        [--max-depth N] [--json]
      Run datastate-keyed BFS over the auto-discovered TYPE_COMPAT
      graph (ADR-0071); print the shortest pipeline by capacity count.
      Default human-readable arrow chain; ``--json`` emits the verbose
      Pipeline + PipelineStep dataclass shape.

  mindsos capacity problem-trace tail [--limit N] [--json]
      Peek at the most-recent N ProblemTraceRecords on the current
      CapacityLayer's sink (default N=10). Peek-only — does NOT drain
      (L4 lifecycle owns drain per ADR-0074).

**Phase 30 scope cut.** The ``invoke`` verb is OMITTED at Phase 30
(R3 PB-36(b) lock) because the CLI constructs a fresh in-memory
``CapacityLayer`` per invocation (R2 PB-27(a)) and Phase 28's
registration verbs are NOT shipped, so any registered-IRI lookup
fails 100%. ``invoke`` ships at Phase 31 alongside text builtins that
auto-register on layer construction.

**Phase 30 CLI is Global-only.** No ``--session-token`` flag at this
phase (R2 PB-30(a) lock). All BFS walks the Global view. Local-scoped
walks land when Phase 31+ wires session resolution.

**Exit code policy (parity with prior phases):**
* exit 0 — success
* exit 1 — domain error (``PipelineNotFoundError``)
* exit 2 — usage error (missing required arg)

Exit code 3 (``InvocationResult.success=False`` envelope; R2 PB-26(b)
lock) is deferred to Phase 31 alongside the ``invoke`` verb (R5 PB-61).
"""

from __future__ import annotations

import dataclasses
import json
import sys
from typing import Optional

import typer

from mindsos_capacity import (
    CapacityLayer,
    Pipeline,
    PipelineNotFoundError,
    ProblemTraceRecord,
    find_pipeline,
)


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
    """Render a Pipeline as a verbose JSON-ready dict (R2 PB-33(a))."""
    return {
        "start_datastate": pipeline.start_datastate,
        "target_datastate": pipeline.target_datastate,
        "length": len(pipeline),
        "steps": [
            {
                "capacity_iri": step.capacity_iri,
                "input_datastates": list(step.input_datastates),
                "output_datastates": list(step.output_datastates),
                "via_datastate": step.via_datastate,
            }
            for step in pipeline.steps
        ],
    }


def _pipeline_to_human(pipeline: Pipeline) -> str:
    """Render a Pipeline as an arrow chain for human-readable output."""
    if not pipeline.steps:
        return (
            f"{pipeline.start_datastate} (already at target; 0 capacities)"
        )
    chain = [pipeline.start_datastate]
    for step in pipeline.steps:
        chain.append(step.capacity_iri)
        # Pick the output that matches the next step's `via_datastate`
        # or the pipeline's target on the last step.
        chain.append(step.output_datastates[0] if step.output_datastates else "?")
    chain[-1] = pipeline.target_datastate
    return " -> ".join(chain)


def _record_to_dict(record: ProblemTraceRecord) -> dict:
    """Render a ProblemTraceRecord as a JSON-ready dict."""
    return {
        "entry_id": record.entry_id,
        "timestamp": record.timestamp,
        "task_id": record.task_id,
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


def register_capacity_app(parent: typer.Typer) -> None:
    """Register the ``capacity`` subapp on the root Typer."""
    parent.add_typer(capacity_app, name="capacity")
