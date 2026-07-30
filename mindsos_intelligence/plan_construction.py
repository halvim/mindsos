"""LifecyclePhase 2 — Plan + Pipeline construction (D-B22/B23, ADR-0171).

Dispatches ``planning.derive_initial_plan`` to seed a Plan, emits the root
Milestone + Plan, lazily decomposes (``planning.decompose`` -> [] at v0)
and tests leaves (``planning.is_leaf`` -> True at v0), then a v0
pipeline-finder emits one Pipeline per leaf Milestone. Cold-start
max-depth=3 (admin-tunable); v0's single-Milestone Plan never reaches it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from mindsos_capacity.builtins.planning_v0 import (
    DS_IS_LEAF,
    DS_MAPPING_RESULT,
    DS_MILESTONE,
    DS_MILESTONE_LIST,
    DS_PLAN,
)
from mindsos_capacity.identifiers import CATEGORY_PLANNING, capacity_iri

DERIVE_PLAN_IRI = capacity_iri(CATEGORY_PLANNING, "derive_initial_plan")
DECOMPOSE_IRI = capacity_iri(CATEGORY_PLANNING, "decompose")
IS_LEAF_IRI = capacity_iri(CATEGORY_PLANNING, "is_leaf")

MAX_DEPTH = 3


@dataclass
class PlanResult:
    plan_ref: str
    root_milestone_ref: str
    leaf_milestone_refs: List[str] = field(default_factory=list)
    pipeline_refs: Dict[str, str] = field(default_factory=dict)
    #: The DataState endpoints of the solve pipeline the leaf(s) run, read from
    #: the planner's ``planning.plan`` output (out-of-CR Step 5). ``None`` when
    #: the plan names none — the v0 placeholder planner does, so the v0 path is
    #: unchanged (``execution.run`` emits the notional record). A real consumer's
    #: ``derive_initial_plan`` (e.g. arc, seeing ``resolved_reference``) names
    #: ``{"start_datastate", "target_datastate"}``; ``execution.run`` then finds
    #: + runs a real pipeline (single-leaf scope at v1; multi-leaf target routing
    #: is deferred with real decomposition / WSD).
    solve_target: Optional[Dict[str, str]] = None
    #: Optional per-leaf solve endpoints ``{leaf_ref: {start_datastate,
    #: target_datastate}}`` for a multi-stage plan whose leaves form a value
    #: chain (collection-iteration Slice 1a — ``execution.run`` threads a leaf's
    #: outputs to a downstream leaf's start via the run blackboard). A leaf with
    #: no entry falls back to the plan-global ``solve_target``; ``None``/absent →
    #: today's single-target behaviour (v0 + Step-5 single-leaf path unchanged).
    #: The map/fold fan-out that populates this for real rides Slice 1b + arc's
    #: planner; the v0 builder below never sets it.
    #:
    #: **Multi-input leaves (map-member multi-input CR):** an entry may declare
    #: plural ``"start_datastates": [ds, ...]`` *instead of* the singular
    #: ``"start_datastate"`` (declaring both raises). More than one start selects
    #: the sound ``ConjunctionFinder``; exactly one keeps ``BFSFinder`` — so
    #: every pre-CR entry composes exactly as before. An optional ``"finder"``
    #: (``"bfs"`` | ``"conjunction"``) overrides that arity derivation;
    #: ``"bfs"`` with plural starts raises rather than silently wiring one input
    #: and dropping the rest.
    leaf_targets: Optional[Dict[str, Dict[str, Any]]] = None
    #: Slice 1b/2 — per-milestone map/fold spec the executor interprets. Maps a
    #: milestone ref to a kind descriptor: a ``map`` node
    #: (``{"kind": "map", "collection_ds", "member_ds", "sub_target",
    #: "out_ds"}``) fans a uniform sub-plan over the ordered members of a
    #: collection DataState (ADR-0199) and writes their ordered ``sub_target``
    #: outputs to ``out_ds``; a ``fold`` node (``{"kind": "fold",
    #: "reducer_iri", "in_ds"}``) dispatches an L3 reducer over that ordered
    #: list. A ref absent from this map is a plain leaf (v0 / Slice-1a path,
    #: unchanged).
    #:
    #: **Nesting (Slice 2):** a ``map`` node may additionally carry an optional
    #: ``"sub_plan"`` — a nested plan
    #: ``{"leaf_milestone_refs", "pipeline_refs", "milestone_specs",
    #: "leaf_targets"?, "solve_target"?}`` (the same shape this dataclass
    #: carries, as a plain dict). When present, each member runs that sub-plan in
    #: an isolated sub-blackboard (seeded with the member value) instead of the
    #: flat 1b ``find_pipeline(member_ds -> sub_target)`` leaf, and the map
    #: collects ``sub_target`` from that sub-blackboard; the sub-plan may itself
    #: contain a nested ``map``/``fold``. When absent, the member runs the flat
    #: 1b path — byte-identical. Emitted by the consumer's planner (arc's
    #: ``derive_initial_plan`` shadow), not by core (locked decision 3).
    #:
    #: **Multi-input members (map-member multi-input CR):** a ``map`` node may
    #: additionally carry an optional ``"shared_inputs": [ds, ...]`` — parent
    #: blackboard keys copied into **every** member's sub-blackboard alongside
    #: the member value, so a member capacity's non-member inputs (domain
    #: constants, or a per-map shared value) have a source inside the member run.
    #: They also join the member composition's start set, so the arity-derived
    #: finder (``ConjunctionFinder`` past one start) wires a multi-input member
    #: soundly; an optional ``"finder"`` key overrides the derivation as for
    #: ``leaf_targets``. A declared key missing from the parent blackboard raises
    #: ``ValueError`` naming the key and the map. Absent → byte-identical to
    #: Slice 1b/2/3b.
    milestone_specs: Optional[Dict[str, Dict[str, Any]]] = None


def _read_solve_target(plan_out: Any) -> Optional[Dict[str, str]]:
    """Extract the solve pipeline's ``{start,target}`` DataState endpoints from
    the planner's ``planning.plan`` output, or ``None``.

    Tolerant by construction: a v0 plan (or any plan without a well-formed
    ``solve_target`` naming both a non-empty ``start_datastate`` and
    ``target_datastate``) yields ``None`` → the notional-record fallback."""
    if not isinstance(plan_out, Mapping):
        return None
    st = plan_out.get("solve_target")
    if not isinstance(st, Mapping):
        return None
    start = st.get("start_datastate")
    target = st.get("target_datastate")
    if not start or not target:
        return None
    return {"start_datastate": start, "target_datastate": target}


def build(
    dispatcher, writer, mapping_result_ref, request_pattern_iri, *,
    resolved_reference: Any = None,
) -> PlanResult:
    # Derive initial plan (v0: single-Milestone). ``resolved_reference`` (Step
    # 5.1 / Phase-1→2 drop fix) rides the already-declared ``DS_MAPPING_RESULT``
    # value dict — no new declared input, so the strict ``_validate_inputs``
    # contract is untouched and the v0 body (reads only ``request_pattern_iri``)
    # ignores it. The planner's output is no longer discarded: its
    # ``solve_target`` (when present) tells ``execution.run`` what pipeline to
    # find + run.
    plan_out = dispatcher.dispatch(
        DERIVE_PLAN_IRI,
        {DS_MAPPING_RESULT: {
            "request_pattern_iri": request_pattern_iri,
            "resolved_reference": resolved_reference,
        }},
    ).outputs.get(DS_PLAN)
    solve_target = _read_solve_target(plan_out)

    # Collection-iteration wiring (ADR-0199 / locked decision 3): when the
    # planner returns an ordered ``milestones`` list, emit one leaf per entry
    # (in planner order) under a non-leaf root and key ``milestone_specs`` /
    # ``leaf_targets`` to the emitted refs. Absent the list, the body below is
    # byte-identical to the v0 / single-``solve_target`` path.
    milestones = _read_milestones(plan_out)
    if milestones is not None:
        return _build_from_milestones(
            writer, mapping_result_ref, milestones, solve_target
        )

    root = writer.emit_milestone("root", 0, is_leaf=True)
    plan = writer.emit_plan(root.iri, mapping_result_ref)

    # lazy decomposition + leaf detection (v0: root is the sole leaf)
    leaves = _decompose_recursive(dispatcher, writer, root, depth=0)

    pipelines: Dict[str, str] = {}
    for leaf_ref in leaves:
        pipe = writer.emit_pipeline(plan.iri, leaf_ref)
        pipelines[leaf_ref] = pipe.iri

    return PlanResult(
        plan_ref=plan.iri,
        root_milestone_ref=root.iri,
        leaf_milestone_refs=leaves,
        pipeline_refs=pipelines,
        solve_target=solve_target,
    )


def _read_milestones(plan_out: Any) -> Optional[List[Mapping]]:
    """Extract a planner's ordered ``milestones`` list from ``plan_out``, or
    ``None`` for the v0 / single-``solve_target`` path.

    Tolerant by construction: anything other than a Mapping carrying a **non-empty
    list** under ``"milestones"`` yields ``None`` (an empty list included -> v0).
    Each entry must be a Mapping ``{"spec"?, "leaf_target"?}``; one malformed entry
    aborts the whole list to ``None`` (a bad shape must not emit a partial plan)."""
    if not isinstance(plan_out, Mapping):
        return None
    ms = plan_out.get("milestones")
    if not isinstance(ms, list) or not ms:
        return None
    if not all(isinstance(m, Mapping) for m in ms):
        return None
    return ms


def _read_leaf_target(entry: Mapping) -> Optional[Dict[str, str]]:
    """A milestone entry's optional per-leaf ``{start,target}`` endpoints, or
    ``None`` -- same well-formedness rule as :func:`_read_solve_target`."""
    lt = entry.get("leaf_target")
    if not isinstance(lt, Mapping):
        return None
    start = lt.get("start_datastate")
    target = lt.get("target_datastate")
    if not start or not target:
        return None
    return {"start_datastate": start, "target_datastate": target}


def _build_from_milestones(
    writer, mapping_result_ref, milestones, solve_target,
) -> PlanResult:
    """Emit one leaf Milestone per planner ``milestones`` entry (in order) under a
    synthetic non-leaf root, keying ``milestone_specs`` / ``leaf_targets`` to the
    emitted refs (collection-iteration; ADR-0199 / locked decision 3).

    The root stays a non-leaf parent -- ``emit_plan`` anchors on it and
    ``root_milestone_ref`` is a single ref -- and the entries are its ordered leaf
    children. ``leaf_milestone_refs`` preserves planner order (the executor's value
    bus depends on it: a map's ``out_ds`` must be produced before the fold reads its
    ``in_ds``). ``spec`` is passed through verbatim (core stays agnostic to map/fold
    contents); ``leaf_target`` is validated like the plan-global ``solve_target``.
    An entry with neither is a plain leaf -- it falls back to ``solve_target`` at
    execution. ``milestone_specs`` / ``leaf_targets`` stay ``None`` when empty so a
    milestones-list of plain leaves keeps the executor's plain-leaf path."""
    root = writer.emit_milestone("root", 0, is_leaf=False)
    plan = writer.emit_plan(root.iri, mapping_result_ref)
    leaf_refs: List[str] = []
    pipelines: Dict[str, str] = {}
    milestone_specs: Dict[str, Dict[str, Any]] = {}
    leaf_targets: Dict[str, Dict[str, str]] = {}
    for idx, entry in enumerate(milestones):
        child = writer.emit_milestone(
            f"m0.{idx}", idx, parent_ref=root.iri, is_leaf=True
        )
        leaf_refs.append(child.iri)
        pipe = writer.emit_pipeline(plan.iri, child.iri)
        pipelines[child.iri] = pipe.iri
        spec = entry.get("spec")
        if isinstance(spec, Mapping):
            milestone_specs[child.iri] = dict(spec)
        leaf_target = _read_leaf_target(entry)
        if leaf_target is not None:
            leaf_targets[child.iri] = leaf_target
    return PlanResult(
        plan_ref=plan.iri,
        root_milestone_ref=root.iri,
        leaf_milestone_refs=leaf_refs,
        pipeline_refs=pipelines,
        solve_target=solve_target,
        leaf_targets=leaf_targets or None,
        milestone_specs=milestone_specs or None,
    )


def _decompose_recursive(dispatcher, writer, milestone, *, depth: int) -> List[str]:
    is_leaf = dispatcher.dispatch(IS_LEAF_IRI, {DS_MILESTONE: {}}).outputs[DS_IS_LEAF]
    if is_leaf or depth >= MAX_DEPTH:
        return [milestone.iri]
    children = dispatcher.dispatch(
        DECOMPOSE_IRI, {DS_MILESTONE: {}}
    ).outputs[DS_MILESTONE_LIST]
    leaves: List[str] = []
    for idx, _child_spec in enumerate(children):
        child = writer.emit_milestone(
            f"m{depth}.{idx}", idx, parent_ref=milestone.iri, is_leaf=False
        )
        leaves.extend(
            _decompose_recursive(dispatcher, writer, child, depth=depth + 1)
        )
    return leaves or [milestone.iri]


__all__ = ["build", "PlanResult", "MAX_DEPTH"]
