"""Reads of stored knowledge are declared by role (``mindsos_llm`` plan I-20,
gate 1; ruling R48).

R48: a capacity declares the L2 roles it reads; the read channels reach a body
only when declared, on both invoke paths, and are limited to the declared
roles. Before it, ``L4Dispatcher.build_context`` handed every body the whole
``KnowledgeLayer`` as ``kl`` and the whole learned-parameters snapshot, and
``CapacityLayer.invoke`` put ``kl`` into every body's dict context - while the
one body that reads L2 (the policy lookup) could not read at all on that path,
because it asks ``getattr(context, "kl")`` of a dict.

The channels, measured (plan section 6, 2026-10-24):

* ``kl`` - the read handle. ``global_view()`` is every Global role and
  ``read_at_version(iri)`` resolves any IRI, in any user's Local too.
* ``learned_parameters_snapshot`` - the ``learned-parameters`` role, so one
  declaration of that role is what lets the snapshot through.

What this file pins:

* **The behaviour, on BOTH invoke paths** - an undeclared body gets ``None``
  for both channels (``None``, not ``{}``: an empty snapshot reads as *"no
  knob set"* and a body falls back to its defaults without a sound); a
  declared body gets a handle that refuses every role it did not declare.
* **The census, both directions** - which bodies reach a read channel, by the
  syntax tree, reconciled against which modules declare ``reads_roles``. The
  shape of ``tests/architecture/test_write_is_declared.py``.

Not claimed: that a body does only what it declares - a body that duck-types
past its context into private attributes is outside what a check outside the
body can see (R53). Where stored content came from (R48).
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

import pytest

from mindsos_capacity import CapacityLayer, CapacityRegistrationError
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import CATEGORY_DERIVATION, capacity_iri, datastate_iri
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.exceptions import UnknownRoleError
from mindsos_knowledge.identifiers import ROLE_LEARNED_PARAMETERS, ROLE_ONTOLOGY
from mindsos_knowledge.learned_parameters_snapshot import read_learned_parameter_snapshot
from mindsos_knowledge.policies import NODE_POLICY_EDITION, ROLE_POLICIES
from mindsos_knowledge.schemas.learned_parameters import NODE_LEARNED_PARAMETER

from tests.run_records._fixtures import (
    CAP_LOOKUP,
    DS_AS_OF_DATE,
    DS_FILING_THRESHOLD,
    Session,
    _datastates,
    build_kl_with_both,
    lookup_declaration,
)

DS_SEEN = datastate_iri("rdr.seen")
CAP_PEEK = capacity_iri(CATEGORY_DERIVATION, "rdr_peek")
CAP_PEEK_PARAMS = capacity_iri(CATEGORY_DERIVATION, "rdr_peek_params")

PARAM_SET = "parameterset:rdr"
PARAM_TARGET = "parameter:rdr.threshold"


def _undeclared_role_error():
    from mindsos_knowledge.declared_reads import UndeclaredRoleReadError

    return UndeclaredRoleReadError


def _channels(context):
    """What a body was handed, whichever context shape it got."""
    if context is None:
        return {"kl": None, "snapshot": None}
    if isinstance(context, Mapping):
        return {"kl": context.get("kl"), "snapshot": context.get("learned_parameters_snapshot")}
    return {
        "kl": getattr(context, "kl", None),
        "snapshot": getattr(context, "learned_parameters_snapshot", None),
    }


def _peek(context=None, **inputs):
    return {DS_SEEN: _channels(context)}


def _layer(kl, *declarations):
    session = Session()
    layer = CapacityLayer(kl=kl)
    layer.register_datastate(
        DataState(name="rdr.seen", shape=ShapeDescriptor.opaque("rdr.seen"),
                  description="the channels a body was handed",
                  provenance_category=CATEGORY_DERIVATION),
        session=session, allow_new_realm=True,
    )
    for declaration in declarations:
        layer.register_capacity(declaration, session=session)
    return layer, session


def _peek_declaration(name="rdr_peek", **flags):
    return Capacity(
        name=name, category=CATEGORY_DERIVATION, inputs=(), outputs=(DS_SEEN,),
        implementation=_peek, description="reports the channels it was handed",
        **flags,
    )


def _seed_parameter(kl, value=0.75):
    graph = next(
        g for g in kl.global_metagraph().graphs.values() if g.role == ROLE_LEARNED_PARAMETERS
    )
    graph.add_node(
        value=value,
        type_name=NODE_LEARNED_PARAMETER,
        properties={"parameter_set_iri": PARAM_SET, "target_parameter_iri": PARAM_TARGET},
        node_id="learned-parameters-v1:parameter:rdr",
    )
    return {PARAM_SET: {PARAM_TARGET: value}}


# ── the declaration ───────────────────────────────────────────────────


def test_a_capacity_declares_no_reads_by_default():
    assert _peek_declaration().reads_roles == ()


def test_the_policy_lookup_declares_the_role_it_reads():
    """Spelled as a literal in the L3 module (it imports no L2 at module
    level); this is what keeps the literal equal to L2's constant."""
    assert lookup_declaration().reads_roles == (ROLE_POLICIES,)


