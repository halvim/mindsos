"""Phase 39 atomic-rename sentinel — D-L2-16 grep-zero criterion.

Asserts retired identifier surfaces are absent from the shipped
mindsos_*/ tree. Catches accidental re-introduction at later phases.
"""

from __future__ import annotations

from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SOURCE_DIRS = (
    "mindsos_core",
    "mindsos_knowledge",
    "mindsos_capacity",
    "mindsos_cli",
    "mindsos_server",
    "mindsos_admin",
    "mindsos_instances",
)


def _grep_source_tree(pattern: str) -> list[str]:
    """Return ``<path>:<line>`` strings for every occurrence of ``pattern``."""
    hits: list[str] = []
    for sd in _SOURCE_DIRS:
        root = _REPO_ROOT / sd
        if not root.exists():
            continue
        for py in root.rglob("*.py"):
            for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                if pattern in line:
                    hits.append(f"{py.relative_to(_REPO_ROOT)}:{i}: {line.strip()}")
    return hits


def test_role_constant_retired_name_absent() -> None:
    """``ROLE_MEMORIES`` identifier is gone from active source tree."""
    hits = _grep_source_tree("ROLE_MEMORIES")
    assert hits == [], (
        f"Retired ROLE_MEMORIES identifier reappeared:\n" + "\n".join(hits)
    )


def test_iri_builder_retired_name_absent() -> None:
    """``memory_iri`` identifier is gone (split into episode_iri +
    memory_composite_iri per ADR-0044 §am-3)."""
    hits = _grep_source_tree("memory_iri")
    # Filter false positives — substrings inside ``memory_iri`` are NONE
    # at the boundary because grep matches literal substring; the only
    # legit substring containment would be ``memory_iri_v2`` etc., none
    # of which ship at Phase 39.
    assert hits == [], (
        f"Retired memory_iri builder identifier reappeared:\n" + "\n".join(hits)
    )


def test_schema_module_retired_path_absent() -> None:
    """Old ``schemas/memories.py`` import/path retired."""
    hits = _grep_source_tree("schemas.memories")
    # Exclude false positives from the new name ``schemas.episodic_memories``.
    real_hits = [h for h in hits if "schemas.episodic_memories" not in h]
    assert real_hits == [], (
        f"Retired schemas/memories module path reappeared:\n" + "\n".join(real_hits)
    )


def test_schema_builder_retired_name_absent() -> None:
    """``build_memories_schema`` factory name retired."""
    hits = _grep_source_tree("build_memories_schema")
    real_hits = [h for h in hits if "build_episodic_memories_schema" not in h]
    assert real_hits == [], (
        f"Retired build_memories_schema factory reappeared:\n"
        + "\n".join(real_hits)
    )


def test_iri_prefix_retired_form_absent() -> None:
    """Old ``memories-`` IRI prefix retired; new form is ``episodic-memories-``."""
    hits = _grep_source_tree("memories-")
    real_hits = [h for h in hits if "episodic-memories-" not in h]
    assert real_hits == [], (
        f"Retired IRI prefix ``memories-`` reappeared:\n" + "\n".join(real_hits)
    )


def test_iri_constants_importable_post_rename() -> None:
    """New identifiers + builders importable from public surface."""
    from mindsos_knowledge import (
        ROLE_EPISODIC_MEMORIES,
        build_episodic_memories_schema,
        episode_iri,
        memory_composite_iri,
    )

    assert ROLE_EPISODIC_MEMORIES == "episodic_memories"
    assert callable(build_episodic_memories_schema)
    assert callable(episode_iri)
    assert callable(memory_composite_iri)


def test_iri_constants_retired_not_importable() -> None:
    """D-L2-16 atomic-hard-rename: no alias/deprecation; old name absent."""
    import mindsos_knowledge

    assert not hasattr(mindsos_knowledge, "ROLE_MEMORIES")
    assert not hasattr(mindsos_knowledge, "memory_iri")
    assert not hasattr(mindsos_knowledge, "build_memories_schema")
