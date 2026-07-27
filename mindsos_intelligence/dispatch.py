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

Phase-48 scope (ADR-0180, write-half close): the blanket Phase-47
pre-gate (``required_capability_for``/``check_write_permitted``, which
demanded ``CAN_WRITE_GLOBAL`` for *any* write-body and so over-restricted
Local writes) is **superseded** by a scope-aware, **call-time** gate
living inside a pre-authorized ``writeable`` capability that ``build_
context`` injects onto the ``CapacityContext``. A write-body obtains its
``KLWriteHandle`` via ``context.writeable(role, scope, version)``; the
gate fires there — Local writes need no capability (``kl.writeable``
enforces own-user scope), Global writes require ``CAN_WRITE_GLOBAL``
(``session is None`` is the ADR-0080 bootstrap carve-out). The context
carries a narrowed capability, not a principal — L3 stays
authorization-free (ADR-0170 §amendment-1).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping, Optional

from mindsos_capacity.context import CancelTokenView, CapacityContext, make_writeable
from mindsos_capacity.runtime import invoke as _runtime_invoke

if TYPE_CHECKING:  # pragma: no cover — typing only
    from .phase1_profile import Phase1Profile


class L4Dispatcher:
    """Builds CapacityContexts (incl. the gated ``writeable`` capability)
    and dispatches L3 capacities for one session (ADR-0180).

    ``phase1_profile`` (ADR-0195) is the construction-bound, per-consumer
    selection of Phase-1 interpretation bodies (``None`` → all v0). It is a
    dispatch-time IRI selection, NOT a registration — the seam never mixes
    Global DataStates with Local capacities in one metagraph.
    """

    def __init__(
        self,
        capacity_layer,
        *,
        session: Any = None,
        kl: Any = None,
        mm_handle: Any = None,
        learned_parameters: Optional[Mapping[str, Any]] = None,
        version_snapshot: Optional[Mapping[str, int]] = None,
        phase1_profile: "Optional[Phase1Profile]" = None,
        modality_profiles: "Optional[Mapping[str, Phase1Profile]]" = None,
    ) -> None:
        self._cl = capacity_layer
        self._session = session
        self._kl = kl
        self._mm_handle = mm_handle
        self._learned_parameters = dict(learned_parameters or {})
        self._version_snapshot = dict(version_snapshot or {})
        self._phase1_profile = phase1_profile
        # ADR-0197 §3 — runtime {modality (ingress DataState IRI) ->
        # Phase1Profile} table, selected per input by the stamped modality.
        self._modality_profiles = dict(modality_profiles or {})

    # ── read-only accessors (used by ``phase_1.interpret`` for
    #    find_pipeline composition + the map-resolution KL check) ─────────

    @property
    def capacity_layer(self):
        return self._cl

    @property
    def session(self):
        return self._session

    @property
    def kl(self):
        return self._kl

    @property
    def phase1_profile(self) -> "Optional[Phase1Profile]":
        return self._phase1_profile

    @property
    def modality_profiles(self) -> "Mapping[str, Phase1Profile]":
        return self._modality_profiles

    def build_context(
        self,
        *,
        cancel_token: Any = None,
        request_iri: Optional[str] = None,
        pattern_iri: Optional[str] = None,
        reads_mm: bool = False,
    ) -> CapacityContext:
        # ADR-0200 (C3) — the body-facing MM read handle is injected only
        # when the declaration sets ``reads_mm=True``. A ``reads_mm=False``
        # body (the default) receives ``mm_handle=None``, so its only
        # read-data source is its declared inputs — declared == body-reads
        # becomes structurally true for the MM channel. ``kl`` and
        # ``writeable`` are untouched (kl carries write handles; its read
        # method has no v1 body caller).
        session = self._session
        return CapacityContext(
            session_id=getattr(session, "session_id", "session"),
            user_id=getattr(session, "user_id", "user"),
            learned_parameters_snapshot=dict(self._learned_parameters),
            mm_handle=self._mm_handle if reads_mm else None,
            cancel_token=(
                CancelTokenView(cancel_token) if cancel_token is not None else None
            ),
            current_request_iri=request_iri,
            current_pattern_iri=pattern_iri,
            version_snapshot=dict(self._version_snapshot),
            kl=self._kl,
            cl=self._cl,
            writeable=make_writeable(self._kl, self._session),
        )

    def dispatch(
        self,
        capacity_iri: str,
        inputs: Mapping[str, Any],
        *,
        cancel_token: Any = None,
        request_iri: Optional[str] = None,
        pattern_iri: Optional[str] = None,
        request_id: Optional[str] = None,
        step_id: Optional[str] = None,
    ):
        declaration = self._cl.resolve_declaration(capacity_iri, session=self._session)
        ctx = self.build_context(
            cancel_token=cancel_token,
            request_iri=request_iri,
            pattern_iri=pattern_iri,
            reads_mm=bool(getattr(declaration, "reads_mm", False)),
        )
        return _runtime_invoke(
            declaration,
            inputs,
            context=ctx,
            request_id=request_id,
            step_id=step_id,
            problem_trace_sink=getattr(self._cl, "problem_trace", None),
        )


__all__ = ["L4Dispatcher"]