def test_an_unknown_role_is_refused_at_registration():
    with pytest.raises(CapacityRegistrationError, match="not a knowledge role"):
        _layer(KnowledgeLayer.bootstrap(), _peek_declaration(reads_roles=("polices",)))


def test_l2_refuses_an_unknown_role_without_a_registration():
    with pytest.raises(UnknownRoleError):
        KnowledgeLayer.bootstrap().declared_reads(("polices",), user_id="u")


# ── the L2 handle ─────────────────────────────────────────────────────


def test_the_declared_handle_satisfies_the_kl_protocol():
    from mindsos_capacity import KLHandle

    assert isinstance(
        KnowledgeLayer.bootstrap().declared_reads((ROLE_POLICIES,), user_id="u"), KLHandle
    )


def test_the_view_reads_a_declared_role_and_refuses_the_rest():
    view = build_kl_with_both().declared_reads((ROLE_POLICIES,), user_id="u").global_view()
    assert len(list(view.iter_nodes(ROLE_POLICIES, type_=NODE_POLICY_EDITION))) == 2
    with pytest.raises(_undeclared_role_error()):
        list(view.iter_nodes(ROLE_ONTOLOGY))
    assert view.roles() == {ROLE_POLICIES}


def test_read_at_version_refuses_a_node_in_an_undeclared_role():
    kl = build_kl_with_both()
    iri = next(iter(kl.global_view().iter_nodes(ROLE_POLICIES))).node_id
    assert kl.declared_reads((ROLE_POLICIES,), user_id="u").read_at_version(iri, 0) is not None
    with pytest.raises(_undeclared_role_error()):
        kl.declared_reads((ROLE_ONTOLOGY,), user_id="u").read_at_version(iri, 0)


def test_read_at_version_does_not_reach_another_users_local():
    kl = KnowledgeLayer.bootstrap()
    _seed_local_parameter(kl, "other")
    iri = "learned-parameters-v1:parameter:rdr-local"
    assert kl.read_at_version(iri, 0) is not None, "the seed did not land"
    reads = kl.declared_reads((ROLE_LEARNED_PARAMETERS,), user_id="me")
    assert reads.read_at_version(iri, 0) is None


def _seed_local_parameter(kl, user):
    graph = next(
        g for g in kl.local_metagraph(user).graphs.values() if g.role == ROLE_LEARNED_PARAMETERS
    )
    graph.add_node(
        value=1, type_name=NODE_LEARNED_PARAMETER,
        properties={"parameter_set_iri": PARAM_SET, "target_parameter_iri": PARAM_TARGET},
        node_id="learned-parameters-v1:parameter:rdr-local",
    )


# ── the dispatcher path ───────────────────────────────────────────────


def _dispatcher(kl, learned=None):
    return L4Dispatcher(
        CapacityLayer(kl=kl), session=Session(), kl=kl, learned_parameters=learned
    )


def test_l4_withholds_both_read_channels_from_an_undeclared_body():
    ctx = _dispatcher(build_kl_with_both(), {PARAM_SET: {PARAM_TARGET: 1}}).build_context()
    assert ctx.kl is None
    assert ctx.learned_parameters_snapshot is None


