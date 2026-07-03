from __future__ import annotations

import pytest

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins.text import install_text_capacities
from mindsos_knowledge import ROLE_CONCEPTS, KnowledgeLayer
from mindsos_server.skills import apply_installed_skills, install_skill, parse_manifest
from mindsos_server.skills.verify import (
    DEFECT,
    NEUTRAL,
    _capacity_view,
    _check_chain,
    _check_drift,
    _check_schema,
    render_json,
    verify_bundle,
)
from tests.fixtures.skill_bundle_ref import MANIFEST_PATH
from tests.fixtures.skill_bundle_ref.installer import CAP_REF_SHOUT

PREFIX = "ref-skill-0.1.0:"


@pytest.fixture()
def kl() -> KnowledgeLayer:
    return KnowledgeLayer.bootstrap()


@pytest.fixture()
def cl() -> CapacityLayer:
    layer = CapacityLayer()
    install_text_capacities(layer)
    return layer


@pytest.fixture()
def installed(kl, cl):
    install_skill(parse_manifest(MANIFEST_PATH), kl=kl, cl=cl, current_phase=50)
    return kl, cl


def test_verify_ref_bundle_happy_path(installed):
    kl, cl = installed
    report = verify_bundle(kl, cl, "ref-skill")

    assert report.found
    assert report.bundle_version == "0.1.0"

    atomic = [r for r in report.stored if r.check == 1 and r.subject == CAP_REF_SHOUT]
    assert atomic and atomic[0].severity != DEFECT

    dangling = [r for r in report.stored if r.check == 2 and r.subject == CAP_REF_SHOUT]
    assert dangling and dangling[0].severity != DEFECT

    drift_defects = [r for r in report.stored if r.check == 3 and r.severity == DEFECT]
    assert not drift_defects

    broken_refs = [r for r in report.stored if r.check == 4 and r.severity == DEFECT]
    assert not broken_refs

    assert report.metrics["broken_atomic"] == 0


def test_ref_bundle_l2_conforms_to_schema(installed):
    kl, cl = installed
    roster = {"l2_iris": [n for g in kl.global_metagraph().graphs.values()
                          for n in g.nodes if n.startswith(PREFIX)]}
    results = _check_schema(kl, roster)
    assert results
    assert not [r for r in results if r.severity == DEFECT]


def test_verify_after_persist_reload(kl, cl):
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.persistence.client import InMemoryClient
    from mindsos_core.reconstruction import MetagraphLoader

    install_skill(parse_manifest(MANIFEST_PATH), kl=kl, cl=cl, current_phase=50)

    mg = kl.global_metagraph()
    client = InMemoryClient()
    MetagraphRepository(client).persist(mg)
    reloaded = MetagraphLoader(client).load(mg.metagraph_id)

    kl2 = KnowledgeLayer(global_metagraph=reloaded)
    cl2 = CapacityLayer()
    install_text_capacities(cl2)
    apply_installed_skills(cl2, kl2)

    report = verify_bundle(kl2, cl2, "ref-skill")
    assert report.found
    assert report.metrics["broken_atomic"] == 0
    assert not [r for r in report.stored if r.check == 3 and r.severity == DEFECT]


def test_drift_flags_missing_capacity(installed):
    kl, cl = installed
    view = _capacity_view(cl)
    roster = {
        "l3_capacities": ["capacity:perception:does.not.exist"],
        "l3_datastates": [],
        "l2_iris": [],
    }
    results = _check_drift(kl, view, roster, PREFIX)
    assert any(r.severity == DEFECT and "l3" in r.name for r in results)


def test_chain_is_neutral(installed):
    kl, _ = installed
    results = _check_chain(kl, {"l3_capacities": [CAP_REF_SHOUT]})
    assert results
    assert all(r.severity == NEUTRAL for r in results)
    assert results[0].detail.startswith("mapped:")


def test_schema_flags_bad_node_type(installed):
    kl, _ = installed
    concept_iri = None
    for graph in kl.global_metagraph().graphs.values():
        if graph.role != ROLE_CONCEPTS:
            continue
        for node_id, node in graph.nodes.items():
            if node_id.startswith(PREFIX):
                node.type_name = "NotARealType"
                concept_iri = node_id
                break
    assert concept_iri is not None

    results = _check_schema(kl, {"l2_iris": [concept_iri]})
    assert any(r.severity == DEFECT for r in results)


def test_verify_unknown_bundle_not_found(kl, cl):
    report = verify_bundle(kl, cl, "no-such-bundle")
    assert not report.found
    assert not report.ok()


def test_render_json_shape(installed):
    kl, cl = installed
    payload = render_json(verify_bundle(kl, cl, "ref-skill"))
    assert payload["bundle"] == "ref-skill"
    assert payload["found"] is True
    assert "stored_links" in payload
    assert "metrics" in payload


def test_cli_verify_requires_target():
    from typer.testing import CliRunner

    from mindsos_cli.app import app

    result = CliRunner().invoke(app, ["skill", "verify"])
    assert result.exit_code == 1


def test_cli_verify_refuses_without_falkor(monkeypatch):
    from typer.testing import CliRunner

    import mindsos_cli.commands.skill as skill_cmd
    from mindsos_cli.app import app

    monkeypatch.setattr(
        skill_cmd,
        "_build_kl_and_client",
        lambda: (KnowledgeLayer.bootstrap(), None),
    )
    result = CliRunner().invoke(app, ["skill", "verify", "ref-skill"])
    assert result.exit_code == 1
    assert "unreachable" in result.output.lower()
