"""Map-member multi-input CR — sound composition + ``shared_inputs``.

Through Slice 3b a map member's (and a plain leaf's) pipeline was composed with
the single-input ``find_pipeline`` (``BFSFinder``) and a member sub-run was
seeded with only the member value. A member whose work is a genuinely
multi-input composed segment therefore could not run: the finder left the other
declared inputs unwired, and even a sound finder had no source for them inside
the member run.

Two additive spec keys lift that — plural ``leaf_targets[…]["start_datastates"]``
and a map spec's ``shared_inputs`` — with the finder chosen by **arity** (more
than one start ⇒ ``ConjunctionFinder``; one ⇒ ``BFSFinder``, the pre-CR path).
These tests exercise it over real capacities (no Falkor), mirroring
``test_slice1b_map_fold.py`` / ``test_slice2_nesting.py``.

The shape under test is the real consumer's: a map over **window start
positions** (the member) with the full signals + a domain constant as shared
inputs, composing ``cut_a``/``cut_b`` → ``feat``/``harm`` → ``sig`` per member.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import CapacityLayer
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_DERIVATION,
    capacity_iri,
    datastate_iri,
)

from mindsos_intelligence import execution
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.plan_construction import PlanResult

# ── multi-input ontology (member = a start position; signals/const shared) ──
DS_COLL = datastate_iri("m2i.starts")       # collection of member positions
DS_POS = datastate_iri("m2i.start")         # one member: a position
DS_SIG_A = datastate_iri("m2i.signal_a")    # shared: full channel A
DS_SIG_B = datastate_iri("m2i.signal_b")    # shared: full channel B
DS_K = datastate_iri("m2i.k")               # shared: a domain constant
DS_WIN_A = datastate_iri("m2i.window_a")
DS_WIN_B = datastate_iri("m2i.window_b")
DS_FEAT = datastate_iri("m2i.features")
DS_HARM = datastate_iri("m2i.harmonics")
DS_SUB = datastate_iri("m2i.signature")     # per-member sub-target
DS_OUT = datastate_iri("m2i.signatures")    # ordered member outputs
DS_AGG = datastate_iri("m2i.conclusion")

CAP_CUT_A = capacity_iri(CATEGORY_DERIVATION, "m2i_cut_a")
CAP_CUT_B = capacity_iri(CATEGORY_DERIVATION, "m2i_cut_b")
CAP_FEAT = capacity_iri(CATEGORY_DERIVATION, "m2i_features")
CAP_HARM = capacity_iri(CATEGORY_DERIVATION, "m2i_harmonics")
CAP_SIG = capacity_iri(CATEGORY_DERIVATION, "m2i_signature")
CAP_REDUCE = capacity_iri(CATEGORY_DERIVATION, "m2i_reduce")

# ── single-input ontology (back-compat: the pre-CR flat member) ──
DS_FLAT_COLL = datastate_iri("m2i.flat_members")
DS_FLAT_MEMBER = datastate_iri("m2i.flat_member")
DS_FLAT_SUB = datastate_iri("m2i.flat_fact")
DS_FLAT_OUT = datastate_iri("m2i.flat_facts")
DS_FLAT_AGG = datastate_iri("m2i.flat_conclusion")
CAP_FLAT_SOLVE = capacity_iri(CATEGORY_DERIVATION, "m2i_flat_solve")
CAP_FLAT_REDUCE = capacity_iri(CATEGORY_DERIVATION, "m2i_flat_reduce")

#: What each multi-input member step actually received (proves the other
#: declared inputs were wired, not dropped) and what the reducer folded.
FEAT_SEEN: list = []
HARM_SEEN: list = []
REDUCER_SEEN: list = []
FLAT_SEEN: list = []
ATTEMPTS: dict = {}


class FakeSession:
    def __init__(self, user_id="u"):
        self.session_id = "s"
        self.user_id = user_id
        self.actor_role = "user"
        self.capabilities = set()

    def has(self, capability: str) -> bool:
        return False


# ── capacity bodies ───────────────────────────────────────────────────


def _cut_a(**kw):
    return {DS_WIN_A: f"a@{kw[DS_POS]}of{kw[DS_SIG_A]}"}


def _cut_b(**kw):
    return {DS_WIN_B: f"b@{kw[DS_POS]}of{kw[DS_SIG_B]}"}


def _features(**kw):
    """Two declared inputs, both produced upstream inside the member run."""
    FEAT_SEEN.append((kw[DS_WIN_A], kw[DS_WIN_B]))
    return {DS_FEAT: [kw[DS_WIN_A], kw[DS_WIN_B]]}


def _harmonics(**kw):
    """One produced input + one shared constant seeded into the member."""
    HARM_SEEN.append((kw[DS_WIN_A], kw[DS_K]))
    return {DS_HARM: [kw[DS_WIN_A], kw[DS_K]]}


def _signature(**kw):
    return {DS_SUB: {"feat": kw[DS_FEAT], "harm": kw[DS_HARM]}}


def _reduce(**kw):
    ordered = kw.get(DS_OUT)
    REDUCER_SEEN.append(ordered)
    return {DS_AGG: {"n": len(ordered or [])}}


def _flat_solve(**kw):
    v = kw.get(DS_FLAT_MEMBER)
    FLAT_SEEN.append(v)
    return {DS_FLAT_SUB: {"solved": v}}


def _flat_reduce(**kw):
    return {DS_FLAT_AGG: list(kw.get(DS_FLAT_OUT) or [])}


# ── registration ──────────────────────────────────────────────────────

_COLLECTIONS = {
    "m2i.starts": dict(collection=True, member_ds=DS_POS),
    "m2i.signatures": dict(collection=True, member_ds=DS_SUB),
    "m2i.flat_members": dict(collection=True, member_ds=DS_FLAT_MEMBER),
    "m2i.flat_facts": dict(collection=True, member_ds=DS_FLAT_SUB),
}

_DS_NAMES = (
    "m2i.starts", "m2i.start", "m2i.signal_a", "m2i.signal_b", "m2i.k",
    "m2i.window_a", "m2i.window_b", "m2i.features", "m2i.harmonics",
    "m2i.signature", "m2i.signatures", "m2i.conclusion",
    "m2i.flat_members", "m2i.flat_member", "m2i.flat_fact", "m2i.flat_facts",
    "m2i.flat_conclusion",
)


def _register(layer, *, session=None, feature_impl=None):
    for name in _DS_NAMES:
        layer.register_datastate(
            DataState(
                name=name,
                shape=ShapeDescriptor.opaque(name),
                description=name,
                provenance_category=CATEGORY_DERIVATION,
                **_COLLECTIONS.get(name, {}),
            ),
            session=session,
            allow_new_realm=True,
        )
    caps = (
        ("m2i_cut_a", (DS_POS, DS_SIG_A), (DS_WIN_A,), _cut_a),
        ("m2i_cut_b", (DS_POS, DS_SIG_B), (DS_WIN_B,), _cut_b),
        ("m2i_features", (DS_WIN_A, DS_WIN_B), (DS_FEAT,),
         feature_impl or _features),
        ("m2i_harmonics", (DS_WIN_A, DS_K), (DS_HARM,), _harmonics),
        ("m2i_signature", (DS_FEAT, DS_HARM), (DS_SUB,), _signature),
        ("m2i_reduce", (DS_OUT,), (DS_AGG,), _reduce),
        ("m2i_flat_solve", (DS_FLAT_MEMBER,), (DS_FLAT_SUB,), _flat_solve),
        ("m2i_flat_reduce", (DS_FLAT_OUT,), (DS_FLAT_AGG,), _flat_reduce),
    )
    for name, inputs, outputs, impl in caps:
        layer.register_capacity(
            Capacity(
                name=name, category=CATEGORY_DERIVATION,
                inputs=inputs, outputs=outputs, implementation=impl,
                description=name,
            ),
            session=session,
        )


def _harness(feature_impl=None):
    sess = FakeSession()
    layer = CapacityLayer()
    _register(layer, session=sess, feature_impl=feature_impl)
    mm = MentalModel(session_id="s", user_id="u")
    disp = L4Dispatcher(layer, session=sess)
    writer = ChainArtifactWriter(mm, "t")
    return mm, disp, writer, writer.emit_request_run()


SHARED = [DS_SIG_A, DS_SIG_B, DS_K]


def _multi_plan(*, shared=SHARED, finder=None, with_fold=True, sub_plan=None):
    spec = {
        "kind": "map", "collection_ds": DS_COLL, "member_ds": DS_POS,
        "sub_target": DS_SUB, "out_ds": DS_OUT,
    }
    if shared is not None:
        spec["shared_inputs"] = list(shared)
    if finder is not None:
        spec["finder"] = finder
    if sub_plan is not None:
        spec["sub_plan"] = sub_plan
    refs = ["mMap", "mFold"] if with_fold else ["mMap"]
    specs = {"mMap": spec}
    if with_fold:
        specs["mFold"] = {"kind": "fold", "reducer_iri": CAP_REDUCE, "in_ds": DS_OUT}
    return PlanResult(
        plan_ref="plan:m2i",
        root_milestone_ref="m0",
        leaf_milestone_refs=refs,
        pipeline_refs={r: f"p{r}" for r in refs},
        milestone_specs=specs,
    )


def _seed(positions=(0, 100)):
    return {
        DS_COLL: list(positions),
        DS_SIG_A: "A", DS_SIG_B: "B", DS_K: 7,
    }


def _clear():
    for lst in (FEAT_SEEN, HARM_SEEN, REDUCER_SEEN, FLAT_SEEN):
        lst.clear()
    ATTEMPTS.clear()


# ── the CR's acceptance test ──────────────────────────────────────────


def test_multi_input_member_fans_out_and_folds():
    """A member whose work is a multi-input composed pipeline (≥2 declared
    inputs, one of them supplied via ``shared_inputs``) fans out and folds
    end-to-end through ``execution.run``."""
    _clear()
    mm, disp, writer, request_run = _harness()
    graphs: list = []
    execution.run(
        disp, writer, _multi_plan(), request_run,
        mm=mm, run_scope="t", solve_seed=_seed(), capacity_graphs=graphs,
    )
    # Both declared inputs of the multi-input step were wired, per member.
    assert FEAT_SEEN == [("a@0ofA", "b@0ofB"), ("a@100ofA", "b@100ofB")]
    # The shared constant reached the member capacity that declares it.
    assert HARM_SEEN == [("a@0ofA", 7), ("a@100ofA", 7)]
    # The fold saw the ordered member outputs.
    assert REDUCER_SEEN == [[
        {"feat": ["a@0ofA", "b@0ofB"], "harm": ["a@0ofA", 7]},
        {"feat": ["a@100ofA", "b@100ofB"], "harm": ["a@100ofA", 7]},
    ]]
    # Two milestone PipelineRuns (map + fold); one grounding graph per member
    # PLUS the fold's own (fold-grounding CR — the fold used to leave nothing).
    assert len(request_run.pipeline_runs) == 2
    assert len(graphs) == 3


# ── back-compat: nothing new declared ⇒ the pre-CR path ───────────────


def _flat_plan():
    return PlanResult(
        plan_ref="plan:m2i-flat",
        root_milestone_ref="m0",
        leaf_milestone_refs=["mMap", "mFold"],
        pipeline_refs={"mMap": "pMap", "mFold": "pFold"},
        milestone_specs={
            "mMap": {
                "kind": "map", "collection_ds": DS_FLAT_COLL,
                "member_ds": DS_FLAT_MEMBER, "sub_target": DS_FLAT_SUB,
                "out_ds": DS_FLAT_OUT,
            },
            "mFold": {
                "kind": "fold", "reducer_iri": CAP_FLAT_REDUCE,
                "in_ds": DS_FLAT_OUT,
            },
        },
    )


def test_map_without_shared_inputs_uses_bfs_unchanged(monkeypatch):
    """No ``shared_inputs`` and a single-input member ⇒ ``BFSFinder``, exactly
    the Slice-1b path. The sound finder is never reached."""
    _clear()
    import mindsos_capacity.pipeline as pipeline_mod

    used: list = []
    for cls in (pipeline_mod.BFSFinder, pipeline_mod.ConjunctionFinder):
        original = cls.find
        name = cls.__name__

        def _spy(self, *a, _o=original, _n=name, **k):
            used.append(_n)
            return _o(self, *a, **k)

        monkeypatch.setattr(cls, "find", _spy)

    mm, disp, writer, request_run = _harness()
    execution.run(
        disp, writer, _flat_plan(), request_run,
        mm=mm, run_scope="t", solve_seed={DS_FLAT_COLL: ["a", "b"]},
    )
    assert FLAT_SEEN == ["a", "b"]
    assert set(used) == {"BFSFinder"}


def test_plain_leaf_singular_start_unchanged():
    """A plain leaf declaring the singular ``start_datastate`` is the 1a path."""
    _clear()
    mm, disp, writer, request_run = _harness()
    plan = PlanResult(
        plan_ref="plan:m2i-leaf1",
        root_milestone_ref="m0",
        leaf_milestone_refs=["mLeaf"],
        pipeline_refs={"mLeaf": "pLeaf"},
        solve_target={
            "start_datastate": DS_FLAT_MEMBER,
            "target_datastate": DS_FLAT_SUB,
        },
    )
    execution.run(
        disp, writer, plan, request_run,
        mm=mm, run_scope="t", solve_seed={DS_FLAT_MEMBER: "x"},
    )
    assert FLAT_SEEN == ["x"]


# ── plural leaf starts ────────────────────────────────────────────────


def test_plain_leaf_plural_starts_composes_multi_input():
    """A plain leaf may declare several available starts; the sound finder wires
    them all. This is the stage that would produce the map's collection."""
    _clear()
    mm, disp, writer, request_run = _harness()
    plan = PlanResult(
        plan_ref="plan:m2i-leafN",
        root_milestone_ref="m0",
        leaf_milestone_refs=["mLeaf"],
        pipeline_refs={"mLeaf": "pLeaf"},
        leaf_targets={
            "mLeaf": {
                "start_datastates": [DS_POS, DS_SIG_A, DS_SIG_B],
                "target_datastate": DS_FEAT,
            }
        },
    )
    execution.run(
        disp, writer, plan, request_run,
        mm=mm, run_scope="t",
        solve_seed={DS_POS: 5, DS_SIG_A: "A", DS_SIG_B: "B"},
    )
    assert FEAT_SEEN == [("a@5ofA", "b@5ofB")]


