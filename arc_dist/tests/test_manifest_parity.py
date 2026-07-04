"""Parity: the shipped manifest roster == what install_arc actually registers.

Guards the dual-source-of-truth (manifest TOML vs installer catalog). Any
capacity/datastate add/remove must regenerate the manifest or this fails.
Also asserts warm-layer idempotency (the ADR-0183 activation contract).
"""
from __future__ import annotations

try:
    import tomllib  # py3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib
from importlib import resources

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins.text import install_text_capacities
from mindsos_capacity.bootstrap import ensure_datastate_graph

from mindsos_arc import capacities as ac


def _manifest():
    with resources.files("mindsos_arc").joinpath("bundle/manifest.toml").open("rb") as f:
        return tomllib.load(f)


def test_manifest_roster_matches_installer_catalog():
    m = _manifest()
    manifest_caps = set(m["l3"]["capacities"])
    manifest_dss = set(m["l3"]["datastates"])
    live_caps = {c.iri for c in ac._all_capacities()}
    live_dss = {d.iri for d in ac.arc_datastates()}
    assert manifest_caps == live_caps, (
        f"capacity roster drift: only-manifest={manifest_caps - live_caps}, "
        f"only-live={live_caps - manifest_caps}"
    )
    assert manifest_dss == live_dss, (
        f"datastate roster drift: only-manifest={manifest_dss - live_dss}, "
        f"only-live={live_dss - manifest_dss}"
    )


def test_manifest_declares_arc_realm_and_entrypoint():
    m = _manifest()
    assert m["l3"]["installers"] == ["mindsos_arc.capacities:install_arc"]
    assert m["l3"]["allow_new_realm"] == ["arc"]
    assert m["bundle"]["name"] == "arc"


def test_install_arc_is_warm_layer_idempotent():
    cl = CapacityLayer()
    install_text_capacities(cl)
    ac.install_arc(cl)              # cold — installs
    ds1 = len(ensure_datastate_graph(cl.global_metagraph(), strict=cl._strict).nodes)
    ac.install_arc(cl)              # warm — must no-op, not raise
    ds2 = len(ensure_datastate_graph(cl.global_metagraph(), strict=cl._strict).nodes)
    assert ds1 == ds2