def test_l4_hands_a_declared_body_only_its_roles():
    kl = build_kl_with_both()
    ctx = _dispatcher(kl, {PARAM_SET: {PARAM_TARGET: 1}}).build_context(
        reads_roles=(ROLE_POLICIES,)
    )
    assert ctx.kl is not None and ctx.kl is not kl
    assert len(list(ctx.kl.global_view().iter_nodes(ROLE_POLICIES))) == 2
    with pytest.raises(_undeclared_role_error()):
        list(ctx.kl.global_view().iter_nodes(ROLE_LEARNED_PARAMETERS))
    assert ctx.learned_parameters_snapshot is None


def test_l4_hands_the_snapshot_only_to_a_body_declaring_learned_parameters():
    learned = {PARAM_SET: {PARAM_TARGET: 1}}
    ctx = _dispatcher(build_kl_with_both(), learned).build_context(
        reads_roles=(ROLE_LEARNED_PARAMETERS,)
    )
    assert dict(ctx.learned_parameters_snapshot) == learned
    with pytest.raises(_undeclared_role_error()):
        list(ctx.kl.global_view().iter_nodes(ROLE_POLICIES))


def test_l4_dispatch_reads_the_declaration():
    kl = build_kl_with_both()
    layer, session = _layer(kl, _peek_declaration(reads_roles=(ROLE_POLICIES,)))
    seen = L4Dispatcher(layer, session=session, kl=kl).dispatch(CAP_PEEK, {}).outputs[DS_SEEN]
    assert seen["kl"] is not None and seen["kl"] is not kl
    assert seen["snapshot"] is None


# ── the direct path ───────────────────────────────────────────────────


def test_direct_invoke_withholds_both_read_channels_from_an_undeclared_body():
    kl = build_kl_with_both()
    layer, session = _layer(kl, _peek_declaration())
    result = layer.invoke(CAP_PEEK, {}, session=session, request_id="T")
    assert result.success, result.error
    assert result.outputs[DS_SEEN] == {"kl": None, "snapshot": None}


def test_direct_invoke_hands_a_declared_reader_its_roles():
    """The policy lookup, on the path where it could not read at all."""
    session = Session()
    layer = CapacityLayer(kl=build_kl_with_both())
    for datastate in _datastates():
        layer.register_datastate(datastate, session=session, allow_new_realm=True)
    layer.register_capacity(lookup_declaration(), session=session)
    result = layer.invoke(
        CAP_LOOKUP, {DS_AS_OF_DATE: "2024-04-15"}, session=session, request_id="T"
    )
    assert result.success, result.error
    assert result.outputs[DS_FILING_THRESHOLD] == 29200


def test_direct_invoke_hands_the_snapshot_to_a_body_declaring_learned_parameters():
    kl = KnowledgeLayer.bootstrap()
    expected = _seed_parameter(kl)
    assert read_learned_parameter_snapshot(kl, "") == expected, "the seed did not land"
    layer, session = _layer(
        kl, _peek_declaration("rdr_peek_params", reads_roles=(ROLE_LEARNED_PARAMETERS,))
    )
    result = layer.invoke(CAP_PEEK_PARAMS, {}, session=session, request_id="T")
    assert result.success, result.error
    assert dict(result.outputs[DS_SEEN]["snapshot"]) == expected


# ── the census ────────────────────────────────────────────────────────


_PACKAGES = (
    "mindsos_core",
    "mindsos_knowledge",
    "mindsos_capacity",
    "mindsos_intelligence",
    "mindsos_llm",
    "mindsos_broker",
    "mindsos_instances",
    "mindsos_admin",
    "mindsos_server",
    "mindsos_cli",
)

_READ_CHANNELS = ("kl", "learned_parameters_snapshot")

#: Every module whose bodies reach a read channel. A new entry means another
#: capacity reads stored knowledge - it arrives here with its declaration.
EXPECTED_READ_BODIES = {
    "mindsos_capacity/builtins/policy_lookup_v0.py": 1,  # policies
}


def _source_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if all((parent / pkg).is_dir() for pkg in _PACKAGES):
            return parent
    raise RuntimeError("source root not found")