def test_leaf_declaring_both_start_forms_raises():
    _clear()
    mm, disp, writer, request_run = _harness()
    plan = PlanResult(
        plan_ref="plan:m2i-both",
        root_milestone_ref="m0",
        leaf_milestone_refs=["mLeaf"],
        pipeline_refs={"mLeaf": "pLeaf"},
        leaf_targets={
            "mLeaf": {
                "start_datastate": DS_WIN_A,
                "start_datastates": [DS_WIN_A, DS_WIN_B],
                "target_datastate": DS_FEAT,
            }
        },
    )
    with pytest.raises(ValueError, match="both"):
        execution.run(
            disp, writer, plan, request_run,
            mm=mm, run_scope="t", solve_seed={DS_WIN_A: "a", DS_WIN_B: "b"},
        )


# ── loud failures ─────────────────────────────────────────────────────


def test_missing_shared_input_raises_naming_key_and_map():
    _clear()
    mm, disp, writer, request_run = _harness()
    seed = _seed()
    del seed[DS_SIG_B]
    with pytest.raises(ValueError) as ei:
        execution.run(
            disp, writer, _multi_plan(), request_run,
            mm=mm, run_scope="t", solve_seed=seed,
        )
    assert DS_SIG_B in str(ei.value)
    assert "mMap" in str(ei.value)


