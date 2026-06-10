"""Phase 50 (SA-1) — ``mindsos skill`` CLI surface.

Thin verb-level coverage (the lifecycle itself is covered by
``test_skill_install_driver.py``): registration on the root app, the
install/list/activate happy paths against the in-memory fallback KL,
and exit-code policy (1 on reject).

Each verb builds its own KL, so cross-verb state does NOT persist
within a test — the CLI's durable mode is ``--persist`` + Falkor,
exercised at the driver level by ``test_skill_record_falkor_live.py``.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app
from tests.fixtures.skill_bundle_ref import MANIFEST_PATH

runner = CliRunner()


def test_skill_subapp_registered() -> None:
    result = runner.invoke(app, ["skill", "--help"])
    assert result.exit_code == 0
    for verb in ("install", "uninstall", "list", "activate"):
        assert verb in result.stdout


def test_skill_install_json_happy(monkeypatch) -> None:
    # Force the in-memory fallback (no Falkor reach-out from unit tests).
    import mindsos_cli.commands.skill as skill_cmd

    monkeypatch.setattr(
        skill_cmd,
        "_build_kl_and_client",
        lambda: (__import__("mindsos_knowledge").KnowledgeLayer.bootstrap(), None),
    )
    result = runner.invoke(
        app, ["skill", "install", "--manifest", str(MANIFEST_PATH), "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["bundle_name"] == "ref-skill"
    assert payload["no_op"] is False
    assert len(payload["l2_written"]) == 3
    assert payload["persisted"] is False


def test_skill_list_empty(monkeypatch) -> None:
    import mindsos_cli.commands.skill as skill_cmd

    monkeypatch.setattr(
        skill_cmd,
        "_build_kl_and_client",
        lambda: (__import__("mindsos_knowledge").KnowledgeLayer.bootstrap(), None),
    )
    result = runner.invoke(app, ["skill", "list", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"bundles": []}


def test_skill_uninstall_absent_exits_one(monkeypatch) -> None:
    import mindsos_cli.commands.skill as skill_cmd

    monkeypatch.setattr(
        skill_cmd,
        "_build_kl_and_client",
        lambda: (__import__("mindsos_knowledge").KnowledgeLayer.bootstrap(), None),
    )
    result = runner.invoke(app, ["skill", "uninstall", "ghost"])
    assert result.exit_code == 1


def test_skill_activate_empty(monkeypatch) -> None:
    import mindsos_cli.commands.skill as skill_cmd

    monkeypatch.setattr(
        skill_cmd,
        "_build_kl_and_client",
        lambda: (__import__("mindsos_knowledge").KnowledgeLayer.bootstrap(), None),
    )
    result = runner.invoke(app, ["skill", "activate", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"activated": []}
