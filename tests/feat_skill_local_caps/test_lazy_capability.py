"""ADR-0183 §am-5 — installed-skill Local capabilities.

Proves the "skill as app" lifecycle at L3, no DB: a capability is registered
metadata-only at boot (no skill code run), its live function is built on first
use, and reused thereafter. Plus the manifest ``[[l3.local_capacity]]`` parse.

Reuses the shipped f9 re-activation fixtures (hand-rolled DataStates + a
Local-scoped session) — the same building blocks ``reactivate_from_descriptors``
is tested with.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    Capacity,
    CapacityLayer,
    ReactivationError,
    register_reactivation_factory,
    unregister_reactivation_factory,
)

from mindsos_server.skills.manifest import parse_manifest
from tests.f9._fixtures import DuckSession, raw_ds, tokens_ds

_IRI = "capacity:perception:text.shout"


def _shout_factory(desc):
    """The skill's builder: produces ONLY the live function (called on first
    use). Uppercases the input."""
    out = desc["outputs"][0]
    inp = desc["inputs"][0]
    return Capacity(
        name=desc["name"],
        category=desc["category"],
        inputs=tuple(desc["inputs"]),
        outputs=tuple(desc["outputs"]),
        implementation=lambda **kw: {out: kw[inp].upper()},
    )


def _descriptor(reactivation_key: str = "shout-demo"):
    return {
        "name": "text.shout",
        "category": CATEGORY_PERCEPTION,
        "inputs": [raw_ds().iri],
        "outputs": [tokens_ds().iri],
        "reactivation_key": reactivation_key,
    }


def _fresh_layer() -> CapacityLayer:
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    cl.register_datastate(raw_ds())
    cl.register_datastate(tokens_ds())
    return cl


@pytest.fixture
def factory():
    register_reactivation_factory("shout-demo", _shout_factory, if_exists="upsert")
    yield
    unregister_reactivation_factory("shout-demo")


def test_boot_registers_metadata_only_then_builds_on_first_use(factory):
    cl = _fresh_layer()
    alice = DuckSession("alice")
    cl.register_lazy_capacity(_descriptor(), session=alice)

    # As at boot: registered + planner-selectable, function NOT built (no skill
    # code ran) — metadata only.
    assert _IRI in cl._declarations
    assert cl._declarations[_IRI].implementation is None

    # First use builds the live function via the builder + runs it.
    res = cl.invoke(_IRI, {raw_ds().iri: "hello"}, session=alice)
    assert res.success
    assert res.outputs[tokens_ds().iri] == "HELLO"

    # Now bound — subsequent resolves reuse the built function.
    assert cl._declarations[_IRI].implementation is not None
    res2 = cl.invoke(_IRI, {raw_ds().iri: "world"}, session=alice)
    assert res2.success
    assert res2.outputs[tokens_ds().iri] == "WORLD"


def test_missing_builder_surfaces_only_on_first_use():
    cl = _fresh_layer()
    alice = DuckSession("alice")
    cl.register_lazy_capacity(
        _descriptor(reactivation_key="no-such-factory"), session=alice
    )
    # Still selectable at boot (metadata only); the missing builder is a
    # first-use failure, not a boot brick.
    assert cl._declarations[_IRI].implementation is None
    with pytest.raises(ReactivationError):
        cl.invoke(_IRI, {raw_ds().iri: "hi"}, session=alice)


_MANIFEST = """\
[bundle]
name = "lazy-demo"
version = "0.1.0"

[[l3.local_capacity]]
name = "text.shout"
category = "perception"
reactivation_key = "shout-demo"
inputs = ["datastate:text.raw"]
outputs = ["datastate:text.tokens"]

[l3.local_capacity.params]
note = "opaque to core"
"""


def test_manifest_parses_local_capacity(tmp_path):
    p = tmp_path / "manifest.toml"
    p.write_text(_MANIFEST)
    m = parse_manifest(p)
    assert len(m.l3_local_capacities) == 1
    e = m.l3_local_capacities[0]
    assert e.name == "text.shout"
    assert e.category == "perception"
    assert e.reactivation_key == "shout-demo"
    assert e.inputs == ("datastate:text.raw",)
    assert e.outputs == ("datastate:text.tokens",)
    assert dict(e.params) == {"note": "opaque to core"}