def test_missing_shared_input_raises_even_for_empty_collection():
    """Validated before the fan-out, so a mis-authored spec is not masked by a
    collection that happens to be empty."""
    _clear()
    mm, disp, writer, request_run = _harness()
    seed = _seed(positions=())
    del seed[DS_K]
    with pytest.raises(ValueError, match="mMap"):
        execution.run(
            disp, writer, _multi_plan(), request_run,
            mm=mm, run_scope="t", solve_seed=seed,
        )


def test_explicit_bfs_with_plural_starts_raises():
    """Never silently under-wire: BFS cannot soundly consume several starts."""
    _clear()
    mm, disp, writer, request_run = _harness()
    with pytest.raises(ValueError) as ei:
        execution.run(
            disp, writer, _multi_plan(finder="bfs"), request_run,
            mm=mm, run_scope="t", solve_seed=_seed(),
        )
    assert "bfs" in str(ei.value)


def test_unknown_finder_name_raises():
    _clear()
    mm, disp, writer, request_run = _harness()
    with pytest.raises(ValueError, match="unknown finder"):
        execution.run(
            disp, writer, _multi_plan(shared=None, finder="dijkstra"), request_run,
            mm=mm, run_scope="t", solve_seed=_seed(),
        )


# ── compose-once + empty collection ───────────────────────────────────


