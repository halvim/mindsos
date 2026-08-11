"""Read the learned-parameters snapshot for L4 dispatch (CR learned-parameters).

This is the READ half of the learned-parameters feature — the L4 plumbing that
fills ``CapacityContext.learned_parameters_snapshot`` so capacity bodies receive
their current learned parameters as arguments. It is deliberately NOT a capacity:
it builds the context that capacities run inside, so it cannot be one (confirmed
in review). The WRITE half is the L3 capacity
``capacity:learning-methods:learn_parameter``.

Placement: ``mindsos_knowledge`` (base layer). Callers span layers —
``mindsos_intelligence`` dispatch and ``mindsos_server`` boot both construct the
``L4Dispatcher`` and need this; both import knowledge, neither the other. Reads
purely over ``KnowledgeLayer`` metagraphs, so knowledge is the natural home.

Realm resolution: **Local overrides Global per knob** (review decision). Global
carries system/admin-applied parameters; the user's Local overrides shadow them
at the ``(parameter_set, target)`` grain — Local-preferring, not
set-shadowing (Option B's clean property: same knob => same key).
"""

from __future__ import annotations

from typing import Any, Dict

from .identifiers import ROLE_LEARNED_PARAMETERS
from .schemas.learned_parameters import NODE_LEARNED_PARAMETER


def _overlay(dst: Dict[str, Dict[str, Any]], mg: Any) -> None:
    """Overlay every LearnedParameter node in ``mg`` onto ``dst`` in place.

    Keys on ``(parameter_set_iri, target_parameter_iri)``; a later call
    (Local) overwrites an earlier one (Global) at the same knob.
    """
    for g in mg.graphs.values():
        if getattr(g, "role", None) != ROLE_LEARNED_PARAMETERS:
            continue
        for n in g.nodes.values():
            if n.type_name != NODE_LEARNED_PARAMETER:
                continue
            props = n.properties or {}
            pset = props.get("parameter_set_iri")
            target = props.get("target_parameter_iri")
            if pset is None or target is None:
                # Not written by the learn_parameter capacity (e.g. a legacy
                # opaque node); skip rather than guess a key.
                continue
            dst.setdefault(str(pset), {})[str(target)] = n.value


def read_learned_parameter_snapshot(
    kl: Any, user: str
) -> Dict[str, Dict[str, Any]]:
    """Return ``{parameter_set_iri: {target_parameter_iri: value}}`` for ``user``.

    Global first, then Local — so Local values override Global per knob. Feed
    the result to ``L4Dispatcher(learned_parameters=...)``; it becomes each
    request's frozen ``learned_parameters_snapshot``.

    **A read must never mint a Local.** ``local_metagraph`` lazily CREATES, so
    calling it unguarded materialises an empty Local for any user who has none
    — and this runs on the L4 dispatch path, where the snapshot is frozen into
    every request, so it is a hotter path than the roster read that was already
    guarded for this reason. Materialising ahead of the durable boot that
    restores a Local is what broke ``test_durable_roundtrip`` (ADR-0183
    §am-6); ``mindsos_server/skills/records.py`` guards the identical call and
    documents the same ground.
    """
    if kl is None:
        return {}
    snapshot: Dict[str, Dict[str, Any]] = {}
    _overlay(snapshot, kl.global_metagraph())
    if user and getattr(kl, "has_local", lambda _u: False)(user):
        _overlay(snapshot, kl.local_metagraph(user))
    return snapshot


def get_parameter(
    snapshot: Any, parameter_set: str, target: str, default: Any = None
) -> Any:
    """Look up one knob in a learned-parameters snapshot; ``default`` if absent."""
    return (snapshot.get(parameter_set) or {}).get(target, default)


__all__ = ["read_learned_parameter_snapshot", "get_parameter"]
