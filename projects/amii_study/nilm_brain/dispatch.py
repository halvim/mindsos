"""Minimal dispatcher over `CapacityLayer.invoke` for in-memory v0.

`mindsos_intelligence.execute_pipeline` is duck-typed on its dispatcher —
its docstring: *"a `.dispatch(capacity_iri, inputs, *, cancel_token=None,
task_id=None, step_id=None)` returning an object with `.success` and
`.outputs`"* — explicitly *"so tests can inject a fake"*. So we run core's
**real** executor over a thin adapter that threads our Local session/context
into `cl.invoke`. This is NOT hand-rolling the walker (arc D8): the walk is
core's `execute_pipeline`; this only supplies the invoke seam. A durable run
would swap this for the real L4Dispatcher from `boot_brain` (v1).
"""

from __future__ import annotations

from typing import Any, Mapping, Optional


class CLDispatcher:
    def __init__(self, cl, session, context: Optional[Mapping[str, Any]] = None):
        self._cl = cl
        self._session = session
        self._context = context

    def dispatch(self, capacity_iri, inputs, *, cancel_token=None,
                 task_id=None, step_id=None):
        # Returns the shipped InvocationResult (.success / .outputs / .error),
        # which is exactly what execute_pipeline reads.
        return self._cl.invoke(
            capacity_iri, inputs, session=self._session,
            context=self._context, task_id=task_id, step_id=step_id,
        )