def test_member_pipeline_composed_once_and_reused(monkeypatch):
    """Starts and target are identical across members, so the finder runs once
    for the whole fan-out — not once per member per retry."""
    _clear()
    import mindsos_capacity.pipeline as pipeline_mod

    calls: list = []
    original = pipeline_mod.ConjunctionFinder.find

    def _counting(self, *a, **k):
        calls.append(1)
        return original(self, *a, **k)

    monkeypatch.setattr(pipeline_mod.ConjunctionFinder, "find", _counting)
    mm, disp, writer, request_run = _harness()
    execution.run(
        disp, writer, _multi_plan(), request_run,
        mm=mm, run_scope="t", solve_seed=_seed(positions=(0, 10, 20, 30)),
    )
    assert len(FEAT_SEEN) == 4
    assert len(calls) == 1


def test_empty_collection_composes_nothing_and_still_folds(monkeypatch):
    """Composition stays lazy: an empty collection must keep completing with an
    empty output list rather than failing to find a member pipeline."""
    _clear()
    import mindsos_capacity.pipeline as pipeline_mod

    calls: list = []
    for cls in (pipeline_mod.BFSFinder, pipeline_mod.ConjunctionFinder):
        original = cls.find

        def _spy(self, *a, _o=original, **k):
            calls.append(1)
            return _o(self, *a, **k)

        monkeypatch.setattr(cls, "find", _spy)

    mm, disp, writer, request_run = _harness()
    execution.run(
        disp, writer, _multi_plan(), request_run,
        mm=mm, run_scope="t", solve_seed=_seed(positions=()),
    )
    assert REDUCER_SEEN == [[]]
    assert calls == []


