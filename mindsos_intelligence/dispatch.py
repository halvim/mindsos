"""L4 capacity dispatch — CapacityContext builder + write-body gate.

The single L4 choke point through which the orchestrator invokes L3
capacities (ADR-0175 / ADR-0170). Two jobs:

1. **Build the typed ``CapacityContext``** (ADR-0159) from the session +
   the layer handles, and thread it into ``runtime.invoke``. This is the
   read path the Phase-47 orchestrator uses for every v0 capacity.

2. **Gate write-bodies** (capacities declaring zero output DataStates,
   ADR-0146) on a required capability held by the acting session, *before*
   invocation. The L3 body stays authorization-free (ADR-0170): the gate
   lives here, in L4 dispatch, which holds the live session.

Phase-47 scope (ADR-0175 §amendment-1, read/write split): the gate
mechanism + its synthetic test ship now. The v0 catalog the orchestrator
dispatches is all reads, so there is no production write-body traffic at
Phase 47; the ``effect_iri``-driven capability resolution + the
``consolidate``/``trace`` write-body migration land at Phase 48 with their
real consumer (wired consolidation). The v0 gate requires
``CAN_WRITE_GLOBAL`` for any write-body — the same capability the shipped
``trace`` body self-checks today.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from mindsos_capacity.capabilities import CAN_WRITE_GLOBAL
from mindsos_capacity.context import CancelTokenView, CapacityContext
from mindsos_capacity.exceptions import CapabilityDeniedError
from mindsos_capacity.runtime import invoke as _runtime_invoke


def required_capability_for(declaration) -> Optional[str]:
    """Capability a session must hold to dispatch ``declaration``.

    v0 (Phase 47): any write-body (zero output DataStates) requires
    ``CAN_WRITE_GLOBAL``; reads require nothing. The ``effect_iri``-driven
    resolution (ADR-0159) lands with the write-path migration at Phase 48.
    """
    if not declaration.outputs:
        return CAN_WRITE_GLOBAL
    return None


class L4Dispatcher:
    """Builds CapacityContexts and gates write-bodies for one session."""

    def __init__(
        self,
        capacity_layer,
        *,
        session: Any = None,
        kl: Any = None,
        mm_handle: Any = None,
        learned_parameters: Optional[Mapping[str, Any]] = None,
        version_snapshot: Optional[Mapping[str, int]] = None,
    ) -> None:
        self._cl = capacity_layer
        self._session = session
        self._kl = kl
        self._mm_handle = mm_handle
        self._learned_parameters = dict(learned_parameters or {})
        self._version_snapshot = dict(version_snapshot or {})

    def build_context(
        self,
        *,
        cancel_token: Any = None,
        task_iri: Optional[str] = None,
        pattern_iri: Optional[str] = None,
    ) -> CapacityContext:
        session = self._session
        return CapacityContext(
            session_id=getattr(session, "session_id", "session"),
            user_id=getattr(session, "user_id", "user"),
            learned_parameters_snapshot=dict(self._learned_parameters),
            mm_handle=self._mm_handle,
            cancel_token=(
                CancelTokenView(cancel_token) if cancel_token is not None else None
            ),
            current_task_iri=task_iri,
            current_pattern_iri=pattern_iri,
            version_snapshot=dict(self._version_snapshot),
            kl=self._kl,
            cl=self._cl,
        )

    def check_write_permitted(self, declaration) -> None:
        """Raise :class:`CapabilityDeniedError` if ``declaration`` writes
        and the session lacks the required capability (ADR-0170 gate)."""
        required = required_capability_for(declaration)
        if required is None:
            return
        if self._session is None or not self._session.has(required):
            who = getattr(self._session, "session_id", None)
            raise CapabilityDeniedError(
                f"L4 dispatch: capacity {declaration.iri!r} writes and "
                f"requires {required!r}; session {who!r} lacks it (ADR-0170)."
            )

    def dispatch(
        self,
        capacity_iri: str,
        inputs: Mapping[str, Any],
        *,
        cancel_token: Any = None,
        task_iri: Optional[str] = None,
        pattern_iri: Optional[str] = None,
        task_id: Optional[str] = None,
        step_id: Optional[str] = None,
    ):
        declaration = self._cl.get_declaration(capacity_iri)
        self.check_write_permitted(declaration)
        ctx = self.build_context(
            cancel_token=cancel_token, task_iri=task_iri, pattern_iri=pattern_iri
        )
        return _runtime_invoke(
            declaration,
            inputs,
            context=ctx,
            task_id=task_id,
            step_id=step_id,
            problem_trace_sink=getattr(self._cl, "problem_trace", None),
        )


__all__ = ["L4Dispatcher", "required_capability_for"]
