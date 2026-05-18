"""Phase 13 — image-completeness sentinel for the 9 new schema modules.

Per `feedback_new_top_level_package.md` site 3 (sentinel paths) +
Phase 12 PB-13 image-completeness pattern. Verifies that the new
sub-package files exist at ``/app/`` in the runtime image.

A new top-level package was NOT added in Phase 13 (subpackage of
existing `mindsos_knowledge`), so Dockerfile COPY discipline is
satisfied by the existing ``COPY mindsos_knowledge`` directive in
both prod + test stages — verified by Step 0 probe #4.
"""

from __future__ import annotations

import os
import pytest


_PHASE_13_NEW_FILES = (
    "mindsos_knowledge/schemas/__init__.py",
    "mindsos_knowledge/schemas/ontology.py",
    "mindsos_knowledge/schemas/lexicon.py",
    "mindsos_knowledge/schemas/concepts.py",
    "mindsos_knowledge/schemas/alignment.py",
    "mindsos_knowledge/schemas/promoted_pipelines.py",
    "mindsos_knowledge/schemas/task_patterns.py",
    "mindsos_knowledge/schemas/memories.py",
    "mindsos_knowledge/schemas/problem_trace.py",
    "mindsos_knowledge/schemas/capacity_state.py",
)


@pytest.mark.parametrize("rel", _PHASE_13_NEW_FILES)
def test_phase_13_new_modules_present_at_repo_root(rel: str) -> None:
    repo_root = os.environ.get("MINDSOS_REPO_ROOT", "/app")
    full = os.path.join(repo_root, rel)
    assert os.path.exists(full), (
        f"Expected {full} to exist; check Dockerfile COPY discipline + "
        "tests/_shared/sentinel_paths.py inclusion."
    )