def _is_context(node) -> bool:
    return isinstance(node, ast.Name) and node.id in ("context", "ctx")


def _is_channel(node) -> bool:
    return isinstance(node, ast.Constant) and node.value in _READ_CHANNELS


def read_channel_reaches(source: str) -> int:
    """Real reaches for a read channel: ``context.kl``, ``getattr(context,
    "kl", ...)``, ``context.get("kl")``, ``context["kl"]`` - and the same for
    ``learned_parameters_snapshot`` - where the name is ``context`` or
    ``ctx``. By the syntax tree, so prose cannot count.

    The ``kl=`` keyword that BUILDS a context is not a reach: building it is
    the dispatcher's job, reaching for it is the body's.
    """
    n = 0
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Attribute) and _is_context(node.value):
            n += node.attr in _READ_CHANNELS
        elif isinstance(node, ast.Subscript) and _is_context(node.value):
            n += _is_channel(node.slice)
        elif isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Name) and func.id == "getattr"
                and len(node.args) >= 2 and _is_context(node.args[0])
                and _is_channel(node.args[1])
            ):
                n += 1
            elif (
                isinstance(func, ast.Attribute) and func.attr == "get"
                and _is_context(func.value) and node.args and _is_channel(node.args[0])
            ):
                n += 1
    return n


def declares_reads(source: str) -> int:
    """``reads_roles=`` keywords whose value is a NON-EMPTY tuple or list
    literal - a declaration names its roles. A forwarded value
    (``build_context(reads_roles=tuple(...))`` in the dispatcher) is plumbing,
    not a declaration, exactly as ``writes=bool(...)`` is not one next door."""
    return sum(
        1
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        for kw in node.keywords
        if kw.arg == "reads_roles"
        and isinstance(kw.value, (ast.Tuple, ast.List))
        and kw.value.elts
    )


def _census(fn) -> dict:
    root = _source_root()
    out = {}
    for pkg in _PACKAGES:
        for path in sorted((root / pkg).rglob("*.py")):
            n = fn(path.read_text(encoding="utf-8"))
            if n:
                out[str(path.relative_to(root))] = n
    return out


def test_read_body_census_is_exact():
    got = _census(read_channel_reaches)
    assert got == EXPECTED_READ_BODIES, (
        "the set of bodies that read stored knowledge changed; it stays "
        f"enumerable by declaration. Got {got!r}"
    )


def test_a_declaration_backs_every_read_body():
    bodies = set(_census(read_channel_reaches))
    declared = set(_census(declares_reads))
    assert bodies <= declared, (
        "these modules reach a read channel without declaring reads_roles, so "
        f"both invoke paths hand them None: {sorted(bodies - declared)}"
    )


def test_every_read_declaration_has_a_body_that_reads():
    bodies = set(_census(read_channel_reaches))
    declared = set(_census(declares_reads))
    assert declared <= bodies, (
        "these modules declare reads_roles but no body in them reaches a read "
        f"channel - drop the declaration or read through it: {sorted(declared - bodies)}"
    )


def test_the_census_is_load_bearing():
    assert sum(EXPECTED_READ_BODIES.values()) >= 1
    assert _census(declares_reads), "no module declares reads_roles"


def test_the_checker_sees_every_reach_shape():
    shapes = (
        "x = context.kl\n",
        "x = getattr(context, 'kl', None)\n",
        "x = ctx.get('kl')\n",
        "x = context['learned_parameters_snapshot']\n",
        "x = ctx.learned_parameters_snapshot\n",
    )
    assert [read_channel_reaches(s) for s in shapes] == [1, 1, 1, 1, 1]


def test_the_checker_does_not_count_prose_construction_or_empty_declarations():
    source = (
        '"""a body that never touches context.kl"""\n'
        "ctx = CapacityContext(kl=reads, learned_parameters_snapshot={})\n"
        "cap = Capacity(name='x', reads_roles=())\n"
    )
    assert read_channel_reaches(source) == 0
    assert declares_reads(source) == 0
    assert declares_reads("cap = Capacity(name='x', reads_roles=(ROLE,))\n") == 1
    assert declares_reads("ctx = d.build_context(reads_roles=tuple(roles))\n") == 0