# ── nesting + barrier semantics ───────────────────────────────────────


def test_shared_inputs_reach_a_sub_plan_member():
    """Slice-2 nesting: the shared inputs seed the member sub-blackboard, so a
    sub-plan leaf can declare them as starts."""
    _clear()
    sub_plan = {
        "leaf_milestone_refs": ["sLeaf"],
        "pipeline_refs": {"sLeaf": "psLeaf"},
        "leaf_targets": {
            "sLeaf": {
                "start_datastates": [DS_POS, DS_SIG_A, DS_SIG_B, DS_K],
                "target_datastate": DS_SUB,
            }
        },
    }
    mm, disp, writer, request_run = _harness()
    execution.run(
        disp, writer, _multi_plan(with_fold=False, sub_plan=sub_plan), request_run,
        mm=mm, run_scope="t", solve_seed=_seed(positions=(0, 5)),
    )
    assert FEAT_SEEN == [("a@0ofA", "b@0ofB"), ("a@5ofA", "b@5ofB")]
    assert HARM_SEEN == [("a@0ofA", 7), ("a@5ofA", 7)]


def test_all_abort_and_retry_cap_unchanged_with_shared_inputs():
    """∀-abort and ``MEMBER_RETRY_CAP`` are untouched by this CR: a member that
    still fails at the cap aborts the map, later members never run, and the fold
    never runs."""
    _clear()

    def _fail_second(**kw):
        FEAT_SEEN.append((kw[DS_WIN_A], kw[DS_WIN_B]))
        if kw[DS_WIN_A].startswith("a@100"):
            raise RuntimeError("member 1 compute failure")
        return {DS_FEAT: [kw[DS_WIN_A], kw[DS_WIN_B]]}

    mm, disp, writer, request_run = _harness(feature_impl=_fail_second)
    with pytest.raises(execution.MemberAbortError) as ei:
        execution.run(
            disp, writer, _multi_plan(), request_run,
            mm=mm, run_scope="t", solve_seed=_seed(positions=(0, 100, 200)),
        )
    assert ei.value.member_index == 1
    failing = [p for p in FEAT_SEEN if p[0].startswith("a@100")]
    assert len(failing) == execution.MEMBER_RETRY_CAP
    assert not any(p[0].startswith("a@200") for p in FEAT_SEEN)
    assert REDUCER_SEEN == []


def test_retry_accepts_first_clean_attempt_with_shared_inputs():
    _clear()

    def _fail_once(**kw):
        FEAT_SEEN.append((kw[DS_WIN_A], kw[DS_WIN_B]))
        key = kw[DS_WIN_A]
        ATTEMPTS[key] = ATTEMPTS.get(key, 0) + 1
        if key.startswith("a@100") and ATTEMPTS[key] == 1:
            raise RuntimeError("transient failure")
        return {DS_FEAT: [kw[DS_WIN_A], kw[DS_WIN_B]]}

    mm, disp, writer, request_run = _harness(feature_impl=_fail_once)
    execution.run(
        disp, writer, _multi_plan(), request_run,
        mm=mm, run_scope="t", solve_seed=_seed(positions=(0, 100, 200)),
    )
    assert ATTEMPTS["a@100ofA"] == 2
    assert len(REDUCER_SEEN) == 1 and len(REDUCER_SEEN[0]) == 3
