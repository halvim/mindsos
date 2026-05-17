"""Tier 13 — Sentinel paths include Phase 11 runtime modules ONLY.

Per PB-16 + `feedback_sentinel_paths_runtime_only.md`:

* Runtime Python modules new in Phase 11 are sentinelled:
  `mindsos_core/schema/migration.py` +
  `mindsos_core/reconstruction/load_report.py`.
* New documentation files (``docs/dev/internals/core.md`` §Phase 11
  +  ``docs/dev/migration-playbook.md``) are NOT sentinelled — they
  live outside the prod/test Docker image's COPY set, so listing
  them caused 4 of 8 B-10-T7 failures.
"""

from __future__ import annotations

from tests._shared.sentinel_paths import SENTINEL_PATHS


def test_sentinel_includes_migration_module() -> None:
    """``mindsos_core/schema/migration.py`` is sentinelled."""
    assert "mindsos_core/schema/migration.py" in SENTINEL_PATHS


def test_sentinel_includes_load_report_module() -> None:
    """``mindsos_core/reconstruction/load_report.py`` is sentinelled."""
    assert "mindsos_core/reconstruction/load_report.py" in SENTINEL_PATHS


def test_sentinel_does_not_include_phase_11_docs() -> None:
    """No docs/ entries for Phase 11 surfaces (PB-16 / RPB-8 lock)."""
    for p in SENTINEL_PATHS:
        assert not p.endswith("migration-playbook.md"), (
            f"docs sentinel forbidden per feedback_sentinel_paths_runtime_only.md: {p}"
        )


def test_sentinel_does_not_include_internals_core_doc() -> None:
    """``docs/dev/internals/core.md`` is not sentinelled."""
    for p in SENTINEL_PATHS:
        assert not p.endswith("internals/core.md"), (
            f"docs sentinel forbidden: {p}"
        )
