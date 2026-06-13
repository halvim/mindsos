"""DM-4 — Mode-A L5 export serializer (``kind:"episode-audit"``).

Builds the per-brain episode/reasoning audit snapshot the dashboard's Export
button consumes (``ROBOT_DEMO_L5_EXPORT_IMPORT_PROMPT.md §D``). Read-only: it
reads the chosen brain's **already-consolidated** Episodes from its Local
``episodic_memories`` graph + the reasoning chain that survives in the brain's
intelligence-MM, and emits a sanitized JSON snapshot.

Grounded design decisions (design-log §22):

* **PB-1 — Episode→chain slice by scope, not ``mm_root_ref``.** Every episode
  in a brain shares the same ``mm_root_ref`` and the ``chain`` graph accumulates
  every task's artifacts. The discriminator is the per-task ``task_scope``,
  embedded in BOTH the chain IRIs (``hintset:<scope>:N``) and the Episode node
  id (the Episode id IS the TaskRun iri, ``…:taskrun:<scope>:N``). We derive the
  scope from each Episode id and slice the chain by it.
* **PB-13 — opaque-token rewrite.** Every internal IRI (chain refs, episode /
  memory ids, ``mm_root_ref``) is rewritten to a stable per-snapshot token via
  :class:`~robot_demo.backend.sanitize.TokenMap`. The UI matches lineage edges
  by ``iri ↔ *_ref`` equality, which survives the bijection. Nothing internal
  reaches the wire.
* **PB-12/14 — plain labels.** ``task_pattern_iri`` → "move to <target>";
  the notional v0 step ``capacity_iri`` → "execute step"; the internal
  ``task_input_ref`` / ``mm_root_ref`` → ``null`` (no UI use).
* **PB-17 — ``task_input``** comes from the ``run_task`` capture map (the
  Episode keeps only a ref string).
* **PB-5 — ``problem_trace`` is ``[]``** (no live producer until the DM-6
  failure path); the UI renders "no errors this run", never hidden.
* **PB-18 — honesty.** ``hints`` is empty (the v0 ``hint.global``), the leaf
  ``step`` is notional, ``replans``/``blame``/``dont_know`` only populate on
  the relevant paths — all rendered "not exercised", never faked.

Memories are grouped by ``task_pattern_iri`` (the exact key the
``MEMORY_CONTAINS_EPISODE`` edge is built on) — no edge-API dependency.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from mindsos_intelligence.chain_artifacts import iter_chain_artifacts
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
from mindsos_knowledge.metagraph_view import MetagraphView

from .brain import refusal_for, task_input_for
from .frames import BRAIN_ALIAS
from .sanitize import TokenMap, find_leaks, plain_capacity, plain_task_pattern

SNAPSHOT_VERSION = 1
KIND_EPISODE_AUDIT = "episode-audit"

# chain-artifact node-id type prefixes (ChainArtifactWriter._mint).
_P_HINTSET = "hintset"
_P_MAPPINGRESULT = "mappingresult"
_P_MILESTONE = "milestone"
_P_PLAN = "plan"
_P_PIPELINE = "pipeline"
_P_PIPELINERUN = "pipelinerun"
_P_TASKRUN = "taskrun"
_P_REPLANRECORD = "replanrecord"
_P_STEP = "stepexecutionrecord"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── chain reading ────────────────────────────────────────────────────────
def _chain_by_scope(mm: Any) -> Dict[str, Dict[str, List[Any]]]:
    """Bucket the brain's chain artifacts as ``{scope: {prefix: [dataclass…]}}``.

    Reads under the MM read lock (``iter_chain_artifacts`` owns the lock). Node
    ids are ``<prefix>:<scope>:<seq>`` and ``scope`` contains no colons, so a
    plain split is unambiguous."""
    out: Dict[str, Dict[str, List[Any]]] = {}
    for node_id, art in iter_chain_artifacts(mm):
        parts = node_id.split(":")
        if len(parts) < 3:
            continue
        prefix, scope = parts[0], parts[1]
        out.setdefault(scope, {}).setdefault(prefix, []).append(art)
    return out


def _scope_of_episode(node_id: str) -> Optional[str]:
    """The task scope embedded in an Episode node id (the Episode id IS the
    TaskRun iri ``taskrun:<scope>:<seq>``). ``<scope>`` has no inner colons."""
    parts = node_id.split(":")
    if "taskrun" in parts:
        i = parts.index("taskrun")
        if i + 1 < len(parts):
            return parts[i + 1]
    return None


# ── reasoning serialization (one task's chain slice) ──────────────────────
def _one(bucket: Dict[str, List[Any]], prefix: str) -> Optional[Any]:
    items = bucket.get(prefix)
    return items[0] if items else None


def _reasoning(
    slice_: Dict[str, List[Any]], tok: TokenMap, refusal: Optional[dict] = None
) -> Dict[str, Any]:
    """Serialize one task's chain slice into the §D ``reasoning`` block, faithful
    to the ``chain_artifacts`` dataclasses, with refs tokenized + IRIs labelled.

    ``refusal`` (DM-5): the captured embodiment-gate verdict for this task's
    scope (``{"reason", "blame"}``) on the dont-know path — the shipped
    ``run_lifecycle`` returns ``blame`` only on the TaskOutcome (never the
    chain), so ``reasoning.blame``/``dont_know`` come from the capture, not
    ``il.mm``. Already behavior-level / sanitized."""
    hs = _one(slice_, _P_HINTSET)
    mr = _one(slice_, _P_MAPPINGRESULT)
    plan = _one(slice_, _P_PLAN)
    tr = _one(slice_, _P_TASKRUN)

    out: Dict[str, Any] = {}
    out["hint_set"] = (
        {"iri": tok.tok(hs.iri), "hints": dict(hs.hints or {})} if hs else None
    )
    out["mapping_result"] = (
        {
            "iri": tok.tok(mr.iri),
            "selected_task_pattern_iri": plain_task_pattern(mr.selected_task_pattern_iri),
            "mapping_confidence": mr.mapping_confidence,
        }
        if mr
        else None
    )
    out["plan"] = (
        {"iri": tok.tok(plan.iri), "root_milestone_ref": tok.tok(plan.root_milestone_ref)}
        if plan
        else None
    )
    out["milestones"] = [
        {
            "iri": tok.tok(m.iri),
            "name": m.name,
            "status": m.status,
            "replans_used": m.replans_used,
        }
        for m in slice_.get(_P_MILESTONE, [])
    ]
    out["pipelines"] = [
        {"iri": tok.tok(p.iri), "milestone_ref": tok.tok(p.milestone_ref)}
        for p in slice_.get(_P_PIPELINE, [])
    ]
    out["pipeline_runs"] = [
        {"iri": tok.tok(pr.iri), "status": pr.status, "task_run_ref": tok.tok(pr.task_run_ref)}
        for pr in slice_.get(_P_PIPELINERUN, [])
    ]
    out["task_run"] = (
        {
            "iri": tok.tok(tr.iri),
            "status": tr.status,
            "replan_history": [tok.tok(r) for r in (tr.replan_history or [])],
            "attention_score": tr.attention_score,
        }
        if tr
        else None
    )
    out["steps"] = [
        {
            "iri": tok.tok(s.iri),
            # PB-18: v0 leaf step is a notional Pipeline ref, not the real
            # motion — label it generically + honestly.
            "capacity_iri": plain_capacity(s.capacity_iri),
            "confidence": s.confidence,
            "milestone_ref": tok.tok(s.milestone_ref),
        }
        for s in slice_.get(_P_STEP, [])
    ]
    # Only-on-the-relevant-path artifacts (DM-6+); honest empties otherwise.
    out["replans"] = [
        {
            "iri": tok.tok(r.iri),
            "replan_level": r.replan_level,
            "verdict": {
                "decision": r.verdict.decision,
                "divergence": r.verdict.divergence,
            },
            "invalidated_refs": [tok.tok(x) for x in (r.invalidated_refs or [])],
            "spawned_refs": [tok.tok(x) for x in (r.spawned_refs or [])],
        }
        for r in slice_.get(_P_REPLANRECORD, [])
    ]
    # DM-5: a real embodiment-gate refusal populates blame + dont_know from the
    # captured TaskOutcome; the happy path stays null ("not exercised this run").
    if refusal:
        reason = refusal.get("reason")
        blame = refusal.get("blame") or {}
        out["blame"] = {
            "chain_level": blame.get("chain_level"),
            "blame_score": blame.get("blame_score"),
            "rationale": blame.get("rationale") or reason,
        }
        out["dont_know"] = {"reason": reason, "cause": "embodiment_gate"}
    else:
        out["blame"] = None       # happy path emits no BlameVerdict
        out["dont_know"] = None    # populated only on a real refusal
    return out


# ── episode + memory serialization ────────────────────────────────────────
def _episodes_and_memories(
    brain: Any, tok: TokenMap
) -> "tuple[List[dict], List[dict]]":
    """Serialize the brain's consolidated Episodes (+ their chain slice) and the
    Memory clusters from its Local ``episodic_memories`` graph."""
    local_mg = brain.kl.local_metagraph(brain.device_id)
    ep_graph = MetagraphView(local_mg).graphs_by_role(ROLE_EPISODIC_MEMORIES)[0]
    # snapshot the node view once (a concurrent consolidate may add a node —
    # both pre/post states are honest at demo scale; design-log §22).
    nodes = list(ep_graph.nodes.values())

    chain = _chain_by_scope(brain.il.mm)

    episodes: List[dict] = []
    for n in nodes:
        if getattr(n, "type_name", None) != "Episode":
            continue
        value = dict(n.value or {})
        scope = _scope_of_episode(n.node_id)
        slice_ = chain.get(scope, {}) if scope else {}
        episodes.append(
            {
                "episode_iri": tok.tok(n.node_id),
                "value": {
                    "task_input_ref": None,  # internal ref — PB-14
                    "mm_root_ref": None,     # internal pointer — PB-14
                    "task_pattern_iri": plain_task_pattern(value.get("task_pattern_iri")),
                    "outcome_classification": value.get("outcome_classification"),
                    "crash_marker": value.get("crash_marker"),
                    "consolidated_at": value.get("consolidated_at"),
                },
                "task_input": task_input_for(scope) if scope else None,
                "reasoning": _reasoning(
                    slice_, tok, refusal_for(scope) if scope else None
                ),
                "problem_trace": [],  # PB-5 — no live producer until DM-6
            }
        )
    # newest-first (coordination doc: "that brain's episode list, newest-first").
    episodes.reverse()

    memories: List[dict] = []
    for n in nodes:
        if getattr(n, "type_name", None) != "Memory":
            continue
        mval = dict(n.value or {})
        tp = mval.get("task_pattern_iri")
        # episode_iris = episodes whose own task_pattern_iri matches this cluster
        # key (exactly the MEMORY_CONTAINS_EPISODE relation) — no edge walk.
        ep_iris = [
            tok.tok(e.node_id)
            for e in nodes
            if getattr(e, "type_name", None) == "Episode"
            and (e.value or {}).get("task_pattern_iri") == tp
        ]
        memories.append(
            {
                "memory_iri": tok.tok(n.node_id),
                "value": {"task_pattern_iri": plain_task_pattern(tp)},
                "episode_iris": ep_iris,
            }
        )
    return episodes, memories


# ── public entry ──────────────────────────────────────────────────────────
def build_episode_audit_snapshot(
    brain: Any,
    *,
    run_id: Optional[str] = None,
    strict: bool = True,
) -> dict:
    """Build the ``kind:"episode-audit"`` snapshot for one brain.

    ``strict`` (default True) runs the banned-token guard over the assembled
    snapshot and raises if any internal token leaked — so a clean wire is
    enforced at the producer, not just in tests."""
    tok = TokenMap()
    episodes, memories = _episodes_and_memories(brain, tok)
    contract_id = BRAIN_ALIAS.get(brain.device_id, brain.device_id)
    snapshot = {
        "snapshot_version": SNAPSHOT_VERSION,
        "kind": KIND_EPISODE_AUDIT,
        "created_at": _utc_now_iso(),
        # PB-3: no ``mindsos_version`` on the wire (IP sanitization addendum).
        "scenario": "open-order",
        "run_id": run_id or f"robot-demo:{contract_id}",
        "brains": {
            contract_id: {
                "device_type": brain.profile.device_type,
                "episodes": episodes,
                "memories": memories,
            }
        },
    }
    if strict:
        leaks = find_leaks(snapshot)
        if leaks:
            raise SanitizationError(
                "episode-audit snapshot leaked internal tokens: "
                + "; ".join(f"[{t}] {s!r}" for t, s in leaks[:8])
            )
    return snapshot


class SanitizationError(RuntimeError):
    """Raised when an assembled snapshot would leak an internal IP token."""


__all__ = [
    "build_episode_audit_snapshot",
    "SanitizationError",
    "SNAPSHOT_VERSION",
    "KIND_EPISODE_AUDIT",
]
