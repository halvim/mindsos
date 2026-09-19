"""A capacity DECLARES that it writes — plan ruling R7 (OWNER 2026-09-18).

``docs/plans/MINDSOS_LLM_PLAN.md`` §2 R7. Before it, ``outputs == ()`` was
the write marker, and both invoke sites gated the ``writeable`` injection on
it. That proxy held only because every write capacity shipped so far happened
to be a terminator; ADR-0210 §am-4 then ruled a recorder that writes AND
declares its pointer as an output, which the proxy makes unreachable on the
direct path while it works under ``L4Dispatcher`` — one asymmetry, two
dispatch paths, and no error message that names the cause.

**What this file pins, and why each half is needed.**

* **The census** — which bodies reach ``context.writeable``. By the syntax
  tree, never by grep: the census next door (``context.llm``) counted a
  docstring saying a capacity never calls a model and reported a consumer
  that does not exist.
* **The reconciliation, in BOTH directions.** A body that reaches
  ``writeable`` without declaring ``writes=True`` gets a context that cannot
  give it one; a declaration whose body never writes claims a capability it
  does not use, and the set of capacities that may write stops being
  enumerable. One direction alone closes nothing.
* **The behaviour** — that the DECLARATION, not the output count, is what
  puts a handle on the context. The census could be exact while the wiring
  reverted underneath it.

⚠ **The reconciliation reads the DECLARATIONS, not a hand-written list**,
except for :data:`EXPECTED_WRITE_BODIES`, which is the enumerable set R7
exists to keep: a new entry is a design event and lands with its row.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from mindsos_capacity import (
    Capacity,
    CapacityLayer,
    CapacityRegistrationError,
    DataState,
    Monitor,
    ShapeDescriptor,
)
from mindsos_capacity.identifiers import CATEGORY_PERCEPTION, capacity_iri
from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.identifiers import ROLE_PROMPTS

from tests.phase_34._fixtures import build_admin_session


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

#: Every body that reaches the injected write capability. A new entry means
#: another capacity mutates L2 — a design event, not an implementation
#: detail — and it arrives here with its row.
EXPECTED_WRITE_BODIES = {
    "mindsos_capacity/builtins/consolidate.py": 1,      # episodic memory
    "mindsos_capacity/builtins/trace.py": 1,            # problem trace
    "mindsos_capacity/builtins/learn_parameter.py": 1,  # learned parameters
    "mindsos_capacity/builtins/prompt_edition_v0.py": 1,  # prompts (I-9)
}


def _source_root() -> Path:
    """Marker-free package anchor — the image copies the packages and
    ``tests`` but no repo-root marker, so anchoring on the packages works in
    a checkout and in the container alike."""
    for parent in Path(__file__).resolve().parents:
        if all((parent / pkg).is_dir() for pkg in _PACKAGES):
            return parent
    raise RuntimeError("source root not found")


def writeable_reaches(source: str) -> int:
    """Count real reaches for the write capability in one module's source.

    ``<name>.writeable`` and ``getattr(<name>, "writeable", ...)`` where
    ``<name>`` is ``context`` or ``ctx``. Neither can be written in a
    comment, which is the whole reason this is an AST walk.

    ⚠ ``make_writeable(...)`` and the ``writeable=`` keyword that BUILDS a
    context are deliberately not counted: constructing the capability is the
    dispatcher's job, and reaching for it is the body's.
    """
    n = 0
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "writeable"
            and isinstance(node.value, ast.Name)
            and node.value.id in ("context", "ctx")
        ):
            n += 1
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id in ("context", "ctx")
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == "writeable"
        ):
            n += 1
    return n


def declares_writes(source: str) -> int:
    """Count ``writes=True`` keywords on calls in one module's source."""
    return sum(
        1
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        for kw in node.keywords
        if kw.arg == "writes"
        and isinstance(kw.value, ast.Constant)
        and kw.value.value is True
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


# ── the census ────────────────────────────────────────────────────────


def test_write_body_census_is_exact():
    got = _census(writeable_reaches)
    assert got == EXPECTED_WRITE_BODIES, (
        "the set of bodies that mutate L2 changed. A write is the one thing "
        "a capacity does that outlives its run, so the set stays enumerable "
        f"by declaration rather than inferred from shape. Got {got!r}"
    )


def test_a_declaration_backs_every_write_body():
    bodies = set(_census(writeable_reaches))
    declared = set(_census(declares_writes))
    assert bodies <= declared, (
        "these modules reach context.writeable without declaring writes=True, "
        "so both invoke sites hand them a context with no write capability "
        f"and the body raises at the first call: {sorted(bodies - declared)}"
    )


def test_every_declaration_has_a_body_that_writes():
    bodies = set(_census(writeable_reaches))
    declared = set(_census(declares_writes))
    assert declared <= bodies, (
        "these modules declare writes=True but no body in them reaches "
        "context.writeable. A declaration that overclaims is how the "
        "enumerable set stops meaning anything - drop the flag, or write "
        f"through the handle: {sorted(declared - bodies)}"
    )


# ── both checkers, shown refusing FABRICATED input ────────────────────
#
# Neither offence exists in the tree, so neither could be born red by
# mutating it (RULES §12, SMALLEST EDIT). A fabricated module is the
# smallest edit that makes each claim false.


def test_the_checker_sees_a_fabricated_undeclared_write():
    undeclared = "def body(**kw):\n    h = context.writeable(role='r', scope='local')\n"
    assert writeable_reaches(undeclared) == 1
    assert declares_writes(undeclared) == 0


def test_the_checker_sees_a_fabricated_overclaiming_declaration():
    overclaim = "cap = Capacity(name='x', outputs=(), writes=True)\n"
    assert declares_writes(overclaim) == 1
    assert writeable_reaches(overclaim) == 0


def test_the_checker_does_not_count_prose_or_context_construction():
    prose = (
        '"""This capacity never calls context.writeable, and writes=True is\n'
        'not what it declares."""\n'
        "ctx = CapacityContext(writeable=make_writeable(kl, session))\n"
    )
    assert writeable_reaches(prose) == 0
    assert declares_writes(prose) == 0


def test_the_census_is_load_bearing():
    """A census whose pattern matches nothing is green while checking zero
    rows — the ADR-guard defect this tree has already paid for once."""
    assert sum(EXPECTED_WRITE_BODIES.values()) >= 4
    assert _census(declares_writes)


# ── the behaviour the census cannot see ───────────────────────────────


DS_POINTER = "datastate:test.write_with_output_pointer"


def _layer_with(declaration, session):
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    layer.register_datastate(
        DataState(name="test.write_with_output_pointer",
                  shape=ShapeDescriptor.scalar("str")),
        session=session,
        allow_new_realm=True,
    )
    layer.register_capacity(declaration, session=session)
    return layer


def _body_that_writes_and_returns(**kwargs):
    context = kwargs.get("context")
    handle = context.writeable(role=ROLE_PROMPTS, scope="local", version="v1")
    return handle.role


def test_a_write_that_declares_an_output_still_gets_the_handle():
    """R7's whole point, and ADR-0210 §am-4's recorder in miniature.

    Under the old rule this capacity fell to the legacy dict context,
    ``getattr(context, "writeable")`` returned ``None``, and the body raised
    - on the direct path only, while the same declaration worked under
    ``L4Dispatcher``.
    """
    session = build_admin_session("admin")
    declaration = Capacity(
        name="write_with_output",
        category=CATEGORY_PERCEPTION,
        inputs=(),
        outputs=(DS_POINTER,),
        writes=True,
        implementation=_body_that_writes_and_returns,
        description="writes AND names what it wrote",
    )
    layer = _layer_with(declaration, session)
    result = layer.invoke(
        capacity_iri(CATEGORY_PERCEPTION, "write_with_output"),
        {},
        session=session,
        request_id="T",
    )
    assert result.success is True, result.error
    assert result.outputs == {DS_POINTER: ROLE_PROMPTS}
    assert result.write_outcome is None, (
        "a write that declares an output returns it in outputs; "
        "write_outcome is the TERMINATOR channel"
    )


def test_a_reactive_capacity_that_neither_produces_nor_writes_is_refused():
    session = build_admin_session("admin")
    declaration = Capacity(
        name="does_nothing_observable",
        category=CATEGORY_PERCEPTION,
        inputs=(),
        outputs=(),
        implementation=lambda **kw: None,
    )
    with pytest.raises(CapacityRegistrationError, match="nothing it does is observable"):
        CapacityLayer(kl=KnowledgeLayer.bootstrap()).register_capacity(
            declaration, session=session
        )


def test_a_monitor_with_no_outputs_is_still_legal():
    """The other door of the same predicate. A Monitor produces no DataState
    and writes nothing BY DEFINITION - the first cut of the refusal above was
    unscoped and would have outlawed every Monitor in the tree."""
    session = build_admin_session("admin")
    monitor = Monitor(
        name="watches_and_says_nothing",
        category=CATEGORY_PERCEPTION,
        inputs=(),
        outputs=(),
        subscribes_to=(),
        emits=(),
        implementation=lambda **kw: None,
        description="a monitor",
    )
    layer = CapacityLayer(kl=KnowledgeLayer.bootstrap())
    layer.register_capacity(monitor, session=session)
    assert capacity_iri(CATEGORY_PERCEPTION, "watches_and_says_nothing") in {
        d.iri for d in layer.iter_declarations()
    }
