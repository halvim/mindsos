"""Phase 45 — ``dream_source_episode_iri`` provenance contract.

At Phase 45 there is no live signal-emitting re-execution path (that is
Phase 46/48). This test asserts the **contract**: every dream directive
carries ``source_episode_iri`` — the provenance the L4 dream loop
propagates onto emitted signals as ``dream_source_episode_iri`` at
Phase 48 (Chat B §5.2 / ADR-0162 §6). Live signal tagging is asserted by
``tests/phase_48/test_dream_pipeline_hookup.py`` (future).
"""

from __future__ import annotations

import pathlib

from mindsos_capacity.builtins.dream import (
    DS_DREAM_TASK_REF,
    DreamDirective,
    build_dream_exploration,
    build_dream_maintenance,
    build_dream_retry,
)

_ADR = (
    pathlib.Path(__file__).resolve().parents[2]
    / "docs"
    / "decisions"
    / "adr"
    / "0162-l3-dream-family.md"
)


def _ref(failed: bool) -> dict:
    return {"source_episode_iri": "ep:42", "task_run_iri": "tr:42", "failed": failed}


def test_every_directive_carries_source_episode_iri():
    for build, failed in (
        (build_dream_maintenance, False),
        (build_dream_exploration, False),
        (build_dream_retry, True),
    ):
        directive = build().implementation(**{DS_DREAM_TASK_REF: _ref(failed)})
        assert isinstance(directive, DreamDirective)
        assert directive.source_episode_iri == "ep:42"


def test_retry_replan_injection_also_carries_provenance():
    directive = build_dream_retry().implementation(
        **{DS_DREAM_TASK_REF: _ref(True)}
    )
    assert directive.replan_injection.source_episode_iri == "ep:42"


def test_adr_documents_signal_provenance_field():
    body = _ADR.read_text(encoding="utf-8")
    assert "dream_source_episode_iri" in body
    assert "source_episode_iri" in body
