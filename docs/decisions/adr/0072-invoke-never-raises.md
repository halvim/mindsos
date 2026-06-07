---
title: invoke() never raises for implementation errors; problem-trace absorbs them
status: Accepted
date: 2026-04-21
layer: L3
aliases: [capacity-ADR-013]
---

# ADR-0072: invoke() never raises for implementation errors

**Status:** Accepted

**Date:** 2026-04-21

## Context

Capacity implementations are arbitrary Python. They will raise. The question is whether `invoke()` propagates the exception (turning every L4 orchestration into a try/except) or absorbs it into a result envelope.

## Decision

`invoke()` returns `InvocationResult(failed=True, exception=..., ...)` for implementation exceptions and emits a `ProblemTraceRecord` to `self.problem_trace`. L3 *does* raise for its own invariants (unknown IRI, reserved-key leak, invalid constraint kind) — those are always caller bugs.

## Consequences

**Good:**
- L4's orchestration code is straight-line: call, check `result.failed`, proceed or branch.
- Problem-traces give L4 the full post-mortem surface it needs.

**Cost:**
- Small semantic burden: callers must remember that `invoke` has two error channels.

## Alternatives considered

1. **Raise everything** — rejected (contaminates L4 with boilerplate).
2. **Absorb everything** — rejected (hides caller bugs).

## Enforced as

Invariant I9 in the L3 handoff.

## §amendment-1 (2026-05-25, Phase 30 — InvocationResult field rename)

§Decision is hereby amended. The shipped `InvocationResult` dataclass field names diverge from the §Decision text — the as-shipped names supersede:

| §Decision text | As-shipped |
|---|---|
| `failed: bool` | `success: bool` (inverted polarity — True on success, False on failure) |
| `exception` | `error: Optional[BaseException]` |
| (implicit) | `outputs: Mapping[str, Any]`, `duration_ms: float`, `signals: Tuple[Any, ...]`, `trace: Mapping[str, Any]` |

The semantic content of §Decision — `invoke()` never raises for implementation errors; an envelope captures success vs failure + the exception; ProblemTraceRecord absorbs failures — is preserved.

L3 *does* raise for its own invariants (unknown IRI via `_resolve_declaration`, reserved-key leak, invalid constraint kind) — unchanged from §Decision.

Status remains Accepted as amended.

## §Implementation (2026-05-25, Phase 30)

Shipped 2026-05-25 in `mindsos_capacity/runtime.py` (NEW module) — `invoke` free function; on caught exception emits `ProblemTraceRecord` to the supplied `ProblemTraceSink` (when both `task_id` and `sink` non-None) and returns `InvocationResult(success=False, error=exc, ...)`. `InvocationResult` + `call_capacity` exports lifted from `mindsos_capacity.capacity` via `__init__.py` per [[ADR-0066]] §Implementation (Phase 30) staging closure.

`CapacityLayer.invoke(capacity_iri, inputs, *, session=None, context=None, task_id=None, step_id=None)` is the method form on the L3 facade — wraps `_runtime_invoke` after `_resolve_declaration` lookup. Unknown IRI raises `CapacityRegistrationError` before invoke runs (§Decision's "L3 raises for its own invariants" carve-out). The Phase 28 `tests/phase_28/test_invocation_not_exported.py` sentinel flips to `test_invocation_exported_phase_30.py` (file rename); the `test_problem_trace_attribute_not_present_at_phase_28` function in `tests/phase_28/test_capacity_layer_init.py` flips to `test_problem_trace_attribute_present_at_phase_30` (function rename only).

**Foot-gun documented in `invoke` docstring:** `task_id=None` short-circuits problem-trace emission — exceptions are still enveloped in `InvocationResult(success=False)` but no trace record is created. L4's lifecycle process is the canonical caller and will always pass `task_id`.

Status remains Accepted as amended (§amendment-1).

## §Amendment (Phase 42 — ADR-0159)

The invoke envelope context transitions toward the typed `CapacityContext` (ADR-0159). v1 invoke plumbing keeps the dict shape; the typed-context conversion + capacity-body `context["kl"]`→`context.kl` migration are deferred to Phase 46 (PB-23). Envelope semantics (never raises for impl errors) unchanged.
