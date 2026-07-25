"""ADR-0183 §am-4 — `local_bootstrap_importer` record prop (Increment 2).

Pure-API coverage for the record-side of the first-run Local-bootstrap
importer. The boot-step behaviour (best-effort invoke, `Stack.
corpus_imports_failed` reporting, warm-Local no-op) needs a live
KnowledgeLayer / boot_brain and is asserted with the repo's fixtures in the
same PR (see the CR RUNBOOK).
"""

from __future__ import annotations

from mindsos_knowledge.schemas.installed_skills import SKILL_INSTALL_RECORD_PROPS
from mindsos_server.skills.records import SkillRecordView


def test_skill_record_view_carries_importer_field():
    v = SkillRecordView(
        iri="installed-skills-v1:record:arc1:1.0:1",
        bundle_name="arc1",
        bundle_version="1.0",
        bundle_digest=None,
        status="installed",
        action="install",
        recorded_at="2026-07-18T00:00:00.000Z",
        seq=1,
        value={},
        local_bootstrap_importer="mindsos_arc.corpus:import_corpus",
    )
    assert v.local_bootstrap_importer == "mindsos_arc.corpus:import_corpus"


def test_skill_record_view_importer_defaults_none():
    v = SkillRecordView(
        iri="installed-skills-v1:record:b:1:1",
        bundle_name="b",
        bundle_version="1",
        bundle_digest=None,
        status="installed",
        action="install",
        recorded_at="2026-07-18T00:00:00.000Z",
        seq=1,
        value={},
    )
    assert v.local_bootstrap_importer is None


def test_advisory_props_include_importer():
    assert "local_bootstrap_importer" in SKILL_INSTALL_RECORD_PROPS
