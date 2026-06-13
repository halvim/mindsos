"""DM-4 — IP-sanitization helpers (policy B, ROBOT_DEMO_IP_SANITIZATION.md).

The wire must leave the backend already clean — the UI does not re-sanitize.
This module is the single source of the sanitization vocabulary, shared by the
producers (``serializer``/``frames``) AND the guard tests so the two can't
drift.

Three jobs:

* **opaque-token rewrite (design-log PB-13).** The reasoning chain's
  cross-reference IRIs (``hintset:demo-arm1-9f3a:1`` …) are exactly what the UI
  needs to draw the linked lineage *and* exactly what policy B bans (artifact
  type names + ``demo-<device>`` layer-arch). :class:`TokenMap` rewrites every
  internal IRI to a stable per-snapshot opaque token (``n1``/``n2``/…). The UI
  matches lineage edges by ``iri ↔ *_ref`` equality, which survives any
  consistent bijection — the lineage renders identically, no internal token
  leaks.

* **plain labels (PB-12/PB-14).** ``task-pattern:…`` and ``capacity:…`` IRIs →
  behavior-level action names ("move to home", "execute step").

* **the guard (PB-7).** :func:`find_leaks` walks string *values* (never the
  agreed structural keys the UI locked) and flags any banned implementation
  token. Used by ``test_dm4_*`` to test-enforce a clean wire.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

# ── canonical banned vocabulary (case-insensitive substring match) ────────
#
# Implementation/IP tokens that must never reach a participant's browser, in
# panel text OR the raw frames (devtools-visible over the tunnel). Superset of
# the original inline list in ``test_dm4_sanitization`` — that test now imports
# this so the two can't drift.
BANNED_TOKENS: Tuple[str, ...] = (
    # tech stack
    "falkor", "sqlite", "server.db", "redis",
    # layer architecture / role-graphs
    "episodic_memories", "promoted-pipelines", "capacity-state", "capacity-gaps",
    "register_capacity", "writeable", "datastate", "data state",
    "intelligence_mm", "run_lifecycle", "local_metagraph", "global_metagraph",
    # chain-artifact type names
    "hintset", "mappingresult", "pipelinerun", "taskrun", "task_run",
    "stepexecution", "replanrecord", "blameverdict",
    # identifiers / constants
    "evt_", "can_write", "can_read",
    # capacity / api / task-pattern IRIs
    "move_to", "place_at_cell", "load_into_box", "stage_at",
    "query_capabilities", "dispatch(", "promote(",
    "comms.", "capacity:", "datastate:", "task-pattern:",
    # internal scope tokens (opaque-token rewrite must remove these)
    "demo-mgr", "demo-arm1", "demo-arm2", "demo-conv",
    "hintset:", "mappingresult:", "milestone:", "plan:", "pipeline:",
    "pipelinerun:", "stepexecutionrecord:", "replanrecord:",
)

#: The only allowed ``message`` party display names (sanitized vocabulary).
ALLOWED_PARTIES: frozenset = frozenset({
    "User", "Orchestrator", "Arm1", "Arm2", "Conveyor",
    "Fleet", "Library", "Demonstration",
})

#: Demo move target codec prefix (mirror of ``comms._TPI_PREFIX``; duplicated
#: here to keep ``sanitize`` import-light — a one-line constant, asserted equal
#: by the export test).
_TPI_PREFIX = "task-pattern:demo:move:"


# ── opaque-token rewrite (PB-13) ──────────────────────────────────────────
class TokenMap:
    """Stable per-snapshot IRI → opaque token (``n1``/``n2``/…) bijection.

    ``tok(None)`` → ``None`` (a missing ref stays missing). The same IRI always
    maps to the same token within one snapshot, so ``iri``/``*_ref`` pairs that
    referenced the same artifact still match after the rewrite — which is all
    the UI needs to draw the lineage edges.
    """

    def __init__(self, prefix: str = "n") -> None:
        self._prefix = prefix
        self._map: Dict[str, str] = {}

    def tok(self, iri: Optional[str]) -> Optional[str]:
        if iri is None:
            return None
        existing = self._map.get(iri)
        if existing is not None:
            return existing
        token = f"{self._prefix}{len(self._map) + 1}"
        self._map[iri] = token
        return token


# ── plain labels (PB-12 / PB-14) ─────────────────────────────────────────
def plain_task_pattern(tpi: Optional[str]) -> Optional[str]:
    """``task-pattern:demo:move:<dst>:<target>[:<item>]`` → a behavior label.

    DM-5: the 3-field codec adds an optional ``item`` segment, so split (don't
    ``partition``, which would fold ``<target>:<item>`` into one — the
    ``"move to r1c1:tube"`` bug). With an item the label is behavior-level
    ("place <item>"); without one it's the DM-4 "move to <target>". Non-demo /
    unrecognised IRIs collapse to a generic "approach". ``None`` passes through."""
    if not tpi:
        return tpi
    if tpi.startswith(_TPI_PREFIX):
        parts = tpi[len(_TPI_PREFIX):].split(":")
        target = parts[1] if len(parts) > 1 and parts[1] else ""
        item = parts[2] if len(parts) > 2 and parts[2] else ""
        if item:
            return f"place {item}"
        return f"move to {target}" if target else "move"
    return "approach"


def plain_capacity(iri: Optional[str]) -> Optional[str]:
    """A capacity / pipeline IRI → a behavior-level action label.

    The v0 chain's leaf ``StepExecutionRecord.capacity_iri`` is a notional
    Pipeline ref (design-log PB-18), not the real motion — so the honest label
    is a generic "execute step"; recognised verbs get a friendlier name."""
    if not iri:
        return iri
    low = iri.lower()
    if "move_to" in low or ":move" in low:
        return "move"
    if "consolidate" in low:
        return "save outcome"
    if "pick" in low:
        return "pick"
    if "place" in low:
        return "place"
    return "execute step"


# ── the guard (PB-7) ──────────────────────────────────────────────────────
def iter_strings(obj: Any) -> Iterable[str]:
    """Yield every string *value* in a nested dict/list (NOT dict keys).

    Keys are excluded deliberately: the snapshot's structural keys (``hint_set``
    /``task_run``/…) are the contract the UI locked and renders as generic
    stages on its side — policy B constrains identifiable *values*, not the
    agreed schema keys (design-log PB-7)."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from iter_strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from iter_strings(v)


def find_leaks(
    obj: Any,
    *,
    banned: Iterable[str] = BANNED_TOKENS,
    parties: Iterable[str] = (),
) -> List[Tuple[str, str]]:
    """Return ``(token, offending_string)`` for every banned token found in a
    string value of ``obj``. ``parties`` (if given) are message from/to display
    names that must be in :data:`ALLOWED_PARTIES`."""
    banned = tuple(banned)
    leaks: List[Tuple[str, str]] = []
    for s in iter_strings(obj):
        low = s.lower()
        for tok in banned:
            if tok in low:
                leaks.append((tok, s))
    for party in parties:
        if party not in ALLOWED_PARTIES:
            leaks.append(("party", str(party)))
    return leaks


__all__ = [
    "BANNED_TOKENS",
    "ALLOWED_PARTIES",
    "TokenMap",
    "plain_task_pattern",
    "plain_capacity",
    "iter_strings",
    "find_leaks",
]
